"""
布鲁塞尔 LCDH — lacasadelhabano.brussels (Shopify, EUR)
全品类古巴雪茄，使用 /products.json 遍历。
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

BASE = "https://lacasadelhabano.brussels"

_COUNT_RE = re.compile(
    r"(\d+)\s*(?:er|x)?\s*(?:kiste|schachtel|cigars?|stück|box|pack|pcs|stuks?)"
    r"|(?:box|coffret|boite|kiste|schachtel)\s+(?:of|de|von)\s*(\d+)",
    re.I,
)
# Brussels 惯例：标题中用 /数量 标注支数，如 "COHIBA X /10 LIMITED EDITION"
_SLASH_COUNT_RE = re.compile(r"/(\d+)")
_KNOWN_SIZES    = {3, 5, 10, 12, 15, 20, 25, 40, 50}


def _count_from_title(title: str) -> int | None:
    """从标题的 /数量 格式提取支数，仅认已知盒型尺寸。"""
    for m in _SLASH_COUNT_RE.finditer(title):
        n = int(m.group(1))
        if n in _KNOWN_SIZES:
            return n
    return None


def _parse(products: list[dict], source_slug: str) -> list[ScrapedItem]:
    items = []
    for p in products:
        title       = p.get("title", "")
        handle      = p.get("handle", "")
        product_url = f"{BASE}/products/{handle}"
        variants    = p.get("variants", [])

        price_single: float | None = None
        price_box:    float | None = None
        box_count:    int   | None = None
        in_stock = False

        for v in variants:
            vt = v.get("title", "Default Title")
            try:
                price = float(v.get("price", "0"))
            except ValueError:
                continue

            if v.get("available") is not False:
                in_stock = True

            vt_lower  = vt.lower()
            count_m   = _COUNT_RE.search(vt_lower)
            count     = int(count_m.group(1) or count_m.group(2)) if count_m else None
            is_single = (
                "einzeln" in vt_lower
                or "single" in vt_lower
                or "stuk" in vt_lower
                or "pièce" in vt_lower
                or vt_lower in ("default title", "1")
                or (count is not None and count == 1)
            )

            if is_single:
                if price_single is None:
                    price_single = price
            elif count and count > 1:
                if price_box is None or count > (box_count or 0):
                    price_box = price
                    box_count = count
            else:
                if price_single is None:
                    price_single = price

        # 变体标题为 Default Title 时，从产品标题的 /数量 格式回退提取
        if box_count is None and price_single is not None:
            n = _count_from_title(title)
            if n:
                box_count    = n
                price_box    = price_single
                price_single = None

        if price_single is not None or price_box is not None:
            items.append(ScrapedItem(
                source_slug  = source_slug,
                raw_name     = title,
                product_url  = product_url,
                price_single = price_single,
                price_box    = price_box,
                box_count    = box_count,
                currency     = "EUR",
                in_stock     = in_stock,
            ))
    return items


@register
class LcdhBrusselsScraper(BaseScraper):
    source_slug = "lcdh-brussels"

    async def scrape(self) -> list[ScrapedItem]:
        all_items: list[ScrapedItem] = []
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            page = 1
            while True:
                url = f"{BASE}/products.json?limit=250&page={page}"
                try:
                    r        = await client.get(url)
                    products = r.json().get("products", [])
                except Exception:
                    break
                if not products:
                    break
                all_items.extend(_parse(products, self.source_slug))
                page += 1
                await asyncio.sleep(0.3)
        return all_items
