"""
CH 站 — cigarhome.org (Hong Kong)
静态 HTML，价格以 USD 显示（不是 HKD），仅盒装价格。
商品列表在首页，商品详情页有支数信息。
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

BASE = "https://www.cigarhome.org"


def _parse_listing(html: str) -> list[tuple[str, str, float]]:
    """返回 [(url, raw_name, box_price), ...]"""
    results = []
    blocks = re.findall(
        r'<a[^>]*href="(/goods/\d+\.html)"[^>]*>.*?'
        r'class="product-title">([^<]+)</div>.*?'
        r'class="product-price">([^<]+)</div>',
        html, re.DOTALL,
    )
    for url, name, price_text in blocks:
        price_m = re.search(r"(\d+(?:[.,]\d+)?)", price_text)
        if price_m:
            results.append((
                BASE + url,
                name.strip(),
                float(price_m.group(1).replace(",", "")),
            ))
    return results


async def _fetch_box_count(client: httpx.AsyncClient, url: str) -> int | None:
    try:
        r = await client.get(url)
        m = re.search(r'規格\(支\).*?<span class="param-value">(\d+)</span>', r.text, re.DOTALL)
        return int(m.group(1)) if m else None
    except Exception:
        return None


@register
class CigarHomeScraper(BaseScraper):
    source_slug = "cigarhome"

    async def scrape(self) -> list[ScrapedItem]:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            r = await client.get(BASE + "/")
            listings = _parse_listing(r.text)

            sem = asyncio.Semaphore(4)

            async def _fetch_item(url: str, name: str, price: float) -> ScrapedItem:
                async with sem:
                    box_count = await _fetch_box_count(client, url)
                    return ScrapedItem(
                        source_slug  = self.source_slug,
                        raw_name     = name,
                        product_url  = url,
                        price_single = None,
                        price_box    = price,
                        box_count    = box_count,
                        currency     = "USD",
                        in_stock     = True,
                    )

            results = await asyncio.gather(*[_fetch_item(u, n, p) for u, n, p in listings])
            return list(results)
