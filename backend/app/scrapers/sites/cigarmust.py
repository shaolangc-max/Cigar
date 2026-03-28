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
_QTY_RE     = re.compile(r"(\d+)\s*(?:pcs|cigars?|stück|er\s*kiste|box)", re.I)
_PAGE_RE    = re.compile(r'resultsPerPage=100&page=(\d+)')


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

                    product_url = name_m.group(1).split("#")[0]  # strip variant fragment
                    name    = name_m.group(2).strip()
                    try:
                        price = float(price_m.group(1))
                    except ValueError:
                        continue
                    currency = curr_m.group(1) if curr_m else "CHF"

                    stock_m = _STOCK_RE.search(tag)
                    in_stock = bool(stock_m and stock_m.group(1) not in ("", "0"))

                    qty_m = _QTY_RE.search(name)
                    box_count = int(qty_m.group(1)) if qty_m else None

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

        return items
