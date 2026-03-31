from typing import Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Category(Base):
    """
    品牌下的大类分组，支持多级嵌套（parent_id 自引用）。
    纯展示用，不影响爬虫匹配逻辑。
    例如：Cohiba → Handmade Cigars → Linea Clasica
    """
    __tablename__ = "categories"

    id:         Mapped[int]            = mapped_column(primary_key=True)
    brand_id:   Mapped[int]            = mapped_column(ForeignKey("brands.id"), index=True)
    parent_id:  Mapped[Optional[int]]  = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    name:       Mapped[str]            = mapped_column(String(100))
    slug:       Mapped[str]            = mapped_column(String(150), unique=True, index=True)
    sort_order: Mapped[int]            = mapped_column(Integer, default=0)

    brand:    Mapped["Brand"]              = relationship(back_populates="categories")
    parent:   Mapped[Optional["Category"]] = relationship(
        "Category", foreign_keys=[parent_id], back_populates="children", remote_side="Category.id"
    )
    children: Mapped[list["Category"]]    = relationship(
        "Category", foreign_keys=[parent_id], back_populates="parent", order_by="Category.sort_order"
    )
    series:   Mapped[list["Series"]]      = relationship(back_populates="category")
    cigars:   Mapped[list["Cigar"]]       = relationship(back_populates="category")
