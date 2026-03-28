from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SearchQuota(Base):
    """每日搜索次数配额（登录用户按 user_id，游客按 IP）"""
    __tablename__ = "search_quotas"
    __table_args__ = (
        UniqueConstraint("user_id", "quota_date", name="uq_quota_user_date"),
        UniqueConstraint("ip",      "quota_date", name="uq_quota_ip_date"),
    )

    id:         Mapped[int]        = mapped_column(primary_key=True)
    user_id:    Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    ip:         Mapped[str | None] = mapped_column(String(45))
    quota_date: Mapped[date]       = mapped_column(Date, index=True)
    count:      Mapped[int]        = mapped_column(Integer, default=0)
