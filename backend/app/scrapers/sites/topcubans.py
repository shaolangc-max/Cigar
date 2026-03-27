"""
瑞士 Top 站 — topcubans.com
静态 HTML，schema.org Product markup，价格以 USD 计价。
URL 结构: /cuban-cigars/{brand}
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
    "Accept-Language": "en-US,en;q=0.9",
}

BASE = "https://www.topcubans.com"


def _parse_brand_page(html: str, source_slug: str) -> list[ScrapedItem]:
    chunks = html.split('<article class="columns" itemprop="item"')
    products: dict[str, dict] = {}

    for chunk in chunks[1:]:
        end = chunk.find("</article>")
        chunk = chunk[:end]

        name_m = re.search(
            r'itemprop="name".*?<a[^>]*title="([^"]+)"[^>]*href="([^"]+)"',
            chunk, re.DOTALL,
        )
        price_m = re.search(r'itemprop="lowPrice"\s+content="([^"]+)"', chunk)
        curr_m  = re.search(r'itemprop="priceCurrency"\s+content="([^"]+)"', chunk)
        qty_m   = re.search(
            r'</h1>\s*</div>\s*<div[^>]*>\s*(.*?)\s*</div>', chunk, re.DOTALL
        )

        if not (name_m and price_m):
            continue

        name     = name_m.group(1).strip()
        url      = name_m.group(2).strip()
        price    = float(price_m.group(1))
        currency = curr_m.group(1) if curr_m else "USD"
        qty_text = qty_m.group(1).strip() if qty_m else ""

        if url not in products:
            products[url] = {
                "name": name, "url": url, "currency": currency,
                "price_single": None, "price_box": None, "box_count": None,
            }

        count_m = re.search(r"(\d+)\s+Cigars?", qty_text, re.I)
        count   = int(count_m.group(1)) if count_m else 1
        if count <= 1:
            products[url]["price_single"] = price
        else:
            products[url]["price_box"]   = price
            products[url]["box_count"]   = count

    items = []
    for p in products.values():
        items.append(ScrapedItem(
            source_slug  = source_slug,
            raw_name     = p["name"],
            product_url  = p["url"],
            price_single = p["price_single"],
            price_box    = p["price_box"],
            box_count    = p["box_count"],
            currency     = p["currency"],
            in_stock     = True,
        ))
    return items


@register
class TopCubansScraper(BaseScraper):
    source_slug = "topcubans"

    async def scrape(self) -> list[ScrapedItem]:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            # 1. 品牌列表
            r = await client.get(f"{BASE}/cuban-cigars/")
            brand_urls = list(dict.fromkeys(
                re.findall(
                    r'href="(https://www\.topcubans\.com/cuban-cigars/[a-z][a-z0-9-]+)"',
                    r.text,
                )
            ))

            # 2. 每个品牌页面
            all_items: list[ScrapedItem] = []
            sem = asyncio.Semaphore(3)

            async def _fetch_brand(url: str):
                async with sem:
                    try:
                        resp = await client.get(url)
                        return _parse_brand_page(resp.text, self.source_slug)
                    except Exception:
                        return []

            results = await asyncio.gather(*[_fetch_brand(u) for u in brand_urls])
            for r in results:
                all_items.extend(r)

        return all_items
