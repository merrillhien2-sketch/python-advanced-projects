"""任务管理路由

提供异步任务的创建、状态查询和列表分页的接口。

接口列表:
    - POST /           创建异步任务（调用 Celery task）
    - GET  /{task_id}  查询任务状态
    - GET  /           分页查询任务列表
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BusinessException, NotFoundException
from app.models.task import TaskRecord
from app.schemas.common import PaginatedResponse, ResponseBase
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _try_dispatch_celery_task(task_type: str, params: dict, task_id: str) -> str:
    """尝试通过 Celery 派发异步任务

    如果 Celery 未配置或任务不可用，则返回 "pending" 状态，
    任务记录仍会保存到数据库，后续可由 worker 处理。

    参数:
        task_type: 任务类型
        params: 任务参数
        task_id: 预生成的任务 ID

    返回:
        任务初始状态字符串
    """
    try:
        # 延迟导入 Celery 应用，避免在 Celery 未安装时影响模块加载
        from app.celery_app import celery_app  # type: ignore

        # 尝试派发任务
        celery_app.send_task(
            name=f"tasks.{task_type}",
            kwargs={"params": params, "task_id": task_id},
            task_id=task_id,
        )
        logger.info("Celery 任务已派发: %s, task_id: %s", task_type, task_id)
        return "queued"
    except ImportError:
        logger.warning("Celery 未配置，任务将以 pending 状态存储等待处理")
        return "pending"
    except Exception as e:
        logger.warning("Celery 任务派发失败: %s，任务以 pending 状态存储", e)
        return "pending"


@router.post(
    "/",
    response_model=ResponseBase[TaskResponse],
    summary="创建异步任务",
)
async def create_task(
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[TaskResponse]:
    """创建异步任务

    生成任务 ID，尝试通过 Celery 派发任务，并在数据库中创建任务记录。

    参数:
        task_in: 任务创建请求（任务类型、参数）
        db: 异步数据库会话

    返回:
        包含任务信息的响应
    """
    # 生成唯一任务 ID
    task_id = str(uuid.uuid4())

    # 尝试通过 Celery 派发任务
    initial_status = _try_dispatch_celery_task(task_in.task_type, task_in.params, task_id)

    try:
        # 创建任务记录
        task_record = TaskRecord(
            task_id=task_id,
            task_type=task_in.task_type,
            status=initial_status,
            started_at=datetime.now(timezone.utc) if initial_status == "queued" else None,
        )
        db.add(task_record)
        await db.commit()
        await db.refresh(task_record)

        return ResponseBase(data=TaskResponse.model_validate(task_record))
    except Exception as e:
        await db.rollback()
        logger.error("创建任务记录失败: %s", e, exc_info=True)
        raise BusinessException(message=f"创建任务失败: {e}")


@router.get(
    "/{task_id}",
    response_model=ResponseBase[TaskResponse],
    summary="查询任务状态",
)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[TaskResponse]:
    """根据任务 ID 查询任务详情和状态

    参数:
        task_id: 任务唯一标识
        db: 异步数据库会话

    返回:
        包含任务详情的响应
    """
    result = await db.execute(
        select(TaskRecord).where(TaskRecord.task_id == task_id)
    )
    task_record = result.scalar_one_or_none()

    if task_record is None:
        raise NotFoundException(f"任务不存在: {task_id}")

    # 尝试从 Celery 同步最新状态
    try:
        from app.celery_app import celery_app  # type: ignore

        celery_result = celery_app.AsyncResult(task_id)
        if celery_result and celery_result.status:
            # 映射 Celery 状态到业务状态
            status_map = {
                "PENDING": "pending",
                "STARTED": "running",
                "SUCCESS": "success",
                "FAILURE": "failed",
                "RETRY": "retrying",
            }
            mapped_status = status_map.get(celery_result.status, task_record.status)

            # 如果状态有变化，更新数据库
            if mapped_status != task_record.status:
                task_record.status = mapped_status
                if mapped_status == "success":
                    task_record.result = str(celery_result.result) if celery_result.result else None
                    task_record.finished_at = datetime.now(timezone.utc)
                elif mapped_status == "failed":
                    task_record.error = str(celery_result.result) if celery_result.result else None
                    task_record.finished_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(task_record)
    except ImportError:
        # Celery 未配置，跳过状态同步
        pass
    except Exception as e:
        logger.warning("从 Celery 同步任务状态失败: %s", e)

    return ResponseBase(data=TaskResponse.model_validate(task_record))


@router.get(
    "/",
    response_model=PaginatedResponse[TaskResponse],
    summary="分页查询任务列表",
)
async def list_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    task_type: str | None = Query(None, description="按任务类型筛选"),
    status: str | None = Query(None, description="按状态筛选"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TaskResponse]:
    """分页查询任务列表

    支持按任务类型和状态进行筛选。

    参数:
        page: 页码，从 1 开始
        page_size: 每页条数
        task_type: 可选，按任务类型筛选
        status: 可选，按状态筛选
        db: 异步数据库会话

    返回:
        分页响应，包含任务列表和分页信息
    """
    # 构建基础查询条件
    conditions = []
    if task_type:
        conditions.append(TaskRecord.task_type == task_type)
    if status:
        conditions.append(TaskRecord.status == status)

    # 查询总数
    count_query = select(func.count(TaskRecord.id))
    for cond in conditions:
        count_query = count_query.where(cond)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 查询当前页数据
    offset = (page - 1) * page_size
    data_query = select(TaskRecord).order_by(TaskRecord.id.desc()).offset(offset).limit(page_size)
    for cond in conditions:
        data_query = data_query.where(cond)
    result = await db.execute(data_query)
    tasks = result.scalars().all()

    # 转换为 TaskResponse 列表
    data = [TaskResponse.model_validate(task) for task in tasks]

    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
    )
