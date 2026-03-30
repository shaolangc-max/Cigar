from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import func, select

from app.api import brands, cigars, prices, admin, auth, billing, alerts, scraper_admin, admin_tools
from app.admin import create_admin
from app.config import settings
from app.db import AsyncSessionLocal
from app.models import Price
from app.scheduler.tasks import run_all_scrapers, update_exchange_rates

import logging
log = logging.getLogger(__name__)


async def _last_scraped_hours_ago() -> float:
    """返回距上次爬取经过了多少小时，数据库为空时返回无穷大。"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.max(Price.scraped_at)))
        ts = result.scalar_one_or_none()
    if ts is None:
        return float("inf")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds() / 3600


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()

    # 只有距上次爬取超过 4 小时才立即执行，避免重启时重复爬取
    hours_ago = await _last_scraped_hours_ago()
    if hours_ago >= 4:
        log.info(f"Last scrape was {hours_ago:.1f}h ago — running now.")
        await update_exchange_rates()
        await run_all_scrapers()
    else:
        log.info(f"Last scrape was {hours_ago:.1f}h ago — skipping immediate run.")

    scheduler.add_job(run_all_scrapers,      "cron", hour="0,4,8,12,16,20", minute=0, id="scrape")
    scheduler.add_job(update_exchange_rates, "cron", hour="0,4,8,12,16,20", minute=0, id="fx")
    scheduler.start()
    log.info("Scheduler started.")

    yield  # 应用运行期间

    scheduler.shutdown(wait=False)
    log.info("Scheduler stopped.")


app = FastAPI(title="Cigar Price API", version="1.0.0", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)

create_admin(app)

app.include_router(auth.router,    prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(brands.router, prefix="/api/v1")
app.include_router(cigars.router, prefix="/api/v1")
app.include_router(prices.router, prefix="/api/v1")
app.include_router(admin.router,  prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(scraper_admin.router, prefix="/api/v1")
app.include_router(admin_tools.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
