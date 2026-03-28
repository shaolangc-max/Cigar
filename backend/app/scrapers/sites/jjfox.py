"""
英国狐狸 LCDH — jjfox.co.uk (Magento 2 GraphQL, GBP)
分类: Cuban Cigars (uid=MjY=)
"""
from __future__ import annotations
import re
import json
import asyncio
import httpx

from app.scrapers.base import BaseScraper, ScrapedItem
from app.scrapers.registry import register

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
}

BASE          = "https://www.jjfox.co.uk"
CATEGORY_UID  = "MjY="   # Cuban Cigars
PAGE_SIZE     = 50

QUERY = """
{
  products(
    filter: { category_uid: { eq: "%s" } }
    pageSize: %d
    currentPage: %d
  ) {
    total_count
    items {
      name
      url_key
      price_range {
        minimum_price {
          regular_price { value currency }
        }
      }
    }
  }
}
"""

_QTY_RE = re.compile(r"(\d+)\s*(?:er\s*Kiste|er\s*Box|Stück|Cigars?|pack|x\s+\d+)", re.I)


@register
class JJFoxScraper(BaseScraper):
    source_slug = "jjfox"

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        page = 1

        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            while True:
                query = json.dumps({"query": QUERY % (CATEGORY_UID, PAGE_SIZE, page)})
                try:
                    r    = await client.post(f"{BASE}/graphql", content=query)
                    data = r.json()["data"]["products"]
                except Exception:
                    break

                for p in data["items"]:
                    name      = p["name"]
                    url_key   = p.get("url_key", "")
                    product_url = f"{BASE}/{url_key}.html" if url_key else None
                    price_obj = p["price_range"]["minimum_price"]["regular_price"]
                    price     = price_obj["value"]
                    currency  = price_obj["currency"]
                    in_stock  = True  # Magento GraphQL stock_status not available on this instance

                    qty_m     = _QTY_RE.search(name)
                    qty       = int(qty_m.group(1)) if qty_m else None

                    if qty and qty > 1:
                        items.append(ScrapedItem(
                            source_slug  = self.source_slug,
                            raw_name     = name,
                            product_url  = product_url,
                            price_single = None,
                            price_box    = price,
                            box_count    = qty,
                            currency     = currency,
                            in_stock     = in_stock,
                        ))
                    else:
                        items.append(ScrapedItem(
                            source_slug  = self.source_slug,
                            raw_name     = name,
                            product_url  = product_url,
                            price_single = price,
                            price_box    = None,
                            box_count    = None,
                            currency     = currency,
                            in_stock     = in_stock,
                        ))

                total = data["total_count"]
                if page * PAGE_SIZE >= total:
                    break
                page += 1
                await asyncio.sleep(0.3)

        return items
