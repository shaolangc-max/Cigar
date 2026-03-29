from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_pro
from app.db import get_db
from app.models.user import User, UserPriceAlert

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    cigar_id:     int
    alert_type:   str          # "price" | "stock"
    target_price: float | None = None
    currency:     str = "USD"


class AlertOut(BaseModel):
    id:           int
    cigar_id:     int
    alert_type:   str
    target_price: float | None
    currency:     str
    is_active:    bool


@router.get("", response_model=list[AlertOut])
async def get_alerts(
    cigar_id: int = Query(...),
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """获取当前用户对某款雪茄的提醒设置"""
    result = await db.execute(
        select(UserPriceAlert).where(
            UserPriceAlert.user_id  == user.id,
            UserPriceAlert.cigar_id == cigar_id,
            UserPriceAlert.is_active == True,
        )
    )
    return [
        AlertOut(
            id=a.id, cigar_id=a.cigar_id, alert_type=a.alert_type,
            target_price=a.target_price, currency=a.currency, is_active=a.is_active,
        )
        for a in result.scalars().all()
    ]


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreate,
    user: User = Depends(require_pro),
    db:   AsyncSession = Depends(get_db),
):
    """创建提醒（PRO 专属）"""
    if body.alert_type not in ("price", "stock"):
        raise HTTPException(400, "alert_type 必须是 price 或 stock")
    if body.alert_type == "price" and body.target_price is None:
        raise HTTPException(400, "降价提醒需要提供 target_price")

    # 同类型提醒已存在则先停用
    existing = await db.execute(
        select(UserPriceAlert).where(
            UserPriceAlert.user_id     == user.id,
            UserPriceAlert.cigar_id    == body.cigar_id,
            UserPriceAlert.alert_type  == body.alert_type,
            UserPriceAlert.is_active   == True,
        )
    )
    for old in existing.scalars().all():
        old.is_active = False

    alert = UserPriceAlert(
        user_id=user.id,
        cigar_id=body.cigar_id,
        alert_type=body.alert_type,
        target_price=body.target_price,
        currency=body.currency,
        is_active=True,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return AlertOut(
        id=alert.id, cigar_id=alert.cigar_id, alert_type=alert.alert_type,
        target_price=alert.target_price, currency=alert.currency, is_active=alert.is_active,
    )


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """取消提醒"""
    result = await db.execute(
        select(UserPriceAlert).where(
            UserPriceAlert.id      == alert_id,
            UserPriceAlert.user_id == user.id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "提醒不存在")
    alert.is_active = False
    await db.commit()
