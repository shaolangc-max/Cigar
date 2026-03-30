import urllib.parse
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db import get_db
from app.models.user import OAuthAccount, User

router = APIRouter(prefix="/auth", tags=["auth"])

CURRENT_CONSENT_VERSION = "1.0"

# Google OAuth 端点（固定地址，无需配置）
GOOGLE_AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


# ── 请求/响应结构 ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: str | None = None
    age_confirmed: bool        # 注册时必须勾选"已满18岁"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    subscription_status: str
    nickname: str | None


class MeResponse(BaseModel):
    id: int
    email: str
    nickname: str | None
    avatar_url: str | None
    subscription_status: str
    subscription_expires_at: datetime | None
    preferred_currency: str


# ── 注册 ───────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # 年龄验证：未勾选则拒绝注册
    if not body.age_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请确认您已年满18周岁",
        )

    # 密码长度基础校验
    if len(body.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码至少需要8位",
        )

    # 检查邮箱是否已注册
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该邮箱已注册，请直接登录",
        )

    # 获取注册 IP（优先取反向代理头，用于风控，不对外暴露）
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        nickname=body.nickname,
        age_confirmed=True,
        consent_version=CURRENT_CONSENT_VERSION,
        registered_ip=client_ip,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        subscription_status=user.subscription_status,
        nickname=user.nickname,
    )


# ── 登录 ───────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # 故意不区分"邮箱不存在"和"密码错误"，防止用户枚举攻击
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    # 更新最后登录时间
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        subscription_status=user.subscription_status,
        nickname=user.nickname,
    )


# ── 获取当前用户信息 ────────────────────────────────────────────────────────────

@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)):
    """获取当前登录用户的基本信息（需要 Token）"""
    return MeResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        subscription_status=user.subscription_status,
        subscription_expires_at=user.subscription_expires_at,
        preferred_currency=user.preferred_currency,
    )


# ── Google OAuth ────────────────────────────────────────────────────────────────

@router.get("/google")
async def google_login():
    """把用户重定向到 Google 授权页面，授权后 Google 直接跳回前端页面"""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google 登录尚未配置")

    # 回调直接指向前端页面，浏览器可以直接访问，不经过任何代理
    callback_url = f"{settings.frontend_url.rstrip('/')}/auth/google-callback"
    params = {
        "client_id":     settings.google_client_id,
        "redirect_uri":  callback_url,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "online",
        "hl":            "zh-CN",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}")


@router.post("/google/exchange")
async def google_exchange(request: Request, db: AsyncSession = Depends(get_db)):
    """
    前端拿到 Google 的 code 后，POST 到这里换取 JWT Token。
    新流程：Google → 前端页面 /auth/google-callback → POST 此接口 → 返回 JWT
    """
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google 登录尚未配置")

    body = await request.json()
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="缺少 code 参数")

    # 用前端传来的 redirect_uri，确保与 Google 授权时完全一致
    callback_url = body.get(
        "redirect_uri",
        f"{settings.frontend_url.rstrip('/')}/auth/google-callback"
    )

    async with httpx.AsyncClient() as client:
        # ① 用 code 换 access_token
        token_res = await client.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri":  callback_url,
            "grant_type":    "authorization_code",
        })
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Google 授权失败，请重新登录")

        access_token = token_res.json().get("access_token")

        # ② 获取用户信息
        info_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_res.status_code != 200:
            raise HTTPException(status_code=400, detail="获取 Google 用户信息失败")

    google_info = info_res.json()
    google_id   = google_info.get("sub")
    email       = google_info.get("email", "")
    nickname    = google_info.get("name")
    avatar_url  = google_info.get("picture")
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )

    # ③ 查找或创建用户
    oauth_result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_user_id == google_id,
        )
    )
    oauth_account = oauth_result.scalar_one_or_none()

    if oauth_account:
        user = await db.get(User, oauth_account.user_id)
        if not user:
            raise HTTPException(status_code=500, detail="用户数据异常，请联系管理员")
    else:
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()

        if not user:
            user = User(
                email=email,
                nickname=nickname,
                avatar_url=avatar_url,
                age_confirmed=True,
                is_email_verified=True,
                consent_version=CURRENT_CONSENT_VERSION,
                registered_ip=client_ip,
                last_login_at=datetime.now(timezone.utc),
            )
            db.add(user)
            await db.flush()
        else:
            # 每次登录更新头像（Google 头像可能变化）
            user.avatar_url = avatar_url

        db.add(OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=google_id,
        ))

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    jwt_token = create_access_token(user.id)
    return TokenResponse(
        access_token=jwt_token,
        subscription_status=user.subscription_status,
        nickname=user.nickname,
    )
