"""
瑞士维拉斯 HS — cigarviu.com (Shopify, CHF)
Collection: cuba
Variant titles in German/mixed: Einzeln / Xer Kiste
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

BASE       = "https://cigarviu.com"
COLLECTION = "cuba"

_COUNT_RE = re.compile(r"(\d+)\s*(?:er|x)?\s*(?:kiste|schachtel|cigars?|stück|box|pack)", re.I)


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
            count     = int(count_m.group(1)) if count_m else None
            is_single = (
                "einzeln" in vt_lower
                or "single" in vt_lower
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

        if price_single is not None or price_box is not None:
            items.append(ScrapedItem(
                source_slug  = source_slug,
                raw_name     = title,
                product_url  = product_url,
                price_single = price_single,
                price_box    = price_box,
                box_count    = box_count,
                currency     = "CHF",
                in_stock     = in_stock,
            ))
    return items


@register
class CigarViuScraper(BaseScraper):
    source_slug = "cigarviu"

    async def scrape(self) -> list[ScrapedItem]:
        all_items: list[ScrapedItem] = []
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            page = 1
            while True:
                url = f"{BASE}/collections/{COLLECTION}/products.json?limit=250&page={page}"
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
