from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import Brand, Series, Cigar

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("")
async def list_brands(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).order_by(Brand.name))
    brands = result.scalars().all()
    return [{"id": b.id, "name": b.name, "slug": b.slug, "logo_url": b.logo_url} for b in brands]


@router.get("/{slug}")
async def get_brand(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Brand)
        .where(Brand.slug == slug)
        .options(selectinload(Brand.series).selectinload(Series.cigars))
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(404, "Brand not found")
    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "description": brand.description,
        "logo_url": brand.logo_url,
        "series": [
            {
                "id": s.id,
                "name": s.name,
                "slug": s.slug,
                "cigars": [
                    {"id": c.id, "name": c.name, "slug": c.slug,
                     "vitola": c.vitola, "image_url": c.image_url}
                    for c in s.cigars
                ],
            }
            for s in brand.series
        ],
    }
