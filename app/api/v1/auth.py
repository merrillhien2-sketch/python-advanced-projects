"""认证路由

提供用户注册、登录和获取当前用户信息的接口。

接口列表:
    - POST /register  用户注册
    - POST /login     用户登录，返回 JWT 令牌
    - GET  /me        获取当前用户信息（需要认证）
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationException,
    BusinessException,
    NotFoundException,
    ValidationException,
)
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.common import ResponseBase
from app.schemas.user import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=ResponseBase[UserResponse], summary="用户注册")
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[UserResponse]:
    """用户注册

    接收用户名、邮箱和密码，校验唯一性后创建用户账户。
    密码经过哈希加密后存储，不保存明文。

    参数:
        user_in: 用户注册信息（用户名、邮箱、密码）
        db: 异步数据库会话

    返回:
        包含新用户信息的响应
    """
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalar_one_or_none() is not None:
        raise ValidationException("用户名已存在")

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none() is not None:
        raise ValidationException("邮箱已被注册")

    try:
        # 哈希加密密码
        hashed_pwd = hash_password(user_in.password)

        # 创建用户
        user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_pwd,
            is_active=True,
            role="user",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return ResponseBase(data=UserResponse.model_validate(user))
    except Exception as e:
        await db.rollback()
        raise BusinessException(message=f"用户注册失败: {e}")


@router.post("/login", response_model=ResponseBase[TokenResponse], summary="用户登录")
async def login(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[TokenResponse]:
    """用户登录

    验证用户名和密码，成功后签发 JWT 访问令牌。

    参数:
        user_in: 登录凭据（用户名、密码）
        db: 异步数据库会话

    返回:
        包含 JWT 令牌的响应
    """
    # 根据用户名查询用户
    result = await db.execute(select(User).where(User.username == user_in.username))
    user = result.scalar_one_or_none()

    # 用户不存在或密码错误
    if user is None or not verify_password(user_in.password, user.hashed_password):
        raise AuthenticationException("用户名或密码错误")

    # 检查账户是否激活
    if not user.is_active:
        raise AuthenticationException("账户已被禁用，请联系管理员")

    # 签发 JWT 令牌
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    token_data = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return ResponseBase(data=token_data)


@router.get("/me", response_model=ResponseBase[UserResponse], summary="获取当前用户信息")
async def get_me(
    current_user: User = Depends(get_current_user),
) -> ResponseBase[UserResponse]:
    """获取当前登录用户信息

    需要携带有效的 JWT 令牌进行认证。
    get_current_user 依赖从 Authorization 头解析令牌并加载 User 对象。

    参数:
        current_user: 当前登录的 User 对象（由 get_current_user 依赖注入）

    返回:
        包含当前用户信息的响应
    """
    return ResponseBase(data=UserResponse.model_validate(current_user))
