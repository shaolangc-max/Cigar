from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Series(Base):
    __tablename__ = "series"

    id:          Mapped[int]       = mapped_column(primary_key=True)
    brand_id:    Mapped[int]       = mapped_column(ForeignKey("brands.id"), index=True)
    name:        Mapped[str]       = mapped_column(String(100))
    slug:        Mapped[str]       = mapped_column(String(150), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    brand:  Mapped["Brand"]         = relationship(back_populates="series")
    cigars: Mapped[list["Cigar"]]   = relationship(back_populates="series")
