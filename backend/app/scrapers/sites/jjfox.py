"""
英国狐狸 LCDH — jjfox.co.uk (Magento 2 GraphQL, GBP)
分类: Cuban Cigars (uid=MjY=)
库存状态：GraphQL 不暴露 stock_status，从产品页 xnotif JSON 解析。
  xnotif 格式：{"<value_index>": {"is_in_stock": true/false, ...}, ...}
  configurable_options.values 提供 label → value_index 的映射。
"""
from __future__ import annotations
import re
import json
import asyncio
import httpx

from app.scrapers.base import BaseScraper, ScrapedItem
from app.scrapers.registry import register

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
}

BASE          = "https://www.jjfox.co.uk"
CATEGORY_UID  = "MjY="   # Cuban Cigars
PAGE_SIZE     = 50

QUERY = """
{
  products(
    filter: { category_uid: { eq: "%s" } }
    pageSize: %d
    currentPage: %d
  ) {
    total_count
    items {
      name
      url_key
      ... on ConfigurableProduct {
        configurable_options {
          values { label value_index }
        }
        variants {
          product {
            price_range {
              minimum_price {
                regular_price { value currency }
              }
            }
          }
          attributes { label }
        }
      }
      price_range {
        minimum_price {
          regular_price { value currency }
        }
      }
    }
  }
}
"""

_QTY_RE       = re.compile(r"(\d+)\s*(?:er\s*Kiste|er\s*Box|Stück|Cigars?|pack|x\s+\d+)", re.I)
_BOX_LABEL_RE = re.compile(r"BOX\s+OF\s+(\d+)", re.I)
# is_in_stock 始终是 xnotif 每个条目的第一个 key，直接匹配 "value_index":{"is_in_stock":...}
_STOCK_RE = re.compile(r'"(\d+)"\s*:\s*\{\s*"is_in_stock"\s*:\s*(true|false)')


def _parse_xnotif(html: str) -> dict[int, bool]:
    """返回 {value_index: is_in_stock}，从产品页 xnotif JSON 解析库存。"""
    idx = html.find('"xnotif"')
    if idx == -1:
        return {}
    # 在 xnotif 后 5000 字符内匹配所有条目（含 HTML 的值不影响首 key 匹配）
    window = html[idx: idx + 5000]
    return {int(k): (v == "true") for k, v in _STOCK_RE.findall(window)}


@register
class JJFoxScraper(BaseScraper):
    source_slug = "jjfox"

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        page = 1
        # 收集所有 configurable 产品，供第二步批量抓库存页
        configurable_products: list[dict] = []
        simple_products: list[dict] = []

        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:

            # ── 第一步：GraphQL 分页获取所有产品 ──────────────────────────────
            while True:
                query = json.dumps({"query": QUERY % (CATEGORY_UID, PAGE_SIZE, page)})
                try:
                    r    = await client.post(f"{BASE}/graphql", content=query)
                    data = r.json()["data"]["products"]
                except Exception:
                    break

                for p in data["items"]:
                    url_key = p.get("url_key", "")
                    if p.get("variants"):
                        configurable_products.append(p)
                    else:
                        simple_products.append(p)

                total = data["total_count"]
                if page * PAGE_SIZE >= total:
                    break
                page += 1
                await asyncio.sleep(0.3)

            # ── 第二步：并发抓产品页，解析 xnotif 库存数据 ────────────────────
            stock_cache: dict[str, dict[int, bool]] = {}  # url_key → {value_index: is_in_stock}
            sem = asyncio.Semaphore(3)

            async def _fetch_stock(url_key: str):
                async with sem:
                    try:
                        r = await client.get(f"{BASE}/{url_key}.html",
                                             headers={"User-Agent": HEADERS["User-Agent"]})
                        stock_cache[url_key] = _parse_xnotif(r.text)
                        await asyncio.sleep(0.2)
                    except Exception:
                        stock_cache[url_key] = {}

            await asyncio.gather(*[
                _fetch_stock(p["url_key"])
                for p in configurable_products
                if p.get("url_key")
            ])

            # ── 第三步：组装 ScrapedItem ──────────────────────────────────────
            for p in configurable_products:
                name        = p["name"]
                url_key     = p.get("url_key", "")
                product_url = f"{BASE}/{url_key}.html" if url_key else None

                # label → value_index 映射（来自 configurable_options）
                label_to_vidx: dict[str, int] = {}
                for opt in (p.get("configurable_options") or []):
                    for v in (opt.get("values") or []):
                        if v.get("label") and v.get("value_index") is not None:
                            label_to_vidx[v["label"]] = v["value_index"]

                stock_map = stock_cache.get(url_key, {})

                for v in p.get("variants") or []:
                    label     = v["attributes"][0]["label"] if v.get("attributes") else ""
                    price_obj = v["product"]["price_range"]["minimum_price"]["regular_price"]
                    price     = price_obj["value"]
                    currency  = price_obj["currency"]

                    # 查库存：label → value_index → is_in_stock
                    vidx     = label_to_vidx.get(label)
                    in_stock = stock_map.get(vidx, True) if vidx is not None else True

                    box_m = _BOX_LABEL_RE.search(label)
                    qty_m = _QTY_RE.search(label) or _QTY_RE.search(name)
                    if box_m:
                        items.append(ScrapedItem(
                            source_slug  = self.source_slug,
                            raw_name     = name,
                            product_url  = product_url,
                            price_single = None,
                            price_box    = price,
                            box_count    = int(box_m.group(1)),
                            currency     = currency,
                            in_stock     = in_stock,
                        ))
                    elif qty_m and int(qty_m.group(1)) > 1:
                        items.append(ScrapedItem(
                            source_slug  = self.source_slug,
                            raw_name     = name,
                            product_url  = product_url,
                            price_single = None,
                            price_box    = price,
                            box_count    = int(qty_m.group(1)),
                            currency     = currency,
                            in_stock     = in_stock,
                        ))
                    else:
                        items.append(ScrapedItem(
                            source_slug  = self.source_slug,
                            raw_name     = name,
                            product_url  = product_url,
                            price_single = price,
                            price_box    = None,
                            box_count    = None,
                            currency     = currency,
                            in_stock     = in_stock,
                        ))

            for p in simple_products:
                name        = p["name"]
                url_key     = p.get("url_key", "")
                product_url = f"{BASE}/{url_key}.html" if url_key else None
                price_obj   = p["price_range"]["minimum_price"]["regular_price"]
                price       = price_obj["value"]
                currency    = price_obj["currency"]
                qty_m       = _QTY_RE.search(name)
                qty         = int(qty_m.group(1)) if qty_m else None

                if qty and qty > 1:
                    items.append(ScrapedItem(
                        source_slug  = self.source_slug,
                        raw_name     = name,
                        product_url  = product_url,
                        price_single = None,
                        price_box    = price,
                        box_count    = qty,
                        currency     = currency,
                        in_stock     = True,  # simple product，无 xnotif 数据
                    ))
                else:
                    items.append(ScrapedItem(
                        source_slug  = self.source_slug,
                        raw_name     = name,
                        product_url  = product_url,
                        price_single = price,
                        price_box    = None,
                        box_count    = None,
                        currency     = currency,
                        in_stock     = True,  # simple product，无 xnotif 数据
                    ))

        return items
