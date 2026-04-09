"""
Odoo Shop 通用爬虫基类。

支持两种品牌标签结构（不同 Odoo 版本/主题）：
  A) dominiquelondon.de: <h3 class="products_item_brand">Brand</h3>
  B) tabashop.ch:        <div class="as-product-brand"><span>Brand</span></div>

共同特征：
  - 产品标题: <h6 class="o_wsale_products_item_title"><a href="/[lang/]shop/xxx?category=N">Name</a>
  - 价格: <span class="oe_currency_value">19.90</span>
  - 库存: 缺货时 out_of_stock_message 有内容，或无 btn-cart 按钮
  - 分页: ?ppg=100&page=N
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

# 按商品信息块分割（两种站点均有此 class）
_SPLIT_RE = re.compile(r'(?=<div[^>]+o_wsale_product_information_text)')

# 品牌 — 支持两种模式
_BRAND_RE = re.compile(
    r'products_item_brand[^>]*>([^<]+)<'             # A: h3 模式
    r'|'
    r'as-product-brand[^>]*>\s*<span[^>]*>([^<]+)</span>',  # B: div/span 模式
    re.DOTALL,
)

# 商品链接与名称（支持语言前缀 /en_US/shop/...）
_LINK_RE = re.compile(
    r'href="(/(?:[a-z]{2}_[A-Z]{2}/)?shop/[^"?]+(?:\?[^"]*)?)"[^>]*>\s*([^<\n]{2,}?)\s*</a>',
    re.DOTALL,
)

# 价格
_PRICE_RE = re.compile(r'oe_currency_value[^>]*>([\d.,]+)<')

# 缺货：有明确的 out-of-stock 可见文字（不只是空 div）
# 匹配 out_of_stock_message div 内有实质文字内容
_OOS_RE   = re.compile(
    r'out_of_stock_message[^>]*>(?:\s*(?:<[^>]+>))*\s*([^\s<][^<]*)',
    re.DOTALL,
)
# 有货：有 Add to Cart / Purchase 按钮文字
_CART_RE  = re.compile(r'btn.?cart|Purchase|Warenkorb|panier|Add to Cart', re.I)

_QTY_RE      = re.compile(r"(\d+)\s*(?:er|x)?\s*(?:kiste|schachtel|cigars?|stück|box|pack|pcs)", re.I)
_URL_QTY_RE  = re.compile(r"-(\d+)(?:\?|$)")
_KNOWN_SIZES = {3, 5, 10, 12, 15, 20, 25, 40, 50}
# 详情页数量提取：匹配 "Coffret de 10", "Box of 10", "10 cigars" 等格式
_DETAIL_COUNT_RE = re.compile(
    r"(?:coffret\s+de|boite\s+de|box\s+of|kiste\s+von|schachtel\s+von)\s*(\d+)"
    r"|(\d+)\s*(?:er|x)?\s*(?:kiste|schachtel|cigars?|stück|box|pack|pcs)",
    re.I,
)

# 详情页规格变体链接（#packaging_products 区块）
_PKG_VARIANT_RE = re.compile(
    r'packaging_product_button"[^>]*href="(/(?:[a-z]{2}/)?shop/[^"?#]+)'
)
# 详情页产品名 <h1 itemprop="name">
_DETAIL_NAME_RE = re.compile(r'itemprop="name"[^>]*>([^<]+)</h1>')


def _count_from_url(url: str) -> int | None:
    m = _URL_QTY_RE.search(url)
    if m:
        n = int(m.group(1))
        if n in _KNOWN_SIZES:
            return n
    return None


def _parse_price(raw: str) -> float | None:
    raw = raw.strip()
    if "," in raw and "." in raw:
        if raw.rfind(".") > raw.rfind(","):
            raw = raw.replace(",", "")           # 1,428.57 → 1428.57
        else:
            raw = raw.replace(".", "").replace(",", ".")  # 1.428,57 → 1428.57
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


class OdooShopScraper(BaseScraper):
    """
    Abstract Odoo shop scraper.
    Subclass must set: source_slug, base_url, category_id, currency
    Optional: lang_prefix (e.g. "en_US"), category_slug (e.g. "cigares-cubains")
              fetch_packaging_variants: also follow #packaging_products links on detail pages
    """
    base_url:                 str
    category_id:              int
    currency:                 str
    lang_prefix:              str  = ""    # URL 语言前缀, 如 "en_US"
    category_slug:            str  = ""    # 分类名前缀, 如 "cigares-cubains"
    fetch_packaging_variants: bool = False # 是否抓取详情页的其他规格变体
    fetch_detail_for_count:   bool = False # 从详情页提取数量（listing 无法识别时）

    def _category_url(self, page: int) -> str:
        lang = f"/{self.lang_prefix}" if self.lang_prefix else ""
        slug = f"{self.category_slug}-" if self.category_slug else ""
        return f"{self.base_url}{lang}/shop/category/{slug}{self.category_id}?ppg=100&page={page}"

    async def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            page = 1
            while True:
                url = self._category_url(page)
                try:
                    r    = await client.get(url)
                    html = r.text
                except Exception:
                    break

                sections = _SPLIT_RE.split(html)
                if len(sections) <= 1:
                    break

                for section in sections[1:]:
                    brand_m = _BRAND_RE.search(section)
                    link_m  = _LINK_RE.search(section)
                    price_m = _PRICE_RE.search(section)
                    if not (link_m and price_m):
                        continue

                    product_url = link_m.group(1)
                    if not product_url.startswith("http"):
                        product_url = self.base_url + product_url
                    name_raw = link_m.group(2).strip()
                    brand = (brand_m.group(1) or brand_m.group(2) or "").strip() if brand_m else ""
                    raw_name = (
                        f"{brand} {name_raw}".strip()
                        if brand and brand.lower() not in name_raw.lower()
                        else name_raw
                    )

                    price = _parse_price(price_m.group(1))
                    if price is None or price <= 0:
                        continue

                    # 库存：有 cart 按钮 = 有货；明确 OOS 标识 = 缺货
                    has_cart = bool(_CART_RE.search(section))
                    is_oos   = bool(_OOS_RE.search(section))
                    in_stock = has_cart or not is_oos

                    qty_m     = _QTY_RE.search(raw_name)
                    box_count = int(qty_m.group(1)) if qty_m else None

                    # 名字未匹配到数量时，从 URL 回退提取
                    if box_count is None:
                        box_count = _count_from_url(product_url)

                    # 仍未知时：取详情页，从变体名称或产品描述提取数量
                    if box_count is None and self.fetch_detail_for_count:
                        try:
                            dp = await client.get(product_url.split("?")[0])
                            for m in _DETAIL_COUNT_RE.finditer(dp.text):
                                n = int(m.group(1) or m.group(2))
                                if n in _KNOWN_SIZES:
                                    box_count = n
                                    break
                        except Exception:
                            pass
                        await asyncio.sleep(0.2)

                    items.append(ScrapedItem(
                        source_slug  = self.source_slug,
                        raw_name     = raw_name,
                        product_url  = product_url,
                        price_single = None if (box_count and box_count > 1) else price,
                        price_box    = price if (box_count and box_count > 1) else None,
                        box_count    = box_count,
                        currency     = self.currency,
                        in_stock     = in_stock,
                    ))

                if f"page={page + 1}" not in html:
                    break
                page += 1
                await asyncio.sleep(0.4)

            if self.fetch_packaging_variants:
                items = await self._enrich_with_variants(client, items)

        return items

    async def _enrich_with_variants(
        self, client: httpx.AsyncClient, items: list[ScrapedItem]
    ) -> list[ScrapedItem]:
        """
        对列表中每个产品，访问其详情页，提取 #packaging_products 中的其他规格链接，
        抓取尚未收录的变体，追加到 items 中。
        """
        seen_urls: set[str] = {
            # 标准化已有 URL：去掉语言前缀和查询参数
            self._norm_url(it.product_url)
            for it in items if it.product_url
        }
        extra: list[ScrapedItem] = []
        sem = asyncio.Semaphore(3)

        async def process(item: ScrapedItem):
            if not item.product_url:
                return
            async with sem:
                try:
                    r = await client.get(item.product_url)
                    detail_html = r.text
                except Exception:
                    return
                await asyncio.sleep(0.2)

            # 提取同一产品的其他规格链接
            for m in _PKG_VARIANT_RE.finditer(detail_html):
                rel_path = m.group(1)
                # 去掉语言前缀 /de/ /en_US/ 等
                clean = re.sub(r'^/[a-z]{2}(?:_[A-Z]{2})?/', '/shop/', rel_path)
                if not clean.startswith('/shop/'):
                    clean = rel_path
                norm = self._norm_url(self.base_url + clean)
                if norm in seen_urls:
                    continue
                seen_urls.add(norm)

                # 抓取变体详情页
                variant_url = self.base_url + clean
                async with sem:
                    try:
                        rv = await client.get(variant_url)
                        vhtml = rv.text
                    except Exception:
                        continue
                    await asyncio.sleep(0.2)

                vi = self._parse_detail_page(vhtml, variant_url)
                if vi:
                    extra.append(vi)

        await asyncio.gather(*[process(it) for it in items])
        return items + extra

    def _norm_url(self, url: str) -> str:
        """标准化 URL：去掉查询参数和语言前缀，仅保留路径主干。"""
        path = url.split("?")[0].split("#")[0]
        path = re.sub(r'^https?://[^/]+', '', path)
        path = re.sub(r'^/[a-z]{2}(?:_[A-Z]{2})?/', '/', path)
        return path.rstrip('/')

    def _parse_detail_page(self, html: str, url: str) -> ScrapedItem | None:
        """从产品详情页提取 ScrapedItem。"""
        name_m  = _DETAIL_NAME_RE.search(html)
        price_m = _PRICE_RE.search(html)
        if not (name_m and price_m):
            return None

        brand_m  = _BRAND_RE.search(html)
        brand    = (brand_m.group(1) or brand_m.group(2) or "").strip() if brand_m else ""
        name_raw = name_m.group(1).strip()
        raw_name = (
            f"{brand} {name_raw}".strip()
            if brand and brand.lower() not in name_raw.lower()
            else name_raw
        )

        price = _parse_price(price_m.group(1))
        if price is None or price <= 0:
            return None

        has_cart = bool(_CART_RE.search(html))
        is_oos   = bool(_OOS_RE.search(html))
        in_stock = has_cart or not is_oos

        qty_m     = _QTY_RE.search(raw_name)
        box_count = int(qty_m.group(1)) if qty_m else _count_from_url(url)
        product_url = url.split("?")[0]

        return ScrapedItem(
            source_slug  = self.source_slug,
            raw_name     = raw_name,
            product_url  = product_url,
            price_single = None if (box_count and box_count > 1) else price,
            price_box    = price if (box_count and box_count > 1) else None,
            box_count    = box_count,
            currency     = self.currency,
            in_stock     = in_stock,
        )
