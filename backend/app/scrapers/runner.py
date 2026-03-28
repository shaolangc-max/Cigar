"""
爬虫运行器 — 执行爬虫并将结果写入数据库。
兼容 SQLite（开发）和 PostgreSQL（生产）。
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models import Cigar, Source, Price, PriceHistory
from app.scrapers.base import ScrapedItem
from app.scrapers.matcher import best_match, extract_brand

log = logging.getLogger(__name__)


async def run_scraper(source_slug: str) -> dict:
    """运行单个爬虫，返回 {scraped, matched, saved, errors}"""
    import app.scrapers.sites  # noqa: F401 触发 @register
    from app.scrapers.registry import get_by_slug

    scraper = get_by_slug(source_slug)
    if scraper is None:
        return {"error": f"No scraper registered for '{source_slug}'"}

    log.info("Starting scraper: %s", source_slug)
    try:
        items = await scraper.scrape()
    except Exception as exc:
        log.exception("Scraper %s failed", source_slug)
        return {"scraped": 0, "matched": 0, "saved": 0, "errors": [str(exc)]}

    log.info("%s: scraped %d items", source_slug, len(items))
    saved, matched, errors = await _save_items(items)
    return {"scraped": len(items), "matched": matched, "saved": saved, "errors": errors}


async def run_all_scrapers() -> list[dict]:
    import app.scrapers.sites  # noqa: F401
    from app.scrapers.registry import get_all

    results = []
    for scraper in get_all():
        result = await run_scraper(scraper.source_slug)
        result["source"] = scraper.source_slug
        results.append(result)
    return results


async def _save_items(items: list[ScrapedItem]) -> tuple[int, int, list[str]]:
    saved = matched = 0
    errors: list[str] = []
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # 预加载 sources slug→id
        sources_result = await db.execute(select(Source.id, Source.slug))
        source_map: dict[str, int] = {row.slug: row.id for row in sources_result}

        # 预加载所有 cigars for fuzzy matching
        cigars_result = await db.execute(select(Cigar.id, Cigar.name, Cigar.slug))
        all_cigars = [{"id": r.id, "name": r.name, "slug": r.slug} for r in cigars_result]

        # ── 第一步：匹配，并按 (cigar_id, source_id) 合并单支/盒装 ──────────
        # key → {"single": item, "box": item, "any": item}
        merged: dict[tuple, dict] = {}

        for item in items:
            try:
                source_id = source_map.get(item.source_slug)
                if source_id is None:
                    errors.append(f"Unknown source: {item.source_slug}")
                    continue

                brand_slug = extract_brand(item.raw_name)
                if brand_slug:
                    candidates = [c for c in all_cigars if brand_slug in c["slug"]]
                else:
                    candidates = all_cigars

                cigar = best_match(item.raw_name, candidates)
                if cigar is None:
                    log.debug("No match for: %s", item.raw_name)
                    continue
                matched += 1

                key = (cigar["id"], source_id)
                if key not in merged:
                    merged[key] = {"single": None, "box": None, "any": item,
                                   "cigar_id": cigar["id"], "source_id": source_id}

                if item.price_single is not None and item.price_box is None:
                    merged[key]["single"] = item
                elif item.price_box is not None and item.price_single is None:
                    merged[key]["box"] = item
                else:
                    merged[key]["any"] = item  # 已含两列或都为 None

            except Exception as exc:
                errors.append(f"{item.raw_name}: {exc}")
                log.exception("Error matching item %s", item.raw_name)

        # ── 第二步：写库 ──────────────────────────────────────────────────
        for key, m in merged.items():
            try:
                cigar_id  = m["cigar_id"]
                source_id = m["source_id"]
                single    = m["single"]
                box       = m["box"]
                base      = single or box or m["any"]

                # 合并价格：单支取 single 行，盒装取 box 行，互不覆盖
                price_single = single.price_single if single else (
                    m["any"].price_single if m["any"] else None
                )
                price_box    = box.price_box if box else (
                    m["any"].price_box if m["any"] else None
                )
                box_count    = box.box_count if box else (
                    m["any"].box_count if m["any"] else None
                )
                in_stock     = any(
                    x.in_stock for x in [single, box, m["any"]] if x is not None
                )

                # 合理性检查：单支价超阈值且无支数 → 可能是未标注支数的盒装
                _SINGLE_LIMIT = {"EUR": 300, "CHF": 250, "USD": 400,
                                 "HKD": 3000, "CNY": 2800, "GBP": 260}
                ccy = base.currency
                limit = _SINGLE_LIMIT.get(ccy, 300)
                if price_single and price_single > limit:
                    if price_box is None:
                        price_box = price_single
                    price_single = None
                    log.debug("Reclassified oversized single as box: %s %.2f %s",
                              base.raw_name, price_box, ccy)

                existing = await db.execute(
                    select(Price).where(
                        Price.cigar_id == cigar_id,
                        Price.source_id == source_id,
                    )
                )
                price_row = existing.scalar_one_or_none()
                if price_row is None:
                    price_row = Price(cigar_id=cigar_id, source_id=source_id)
                    db.add(price_row)

                price_row.price_single = price_single
                price_row.price_box    = price_box
                price_row.box_count    = box_count
                price_row.currency     = base.currency
                price_row.product_url  = base.product_url
                price_row.in_stock     = in_stock
                price_row.scraped_at   = now

                db.add(PriceHistory(
                    cigar_id=cigar_id,
                    source_id=source_id,
                    price_single=price_single,
                    price_box=price_box,
                    currency=base.currency,
                    scraped_at=now,
                ))
                saved += 1

            except Exception as exc:
                errors.append(f"save {key}: {exc}")
                log.exception("Error saving key %s", key)

        await db.commit()

    return saved, matched, errors
