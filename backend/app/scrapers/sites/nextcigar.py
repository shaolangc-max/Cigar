"""
NEXT 站 — nextcigar.com (Hong Kong, Shopify)
Shopify JSON API，HKD 计价，仅有盒装价格。
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

BASE = "https://www.nextcigar.com"

# 古巴雪茄相关 collections
COLLECTIONS = [
    "cuban-cigars",
]


@register
class NextCigarScraper(BaseScraper):
    source_slug = "nextcigar"

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            for collection in COLLECTIONS:
                page = 1
                while True:
                    url = f"{BASE}/collections/{collection}/products.json?limit=250&page={page}"
                    try:
                        r = await client.get(url)
                        data = r.json()
                    except Exception:
                        break

                    products = data.get("products", [])
                    if not products:
                        break

                    for p in products:
                        for v in p.get("variants", []):
                            title     = p.get("title", "")
                            v_title   = v.get("title", "Default Title")
                            price_raw = v.get("price", "0")
                            try:
                                price = float(price_raw)
                            except ValueError:
                                continue

                            count_m   = re.search(r"(\d+)\s*Cigars?", v_title, re.I)
                            box_count = int(count_m.group(1)) if count_m else None
                            is_stick  = (
                                "stick" in v_title.lower()
                                or "single" in v_title.lower()
                                or (box_count is not None and box_count == 1)
                            )

                            product_url = f"{BASE}/products/{p.get('handle', '')}"
                            items.append(ScrapedItem(
                                source_slug  = self.source_slug,
                                raw_name     = title,
                                product_url  = product_url,
                                price_single = price if is_stick else None,
                                price_box    = price if not is_stick else None,
                                box_count    = box_count if not is_stick else None,
                                currency     = "USD",
                                in_stock     = (v.get("inventory_quantity") or 0) > 0,
                            ))

                    page += 1

        return items
