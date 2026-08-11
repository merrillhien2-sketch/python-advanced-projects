"""任务相关 Schema

定义异步任务创建、详情响应及状态查询的数据模型。
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    """任务创建请求

    属性:
        task_type: 任务类型，如 crawl、ocr、sentiment 等
        params: 任务参数字典，传递给 Celery 任务
    """

    task_type: str = Field(..., description="任务类型")
    params: dict[str, Any] = Field(default_factory=dict, description="任务参数")


class TaskResponse(BaseModel):
    """任务详情响应"""

    model_config = ConfigDict(from_attributes=True)

    task_id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型")
    status: str = Field(..., description="任务状态")
    result: Optional[str] = Field(default=None, description="任务结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="完成时间")
    created_at: datetime = Field(..., description="创建时间")


class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
