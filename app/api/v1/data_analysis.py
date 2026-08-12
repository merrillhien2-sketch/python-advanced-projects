"""数据分析可视化路由

提供订单创建、批量导入、仪表盘统计、营收趋势、品类分布、
用户画像查询与批量生成等接口。

接口列表:
    - POST /orders                    创建订单
    - POST /orders/batch               批量导入订单
    - GET  /dashboard                  仪表盘统计数据
    - GET  /revenue-trend              营收趋势
    - GET  /category-distribution      品类分布
    - GET  /user-profile/{user_id}     用户画像
    - POST /user-profiles/generate     批量生成用户画像
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import PaginatedResponse, ResponseBase
from app.schemas.data_analysis import (
    DashboardStats,
    OrderCreate,
    OrderResponse,
    UserProfileResponse,
)
from app.services.data_analysis_service import DataAnalysisService

router = APIRouter()


@router.post(
    "/orders",
    response_model=ResponseBase[OrderResponse],
    summary="创建订单",
)
async def create_order(
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[OrderResponse]:
    """创建单笔订单记录

    参数:
        order_in: 订单创建请求体
        db: 异步数据库会话

    返回:
        包含订单信息的响应
    """
    order = await DataAnalysisService.create_order(order_in.model_dump(), db)
    return ResponseBase(data=OrderResponse.model_validate(order))


@router.post(
    "/orders/batch",
    response_model=ResponseBase[dict],
    summary="批量导入订单",
)
async def batch_import_orders(
    orders: list[OrderCreate],
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """批量导入订单记录

    参数:
        orders: 订单创建请求列表
        db: 异步数据库会话

    返回:
        包含导入统计（成功/失败数）的响应
    """
    order_list = [item.model_dump() for item in orders]
    result = await DataAnalysisService.batch_import_orders(order_list, db)
    return ResponseBase(data=result)


@router.get(
    "/dashboard",
    response_model=ResponseBase[DashboardStats],
    summary="仪表盘统计数据",
)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[DashboardStats]:
    """获取仪表盘统计数据

    返回总营收、总订单数、客单价、品类 TOP5 与地区营收分布。

    参数:
        db: 异步数据库会话

    返回:
        仪表盘统计响应
    """
    stats = await DataAnalysisService.get_dashboard_stats(db)
    return ResponseBase(data=stats)


@router.get(
    "/revenue-trend",
    response_model=ResponseBase[list[dict]],
    summary="营收趋势",
)
async def get_revenue_trend(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[list[dict]]:
    """获取营收趋势（按日期聚合）

    参数:
        days: 统计天数，默认 30
        db: 异步数据库会话

    返回:
        每日营收趋势列表
    """
    trend = await DataAnalysisService.get_revenue_trend(days, db)
    return ResponseBase(data=trend)


@router.get(
    "/category-distribution",
    response_model=ResponseBase[list[dict]],
    summary="品类分布",
)
async def get_category_distribution(
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[list[dict]]:
    """获取品类分布

    参数:
        db: 异步数据库会话

    返回:
        各品类订单数与营收分布列表
    """
    distribution = await DataAnalysisService.get_category_distribution(db)
    return ResponseBase(data=distribution)


@router.get(
    "/user-profile/{user_id}",
    response_model=ResponseBase[dict],
    summary="用户画像",
)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """获取用户画像（消费行为标签）

    参数:
        user_id: 用户 ID
        db: 异步数据库会话

    返回:
        用户画像信息响应
    """
    profile = await DataAnalysisService.get_user_profile(user_id, db)
    return ResponseBase(data=profile)


@router.post(
    "/user-profiles/generate",
    response_model=ResponseBase[dict],
    summary="批量生成用户画像",
)
async def generate_user_profiles(
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """批量生成用户画像

    基于全量订单数据聚合生成所有用户的消费画像。

    参数:
        db: 异步数据库会话

    返回:
        包含生成数量与用户画像摘要的响应
    """
    result = await DataAnalysisService.generate_user_profiles(db)
    return ResponseBase(data=result)
