"""通用响应 Schema

定义统一的 API 响应包装结构，包括标准响应和分页响应。
所有接口返回的数据均使用这两个包装器进行封装，保证响应格式一致。
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

# 泛型类型变量，用于响应数据的类型参数化
T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    """标准响应包装

    统一的 API 响应结构，包含状态码、消息和数据体。

    属性:
        code: 业务状态码，200 表示成功
        message: 提示消息
        data: 响应数据，泛型类型
    """

    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应包装

    用于返回分页列表数据的响应结构。

    属性:
        code: 业务状态码，200 表示成功
        message: 提示消息
        data: 当前页的数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页条数
    """

    code: int = 200
    message: str = "success"
    data: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
