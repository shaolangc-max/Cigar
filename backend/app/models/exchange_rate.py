from datetime import datetime
from sqlalchemy import Float, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base


class ExchangeRate(Base):
    """汇率缓存（以 USD 为基准）"""
    __tablename__ = "exchange_rates"

    currency:   Mapped[str]      = mapped_column(String(10), primary_key=True)
    rate_to_usd: Mapped[float]   = mapped_column(Float)   # 1 USD = rate 该货币
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
