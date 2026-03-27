"""
德国雪茄世界 — cigarworld.de
静态 HTML，EUR 计价。
目录结构: /zigarren/kuba/{category}
商品页: /zigarren/kuba/{category}/{name}_{id}
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


def _parse_product(html: str) -> list[tuple[float, str, bool]]:
    """从商品详情页提取 [(price, unit_label, in_stock), ...]
    unit_label 形如 '1er', '10er Kiste', '25er Kiste'
    """
    rows = re.findall(
        r'<div class="ws-g DetailOrderbox-row">(.*?)</div>\s*</div>',
        html, re.DOTALL,
    )
    results = []
    for row in rows:
        price = re.search(r'data-eurval="([^"]+)"', row)
        unit  = re.search(r'class="einheitlabel[^"]*"[^>]*>([^<]+)', row)
        avail = re.search(r'title="(Auf Lager|Momentan nicht|Ausverkauft)"', row)
        if price and unit:
            p    = float(price.group(1))
            u    = unit.group(1).strip()
            ok   = avail and "Lager" in avail.group(1)
            results.append((p, u, bool(ok)))
    return results


@register
class CigarWorldScraper(BaseScraper):
    source_slug = "cigarworld"

    async def scrape(self) -> list[ScrapedItem]:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            # 1. 汇总各目录页所有商品
            listing_items: dict[str, dict] = {}  # url -> {name, price_single, in_stock}
            sem_list = asyncio.Semaphore(3)

            async def _fetch_cat(cat_path: str):
                async with sem_list:
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

            # 2. 访问商品详情页获取盒装价格
            sem_prod = asyncio.Semaphore(4)

            async def _fetch_product(url: str) -> ScrapedItem | None:
                async with sem_prod:
                    info = listing_items[url]
                    price_single = info["price_single"]
                    price_box    = None
                    box_count    = None

                    try:
                        r = await client.get(url)
                        rows = _parse_product(r.text)
                        for price, unit, ok in rows:
                            count_m = re.search(r"(\d+)er", unit)
                            count   = int(count_m.group(1)) if count_m else 1
                            if count <= 1:
                                price_single = price
                                info["in_stock"] = ok
                            else:
                                # 取数量最大的盒装（通常是标准盒）
                                if price_box is None or count > (box_count or 0):
                                    price_box = price
                                    box_count = count
                    except Exception:
                        pass

                    return ScrapedItem(
                        source_slug  = self.source_slug,
                        raw_name     = info["name"],
                        product_url  = url,
                        price_single = price_single,
                        price_box    = price_box,
                        box_count    = box_count,
                        currency     = "EUR",
                        in_stock     = info["in_stock"],
                    )

            tasks = [_fetch_product(u) for u in listing_items]
            results = await asyncio.gather(*tasks)
            return [r for r in results if r is not None]
