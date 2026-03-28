from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# 使用 bcrypt 算法加密密码（业界标准，不可逆）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """把明文密码加密成哈希值，存入数据库"""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """验证用户输入的密码是否和数据库中的哈希值匹配"""
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    """
    生成 JWT Token（用户登录后颁发的"通行证"）
    Token 里存了 user_id，有效期7天
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """
    解析 JWT Token，返回 user_id
    Token 无效或过期时返回 None
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None
