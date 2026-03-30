from typing import Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Series(Base):
    __tablename__ = "series"

    id:          Mapped[int]           = mapped_column(primary_key=True)
    brand_id:    Mapped[int]           = mapped_column(ForeignKey("brands.id"), index=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    name:        Mapped[str]           = mapped_column(String(100))
    slug:        Mapped[str]           = mapped_column(String(150), unique=True, index=True)

    brand:    Mapped["Brand"]            = relationship(back_populates="series")
    category: Mapped[Optional["Category"]] = relationship(back_populates="series")
    cigars:   Mapped[list["Cigar"]]      = relationship(back_populates="series")
