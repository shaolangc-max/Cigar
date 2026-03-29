from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class User(Base):
    """用户主表"""
    __tablename__ = "users"

    id:           Mapped[int]           = mapped_column(primary_key=True)
    email:        Mapped[str]           = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None]   = mapped_column(String(255))        # 纯 OAuth 用户可为空
    nickname:     Mapped[str | None]    = mapped_column(String(50))
    avatar_url:   Mapped[str | None]   = mapped_column(String(500))

    # 订阅
    subscription_status:     Mapped[str]            = mapped_column(String(20), default="free")  # free / pro / expired
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stripe_customer_id:      Mapped[str | None]     = mapped_column(String(100))

    # 安全与合规
    registered_ip:     Mapped[str | None] = mapped_column(String(45))       # 支持 IPv6
    registered_at:     Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_email_verified: Mapped[bool]       = mapped_column(Boolean, default=False)
    age_confirmed:     Mapped[bool]       = mapped_column(Boolean, default=False)  # 注册时勾选"已满18岁"
    consent_version:   Mapped[str | None] = mapped_column(String(20))       # 记录同意的隐私条款版本，如 "1.0"

    # 偏好
    preferred_currency: Mapped[str] = mapped_column(String(10), default="USD")
    locale:             Mapped[str] = mapped_column(String(10), default="zh-CN")

    # 关联
    oauth_accounts: Mapped[list["OAuthAccount"]]  = relationship(back_populates="user", cascade="all, delete-orphan")
    favorites:      Mapped[list["UserFavorite"]]  = relationship(back_populates="user", cascade="all, delete-orphan")
    price_alerts:   Mapped[list["UserPriceAlert"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    view_history:   Mapped[list["UserViewHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class OAuthAccount(Base):
    """第三方 OAuth 绑定（一个用户可绑定多个）"""
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_uid"),
    )

    id:               Mapped[int]      = mapped_column(primary_key=True)
    user_id:          Mapped[int]      = mapped_column(ForeignKey("users.id"), index=True)
    provider:         Mapped[str]      = mapped_column(String(20))   # google / wechat / alipay / apple
    provider_user_id: Mapped[str]      = mapped_column(String(255))  # 第三方平台的唯一 ID
    linked_at:        Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")


class UserFavorite(Base):
    """用户收藏的雪茄"""
    __tablename__ = "user_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "cigar_id", name="uq_favorite_user_cigar"),
    )

    id:         Mapped[int]      = mapped_column(primary_key=True)
    user_id:    Mapped[int]      = mapped_column(ForeignKey("users.id"), index=True)
    cigar_id:   Mapped[int]      = mapped_column(ForeignKey("cigars.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user:  Mapped["User"]  = relationship(back_populates="favorites")
    cigar: Mapped["Cigar"] = relationship()


class UserPriceAlert(Base):
    """价格提醒：price=低于目标价通知，stock=到货通知"""
    __tablename__ = "user_price_alerts"

    id:               Mapped[int]           = mapped_column(primary_key=True)
    user_id:          Mapped[int]           = mapped_column(ForeignKey("users.id"), index=True)
    cigar_id:         Mapped[int]           = mapped_column(ForeignKey("cigars.id"), index=True)
    alert_type:       Mapped[str]           = mapped_column(String(10), default="price")  # price | stock
    target_price:     Mapped[float | None]  = mapped_column(Float)        # stock 提醒时为 None
    currency:         Mapped[str]           = mapped_column(String(10), default="USD")
    source_id:        Mapped[int | None]    = mapped_column(ForeignKey("sources.id"))
    is_active:        Mapped[bool]          = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())

    user:   Mapped["User"]         = relationship(back_populates="price_alerts")
    cigar:  Mapped["Cigar"]        = relationship()
    source: Mapped["Source | None"] = relationship()


class UserViewHistory(Base):
    """浏览历史（保留30天，自动清理）"""
    __tablename__ = "user_view_history"

    id:         Mapped[int]      = mapped_column(primary_key=True)
    user_id:    Mapped[int]      = mapped_column(ForeignKey("users.id"), index=True)
    cigar_id:   Mapped[int]      = mapped_column(ForeignKey("cigars.id"), index=True)
    viewed_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user:  Mapped["User"]  = relationship(back_populates="view_history")
    cigar: Mapped["Cigar"] = relationship()
