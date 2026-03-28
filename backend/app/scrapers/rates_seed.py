"""
写入初始汇率（相对 USD）。生产环境由 APScheduler 定时更新，此脚本提供初始值。
"""
import asyncio
from datetime import datetime, timezone
from sqlalchemy import text
from app.db import AsyncSessionLocal

RATES = {
    "USD": 1.0,
    "HKD": 7.78,
    "CNY": 7.25,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.36,
    "AUD": 1.55,
    "CHF": 0.90,
    "SGD": 1.35,
}


async def seed():
    now = datetime.now(timezone.utc).isoformat()
    async with AsyncSessionLocal() as db:
        for currency, rate in RATES.items():
            await db.execute(
                text(
                    "INSERT INTO exchange_rates (currency, rate_to_usd, updated_at) "
                    "VALUES (:c, :r, :t) "
                    "ON CONFLICT(currency) DO UPDATE SET "
                    "rate_to_usd=excluded.rate_to_usd, updated_at=excluded.updated_at"
                ),
                {"c": currency, "r": rate, "t": now},
            )
        await db.commit()
    print(f"✓ Seeded {len(RATES)} exchange rates")


if __name__ == "__main__":
    asyncio.run(seed())
