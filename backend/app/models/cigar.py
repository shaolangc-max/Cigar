from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Cigar(Base):
    """
    标准化雪茄规格。
    vitola: 茄型名称，如 Robusto / Churchill / Lancero
    length_mm: 茄体长度（毫米）
    ring_gauge: 环径（1/64 英寸）
    """
    __tablename__ = "cigars"

    id:          Mapped[int]        = mapped_column(primary_key=True)
    series_id:   Mapped[int]        = mapped_column(ForeignKey("series.id"), index=True)
    name:        Mapped[str]        = mapped_column(String(200))   # 完整商品名
    slug:        Mapped[str]        = mapped_column(String(250), unique=True, index=True)
    vitola:      Mapped[str | None] = mapped_column(String(100))   # 茄型
    length_mm:   Mapped[float | None] = mapped_column(Float)
    ring_gauge:  Mapped[float | None] = mapped_column(Float)
    image_url:   Mapped[str | None] = mapped_column(String(500))

    series: Mapped["Series"]          = relationship(back_populates="cigars")
    prices: Mapped[list["Price"]]     = relationship(back_populates="cigar")
