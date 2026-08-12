"""代理 IP 池路由

提供代理 IP 的添加、批量导入、分页查询、随机获取、统计、
单个检查、批量检查与删除等接口。

接口列表:
    - POST   /                 添加代理
    - POST   /batch            批量导入
    - GET    /                 分页查询代理列表
    - GET    /get              随机获取一个可用代理
    - GET    /stats            代理统计
    - POST   /check/{proxy_id}  检查单个代理
    - POST   /check/batch      批量检查
    - DELETE /{proxy_id}        删除代理
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import PaginatedResponse, ResponseBase
from app.schemas.proxy_pool import (
    ProxyIPBatchImport,
    ProxyIPCreate,
    ProxyIPResponse,
)
from app.services.proxy_pool_service import ProxyPoolService

router = APIRouter()


@router.post(
    "/",
    response_model=ResponseBase[ProxyIPResponse],
    summary="添加代理",
)
async def add_proxy(
    proxy_in: ProxyIPCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[ProxyIPResponse]:
    """添加单个代理 IP

    参数:
        proxy_in: 代理创建请求体
        db: 异步数据库会话

    返回:
        包含代理信息的响应
    """
    proxy = await ProxyPoolService.add_proxy(proxy_in.model_dump(), db)
    return ResponseBase(data=ProxyIPResponse.model_validate(proxy))


@router.post(
    "/batch",
    response_model=ResponseBase[dict],
    summary="批量导入",
)
async def batch_add_proxies(
    batch_in: ProxyIPBatchImport,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """批量导入代理 IP

    参数:
        batch_in: 批量导入请求体（含代理列表）
        db: 异步数据库会话

    返回:
        包含导入统计（成功/失败数）的响应
    """
    proxies = [item.model_dump() for item in batch_in.proxies]
    result = await ProxyPoolService.batch_add_proxies(proxies, db)
    return ResponseBase(data=result)


@router.get(
    "/",
    response_model=PaginatedResponse[ProxyIPResponse],
    summary="分页查询代理列表",
)
async def list_proxies(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    protocol: str | None = Query(None, description="按协议筛选"),
    region: str | None = Query(None, description="按地区筛选"),
    available_only: bool = Query(False, description="是否仅查询可用代理"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProxyIPResponse]:
    """分页查询代理 IP 列表

    参数:
        page: 页码
        page_size: 每页条数
        protocol: 可选，按协议筛选
        region: 可选，按地区筛选
        available_only: 是否仅查询可用代理
        db: 异步数据库会话

    返回:
        分页响应，包含代理列表和分页信息
    """
    result = await ProxyPoolService.get_proxies(
        page, page_size, protocol, region, available_only, db
    )
    data = [ProxyIPResponse(**item) for item in result["data"]]
    return PaginatedResponse(
        data=data,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/get",
    response_model=ResponseBase[dict],
    summary="随机获取一个可用代理",
)
async def get_proxy(
    protocol: str | None = Query(None, description="按协议筛选"),
    region: str | None = Query(None, description="按地区筛选"),
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """随机获取一个可用代理（优先返回速度快的）

    参数:
        protocol: 可选，按协议筛选
        region: 可选，按地区筛选
        db: 异步数据库会话

    返回:
        包含单个代理信息的响应
    """
    proxy = await ProxyPoolService.get_proxy(protocol, region, db)
    return ResponseBase(data=proxy)


@router.get(
    "/stats",
    response_model=ResponseBase[dict],
    summary="代理统计",
)
async def get_proxy_stats(
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """获取代理池统计信息

    参数:
        db: 异步数据库会话

    返回:
        包含总数、可用数、不可用数及按协议分组的响应
    """
    stats = await ProxyPoolService.get_proxy_stats(db)
    return ResponseBase(data=stats)


@router.post(
    "/check/{proxy_id}",
    response_model=ResponseBase[dict],
    summary="检查单个代理",
)
async def check_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """检查单个代理可用性

    参数:
        proxy_id: 代理 ID
        db: 异步数据库会话

    返回:
        包含检查结果（可用性、响应时间）的响应
    """
    result = await ProxyPoolService.check_proxy(proxy_id, db)
    return ResponseBase(data=result)


@router.post(
    "/check/batch",
    response_model=ResponseBase[dict],
    summary="批量检查",
)
async def batch_check_proxies(
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """批量检查所有代理可用性

    参数:
        db: 异步数据库会话

    返回:
        包含检查统计与各代理结果的响应
    """
    result = await ProxyPoolService.batch_check_proxies(db)
    return ResponseBase(data=result)


@router.delete(
    "/{proxy_id}",
    response_model=ResponseBase[dict],
    summary="删除代理",
)
async def delete_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """删除代理 IP

    参数:
        proxy_id: 代理 ID
        db: 异步数据库会话

    返回:
        包含删除结果的响应
    """
    result = await ProxyPoolService.delete_proxy(proxy_id, db)
    return ResponseBase(data=result)
