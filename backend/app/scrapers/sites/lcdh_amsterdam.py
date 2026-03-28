"""
荷兰阿姆斯特丹 LCDH — lcdh-amsterdam.com (OpenCart, EUR)
分类路径: path=59_<brand_id>
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

BASE = "https://lcdh-amsterdam.com"

# (subcategory_id, brand_hint) — 主要古巴品牌
BRAND_CATS = [
    64, 66, 67, 71, 78, 79, 80, 81, 82, 85,
    86, 87, 89, 90, 91, 92, 93, 94, 95, 96,
    70, 75, 76, 77, 72, 103, 104, 116, 119,
]

_PRICE_RE = re.compile(r"€\s*([\d.,]+)")
_QTY_RE   = re.compile(r"(\d+)\s*(?:Cigars?|stuks?|st\.|box|Stück|er\s*Kiste)", re.I)


def _parse_eur(text: str) -> float | None:
    m = _PRICE_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


@register
class LcdhAmsterdamScraper(BaseScraper):
    source_slug = "lcdh-amsterdam"

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            sem = asyncio.Semaphore(3)

            async def fetch_brand(cat_id: int):
                async with sem:
                    page = 1
                    while True:
                        url = (
                            f"{BASE}/index.php?route=product/category"
                            f"&path=59_{cat_id}&limit=100&page={page}"
                        )
                        try:
                            r = await client.get(url)
                            html = r.text
                        except Exception:
                            break

                        # product-thumb blocks
                        blocks = re.findall(
                            r'product-thumb">(.*?)</div>\s*</div>\s*</div>',
                            html, re.DOTALL,
                        )
                        if not blocks:
                            break

                        for block in blocks:
                            name_m = re.search(r'<h4><a href="([^"]+)">([^<]+)</a></h4>', block)
                            price_m = re.search(r'<p class="price">\s*(.*?)\s*<', block, re.DOTALL)
                            if not (name_m and price_m):
                                continue

                            product_url = name_m.group(1).replace("&amp;", "&")
                            name = name_m.group(2).strip()
                            price = _parse_eur(price_m.group(1))
                            if price is None:
                                continue

                            qty = _QTY_RE.search(name)
                            box_count = int(qty.group(1)) if qty else None

                            items.append(ScrapedItem(
                                source_slug=self.source_slug,
                                raw_name=name,
                                product_url=product_url,
                                price_single=None if (box_count and box_count > 1) else price,
                                price_box=price if (box_count and box_count > 1) else None,
                                box_count=box_count,
                                currency="EUR",
                                in_stock=True,
                            ))

                        # 检查是否有下一页
                        if f"page={page + 1}" not in html:
                            break
                        page += 1
                        await asyncio.sleep(0.2)

            await asyncio.gather(*[fetch_brand(cid) for cid in BRAND_CATS])

        return items
