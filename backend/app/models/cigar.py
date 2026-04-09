from typing import Optional
from sqlalchemy import String, Float, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Cigar(Base):
    """
    标准化雪茄规格。
    vitola: 茄型名称，如 Robusto / Churchill / Lancero
    length_mm: 茄体长度（毫米）
    ring_gauge: 环径（1/64 英寸）
    edition_type: reserva / gran_reserva / edicion_limitada / regional / aniversario / lcdh / None
    edition: 显示用标签，如 "Cosecha 2014" / "Edición Limitada 2021"
    parent_cigar_id: 指向标准版 cigar.id，标准版本身为 None
    category_id: 纯展示分类，指向 categories.id（可空）；与爬虫完全隔离
    """
    __tablename__ = "cigars"

    id:               Mapped[int]            = mapped_column(primary_key=True)
    series_id:        Mapped[int]            = mapped_column(ForeignKey("series.id"), index=True)
    name:             Mapped[str]            = mapped_column(String(200))
    slug:             Mapped[str]            = mapped_column(String(250), unique=True, index=True)
    vitola:           Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    length_mm:        Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ring_gauge:       Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    image_url:        Mapped[Optional[str]]  = mapped_column(String(500), nullable=True)
    edition_type:     Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    edition:          Mapped[Optional[str]]  = mapped_column(String(200), nullable=True)
    parent_cigar_id:  Mapped[Optional[int]]  = mapped_column(ForeignKey("cigars.id"), nullable=True, index=True)
    category_id:      Mapped[Optional[int]]  = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    sort_order:       Mapped[int]            = mapped_column(Integer, default=0, server_default="0")
    description:      Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    image_single_url: Mapped[Optional[str]]  = mapped_column(String(500), nullable=True)
    image_box_url:    Mapped[Optional[str]]  = mapped_column(String(500), nullable=True)

    series:    Mapped["Series"]        = relationship(back_populates="cigars")
    prices:    Mapped[list["Price"]]   = relationship(back_populates="cigar")
    versions:  Mapped[list["Cigar"]]   = relationship("Cigar", foreign_keys=[parent_cigar_id],
                                                       primaryjoin="Cigar.parent_cigar_id == Cigar.id")
    category:  Mapped[Optional["Category"]] = relationship(back_populates="cigars")
