"""
爬虫监控管理接口 — 查看运行记录、汇总统计、未匹配条目、手动触发。
仅限已登录用户访问（生产环境建议进一步限制为管理员）。
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, cast, Float, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db import get_db
from app.models import ScraperRun, UnmatchedItem
from app.models.user import User

router = APIRouter(prefix="/scraper-admin", tags=["scraper-admin"])


# ── GET /runs ─────────────────────────────────────────────────────────────────

@router.get("/runs", summary="最近100条爬虫运行记录")
async def list_runs(
    source_slug: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    stmt = select(ScraperRun).order_by(ScraperRun.started_at.desc()).limit(100)
    if source_slug:
        stmt = stmt.where(ScraperRun.source_slug == source_slug)
    if status:
        stmt = stmt.where(ScraperRun.status == status)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "source_slug": r.source_slug,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "status": r.status,
            "items_scraped": r.items_scraped,
            "items_matched": r.items_matched,
            "items_unmatched": r.items_unmatched,
            "error_msg": r.error_msg,
        }
        for r in rows
    ]


# ── GET /runs/summary ─────────────────────────────────────────────────────────

@router.get("/runs/summary", summary="按 source_slug 汇总运行统计")
async def runs_summary(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    stmt = (
        select(
            ScraperRun.source_slug,
            func.count(ScraperRun.id).label("total_runs"),
            func.sum(
                case((ScraperRun.status == "success", 1), else_=0)
            ).label("success_runs"),
            func.avg(
                case(
                    (ScraperRun.items_scraped > 0,
                     cast(ScraperRun.items_matched, Float) / ScraperRun.items_scraped * 100),
                    else_=None,
                )
            ).label("avg_match_rate"),
            func.max(ScraperRun.started_at).label("last_run_at"),
        )
        .group_by(ScraperRun.source_slug)
        .order_by(ScraperRun.source_slug)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "source_slug": r.source_slug,
            "total_runs": r.total_runs,
            "success_runs": r.success_runs or 0,
            "avg_match_rate": round(r.avg_match_rate, 1) if r.avg_match_rate is not None else None,
            "last_run_at": r.last_run_at,
        }
        for r in rows
    ]


# ── GET /unmatched ────────────────────────────────────────────────────────────

@router.get("/unmatched", summary="未匹配条目列表（最近500条）")
async def list_unmatched(
    source_slug: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    stmt = (
        select(UnmatchedItem)
        .order_by(UnmatchedItem.id.desc())
        .limit(500)
    )
    if source_slug:
        stmt = stmt.where(UnmatchedItem.source_slug == source_slug)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id": u.id,
            "run_id": u.run_id,
            "source_slug": u.source_slug,
            "raw_name": u.raw_name,
            "price_single": u.price_single,
            "price_box": u.price_box,
            "currency": u.currency,
            "product_url": u.product_url,
        }
        for u in rows
    ]


# ── GET /sources ───────────────────────────────────────────────────────────────

@router.get("/sources", summary="所有已注册爬虫站点")
async def list_sources(_user: User = Depends(get_current_user)):
    import app.scrapers.sites  # noqa: F401
    from app.scrapers.registry import get_all
    scrapers = get_all()
    return [{"source_slug": s.source_slug} for s in scrapers]


# ── POST /trigger ──────────────────────────────────────────────────────────────

@router.post("/trigger", status_code=202, summary="触发全站爬取")
async def trigger_all(_user: User = Depends(get_current_user)):
    from app.scheduler.tasks import run_all_scrapers
    asyncio.create_task(run_all_scrapers())
    return {"status": "triggered", "target": "all"}


@router.post("/trigger/{source_slug}", status_code=202, summary="触发单站爬取")
async def trigger_one(
    source_slug: str,
    _user: User = Depends(get_current_user),
):
    import app.scrapers.sites  # noqa: F401
    from app.scrapers.registry import get_by_slug
    from app.scheduler.tasks import run_single_scraper
    if not get_by_slug(source_slug):
        raise HTTPException(404, f"未知站点: {source_slug}")
    asyncio.create_task(run_single_scraper(source_slug))
    return {"status": "triggered", "target": source_slug}
