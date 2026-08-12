"""数据分析可视化 Schema

定义订单创建、订单响应、用户画像响应、仪表盘统计及图表数据的
数据模型，用于请求参数校验与响应结构约束。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    """订单创建请求

    用于创建单笔订单记录时的请求体校验。
    """

    order_id: str = Field(..., description="业务订单号")
    product_name: str = Field(..., description="商品名称")
    category: str = Field(..., description="商品品类")
    amount: float = Field(..., description="订单金额")
    quantity: int = Field(..., ge=1, description="购买数量")
    user_id: int = Field(..., description="下单用户ID")
    region: str = Field(..., description="下单地区")
    payment_method: str = Field(..., description="支付方式")
    order_date: datetime = Field(..., description="下单时间")


class OrderResponse(BaseModel):
    """订单信息响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="记录ID")
    order_id: str = Field(..., description="业务订单号")
    product_name: str = Field(..., description="商品名称")
    category: str = Field(..., description="商品品类")
    amount: float = Field(..., description="订单金额")
    quantity: int = Field(..., description="购买数量")
    user_id: int = Field(..., description="下单用户ID")
    region: str = Field(..., description="下单地区")
    payment_method: str = Field(..., description="支付方式")
    order_date: datetime = Field(..., description="下单时间")
    created_at: datetime = Field(..., description="创建时间")


class UserProfileResponse(BaseModel):
    """用户画像信息响应"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(..., description="用户ID")
    age: Optional[int] = Field(default=None, description="年龄")
    gender: Optional[str] = Field(default=None, description="性别")
    region: str = Field(..., description="主要消费地区")
    total_orders: int = Field(..., description="累计订单数")
    total_amount: float = Field(..., description="累计消费金额")
    tags: Optional[str] = Field(default=None, description="消费行为标签")


class DashboardStats(BaseModel):
    """仪表盘统计数据

    汇总全量订单的核心运营指标，用于首页数据看板展示。
    """

    total_revenue: float = Field(default=0.0, description="总营收")
    total_orders: int = Field(default=0, description="总订单数")
    avg_order_amount: float = Field(default=0.0, description="客单价")
    top_categories: list[dict] = Field(
        default_factory=list, description="品类TOP5(品类名与营收)"
    )
    revenue_by_region: list[dict] = Field(
        default_factory=list, description="地区营收分布"
    )


class ChartData(BaseModel):
    """图表数据

    通用图表数据结构，支持折线图、柱状图、饼图等多种图表类型。
    """

    title: str = Field(..., description="图表标题")
    chart_type: str = Field(..., description="图表类型")
    categories: list[str] = Field(default_factory=list, description="分类轴标签")
    series: list[dict] = Field(
        default_factory=list, description="数据系列"
    )
