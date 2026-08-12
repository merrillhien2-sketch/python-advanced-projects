"""电商价格监控相关 Schema

定义商品创建、商品响应、价格历史、价格告警、价格统计等
数据模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    """商品创建请求

    属性:
        name: 商品名称
        url: 商品链接地址
        platform: 商品平台（jd/tmall/pdd/amazon）
        target_price: 目标价格，可为空
        image_url: 商品图片链接，可为空
    """

    name: str = Field(..., description="商品名称")
    url: str = Field(..., description="商品链接")
    platform: str = Field(..., description="商品平台")
    target_price: Optional[float] = Field(default=None, description="目标价格")
    image_url: Optional[str] = Field(default=None, description="商品图片链接")


class ProductResponse(BaseModel):
    """商品响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="商品ID")
    name: str = Field(..., description="商品名称")
    url: str = Field(..., description="商品链接")
    platform: str = Field(..., description="商品平台")
    current_price: Optional[float] = Field(default=None, description="当前价格")
    target_price: Optional[float] = Field(default=None, description="目标价格")
    image_url: Optional[str] = Field(default=None, description="商品图片链接")
    is_active: bool = Field(..., description="是否启用监控")
    created_at: datetime = Field(..., description="创建时间")


class PriceHistoryResponse(BaseModel):
    """价格历史响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="记录ID")
    product_id: int = Field(..., description="商品ID")
    price: float = Field(..., description="价格")
    recorded_at: datetime = Field(..., description="记录时间")


class PriceAlertResponse(BaseModel):
    """价格告警响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="告警ID")
    product_id: int = Field(..., description="商品ID")
    alert_type: str = Field(..., description="告警类型")
    threshold: Optional[float] = Field(default=None, description="告警阈值")
    message: Optional[str] = Field(default=None, description="告警消息")
    is_read: bool = Field(..., description="是否已读")
    created_at: datetime = Field(..., description="创建时间")


class PriceStats(BaseModel):
    """价格统计

    属性:
        product_id: 商品 ID
        name: 商品名称
        current_price: 当前价格
        lowest_price: 历史最低价
        highest_price: 历史最高价
        avg_price: 平均价
        price_change_rate: 涨跌幅（百分比）
        total_records: 总记录数
    """

    product_id: int = Field(..., description="商品ID")
    name: str = Field(..., description="商品名称")
    current_price: Optional[float] = Field(default=None, description="当前价格")
    lowest_price: Optional[float] = Field(default=None, description="历史最低价")
    highest_price: Optional[float] = Field(default=None, description="历史最高价")
    avg_price: Optional[float] = Field(default=None, description="平均价")
    price_change_rate: Optional[float] = Field(
        default=None, description="涨跌幅(百分比)"
    )
    total_records: int = Field(0, description="总记录数")
