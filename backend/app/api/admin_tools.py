"""
/admin-tools — 辅助管理工具（需要 admin session）
功能：触发爬虫（全站 / 单站）。
匹配别名管理已迁移至 /admin-tools/catalog。
"""
import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.db import AsyncSessionLocal  # noqa: F401 — kept for future use

router = APIRouter(prefix="/admin-tools", tags=["admin-tools"])


def _require_admin(request: Request) -> bool:
    return request.session.get("admin", False)


# ── 爬虫触发（session 鉴权，供 SQLAdmin 页内 JS 调用）─────────────────────────

@router.post("/trigger", summary="触发全站爬取")
async def trigger_all(request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from app.scheduler.tasks import run_all_scrapers
    asyncio.create_task(run_all_scrapers())
    return JSONResponse({"status": "triggered", "target": "all"})


@router.post("/trigger/{source_slug}", summary="触发单站爬取")
async def trigger_one(source_slug: str, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    import app.scrapers.sites  # noqa: F401
    from app.scrapers.registry import get_by_slug
    from app.scheduler.tasks import run_single_scraper
    if not get_by_slug(source_slug):
        return JSONResponse({"error": f"未知站点: {source_slug}"}, status_code=404)
    asyncio.create_task(run_single_scraper(source_slug))
    return JSONResponse({"status": "triggered", "target": source_slug})
