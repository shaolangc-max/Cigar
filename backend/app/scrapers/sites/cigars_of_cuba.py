"""
瑞士 Coc 站 — cigars-of-cuba.com (自建平台, schema.org, EUR/CHF)
按品牌爬取: /cigars/{brand}?cur=EUR
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

BASE = "https://www.cigars-of-cuba.com"

CUBAN_BRANDS = [
    "cohiba", "bolivar", "montecristo", "romeo-y-julieta", "partagas",
    "hoyo-de-monterrey", "trinidad", "h-upmann", "punch", "diplomaticos",
    "cuaba", "fonseca", "vegas-robaina", "ramon-allones", "san-cristobal",
    "por-larranaga", "rafael-gonzalez", "el-rey-del-mundo",
    "quai-dorsay", "juan-lopez", "guantanamera", "saint-luis-rey",
]

_ARTICLE_RE = re.compile(r'<article[^>]*product-item[^>]*>(.*?)</article>', re.DOTALL)
_NAME_RE    = re.compile(r'itemprop="name"[^>]*>([^<]+)<')
_HREF_RE    = re.compile(r'<a[^>]*href="(https?://[^"]+)"')
_PRICE_RE   = re.compile(r'itemprop="price"\s+content="([^"]+)"')
_CURR_RE    = re.compile(r'itemprop="priceCurrency"\s+content="([^"]+)"')
_AVAIL_RE   = re.compile(r'itemprop="availability"\s+content="([^"]+)"', re.I)
_QTY_RE     = re.compile(r"[-–]\s*(?:Box of |Boite de )?(\d+)\s*(?:Cigars?|pcs?|st\.)?(?:\s|$)", re.I)


@register
class CigarsOfCubaScraper(BaseScraper):
    source_slug = "cigars-of-cuba"

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen: set[str] = set()

        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            sem = asyncio.Semaphore(3)

            async def fetch_brand(brand: str):
                async with sem:
                    url = f"{BASE}/cigars/{brand}?cur=EUR&limit=200"
                    # 品牌名用于前缀（如 "cohiba" → "Cohiba"）
                    brand_prefix = brand.replace("-", " ").title()
                    try:
                        r = await client.get(url)
                        html = r.text
                    except Exception:
                        return

                    for art in _ARTICLE_RE.findall(html):
                        name_m  = _NAME_RE.search(art)
                        price_m = _PRICE_RE.search(art)
                        curr_m  = _CURR_RE.search(art)
                        href_m  = _HREF_RE.search(art)
                        avail_m = _AVAIL_RE.search(art)
                        if not (name_m and price_m):
                            continue

                        product_url = href_m.group(1) if href_m else None
                        if product_url and product_url in seen:
                            continue
                        if product_url:
                            seen.add(product_url)

                        raw = name_m.group(1).strip()
                        # 若名称不含品牌，补全前缀以提升匹配率
                        name = raw if raw.lower().startswith(brand.split("-")[0]) else f"{brand_prefix} {raw}"
                        try:
                            price = float(price_m.group(1))
                        except ValueError:
                            continue
                        currency = curr_m.group(1) if curr_m else "EUR"

                        avail = avail_m.group(1) if avail_m else ""
                        in_stock = "OutOfStock" not in avail

                        # URL 优先（结构化、无歧义），再回退到名称正则
                        url_qty = re.search(r'(?:box|cabinet|slb|pack)-of-(\d+)', product_url or '', re.I)
                        name_qty = _QTY_RE.search(name)
                        # 名称正则加合理性检查：过滤年份等误匹配（>200 不可能是支数）
                        if name_qty and int(name_qty.group(1)) > 200:
                            name_qty = None
                        box_count_raw = url_qty or name_qty
                        box_count = int(box_count_raw.group(1)) if box_count_raw else None

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
                    await asyncio.sleep(0.2)

            await asyncio.gather(*[fetch_brand(b) for b in CUBAN_BRANDS])

        return items
