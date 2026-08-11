"""安全工具模块。

提供 JWT 令牌生成与解析、bcrypt 密码哈希与校验，
以及基于 Authorization 头解析当前用户并加载用户对象的 FastAPI 依赖。
所有密钥与算法从 settings 读取。
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationException
from app.models.user import User


# Bearer 认证方案，auto_error=False 以便自定义错误响应
security_scheme = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT 访问令牌。

    Args:
        data: 需要编码到令牌中的声明数据（如用户标识）
        expires_delta: 自定义过期时长，默认使用配置项 ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        编码后的 JWT 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解析并校验 JWT 令牌。

    Args:
        token: JWT 字符串

    Returns:
        解码后的载荷字典

    Raises:
        AuthenticationException: 令牌无效或已过期
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        raise AuthenticationException("无效或已过期的访问令牌")


def hash_password(password: str) -> str:
    """使用 bcrypt 对明文密码进行哈希。

    Args:
        password: 明文密码

    Returns:
        哈希后的密码字符串
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希值是否匹配。

    Args:
        plain: 明文密码
        hashed: 已哈希的密码

    Returns:
        匹配返回 True，否则 False
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI 依赖：从 Authorization 头解析令牌并加载当前用户对象。

    期望请求头格式为 ``Authorization: Bearer <token>``。
    解析令牌后根据 ``sub`` 声明（用户 ID）从数据库加载用户，
    用户不存在或已被禁用时抛出认证异常。

    Args:
        credentials: Bearer 认证凭据
        db: 异步数据库会话

    Returns:
        当前登录的 User 对象

    Raises:
        AuthenticationException: 未提供凭据、令牌无效、用户不存在或已被禁用
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationException("未提供认证凭据")

    payload = decode_access_token(credentials.credentials)

    # 令牌载荷中的 sub 为用户 ID（字符串形式）
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationException("令牌缺少用户标识")

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise AuthenticationException("无效的用户标识")

    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationException("用户不存在或已被删除")
    if not user.is_active:
        raise AuthenticationException("账户已被禁用")

    return user
