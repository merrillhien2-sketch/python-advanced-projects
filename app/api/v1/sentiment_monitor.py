"""舆情监控路由

提供监控任务创建与启停、舆情记录分页查询、情感汇总、
手动情感分析及舆情记录添加等接口。

接口列表:
    - POST   /tasks                 创建监控任务
    - GET    /tasks                  分页查询任务列表
    - GET    /records/{task_id}      分页查询舆情记录
    - GET    /summary/{task_id}      舆情汇总
    - POST   /analyze/{task_id}      手动触发情感分析
    - PATCH  /tasks/{task_id}        启用/停用任务
    - POST   /records                手动添加舆情记录
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import PaginatedResponse, ResponseBase
from app.schemas.sentiment_monitor import (
    MonitorTaskCreate,
    MonitorTaskResponse,
    SentimentRecordResponse,
)
from app.services.sentiment_monitor_service import SentimentMonitorService

router = APIRouter()


class ToggleTaskRequest(BaseModel):
    """启用/停用任务请求体"""

    is_active: bool


class SentimentRecordCreate(BaseModel):
    """舆情记录创建请求体（手动添加）"""

    task_id: int
    source_type: str | None = None
    content: str
    author: str | None = None
    url: str | None = None
    published_at: str | None = None


@router.post(
    "/tasks",
    response_model=ResponseBase[MonitorTaskResponse],
    summary="创建监控任务",
)
async def create_monitor_task(
    task_in: MonitorTaskCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[MonitorTaskResponse]:
    """创建舆情监控任务

    参数:
        task_in: 任务创建请求体
        db: 异步数据库会话

    返回:
        包含任务信息的响应
    """
    task = await SentimentMonitorService.create_monitor_task(
        task_in.model_dump(), db
    )
    return ResponseBase(data=MonitorTaskResponse.model_validate(task))


@router.get(
    "/tasks",
    response_model=PaginatedResponse[MonitorTaskResponse],
    summary="分页查询任务列表",
)
async def list_monitor_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MonitorTaskResponse]:
    """分页查询监控任务列表

    参数:
        page: 页码
        page_size: 每页条数
        db: 异步数据库会话

    返回:
        分页响应，包含任务列表和分页信息
    """
    result = await SentimentMonitorService.get_monitor_tasks(
        page, page_size, db
    )
    data = [MonitorTaskResponse(**item) for item in result["data"]]
    return PaginatedResponse(
        data=data,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/records/{task_id}",
    response_model=PaginatedResponse[SentimentRecordResponse],
    summary="分页查询舆情记录",
)
async def list_sentiment_records(
    task_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SentimentRecordResponse]:
    """分页查询某任务下的舆情记录

    参数:
        task_id: 监控任务 ID
        page: 页码
        page_size: 每页条数
        db: 异步数据库会话

    返回:
        分页响应，包含舆情记录列表和分页信息
    """
    result = await SentimentMonitorService.get_sentiment_records(
        task_id, page, page_size, db
    )
    data = [SentimentRecordResponse(**item) for item in result["data"]]
    return PaginatedResponse(
        data=data,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/summary/{task_id}",
    response_model=ResponseBase[dict],
    summary="舆情汇总",
)
async def get_sentiment_summary(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """获取任务舆情汇总统计

    参数:
        task_id: 监控任务 ID
        db: 异步数据库会话

    返回:
        舆情汇总响应（正/负/中性数量及占比）
    """
    summary = await SentimentMonitorService.get_sentiment_summary(task_id, db)
    return ResponseBase(data=summary)


@router.post(
    "/analyze/{task_id}",
    response_model=ResponseBase[dict],
    summary="手动触发情感分析",
)
async def analyze_sentiment(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """对任务下的舆情记录手动执行情感分析

    参数:
        task_id: 监控任务 ID
        db: 异步数据库会话

    返回:
        包含分析数量与汇总的响应
    """
    result = await SentimentMonitorService.analyze_sentiment_for_task(
        task_id, db
    )
    return ResponseBase(data=result)


@router.patch(
    "/tasks/{task_id}",
    response_model=ResponseBase[MonitorTaskResponse],
    summary="启用/停用任务",
)
async def toggle_monitor_task(
    task_id: int,
    body: ToggleTaskRequest,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[MonitorTaskResponse]:
    """启用或停用监控任务

    参数:
        task_id: 监控任务 ID
        body: 包含 is_active 目标状态的请求体
        db: 异步数据库会话

    返回:
        更新后的任务信息响应
    """
    task = await SentimentMonitorService.toggle_monitor_task(
        task_id, body.is_active, db
    )
    return ResponseBase(data=MonitorTaskResponse.model_validate(task))


@router.post(
    "/records",
    response_model=ResponseBase[SentimentRecordResponse],
    summary="手动添加舆情记录",
)
async def add_sentiment_record(
    record_in: SentimentRecordCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[SentimentRecordResponse]:
    """手动添加舆情记录（自动执行情感分析）

    参数:
        record_in: 舆情记录创建请求体
        db: 异步数据库会话

    返回:
        包含舆情记录（含情感分析结果）的响应
    """
    record = await SentimentMonitorService.add_sentiment_record(
        record_in.model_dump(), db
    )
    return ResponseBase(data=SentimentRecordResponse.model_validate(record))
