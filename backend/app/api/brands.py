from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import Brand, Series, Cigar, Price, ExchangeRate

router = APIRouter(prefix="/brands", tags=["brands"])

SUPPORTED_CURRENCIES = {"CNY", "HKD", "USD", "EUR"}


@router.get("")
async def list_brands(db: AsyncSession = Depends(get_db)):
    # 品牌列表 + 每个品牌下的雪茄数量
    result = await db.execute(
        select(Brand)
        .options(selectinload(Brand.series).selectinload(Series.cigars))
        .order_by(Brand.name)
    )
    brands = result.scalars().all()
    return [
        {
            "id":          b.id,
            "name":        b.name,
            "slug":        b.slug,
            "country":     b.country,
            "image_url":   b.image_url,
            "cigar_count": sum(len(s.cigars) for s in b.series),
        }
        for b in brands
    ]


@router.get("/{slug}")
async def get_brand(
    slug: str,
    currency: str = Query("USD"),
    db: AsyncSession = Depends(get_db),
):
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"currency must be one of {SUPPORTED_CURRENCIES}")

    result = await db.execute(
        select(Brand)
        .where(Brand.slug == slug)
        .options(
            selectinload(Brand.series).selectinload(Series.cigars).selectinload(Cigar.prices)
        )
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(404, "Brand not found")

    # 汇率
    rates_result = await db.execute(select(ExchangeRate))
    rates = {r.currency: r.rate_to_usd for r in rates_result.scalars().all()}

    def convert(amount: float | None, from_ccy: str) -> float | None:
        if amount is None or not rates:
            return None
        in_usd = amount / rates.get(from_ccy, 1.0)
        return round(in_usd * rates.get(currency, 1.0), 2)

    return {
        "id":        brand.id,
        "name":      brand.name,
        "slug":      brand.slug,
        "country":   brand.country,
        "image_url": brand.image_url,
        "series": [
            {
                "id":   s.id,
                "name": s.name,
                "slug": s.slug,
                "cigars": [
                    {
                        "id":        c.id,
                        "name":      c.name,
                        "slug":      c.slug,
                        "vitola":    c.vitola,
                        "image_url": c.image_url,
                        "series":    s.name,
                        "brand":     brand.name,
                        "brand_slug": brand.slug,
                        "currency":  currency,
                        "min_price_single": _min_price(c.prices, "single", currency, rates, convert),
                        "min_price_box":    _min_price(c.prices, "box",    currency, rates, convert),
                    }
                    for c in s.cigars
                ],
            }
            for s in brand.series
        ],
    }


def _min_price(prices, kind: str, currency: str, rates: dict, convert) -> float | None:
    vals = []
    for p in prices:
        raw = p.price_single if kind == "single" else p.price_box
        v = convert(raw, p.currency)
        if v is not None:
            vals.append(v)
    return min(vals) if vals else None
