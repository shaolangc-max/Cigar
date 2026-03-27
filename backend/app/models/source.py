from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Source(Base):
    """来源网站配置"""
    __tablename__ = "sources"

    id:          Mapped[int]  = mapped_column(primary_key=True)
    name:        Mapped[str]  = mapped_column(String(100), unique=True)
    slug:        Mapped[str]  = mapped_column(String(100), unique=True, index=True)
    base_url:    Mapped[str]  = mapped_column(String(500))
    currency:    Mapped[str]  = mapped_column(String(10))   # CNY / HKD / USD / EUR
    active:      Mapped[bool] = mapped_column(Boolean, default=True)
    # 爬虫配置 JSON: {"type": "static"|"playwright", "selectors": {...}}
    scraper_config: Mapped[dict | None] = mapped_column(JSON)

    prices: Mapped[list["Price"]] = relationship(back_populates="source")
