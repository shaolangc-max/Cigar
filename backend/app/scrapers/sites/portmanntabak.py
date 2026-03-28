"""
瑞士圣加伦 LCDH — lcdh.portmanntabak.ch (PrestaShop, CHF)
分类: /3-zigarren (含非古巴雪茄，通过 URL 路径 /Kuba/ 过滤)
价格格式: 欧式（逗号为小数点，点为千位分隔）如 3.150,00 CHF
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

BASE         = "https://lcdh.portmanntabak.ch"
CATEGORY_URL = f"{BASE}/3-zigarren?resultsPerPage=100"

_ARTICLE_RE = re.compile(r'<article[^>]*>(.*?)</article>', re.DOTALL)
_TITLE_RE   = re.compile(
    r'product-title[^>]*>\s*<a\s+href="([^"]+)"[^>]*>([^<]+)</a>',
    re.DOTALL,
)
_PRICE_RE   = re.compile(r'class="price"[^>]*>\s*([\d.,]+)\s*CHF', re.DOTALL)
_QTY_RE     = re.compile(r"(\d+)\s*(?:pcs|cigars?|stück|er\s*kiste|box)", re.I)


def _eu_price(raw: str) -> float | None:
    """欧式价格: 3.150,00 → 3150.0"""
    raw = raw.strip()
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


@register
class PortmannTabakScraper(BaseScraper):
    source_slug = "portmanntabak"

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        page = 1

        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            while True:
                url = CATEGORY_URL if page == 1 else f"{CATEGORY_URL}&page={page}"
                try:
                    r    = await client.get(url)
                    html = r.text
                except Exception:
                    break

                articles = _ARTICLE_RE.findall(html)
                if not articles:
                    break

                for body in articles:
                    title_m = _TITLE_RE.search(body)
                    price_m = _PRICE_RE.search(body)
                    if not (title_m and price_m):
                        continue

                    product_url = title_m.group(1)
                    name        = title_m.group(2).strip()

                    # 仅保留古巴产品（URL 包含 /Kuba/ 路径）
                    if "/Kuba/" not in product_url and "/kuba/" not in product_url:
                        continue

                    price = _eu_price(price_m.group(1))
                    if price is None or price <= 0:
                        continue

                    # 库存: PrestaShop 缺货时通常有 "out-of-stock" 类
                    in_stock = "out-of-stock" not in body.lower()

                    qty_m     = _QTY_RE.search(name)
                    box_count = int(qty_m.group(1)) if qty_m else None

                    items.append(ScrapedItem(
                        source_slug  = self.source_slug,
                        raw_name     = name,
                        product_url  = product_url,
                        price_single = None if (box_count and box_count > 1) else price,
                        price_box    = price if (box_count and box_count > 1) else None,
                        box_count    = box_count,
                        currency     = "CHF",
                        in_stock     = in_stock,
                    ))

                if f"page={page + 1}" not in html:
                    break
                page += 1
                await asyncio.sleep(0.3)

        return items
