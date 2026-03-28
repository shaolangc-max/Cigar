"""
瑞士 Vip 站 — vipcigars.com (自建平台, GTM dataLayer, EUR/CHF)
从每个古巴品牌页面的 view_item_list dataLayer 抽取产品和价格。
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

BASE = "https://www.vipcigars.com"

CUBAN_BRANDS = [
    "cohiba", "bolivar", "montecristo", "romeo-y-julieta", "partagas",
    "hoyo-de-monterrey", "trinidad", "h-upmann", "punch", "diplomaticos",
    "cuaba", "fonseca", "vegas-robaina", "ramon-allones", "san-cristobal",
    "por-larranaga", "el-rey-del-mundo", "quai-dorsay", "guantanamera",
    "saint-luis-rey", "juan-lopez", "rafael-gonzalez",
]

# dataLayer 中的 view_item_list 块
_BLOCK_RE  = re.compile(r'event:\s*"view_item_list"(.*?)\}\s*\)\s*;', re.DOTALL)
_ITEM_RE   = re.compile(
    r'item_name:\s*"([^"]+)".*?price:\s*([\d.]+).*?in_stock:\s*"([^"]+)"',
    re.DOTALL,
)
_CURR_RE   = re.compile(r'currency:\s*"([A-Z]{3})"')
_QTY_RE    = re.compile(r"(?:Box of |Boite de |Pack of )?(\d+)\s*(?:Cigars?|pcs?|st\.)?(?:\s|$)", re.I)


def _parse_qty(name: str) -> int | None:
    # Name format: "Xxx - Box of 25" or "Xxx Box of 10" or "Xxx 25s"
    m = re.search(r"(?:box\s*of|pack\s*of|boite\s*de)\s*(\d+)", name, re.I)
    if m:
        return int(m.group(1))
    # "25 Cigars" in name
    m2 = re.search(r"(\d+)\s*Cigars?", name, re.I)
    if m2:
        return int(m2.group(1))
    return None


@register
class VipCigarsScraper(BaseScraper):
    source_slug = "vipcigars"

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen: set[str] = set()

        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            sem = asyncio.Semaphore(3)

            async def fetch_brand(brand: str):
                async with sem:
                    url = f"{BASE}/cuban-cigars/{brand}"
                    brand_prefix = brand.replace("-", " ").title()
                    try:
                        r = await client.get(url)
                        html = r.text
                    except Exception:
                        return

                    block_m = _BLOCK_RE.search(html)
                    if not block_m:
                        return

                    block = block_m.group(1)
                    currency = (_CURR_RE.search(html) or re.search(r'currency:\s*"([A-Z]{3})"', block))
                    currency_str = currency.group(1) if currency else "EUR"

                    for item_m in _ITEM_RE.finditer(block):
                        raw  = item_m.group(1).strip()
                        # 若名称不含品牌，补全前缀
                        name = raw if raw.lower().startswith(brand.split("-")[0]) else f"{brand_prefix} {raw}"
                        price    = float(item_m.group(2))
                        in_stock = item_m.group(3) == "1"

                        if name in seen:
                            continue
                        seen.add(name)

                        qty = _parse_qty(name)
                        product_url = f"{url}/{name.lower().replace(' ', '-').replace('/', '')}"

                        items.append(ScrapedItem(
                            source_slug=self.source_slug,
                            raw_name=name,
                            product_url=None,   # no reliable URL from dataLayer
                            price_single=None if (qty and qty > 1) else price,
                            price_box=price if (qty and qty > 1) else None,
                            box_count=qty,
                            currency=currency_str,
                            in_stock=in_stock,
                        ))
                    await asyncio.sleep(0.3)

            await asyncio.gather(*[fetch_brand(b) for b in CUBAN_BRANDS])

        return items
