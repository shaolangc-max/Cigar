"""
德国雪茄世界 — cigarworld.de
静态 HTML，EUR 计价。
目录结构: /zigarren/kuba/{category}
注：详情页为 SPA，无法解析盒装价格，仅采集列表页单支价格。
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

BASE = "https://www.cigarworld.de"

CUBAN_CATEGORIES = [
    "/zigarren/kuba/anejados",
    "/zigarren/kuba/anos-chinos",
    "/zigarren/kuba/especiales",
    "/zigarren/kuba/exclusivos-lcdh",
    "/zigarren/kuba/gran-reservas",
    "/zigarren/kuba/limitadas",
    "/zigarren/kuba/regionales",
    "/zigarren/kuba/regulares",
    "/zigarren/kuba/reservas",
]


def _parse_listing(html: str) -> list[tuple[str, str, float, bool]]:
    """返回 [(url, raw_name, price_single, in_stock), ...]"""
    results = []
    items = re.findall(
        r'<a class="search-result-item-inner" href="([^"]+)"[^>]*>(.*?)</a>',
        html, re.DOTALL,
    )
    for href, content in items:
        brand = re.search(r'class="brand">([^<]+)', content)
        name  = re.search(r'class="name">([^<]+)', content)
        price = re.search(r'data-eurval="([^"]+)"', content)
        avail = re.search(r'item-availability--(\d+)', content)

        b = brand.group(1).strip() if brand else ""
        n = name.group(1).strip() if name else ""
        raw_name = f"{b} {n}".strip() if b else n
        p = float(price.group(1)) if price else None
        in_stock = avail and avail.group(1) == "1"

        if raw_name and p:
            url = BASE + href if href.startswith("/") else href
            results.append((url, raw_name, p, bool(in_stock)))
    return results


@register
class CigarWorldScraper(BaseScraper):
    source_slug = "cigarworld"

    async def scrape(self) -> list[ScrapedItem]:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            listing_items: dict[str, dict] = {}
            sem = asyncio.Semaphore(3)

            async def _fetch_cat(cat_path: str):
                async with sem:
                    try:
                        r = await client.get(BASE + cat_path)
                        for url, name, price, ok in _parse_listing(r.text):
                            if url not in listing_items:
                                listing_items[url] = {
                                    "name": name,
                                    "price_single": price,
                                    "in_stock": ok,
                                }
                    except Exception:
                        pass

            await asyncio.gather(*[_fetch_cat(c) for c in CUBAN_CATEGORIES])

            return [
                ScrapedItem(
                    source_slug  = self.source_slug,
                    raw_name     = info["name"],
                    product_url  = url,
                    price_single = info["price_single"],
                    price_box    = None,
                    box_count    = None,
                    currency     = "EUR",
                    in_stock     = info["in_stock"],
                )
                for url, info in listing_items.items()
            ]
