"""代理 IP 池 Schema

定义代理 IP 创建、响应、批量导入及获取请求的数据模型，
用于请求参数校验与响应结构约束。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProxyIPCreate(BaseModel):
    """代理 IP 创建请求"""

    ip: str = Field(..., description="代理IP地址")
    port: int = Field(..., ge=1, le=65535, description="代理端口")
    protocol: str = Field(default="http", description="代理协议")
    region: Optional[str] = Field(default=None, description="归属地区")
    is_anonymous: bool = Field(default=True, description="是否匿名")


class ProxyIPResponse(BaseModel):
    """代理 IP 信息响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="记录ID")
    ip: str = Field(..., description="代理IP地址")
    port: int = Field(..., description="代理端口")
    protocol: str = Field(..., description="代理协议")
    region: Optional[str] = Field(default=None, description="归属地区")
    is_anonymous: bool = Field(..., description="是否匿名")
    speed: Optional[float] = Field(default=None, description="响应时间(毫秒)")
    is_available: bool = Field(..., description="是否可用")
    last_check_at: Optional[datetime] = Field(
        default=None, description="上次检查时间"
    )
    fail_count: int = Field(..., description="连续失败次数")
    created_at: datetime = Field(..., description="创建时间")


class ProxyIPBatchImport(BaseModel):
    """代理 IP 批量导入请求"""

    proxies: list[ProxyIPCreate] = Field(..., description="代理IP列表")


class ProxyGetRequest(BaseModel):
    """随机获取代理请求参数"""

    protocol: Optional[str] = Field(default=None, description="代理协议筛选")
    region: Optional[str] = Field(default=None, description="归属地区筛选")
    anonymous: Optional[bool] = Field(default=None, description="是否匿名筛选")
