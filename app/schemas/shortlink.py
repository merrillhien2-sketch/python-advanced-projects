"""短链相关 Schema

定义短链创建、响应及跳转请求的数据模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ShortLinkCreate(BaseModel):
    """短链创建请求"""

    original_url: HttpUrl = Field(..., description="原始URL")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")


class ShortLinkResponse(BaseModel):
    """短链信息响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="短链ID")
    original_url: str = Field(..., description="原始URL")
    short_code: str = Field(..., description="短码")
    click_count: int = Field(..., description="点击次数")
    is_active: bool = Field(..., description="是否启用")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")
    created_at: datetime = Field(..., description="创建时间")


class ShortLinkRedirect(BaseModel):
    """短链跳转请求"""

    short_code: str = Field(..., min_length=1, max_length=10, description="短码")
