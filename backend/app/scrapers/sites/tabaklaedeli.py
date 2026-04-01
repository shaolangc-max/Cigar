"""瑞士补漏站 — tabaklaedeli.ch (WooCommerce, CHF)

Variable 产品（仅销整盒）的 qty 信息不在 WooCommerce Store API 里，
需访产品详情页从 JSON-LD offer URL 提取：
  attribute_pa_lieferbar=25er-holzkiste  →  box_count=25
"""
from __future__ import annotations
import re
import asyncio
import json
import httpx

from app.scrapers.registry import register
from app.scrapers.woocommerce_base import WooCommerceScraper, _parse_qty, _clean, HEADERS

# JSON-LD offer URL 里的属性，如 25er-holzkiste / 10er-kiste
_ATTR_QTY_RE = re.compile(r'attribute_pa_\w+=(\d+)er', re.I)


async def _fetch_qty_from_page(client: httpx.AsyncClient, url: str) -> int | None:
    """访产品详情页，从 JSON-LD offers[0].url 提取支数。"""
    try:
        r = await client.get(url)
        for ld_raw in re.findall(r'application/ld\+json[^>]*>(.*?)</script>', r.text, re.DOTALL):
            try:
                d = json.loads(ld_raw)
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            offers = d.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            for offer in offers:
                offer_url = offer.get("url", "")
                m = _ATTR_QTY_RE.search(offer_url)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return None


@register
class TabaklaedeliScraper(WooCommerceScraper):
    source_slug = "tabaklaedeli"
    base_url    = "https://www.tabaklaedeli.ch"
    currency    = "CHF"
    categories  = ["cuba"]

    async def scrape(self):
        # 先用父类标准逻辑爬
        items = await super().scrape()

        # 对 qty 未知且价格偏高（> 200）的条目，补取详情页
        # （这些产品是 WooCommerce variable 产品，仅卖整盒）
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            sem = asyncio.Semaphore(3)
            async def enrich(item):
                if item.box_count is None and (item.price_single or 0) > 200:
                    async with sem:
                        qty = await _fetch_qty_from_page(client, item.product_url)
                        await asyncio.sleep(0.2)
                    if qty and qty > 1:
                        item.price_box    = item.price_single
                        item.price_single = None
                        item.box_count    = qty

            await asyncio.gather(*[enrich(it) for it in items])

        return items
