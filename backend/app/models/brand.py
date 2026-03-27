from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Brand(Base):
    __tablename__ = "brands"

    id:          Mapped[int]  = mapped_column(primary_key=True)
    name:        Mapped[str]  = mapped_column(String(100), unique=True)
    slug:        Mapped[str]  = mapped_column(String(100), unique=True, index=True)
    origin:      Mapped[str]  = mapped_column(String(50), default="Cuba")
    description: Mapped[str | None] = mapped_column(Text)
    logo_url:    Mapped[str | None] = mapped_column(String(500))

    series: Mapped[list["Series"]] = relationship(back_populates="brand")
