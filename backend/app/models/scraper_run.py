from datetime import datetime
from typing import Optional
from sqlalchemy import Float, Integer, ForeignKey, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ScraperRun(Base):
    """每次爬虫运行的记录"""
    __tablename__ = "scraper_runs"

    id:               Mapped[int]           = mapped_column(primary_key=True)
    source_slug:      Mapped[str]           = mapped_column(String(50), index=True)
    started_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True))
    finished_at:      Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status:           Mapped[str]           = mapped_column(String(20), default="running")
    # running / success / failed / partial
    items_scraped:    Mapped[int]           = mapped_column(Integer, default=0)
    items_matched:    Mapped[int]           = mapped_column(Integer, default=0)
    items_unmatched:  Mapped[int]           = mapped_column(Integer, default=0)
    error_msg:        Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    unmatched_items: Mapped[list["UnmatchedItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class UnmatchedItem(Base):
    """爬取到但未能匹配到数据库 cigar 的条目"""
    __tablename__ = "unmatched_items"

    id:             Mapped[int]             = mapped_column(primary_key=True)
    run_id:         Mapped[int]             = mapped_column(ForeignKey("scraper_runs.id"), index=True)
    source_slug:    Mapped[str]             = mapped_column(String(50), index=True)
    raw_name:       Mapped[str]             = mapped_column(String(500))
    price_single:   Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_box:      Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency:       Mapped[str]             = mapped_column(String(10))
    product_url:    Mapped[Optional[str]]   = mapped_column(String(500), nullable=True)
    match_score:    Mapped[Optional[float]] = mapped_column(Float, nullable=True)   # 最高相似度（0~1）
    best_candidate: Mapped[Optional[str]]   = mapped_column(String(500), nullable=True)  # 最接近的雪茄名

    run: Mapped["ScraperRun"] = relationship(back_populates="unmatched_items")
