"""
支付相关接口

流程：
  1. 前端 POST /billing/checkout  →  后端创建 Stripe Checkout Session，返回跳转 URL
  2. 用户在 Stripe 托管页面完成付款
  3. Stripe 把付款结果 POST 到 /billing/webhook
  4. 后端收到 webhook，更新用户的订阅状态
"""

from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.db import get_db
from app.models.user import User

router = APIRouter(prefix="/billing", tags=["billing"])

# 用配置里的密钥初始化 Stripe
stripe.api_key = settings.stripe_secret_key


# ── 创建支付会话 ────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str   # "monthly" 或 "yearly"


class CheckoutResponse(BaseModel):
    checkout_url: str   # 跳转到 Stripe 托管支付页面的 URL


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="支付功能尚未配置，请联系管理员")

    if body.plan == "monthly":
        price_id = settings.stripe_price_monthly
    elif body.plan == "yearly":
        price_id = settings.stripe_price_yearly
    else:
        raise HTTPException(status_code=400, detail="plan 必须是 monthly 或 yearly")

    if not price_id:
        raise HTTPException(status_code=503, detail="该套餐尚未配置，请联系管理员")

    # 如果用户还没有 Stripe Customer ID，先创建一个
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        user.stripe_customer_id = customer.id
        await db.commit()

    # 创建 Stripe Checkout Session（托管支付页面）
    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.frontend_url}/pricing",
        metadata={"user_id": str(user.id)},
    )

    return CheckoutResponse(checkout_url=session.url)


# ── Stripe Webhook（付款结果回调）──────────────────────────────────────────────

@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """
    Stripe 在以下事件发生时会 POST 到此接口：
      - checkout.session.completed   付款成功
      - customer.subscription.updated  订阅续费/变更
      - customer.subscription.deleted  订阅取消
    """
    body = await request.body()

    # 用 webhook secret 验证请求确实来自 Stripe，防止伪造
    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Webhook 签名验证失败")

    event_type = event["type"]
    data = event["data"]["object"]

    # ── 付款成功 ──────────────────────────────────────────────────────────────
    if event_type == "checkout.session.completed":
        user_id = int(data["metadata"].get("user_id", 0))
        subscription_id = data.get("subscription")

        if user_id and subscription_id:
            # 获取订阅详情，拿到到期时间
            sub = stripe.Subscription.retrieve(subscription_id)
            expires_at = datetime.fromtimestamp(
                sub["current_period_end"], tz=timezone.utc
            )

            user = await db.get(User, user_id)
            if user:
                user.subscription_status = "pro"
                user.subscription_expires_at = expires_at
                await db.commit()

    # ── 订阅续费或变更 ─────────────────────────────────────────────────────────
    elif event_type == "customer.subscription.updated":
        customer_id = data["customer"]
        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user:
            expires_at = datetime.fromtimestamp(
                data["current_period_end"], tz=timezone.utc
            )
            # active / trialing 都算有效
            if data["status"] in ("active", "trialing"):
                user.subscription_status = "pro"
                user.subscription_expires_at = expires_at
            else:
                user.subscription_status = "expired"
            await db.commit()

    # ── 订阅取消 ───────────────────────────────────────────────────────────────
    elif event_type == "customer.subscription.deleted":
        customer_id = data["customer"]
        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.subscription_status = "expired"
            await db.commit()

    return {"received": True}


# ── 查询当前订阅状态 ────────────────────────────────────────────────────────────

class SubscriptionStatus(BaseModel):
    status: str
    expires_at: datetime | None


@router.get("/status", response_model=SubscriptionStatus)
async def subscription_status(user: User = Depends(get_current_user)):
    """返回当前用户的订阅状态，前端用于显示是否为 PRO"""
    return SubscriptionStatus(
        status=user.subscription_status,
        expires_at=user.subscription_expires_at,
    )
