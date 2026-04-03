"""
瑞士 Vip 站 — vipcigars.com (自建平台, GTM dataLayer, EUR/CHF)
从每个古巴品牌页面的 view_item_list dataLayer 抽取产品和价格。
URL 通过 HTML 产品卡片中的 p_id 与 dataLayer item_id 对应获取，无需 slug 匹配。
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
_BLOCK_RE = re.compile(r'event:\s*"view_item_list"(.*?)\}\s*\)\s*;', re.DOTALL)
_ITEM_RE  = re.compile(
    r'item_id:\s*"(\d+)".*?item_name:\s*"([^"]+)".*?price:\s*([\d.]+).*?in_stock:\s*"([^"]+)"',
    re.DOTALL,
)
_CURR_RE  = re.compile(r'currency:\s*"([A-Z]{3})"')

# 从产品卡片 HTML 提取 p_id → URL
_ARTICLE_RE  = re.compile(r'<article\b[^>]*>(.*?)</article>', re.DOTALL)
_CARD_URL_RE = re.compile(r'href="(https://www\.vipcigars\.com/[^"]+\.html)"')
_CARD_PID_RE = re.compile(r'<input[^>]*name="p_id"[^>]*value="(\d+)"')


def _build_pid_url_map(html: str) -> dict[str, str]:
    """从 HTML 产品卡片提取 {p_id → product_url} 映射。"""
    pid_map: dict[str, str] = {}
    for m in _ARTICLE_RE.finditer(html):
        article = m.group(1)
        url_m = _CARD_URL_RE.search(article)
        pid_m = _CARD_PID_RE.search(article)
        if url_m and pid_m:
            pid_map[pid_m.group(1)] = url_m.group(1)
    return pid_map


def _parse_qty(name: str) -> int | None:
    m = re.search(r"(?:box\s*of|pack\s*of|cabinet\s*of|cube\s*of|boite\s*de)\s*(\d+)", name, re.I)
    if m:
        return int(m.group(1))
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
                    currency_m = _CURR_RE.search(html) or _CURR_RE.search(block)
                    currency_str = currency_m.group(1) if currency_m else "EUR"

                    pid_url_map = _build_pid_url_map(html)

                    for item_m in _ITEM_RE.finditer(block):
                        item_id  = item_m.group(1)
                        raw      = item_m.group(2).strip()
                        price    = float(item_m.group(3))
                        in_stock = item_m.group(4) == "1"

                        # 若名称不含品牌前缀，补全
                        name = raw if raw.lower().startswith(brand.split("-")[0]) else f"{brand_prefix} {raw}"

                        if name in seen:
                            continue
                        seen.add(name)

                        qty = _parse_qty(name)
                        product_url = pid_url_map.get(item_id)

                        items.append(ScrapedItem(
                            source_slug=self.source_slug,
                            raw_name=name,
                            product_url=product_url,
                            price_single=None if (qty and qty > 1) else price,
                            price_box=price if (qty and qty > 1) else None,
                            box_count=qty,
                            currency=currency_str,
                            in_stock=in_stock,
                        ))
                    await asyncio.sleep(0.3)

            await asyncio.gather(*[fetch_brand(b) for b in CUBAN_BRANDS])

        return items
