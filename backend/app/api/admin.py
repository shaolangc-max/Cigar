"""
管理接口 — 手动触发爬虫、查看状态等。
"""
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])

# 简单的运行状态追踪
_running: dict[str, bool] = {}


class ScrapeResult(BaseModel):
    source: str | None = None
    scraped: int = 0
    matched: int = 0
    saved: int = 0
    errors: list[str] = []


@router.post("/scrape", response_model=list[ScrapeResult], summary="触发所有爬虫")
async def trigger_all(background_tasks: BackgroundTasks):
    """后台运行所有已注册爬虫，立即返回 202。"""
    background_tasks.add_task(_run_all_bg)
    return []


@router.post("/scrape/{source_slug}", response_model=ScrapeResult, summary="触发单个爬虫（同步）")
async def trigger_one(source_slug: str):
    """同步运行指定爬虫，等待完成后返回结果。适合测试单个爬虫。"""
    if _running.get(source_slug):
        raise HTTPException(409, detail=f"Scraper '{source_slug}' is already running")

    from app.scrapers.runner import run_scraper
    _running[source_slug] = True
    try:
        result = await run_scraper(source_slug)
    finally:
        _running[source_slug] = False

    if "error" in result:
        raise HTTPException(404, detail=result["error"])
    result.setdefault("source", source_slug)
    return result


@router.get("/scrapers", summary="查看已注册的爬虫列表")
async def list_scrapers():
    import app.scrapers.sites  # noqa: F401
    from app.scrapers.registry import _registry
    return {"scrapers": list(_registry.keys())}


async def _run_all_bg():
    from app.scrapers.runner import run_all_scrapers
    import logging
    log = logging.getLogger(__name__)
    results = await run_all_scrapers()
    for r in results:
        log.info("Scrape done: %s", r)
