from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import Cigar, Price, Source, ExchangeRate, Series, Brand

router = APIRouter(prefix="/cigars", tags=["cigars"])

SUPPORTED_CURRENCIES = {"CNY", "HKD", "USD", "EUR"}


@router.get("/{slug}")
async def get_cigar(
    slug: str,
    currency: str = Query("USD", description="CNY/HKD/USD/EUR"),
    db: AsyncSession = Depends(get_db),
):
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"currency must be one of {SUPPORTED_CURRENCIES}")

    result = await db.execute(
        select(Cigar)
        .where(Cigar.slug == slug)
        .options(
            selectinload(Cigar.series).selectinload(Series.brand),
            selectinload(Cigar.prices).selectinload(Price.source),
        )
    )
    cigar = result.scalar_one_or_none()
    if not cigar:
        raise HTTPException(404, "Cigar not found")

    # 汇率
    rates_result = await db.execute(select(ExchangeRate))
    rates = {r.currency: r.rate_to_usd for r in rates_result.scalars().all()}

    def convert(amount: float | None, from_ccy: str) -> float | None:
        if amount is None:
            return None
        in_usd = amount / rates.get(from_ccy, 1.0)
        return round(in_usd * rates.get(currency, 1.0), 2)

    prices = [
        {
            "source_id":       p.source_id,
            "source_name":     p.source.name,
            "source_slug":     p.source.slug,
            "base_url":        p.source.base_url,
            "product_url":     p.product_url,
            "currency":        currency,
            "source_currency": p.currency,          # 原始货币
            "price_single":    convert(p.price_single, p.currency),
            "price_box":       convert(p.price_box, p.currency),
            "price_single_src": p.price_single,     # 原始货币金额
            "price_box_src":    p.price_box,
            "box_count":       p.box_count,
            "in_stock":        p.in_stock,
            "scraped_at":      p.scraped_at.isoformat(),
        }
        for p in cigar.prices
        if p.source.active
    ]
    prices.sort(key=lambda x: (x["price_single"] or float("inf")))

    return {
        "id":        cigar.id,
        "name":      cigar.name,
        "slug":      cigar.slug,
        "vitola":    cigar.vitola,
        "length_mm": cigar.length_mm,
        "ring_gauge": cigar.ring_gauge,
        "image_url": cigar.image_url,
        "series":    {"name": cigar.series.name, "slug": cigar.series.slug},
        "brand":     {"name": cigar.series.brand.name, "slug": cigar.series.brand.slug},
        "prices":    prices,
        "currency":  currency,
    }


@router.get("")
async def search_cigars(
    q: str = Query("", min_length=1),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cigar)
        .where(
            or_(
                Cigar.name.ilike(f"%{q}%"),
                Cigar.vitola.ilike(f"%{q}%"),
            )
        )
        .options(selectinload(Cigar.series).selectinload(Series.brand))
        .limit(30)
    )
    cigars = result.scalars().all()
    return [
        {
            "id":       c.id,
            "name":     c.name,
            "slug":     c.slug,
            "vitola":   c.vitola,
            "image_url": c.image_url,
            "series":   c.series.name,
            "brand":    c.series.brand.name,
            "brand_slug": c.series.brand.slug,
        }
        for c in cigars
    ]
