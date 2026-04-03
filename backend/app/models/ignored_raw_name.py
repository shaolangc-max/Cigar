from datetime import datetime, timezone
from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class IgnoredRawName(Base):
    """管理员手动忽略的 (source_slug, raw_name) 组合，爬虫重跑后不再展示"""
    __tablename__ = "ignored_raw_names"
    __table_args__ = (
        UniqueConstraint("source_slug", "raw_name", name="uq_ignored_source_raw"),
    )

    id:          Mapped[int]      = mapped_column(primary_key=True)
    source_slug: Mapped[str]      = mapped_column(String(50), index=True)
    raw_name:    Mapped[str]      = mapped_column(String(500))
    ignored_at:  Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
