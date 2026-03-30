from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Category(Base):
    """
    品牌下的大类分组，如 Cohiba → Handmade Cigars / Machine-made Cigars。
    纯展示用，不影响爬虫匹配逻辑。
    """
    __tablename__ = "categories"

    id:         Mapped[int]      = mapped_column(primary_key=True)
    brand_id:   Mapped[int]      = mapped_column(ForeignKey("brands.id"), index=True)
    name:       Mapped[str]      = mapped_column(String(100))
    slug:       Mapped[str]      = mapped_column(String(150), unique=True, index=True)
    sort_order: Mapped[int]      = mapped_column(Integer, default=0)

    brand:  Mapped["Brand"]        = relationship(back_populates="categories")
    series: Mapped[list["Series"]] = relationship(back_populates="category")
