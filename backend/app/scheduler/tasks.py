"""
调度任务：爬取 + 汇率更新。
"""
import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, update

from app.config import settings

if settings.database_url.startswith("postgresql"):
    from sqlalchemy.dialects.postgresql import insert
else:
    from sqlalchemy.dialects.sqlite import insert
from app.db import AsyncSessionLocal
from app.models import Cigar, Source, Price, PriceHistory, ExchangeRate
from app.scrapers.registry import get_all
from app.scrapers.matcher import best_match
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


async def run_all_scrapers():
    scrapers = get_all()
    log.info(f"Starting scrape: {len(scrapers)} sources")
    sem = asyncio.Semaphore(settings.scraper_concurrency)

    async def _run_one(scraper):
        async with sem:
            try:
                items = await scraper.scrape()
                await _save_items(items)
                log.info(f"  {scraper.source_slug}: {len(items)} items")
            except Exception as e:
                log.error(f"  {scraper.source_slug} failed: {e}")

    await asyncio.gather(*[_run_one(s) for s in scrapers])
    log.info("Scrape complete")


async def _save_items(items):
    if not items:
        return
    async with AsyncSessionLocal() as db:
        source_result = await db.execute(
            select(Source).where(Source.slug == items[0].source_slug)
        )
        source = source_result.scalar_one_or_none()
        if not source:
            return

        # 加载该网站品牌的所有 cigar（减少查询次数）
        cigar_result = await db.execute(select(Cigar))
        all_cigars = [
            {"id": c.id, "name": c.name, "slug": c.slug}
            for c in cigar_result.scalars().all()
        ]

        now = datetime.now(timezone.utc)
        for item in items:
            cigar = best_match(item.raw_name, all_cigars)
            if not cigar:
                continue

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
