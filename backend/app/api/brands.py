from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import Brand, Category, Series, Cigar, Price, ExchangeRate

router = APIRouter(prefix="/brands", tags=["brands"])

SUPPORTED_CURRENCIES = {"CNY", "HKD", "USD", "EUR"}


@router.get("")
async def list_brands(db: AsyncSession = Depends(get_db)):
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
            selectinload(Brand.categories),
            selectinload(Brand.series)
                .selectinload(Series.cigars)
                .selectinload(Cigar.prices),
        )
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(404, "Brand not found")

    rates_result = await db.execute(select(ExchangeRate))
    rates = {r.currency: r.rate_to_usd for r in rates_result.scalars().all()}

    def convert(amount: float | None, from_ccy: str) -> float | None:
        if amount is None:
            return None
        in_usd = amount / (rates.get(from_ccy, 1.0) or 1.0)
        return round(in_usd * (rates.get(currency, 1.0) or 1.0), 2)

    def cigar_payload(c: Cigar, s: Series) -> dict:
        return {
            "id":               c.id,
            "name":             c.name,
            "slug":             c.slug,
            "vitola":           c.vitola,
            "image_url":        c.image_url,
            "series":           s.name,
            "brand":            brand.name,
            "brand_slug":       brand.slug,
            "currency":         currency,
            "min_price_single": _min_price(c.prices, "single", convert),
            "min_price_box":    _min_price(c.prices, "box",    convert),
        }

    # Build flat cigar list with series context
    all_cigars: list[tuple[Cigar, Series]] = []
    for s in brand.series:
        for c in s.cigars:
            all_cigars.append((c, s))

    # Separate into categorized (by cigar.category_id) and uncategorized
    cat_map: dict[int, Category] = {c.id: c for c in brand.categories}
    # cigars grouped by category_id
    cat_cigars: dict[int, list[dict]] = {c.id: [] for c in brand.categories}
    # cigars without category_id → fall back to series grouping
    uncategorized_by_series: dict[int, tuple[Series, list[dict]]] = {}

    for cigar, series in all_cigars:
        payload = cigar_payload(cigar, series)
        if cigar.category_id and cigar.category_id in cat_cigars:
            cat_cigars[cigar.category_id].append(payload)
        else:
            if series.id not in uncategorized_by_series:
                uncategorized_by_series[series.id] = (series, [])
            uncategorized_by_series[series.id][1].append(payload)

    # Build category tree (recursive)
    def build_tree(parent_id: int | None) -> list[dict]:
        children = [
            c for c in brand.categories
            if (c.parent_id or None) == parent_id
        ]
        children.sort(key=lambda c: (c.sort_order, c.name))
        result_nodes = []
        for cat in children:
            sub = build_tree(cat.id)
            cigars_here = cat_cigars.get(cat.id, [])
            # Only include node if it has cigars or sub-nodes
            if cigars_here or sub:
                result_nodes.append({
                    "id":         cat.id,
                    "name":       cat.name,
                    "slug":       cat.slug,
                    "sort_order": cat.sort_order,
                    "children":   sub,
                    "cigars":     cigars_here,
                })
        return result_nodes

    category_tree = build_tree(None)

    # Uncategorized → series groups (existing behaviour)
    uncategorized_series = [
        {
            "id":     s.id,
            "name":   s.name,
            "slug":   s.slug,
            "cigars": cigars,
        }
        for s, cigars in sorted(uncategorized_by_series.values(), key=lambda x: x[0].name)
        if cigars
    ]

    return {
        "id":               brand.id,
        "name":             brand.name,
        "slug":             brand.slug,
        "country":          brand.country,
        "image_url":        brand.image_url,
        "category_tree":    category_tree,     # new: recursive tree with cigars
        "series":           uncategorized_series,  # cigars not yet categorized
        # Legacy compat: flat categories list (empty now, tree replaces it)
        "categories":       [],
    }


def _min_price(prices, kind: str, convert) -> float | None:
    vals = []
    for p in prices:
        raw = p.price_single if kind == "single" else p.price_box
        v = convert(raw, p.currency)
        if v is not None:
            vals.append(v)
    return min(vals) if vals else None
