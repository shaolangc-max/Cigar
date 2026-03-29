from datetime import datetime
from sqlalchemy import Float, Integer, ForeignKey, DateTime, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Price(Base):
    """各站当前价格（每次抓取覆盖）"""
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint("cigar_id", "source_id", name="uq_price_cigar_source"),
    )

    id:           Mapped[int]         = mapped_column(primary_key=True)
    cigar_id:     Mapped[int]         = mapped_column(ForeignKey("cigars.id"), index=True)
    source_id:    Mapped[int]         = mapped_column(ForeignKey("sources.id"), index=True)
    price_single: Mapped[float | None] = mapped_column(Float)  # 单支价格（原币种）
    price_box:    Mapped[float | None] = mapped_column(Float)  # 盒装价格（原币种）
    box_count:    Mapped[int | None]   = mapped_column(Integer)  # 盒装支数
    currency:     Mapped[str]          = mapped_column(String(10))
    product_url:  Mapped[str | None]   = mapped_column(String(500))
    in_stock:     Mapped[bool]         = mapped_column(default=True)
    scraped_at:   Mapped[datetime]     = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    cigar:  Mapped["Cigar"]  = relationship(back_populates="prices")
    source: Mapped["Source"] = relationship(back_populates="prices")


class PriceHistory(Base):
    """价格历史（每次抓取追加）"""
    __tablename__ = "price_history"

    id:           Mapped[int]         = mapped_column(primary_key=True)
    cigar_id:     Mapped[int]         = mapped_column(ForeignKey("cigars.id"), index=True)
    source_id:    Mapped[int]         = mapped_column(ForeignKey("sources.id"), index=True)
    price_single: Mapped[float | None] = mapped_column(Float)
    price_box:    Mapped[float | None] = mapped_column(Float)
    currency:     Mapped[str]          = mapped_column(String(10))
    scraped_at:   Mapped[datetime]     = mapped_column(DateTime(timezone=True), index=True)
