"""
调度任务：爬取 + 汇率更新。
"""
import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import delete, select, update

from app.config import settings

if settings.database_url.startswith("postgresql"):
    from sqlalchemy.dialects.postgresql import insert
else:
    from sqlalchemy.dialects.sqlite import insert
from app.db import AsyncSessionLocal
from app.models import Cigar, Source, Price, PriceHistory, ExchangeRate, ScraperRun, UnmatchedItem
from app.models.alias import ScraperNameAlias
from app.scrapers.registry import get_all
from app.scrapers.matcher import best_match_with_aliases
import app.scrapers.sites  # noqa: F401 — 触发所有爬虫注册

log = logging.getLogger(__name__)

CURRENCIES = ["CNY", "HKD", "USD", "EUR", "CHF", "GBP", "CAD", "RUB"]


async def update_exchange_rates():
    """从 exchangerate-api.com 更新汇率（以 USD 为基准）"""
    if not settings.exchange_rate_api_key:
        log.warning("No EXCHANGE_RATE_API_KEY — using static fallback rates")
        rates = {"USD": 1.0, "CNY": 7.25, "HKD": 7.83, "EUR": 0.92}
    else:
        url = f"https://v6.exchangerate-api.com/v6/{settings.exchange_rate_api_key}/latest/USD"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10)
            data = r.json()
            conv = data.get("conversion_rates", {})
            rates = {c: conv.get(c, 1.0) for c in CURRENCIES}

    async with AsyncSessionLocal() as db:
        for currency, rate in rates.items():
            stmt = insert(ExchangeRate).values(currency=currency, rate_to_usd=rate, updated_at=datetime.now(timezone.utc))
            stmt = stmt.on_conflict_do_update(
                index_elements=["currency"],
                set_={"rate_to_usd": rate, "updated_at": datetime.now(timezone.utc)},
            )
            await db.execute(stmt)
        await db.commit()
    log.info(f"Exchange rates updated: {rates}")


async def _run_scraper(scraper) -> None:
    """运行单个爬虫并记录结果，无并发限制（调用方自行控制并发）。"""
    started_at = datetime.now(timezone.utc)
    run_id: int | None = None
    async with AsyncSessionLocal() as db:
        run = ScraperRun(
            source_slug=scraper.source_slug,
            started_at=started_at,
            status="running",
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id

    try:
        items = await scraper.scrape()
        scraped, matched, unmatched_items_data = await _save_items(items)
        finished_at = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            # 先清除该站上次运行留下的未匹配条目，避免重复累积
            await db.execute(
                delete(UnmatchedItem).where(UnmatchedItem.source_slug == scraper.source_slug)
            )
            for u in unmatched_items_data:
                db.add(UnmatchedItem(
                    run_id=run_id,
                    source_slug=scraper.source_slug,
                    raw_name=u["raw_name"],
                    price_single=u.get("price_single"),
                    price_box=u.get("price_box"),
                    currency=u["currency"],
                    product_url=u.get("product_url"),
                    match_score=u.get("match_score"),
                    best_candidate=u.get("best_candidate"),
                ))
            run_obj = await db.get(ScraperRun, run_id)
            if run_obj:
                run_obj.status = "success"
                run_obj.finished_at = finished_at
                run_obj.items_scraped = scraped
                run_obj.items_matched = matched
                run_obj.items_unmatched = len(unmatched_items_data)
            await db.commit()

        log.info(f"  {scraper.source_slug}: {scraped} scraped, {matched} matched, {len(unmatched_items_data)} unmatched")
    except Exception as e:
        finished_at = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            run_obj = await db.get(ScraperRun, run_id)
            if run_obj:
                run_obj.status = "failed"
                run_obj.finished_at = finished_at
                run_obj.error_msg = str(e)[:2000]
            await db.commit()
        log.error(f"  {scraper.source_slug} failed: {e}")


async def run_single_scraper(source_slug: str) -> None:
    """手动触发单个爬虫（供 API 调用）。"""
    from app.scrapers.registry import get_by_slug
    scraper = get_by_slug(source_slug)
    if not scraper:
        log.error(f"run_single_scraper: unknown slug {source_slug!r}")
        return
    log.info(f"Manual trigger: {source_slug}")
    await _run_scraper(scraper)


async def run_all_scrapers():
    scrapers = get_all()
    log.info(f"Starting scrape: {len(scrapers)} sources")
    sem = asyncio.Semaphore(settings.scraper_concurrency)

    async def _run_one(scraper):
        async with sem:
            await _run_scraper(scraper)

    await asyncio.gather(*[_run_one(s) for s in scrapers])
    log.info("Scrape complete")


async def _save_items(items) -> tuple[int, int, list[dict]]:
    """保存爬取结果，返回 (总条数, 匹配条数, 未匹配条目列表)"""
    if not items:
        return 0, 0, []
    async with AsyncSessionLocal() as db:
        source_result = await db.execute(
            select(Source).where(Source.slug == items[0].source_slug)
        )
        source = source_result.scalar_one_or_none()
        if not source:
            return len(items), 0, []

        # 加载全部 cigar
        cigar_result = await db.execute(select(Cigar))
        all_cigars = [
            {"id": c.id, "name": c.name, "slug": c.slug}
            for c in cigar_result.scalars().all()
        ]

        # 加载别名表
        alias_result = await db.execute(select(ScraperNameAlias))
        aliases: dict[tuple[str, str], int] = {
            (a.source_slug, a.raw_name): a.cigar_id
            for a in alias_result.scalars().all()
        }

        now = datetime.now(timezone.utc)
        matched_count = 0
        unmatched: list[dict] = []

        for item in items:
            cigar, score, best_candidate = best_match_with_aliases(
                item.raw_name, item.source_slug, aliases, all_cigars
            )
            if not cigar:
                unmatched.append({
                    "raw_name": item.raw_name,
                    "price_single": item.price_single,
                    "price_box": item.price_box,
                    "currency": item.currency,
                    "product_url": item.product_url,
                    "match_score": round(score, 3),
                    "best_candidate": best_candidate,
                })
                continue

            matched_count += 1

            # upsert 当前价格
            stmt = insert(Price).values(
                cigar_id=cigar["id"],
                source_id=source.id,
                price_single=item.price_single,
                price_box=item.price_box,
                box_count=item.box_count,
                currency=item.currency,
                product_url=item.product_url,
                in_stock=item.in_stock,
                scraped_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["cigar_id", "source_id"],
                set_={
                    "price_single": item.price_single,
                    "price_box": item.price_box,
                    "box_count": item.box_count,
                    "currency": item.currency,
                    "product_url": item.product_url,
                    "in_stock": item.in_stock,
                    "scraped_at": now,
                },
            )
            await db.execute(stmt)

            # 追加历史
            db.add(PriceHistory(
                cigar_id=cigar["id"],
                source_id=source.id,
                price_single=item.price_single,
                price_box=item.price_box,
                currency=item.currency,
                scraped_at=now,
            ))

        await db.commit()

    return len(items), matched_count, unmatched
