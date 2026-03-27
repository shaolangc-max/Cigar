from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import PriceHistory, ExchangeRate

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/history/{cigar_id}")
async def price_history(
    cigar_id: int,
    source_id: int | None = Query(None),
    currency: str = Query("USD"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PriceHistory).where(PriceHistory.cigar_id == cigar_id)
    if source_id:
        stmt = stmt.where(PriceHistory.source_id == source_id)
    stmt = stmt.order_by(PriceHistory.scraped_at)

    result = await db.execute(stmt)
    history = result.scalars().all()

    rates_result = await db.execute(select(ExchangeRate))
    rates = {r.currency: r.rate_to_usd for r in rates_result.scalars().all()}

    def convert(amount, from_ccy):
        if amount is None:
            return None
        return round(amount / rates.get(from_ccy, 1.0) * rates.get(currency, 1.0), 2)

    return [
        {
            "source_id":    h.source_id,
            "price_single": convert(h.price_single, h.currency),
            "price_box":    convert(h.price_box, h.currency),
            "scraped_at":   h.scraped_at.isoformat(),
        }
        for h in history
    ]
