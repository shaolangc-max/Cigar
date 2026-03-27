"""
调度器入口 — 每4小时触发一次全量爬取。
"""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.tasks import run_all_scrapers, update_exchange_rates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def main():
    scheduler = AsyncIOScheduler()

    # 启动时立即执行一次
    await update_exchange_rates()
    await run_all_scrapers()

    # 每4小时爬取一次
    scheduler.add_job(run_all_scrapers, "interval", hours=4, id="scrape")
    # 每小时更新汇率
    scheduler.add_job(update_exchange_rates, "interval", hours=1, id="fx")

    scheduler.start()
    log.info("Scheduler started. Next scrape in 4 hours.")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
