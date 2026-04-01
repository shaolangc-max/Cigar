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
# 从 HTML 中提取产品详情页链接，格式：/cuban-cigars/{brand}/{slug}.html
_PROD_URL_RE = re.compile(r'href="(https://www\.vipcigars\.com/cuban-cigars/[^/]+/[^"]+\.html)"')


_QTY_SUFFIX_RE = re.compile(
    r"[-\s](?:box|pack|cabinet|cube|slb|boite)-?(?:of-?)?[\d]+(?:-\d+)?$"
)


def _name_to_slug(name: str, brand: str) -> str:
    """将产品名转换为 URL slug（去品牌前缀后小写连字符化）。"""
    brand_prefix = brand.replace("-", " ").lower()
    norm = name.lower().strip()
    if norm.startswith(brand_prefix):
        norm = norm[len(brand_prefix):].strip()
    return re.sub(r"[^a-z0-9]+", "-", norm).strip("-")


def _slug_variants(slug: str) -> list[str]:
    """生成 slug 的多个候选变体，用于 fallback 匹配。"""
    variants = [slug]
    # 去掉末尾数量后缀（box-of-25, pack-of-5, cabinet-of-25 等）
    bare = _QTY_SUFFIX_RE.sub("", slug)
    if bare != slug:
        variants.append(bare)
    # cabinet / box / pack 三者互换
    for s in list(variants):
        for a, b in [("cabinet-of", "box-of"), ("cabinet-of", "pack-of"),
                     ("box-of", "cabinet-of"), ("box-of", "pack-of"),
                     ("pack-of", "box-of"), ("pack-of", "cabinet-of")]:
            if a in s:
                variants.append(s.replace(a, b))
    # slb → cabinet
    for s in list(variants):
        if "-slb-" in s or s.endswith("-slb"):
            variants.append(re.sub(r"-slb", "", s))
    return variants


def _build_url_map(html: str, brand: str) -> dict[str, str]:
    """从页面 HTML 提取 slug→URL 映射（每个 URL 只出现一次）。"""
    prefix = f"/cuban-cigars/{brand}/"
    seen: set[str] = set()
    url_map: dict[str, str] = {}
    for m in _PROD_URL_RE.finditer(html):
        full_url = m.group(1)
        if prefix not in full_url:
            continue
        slug = full_url.split(prefix)[-1].removesuffix(".html")
        if slug not in seen:
            seen.add(slug)
            url_map[slug] = full_url
    return url_map


def _lookup_url(url_map: dict[str, str], name: str, brand: str) -> str | None:
    """用多级 fallback 策略在 url_map 中查找产品 URL。"""
    slug = _name_to_slug(name, brand)
    for variant in _slug_variants(slug):
        if variant in url_map:
            return url_map[variant]
    return None


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

                    url_map = _build_url_map(html, brand)

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
                        product_url = _lookup_url(url_map, name, brand)

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
