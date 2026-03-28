from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db import get_db
from app.models.user import User

bearer_scheme = HTTPBearer()


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


async def require_pro(user: User = Depends(get_current_user)) -> User:
    """
    检查用户是否有有效的付费订阅
    用于保护价格历史、价格提醒等付费功能
    """
    if user.subscription_status == "pro":
        # 检查订阅是否过期
        if user.subscription_expires_at and user.subscription_expires_at > datetime.now(timezone.utc):
            return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="此功能需要订阅会员，请升级后使用",
    )
