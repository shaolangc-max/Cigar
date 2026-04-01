"""
WooCommerce Store API 通用爬虫基类（/wp-json/wc/store/v1/products）。

子类只需声明：
  source_slug, base_url, currency, categories (list of WC category slugs)

价格单位：WooCommerce 以整数（最小货币单位）返回，除以 10^currency_minor_unit。
库存：通过 add_to_cart_description 判断（"Add to cart" = in stock）。
支数：从 short_description / name 解析 "X Stück / X Cigars / X er Kiste"。
"""
from __future__ import annotations
import re
import asyncio
import httpx

from app.scrapers.base import BaseScraper, ScrapedItem


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

_QTY_RE = re.compile(
    r"(\d+)\s*(?:Stück|Cigars?|er\s*Kiste|er\s*Box|pack|st\.)"
    r"|"
    r"\((\d+)\)\s*$"    # 末尾括号数量，如 "Product Name (25)"
    r"|"
    r"[Bb]ox\s+of\s+(\d+)",   # "Box of 20"
    re.I,
)


def _parse_qty(text: str) -> int | None:
    m = _QTY_RE.search(text or "")
    if not m:
        return None
    return int(m.group(1) or m.group(2) or m.group(3))


def _clean(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


# permalink 倒数第二段 → 标准品牌名
# 适用于德语系 WooCommerce 站（品牌作为子分类，不写入商品名）
_BRAND_SLUG_MAP: dict[str, str] = {
    "cohiba-zigarren":          "Cohiba",
    "montecristo-zigarren":     "Montecristo",
    "romeo-y-julieta-zigarren": "Romeo Y Julieta",
    "partagas-zigarren":        "Partagas",
    "h-upmann-zigarren":        "H Upmann",
    "bolivar-zigarren":         "Bolivar",
    "punch-zigarren":           "Punch",
    "trinidad-zigarren":        "Trinidad",
    "hoyo-de-monterrey-zigarren": "Hoyo De Monterrey",
    "por-larranaga-zigarren":   "Por Larranaga",
    "saint-luis-rey-zigarren":  "Saint Luis Rey",
    "quai-dorsay-zigarren":     "Quai D Orsay",
}


def _brand_from_permalink(permalink: str) -> str | None:
    """从 permalink 倒数第二段提取品牌名，无法识别时返回 None。"""
    parts = permalink.rstrip("/").split("/")
    segment = parts[-2] if len(parts) >= 2 else ""
    return _BRAND_SLUG_MAP.get(segment)


class WooCommerceScraper(BaseScraper):
    """
    Abstract WooCommerce Store API scraper.

    Subclass must set: source_slug, base_url, currency, categories
    """
    base_url: str
    currency: str
    categories: list[str]  # WooCommerce category slugs

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=30, follow_redirects=True
        ) as client:
            for category in self.categories:
                page = 1
                while True:
                    url = (
                        f"{self.base_url}/wp-json/wc/store/v1/products"
                        f"?category={category}&per_page=100&page={page}"
                        f"&_fields=name,permalink,prices,short_description,add_to_cart"
                    )
                    try:
                        r = await client.get(url)
                        if r.status_code != 200:
                            break
                        products = r.json()
                        if not products:
                            break
                    except Exception:
                        break

                    for p in products:
                        name  = p.get("name", "")
                        url_p = p.get("permalink", "")
                        brand = _brand_from_permalink(url_p)
                        raw_name = f"{brand} {name}" if brand else name
                        prices_obj = p.get("prices", {})
                        minor = prices_obj.get("currency_minor_unit", 2)
                        divisor = 10 ** minor

                        raw_price = prices_obj.get("price")
                        if raw_price is None:
                            continue
                        price = int(raw_price) / divisor
                        if price <= 0:
                            continue

                        in_stock = "add to cart" in (
                            p.get("add_to_cart", {}).get("description", "").lower()
                        )

                        # 从描述解析支数
                        desc = _clean(p.get("short_description") or "")
                        qty = _parse_qty(desc) or _parse_qty(name)

                        if qty and qty > 1:
                            items.append(ScrapedItem(
                                source_slug=self.source_slug,
                                raw_name=raw_name,
                                product_url=url_p,
                                price_single=None,
                                price_box=price,
                                box_count=qty,
                                currency=self.currency,
                                in_stock=in_stock,
                            ))
                        else:
                            items.append(ScrapedItem(
                                source_slug=self.source_slug,
                                raw_name=raw_name,
                                product_url=url_p,
                                price_single=price,
                                price_box=None,
                                box_count=None,
                                currency=self.currency,
                                in_stock=in_stock,
                            ))

                    total_pages = _get_total_pages(r)
                    if page >= total_pages:
                        break
                    page += 1
                    await asyncio.sleep(0.3)

        return items


def _get_total_pages(r: httpx.Response) -> int:
    total = int(r.headers.get("x-wp-totalpages", "1"))
    return total
