from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ScraperNameAlias(Base):
    """管理员手动建立的 (source_slug, raw_name) → Cigar 映射"""
    __tablename__ = "scraper_name_aliases"
    __table_args__ = (
        UniqueConstraint("source_slug", "raw_name", name="uq_alias_source_raw"),
    )

    id:          Mapped[int]      = mapped_column(primary_key=True)
    source_slug: Mapped[str]      = mapped_column(String(50), index=True)
    raw_name:    Mapped[str]      = mapped_column(String(500))
    cigar_id:    Mapped[int]      = mapped_column(ForeignKey("cigars.id"), index=True)
    created_at:  Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    cigar: Mapped["Cigar"] = relationship()
