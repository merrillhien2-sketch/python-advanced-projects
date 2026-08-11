"""用户相关 Schema

定义用户注册、登录、信息响应及令牌响应的数据模型。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """用户注册请求"""

    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        description="邮箱地址",
    )
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class UserLogin(BaseModel):
    """用户登录请求"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    is_active: bool = Field(..., description="是否激活")
    role: str = Field(..., description="用户角色")
    created_at: datetime = Field(..., description="创建时间")


class TokenResponse(BaseModel):
    """令牌响应"""

    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌有效期（秒）")
