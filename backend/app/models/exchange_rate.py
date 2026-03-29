from datetime import datetime
from sqlalchemy import Float, String, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ExchangeRate(Base):
    """汇率缓存（以 USD 为基准）"""
    __tablename__ = "exchange_rates"

    currency:   Mapped[str]      = mapped_column(String(10), primary_key=True)
    rate_to_usd: Mapped[float]   = mapped_column(Float)   # 1 USD = rate 该货币
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
