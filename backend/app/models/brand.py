from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Brand(Base):
    __tablename__ = "brands"

    id:        Mapped[int]      = mapped_column(primary_key=True)
    name:      Mapped[str]      = mapped_column(String(100), unique=True)
    slug:      Mapped[str]      = mapped_column(String(100), unique=True, index=True)
    country:   Mapped[str | None] = mapped_column(String(50))
    image_url: Mapped[str | None] = mapped_column(String(500))

    series:     Mapped[list["Series"]]    = relationship(back_populates="brand")
    categories: Mapped[list["Category"]] = relationship(back_populates="brand", order_by="Category.sort_order")
