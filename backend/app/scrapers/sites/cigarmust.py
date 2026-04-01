"""
瑞士卢加诺 LCDH — cigarmust.com (PrestaShop, CHF)
Cuban Habanos category id: 170
"""
from __future__ import annotations
import re
import asyncio
import httpx

from app.scrapers.base import BaseScraper, ScrapedItem
from app.scrapers.registry import register

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

BASE = "https://cigarmust.com"
CATEGORY_URL = f"{BASE}/en/170-cuban-habanos?resultsPerPage=100"

_ARTICLE_RE = re.compile(r'(<article[^>]*>)(.*?)</article>', re.DOTALL)
_STOCK_RE   = re.compile(r'x-data-product-quantity="(\d*)"')
_NAME_RE    = re.compile(r'itemprop="name"[^>]*><a href="([^"]+)"[^>]*>([^<]+)<')
_PRICE_RE   = re.compile(r'itemprop="price"\s+content="([^"]+)"')
_CURR_RE    = re.compile(r'itemprop="priceCurrency"\s+content="([^"]+)"')
_QTY_RE      = re.compile(r"(\d+)\s*(?:pcs|cigars?|stück|er\s*kiste|box)", re.I)
# 产品详情页 select option，如 "Box 12 Pcs." 或 "box_12_pcs"
_PAGE_BOX_RE   = re.compile(r'(?:box|humidor|book)[_\s-]+(\d+)[_\s-]*pcs', re.I)
# 加湿盒/礼盒展示套装 — 跳过
_SKIP_NAME_RE  = re.compile(r'\b(?:humidor[e]?|cabinet\s+selection|lugano\s+humidor)\b', re.I)
_SKIP_URL_RE   = re.compile(r'humidor', re.I)
_PAGE_RE     = re.compile(r'resultsPerPage=100&page=(\d+)')
_URL_QTY_RE  = re.compile(r"-(\d+)(?:\.html)?$")
_KNOWN_SIZES = {3, 5, 10, 12, 15, 20, 25, 40, 50}


def _count_from_url(url: str) -> int | None:
    if "slb" in url.lower():
        return 25
    m = _URL_QTY_RE.search(url)
    if m:
        n = int(m.group(1))
        if n in _KNOWN_SIZES:
            return n
    return None


@register
class CigarmustScraper(BaseScraper):
    source_slug = "cigarmust"

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        page = 1

        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            while True:
                url = CATEGORY_URL if page == 1 else f"{CATEGORY_URL}&page={page}"
                try:
                    r = await client.get(url)
                    html = r.text
                except Exception:
                    break

                articles = _ARTICLE_RE.findall(html)
                if not articles:
                    break

                for tag, body in articles:
                    name_m  = _NAME_RE.search(body)
                    price_m = _PRICE_RE.search(body)
                    curr_m  = _CURR_RE.search(body)
                    if not (name_m and price_m):
                        continue

                    raw_url     = name_m.group(1)
                    fragment    = raw_url.split("#")[1] if "#" in raw_url else ""
                    product_url = raw_url.split("#")[0]
                    name    = name_m.group(2).strip()
                    if _SKIP_NAME_RE.search(name) or _SKIP_URL_RE.search(raw_url):
                        continue
                    try:
                        price = float(price_m.group(1))
                    except ValueError:
                        continue
                    currency = curr_m.group(1) if curr_m else "CHF"

                    stock_m = _STOCK_RE.search(tag)
                    in_stock = bool(stock_m and stock_m.group(1) not in ("", "0"))

                    qty_m = _QTY_RE.search(name)
                    box_count = int(qty_m.group(1)) if qty_m else None

                    # 名字未匹配到数量时，从 URL 回退提取
                    if box_count is None:
                        box_count = _count_from_url(product_url)
                    # 从 URL fragment 提取：box_25_pcs / book_20_pcs / humidor_88_pcs / box-1pcs
                    if box_count is None and fragment:
                        fm = _PAGE_BOX_RE.search(fragment)
                        if fm:
                            box_count = int(fm.group(1))

                    items.append(ScrapedItem(
                        source_slug=self.source_slug,
                        raw_name=name,
                        product_url=product_url,
                        price_single=None if (box_count and box_count > 1) else price,
                        price_box=price if (box_count and box_count > 1) else None,
                        box_count=box_count,
                        currency=currency,
                        in_stock=in_stock,
                    ))

                # 下一页
                if f"page={page + 1}" not in html and f"resultsPerPage=100&page={page+1}" not in html:
                    break
                page += 1
                await asyncio.sleep(0.3)

        # 对 box_count 仍未知且价格偏高的条目，补访产品详情页
        sem = asyncio.Semaphore(3)
        async def enrich(item, client_inner):
            if item.box_count is None and (item.price_single or 0) > 200:
                async with sem:
                    try:
                        rp = await client_inner.get(item.product_url)
                        m  = _PAGE_BOX_RE.search(rp.text)
                        if m:
                            bc = int(m.group(1))
                            item.price_box    = item.price_single
                            item.price_single = None
                            item.box_count    = bc
                    except Exception:
                        pass
                    await asyncio.sleep(0.2)

        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client2:
            await asyncio.gather(*[enrich(it, client2) for it in items])

        return items
