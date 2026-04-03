"""
德国雪茄世界 — cigarworld.de
静态 HTML，EUR 计价。
目录结构: /zigarren/kuba/{category}
详情页同为静态 HTML，包含所有包装规格（单支 / 整盒）的价格。
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

# Matches "1er", "25er Kiste", "5er Kiste", "3er" etc.
_UNIT_RE = re.compile(r'^(\d+)er', re.I)

# Matches a single DetailOrderbox data row (has eurval + einheitlabel, skips title row)
_ROW_RE = re.compile(
    r'DetailOrderbox-row.*?'
    r'data-eurval="([\d.]+)".*?'
    r'einheitlabel\s+(avail_\d+)[^>]*>([^<]+)',
    re.S,
)


def _parse_listing(html: str) -> list[tuple[str, str]]:
    """返回 [(url, raw_name), ...]"""
    results = []
    items = re.findall(
        r'<a class="search-result-item-inner" href="([^"]+)"[^>]*>(.*?)</a>',
        html, re.DOTALL,
    )
    for href, content in items:
        brand = re.search(r'class="brand">([^<]+)', content)
        name  = re.search(r'class="name">([^<]+)', content)
        b = brand.group(1).strip() if brand else ""
        n = name.group(1).strip() if name else ""
        raw_name = f"{b} {n}".strip() if b else n
        if raw_name:
            url = BASE + href if href.startswith("/") else href
            results.append((url, raw_name))
    return results


def _parse_detail(html: str, url: str, raw_name: str, source_slug: str) -> list[ScrapedItem]:
    """从详情页解析所有包装规格，返回 ScrapedItem 列表。"""
    # 定位订购表单区域，避免匹配到页面其他价格数据
    form_m = re.search(r'data-addtocart="form">(.*?)</form>', html, re.S)
    if not form_m:
        return []

    items = []
    for price_str, avail_class, label in _ROW_RE.findall(form_m.group(1)):
        unit_m = _UNIT_RE.match(label.strip())
        if not unit_m:
            continue
        qty      = int(unit_m.group(1))
        price    = float(price_str)
        in_stock = avail_class == "avail_1"

        if qty == 1:
            items.append(ScrapedItem(
                source_slug  = source_slug,
                raw_name     = raw_name,
                product_url  = url,
                price_single = price,
                price_box    = None,
                box_count    = None,
                currency     = "EUR",
                in_stock     = in_stock,
            ))
        else:
            items.append(ScrapedItem(
                source_slug  = source_slug,
                raw_name     = raw_name,
                product_url  = url,
                price_single = None,
                price_box    = price,
                box_count    = qty,
                currency     = "EUR",
                in_stock     = in_stock,
            ))
    return items


@register
class CigarWorldScraper(BaseScraper):
    source_slug = "cigarworld"
    min_interval_hours = 12  # 详情页抓取较慢，限制每 12 小时最多跑一次

    async def scrape(self) -> list[ScrapedItem]:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            # 第一步：抓所有分类列表页，收集商品 URL + 名称（去重）
            products: dict[str, str] = {}  # url → raw_name
            sem_list = asyncio.Semaphore(3)

            async def _fetch_cat(cat_path: str):
                async with sem_list:
                    try:
                        r = await client.get(BASE + cat_path)
                        for url, name in _parse_listing(r.text):
                            if url not in products:
                                products[url] = name
                    except Exception:
                        pass

            await asyncio.gather(*[_fetch_cat(c) for c in CUBAN_CATEGORIES])

            # 第二步：并发抓详情页，解析单支 + 整盒价格
            all_items: list[ScrapedItem] = []
            sem_detail = asyncio.Semaphore(3)

            async def _fetch_detail(url: str, name: str):
                async with sem_detail:
                    try:
                        r = await client.get(url)
                        parsed = _parse_detail(r.text, url, name, self.source_slug)
                        all_items.extend(parsed)
                        await asyncio.sleep(0.3)
                    except Exception:
                        pass

            await asyncio.gather(*[
                _fetch_detail(url, name) for url, name in products.items()
            ])

            return all_items
