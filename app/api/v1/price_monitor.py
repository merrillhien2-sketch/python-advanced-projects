"""电商价格监控路由

提供商品管理、价格记录、价格历史与统计、告警管理等接口。

接口列表:
    - POST   /products                    添加监控商品
    - GET    /products                    分页查询商品列表
    - POST   /products/{product_id}/price 记录最新价格
    - GET    /products/{product_id}/history 价格历史
    - GET    /products/{product_id}/stats   价格统计
    - GET    /alerts                      分页查询告警
    - PATCH  /alerts/{alert_id}/read      标记告警已读
    - POST   /batch-check                 批量检查价格
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import PaginatedResponse, ResponseBase
from app.schemas.price_monitor import (
    PriceAlertResponse,
    PriceHistoryResponse,
    PriceStats,
    ProductCreate,
    ProductResponse,
)
from app.services.price_monitor_service import PriceMonitorService

router = APIRouter()


@router.post(
    "/products",
    response_model=ResponseBase[ProductResponse],
    summary="添加监控商品",
)
async def add_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[ProductResponse]:
    """添加监控商品

    参数:
        product_in: 商品创建请求（名称、链接、平台、目标价格等）
        db: 异步数据库会话

    返回:
        包含商品信息的响应
    """
    product = await PriceMonitorService.add_product(product_in.model_dump(), db)
    return ResponseBase(data=ProductResponse.model_validate(product))


@router.get(
    "/products",
    response_model=PaginatedResponse[ProductResponse],
    summary="分页查询商品列表",
)
async def list_products(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    platform: str | None = Query(None, description="按平台筛选"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProductResponse]:
    """分页查询商品列表

    支持按平台筛选。

    参数:
        page: 页码，从 1 开始
        page_size: 每页条数
        platform: 可选，按平台筛选（jd/tmall/pdd/amazon）
        db: 异步数据库会话

    返回:
        分页响应，包含商品列表和分页信息
    """
    result = await PriceMonitorService.get_products(page, page_size, platform, db)
    data = [ProductResponse(**item) for item in result["data"]]
    return PaginatedResponse(
        data=data,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post(
    "/products/{product_id}/price",
    response_model=ResponseBase[PriceHistoryResponse],
    summary="记录最新价格",
)
async def record_price(
    product_id: int,
    price: float = Query(..., ge=0, description="记录的价格"),
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[PriceHistoryResponse]:
    """记录商品的最新价格

    记录价格历史，同时更新商品当前价格，并检查是否触发告警。

    参数:
        product_id: 商品 ID
        price: 记录的价格
        db: 异步数据库会话

    返回:
        包含价格历史记录的响应
    """
    history = await PriceMonitorService.record_price(product_id, price, db)
    return ResponseBase(data=PriceHistoryResponse.model_validate(history))


@router.get(
    "/products/{product_id}/history",
    response_model=ResponseBase[list[PriceHistoryResponse]],
    summary="价格历史",
)
async def get_price_history(
    product_id: int,
    days: int = Query(30, ge=1, le=365, description="查询天数"),
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[list[PriceHistoryResponse]]:
    """查询商品的价格历史

    参数:
        product_id: 商品 ID
        days: 查询最近多少天的数据，默认 30
        db: 异步数据库会话

    返回:
        包含价格历史列表的响应
    """
    data = await PriceMonitorService.get_price_history(product_id, days, db)
    histories = [PriceHistoryResponse(**item) for item in data]
    return ResponseBase(data=histories)


@router.get(
    "/products/{product_id}/stats",
    response_model=ResponseBase[PriceStats],
    summary="价格统计",
)
async def get_price_stats(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[PriceStats]:
    """查询商品的价格统计

    统计最低价、最高价、均价和涨跌幅。

    参数:
        product_id: 商品 ID
        db: 异步数据库会话

    返回:
        包含价格统计信息的响应
    """
    stats = await PriceMonitorService.get_price_stats(product_id, db)
    return ResponseBase(data=PriceStats(**stats))


@router.get(
    "/alerts",
    response_model=PaginatedResponse[PriceAlertResponse],
    summary="分页查询告警",
)
async def list_alerts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    unread_only: bool = Query(False, description="是否仅查询未读告警"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PriceAlertResponse]:
    """分页查询价格告警

    参数:
        page: 页码，从 1 开始
        page_size: 每页条数
        unread_only: 是否仅查询未读告警
        db: 异步数据库会话

    返回:
        分页响应，包含告警列表和分页信息
    """
    result = await PriceMonitorService.get_alerts(page, page_size, unread_only, db)
    data = [PriceAlertResponse(**item) for item in result["data"]]
    return PaginatedResponse(
        data=data,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.patch(
    "/alerts/{alert_id}/read",
    response_model=ResponseBase[dict],
    summary="标记告警已读",
)
async def mark_alert_read(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """标记指定告警为已读

    参数:
        alert_id: 告警 ID
        db: 异步数据库会话

    返回:
        包含更新结果的响应
    """
    result = await PriceMonitorService.mark_alert_read(alert_id, db)
    return ResponseBase(data=result)


@router.post(
    "/batch-check",
    response_model=ResponseBase[dict],
    summary="批量检查价格",
)
async def batch_check_prices(
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """批量检查所有启用商品的价格

    模拟爬取并更新所有启用监控商品的价格，返回更新统计信息。

    参数:
        db: 异步数据库会话

    返回:
        包含更新统计信息的响应
    """
    result = await PriceMonitorService.batch_check_prices(db)
    return ResponseBase(data=result)
