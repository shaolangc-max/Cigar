"""
德国C茄 HS — c-cigars.de (Shopify)
EUR 计价，variant 标题为德语。
Einzeln = 单支，Xer Kiste/Schachtel = X支盒装。
"""
from __future__ import annotations
import re
import httpx

from app.scrapers.base import BaseScraper, ScrapedItem
from app.scrapers.registry import register

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

BASE = "https://c-cigars.de"
COLLECTION = "kubanische-zigarren"


def _parse_products(products: list[dict], source_slug: str) -> list[ScrapedItem]:
    items = []
    for p in products:
        title = p.get("title", "")
        handle = p.get("handle", "")
        product_url = f"{BASE}/products/{handle}"
        variants = p.get("variants", [])

        price_single: float | None = None
        price_box:    float | None = None
        box_count:    int   | None = None
        in_stock = False

        for v in variants:
            vt = v.get("title", "")
            try:
                price = float(v.get("price", "0"))
            except ValueError:
                continue

            vt_lower = vt.lower()
            count_m = re.search(r"(\d+)er", vt_lower)
            count   = int(count_m.group(1)) if count_m else 1

            if v.get("available"):
                in_stock = True

            is_single = "einzeln" in vt_lower or count == 1

            if is_single:
                if price_single is None:
                    price_single = price
            elif count > 1:
                # 选最大的标准盒（Kiste优先于Schachtel）
                is_kiste = "kiste" in vt_lower
                if price_box is None or (is_kiste and count > (box_count or 0)):
                    price_box = price
                    box_count = count

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
class CCigarsScraper(BaseScraper):
    source_slug = "c-cigars"

    async def scrape(self) -> list[ScrapedItem]:
        all_items: list[ScrapedItem] = []
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            page = 1
            while True:
                url = f"{BASE}/collections/{COLLECTION}/products.json?limit=250&page={page}"
                try:
                    r = await client.get(url)
                    products = r.json().get("products", [])
                except Exception:
                    break

                if not products:
                    break

                all_items.extend(_parse_products(products, self.source_slug))
                page += 1

        return all_items
