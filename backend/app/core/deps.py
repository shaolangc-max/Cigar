from datetime import date, datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db import get_db
from app.models.user import User
from app.models.search_quota import SearchQuota

bearer_scheme = HTTPBearer()
bearer_optional = HTTPBearer(auto_error=False)

FREE_SEARCH_LIMIT = 15


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    从请求头的 Authorization: Bearer <token> 中解析出当前用户
    Token 无效或用户不存在时返回 401 错误
    """
    token = credentials.credentials
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期，请重新登录",
        )

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """尝试从 Token 中解析用户，没有 Token 或无效时返回 None（不报错）"""
    if credentials is None:
        return None
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        return None
    return await db.get(User, user_id)


async def check_search_quota(
    request: Request,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    搜索限速：免费用户（含游客）每天最多 15 次搜索。
    PRO 用户不限速。超限返回 429。
    """
    # PRO 用户直接放行
    if user and user.subscription_status == "pro":
        expires = user.subscription_expires_at
        if expires is not None:
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires > datetime.now(timezone.utc):
                return

    today = date.today()

    if user:
        # 登录用户按 user_id 记录
        stmt = select(SearchQuota).where(
            SearchQuota.user_id == user.id,
            SearchQuota.quota_date == today,
        )
    else:
        # 游客按 IP 记录
        client_ip = request.client.host if request.client else "unknown"
        stmt = select(SearchQuota).where(
            SearchQuota.ip == client_ip,
            SearchQuota.quota_date == today,
        )

    result = await db.execute(stmt)
    quota = result.scalar_one_or_none()

    if quota is None:
        # 第一次搜索，建记录
        quota = SearchQuota(
            user_id=user.id if user else None,
            ip=None if user else (request.client.host if request.client else "unknown"),
            quota_date=today,
            count=1,
        )
        db.add(quota)
    else:
        if quota.count >= FREE_SEARCH_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"今日搜索次数已用完（{FREE_SEARCH_LIMIT}次），升级 PRO 享无限搜索",
            )
        quota.count += 1

    await db.commit()


async def require_pro(user: User = Depends(get_current_user)) -> User:
    """
    检查用户是否有有效的付费订阅
    用于保护价格历史、价格提醒等付费功能
    """
    if user.subscription_status == "pro":
        expires = user.subscription_expires_at
        if expires is not None:
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires > datetime.now(timezone.utc):
                return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="此功能需要订阅会员，请升级后使用",
    )
