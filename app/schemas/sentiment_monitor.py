"""舆情监控 Schema

定义监控任务创建、任务响应、舆情记录响应及舆情汇总统计的数据模型，
用于请求参数校验与响应结构约束。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MonitorTaskCreate(BaseModel):
    """监控任务创建请求"""

    name: str = Field(..., description="任务名称")
    source_type: str = Field(..., description="数据来源类型")
    keywords: str = Field(..., description="监控关键词")
    interval_minutes: int = Field(default=30, ge=1, description="采集间隔(分钟)")


class MonitorTaskResponse(BaseModel):
    """监控任务信息响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    source_type: str = Field(..., description="数据来源类型")
    keywords: str = Field(..., description="监控关键词")
    interval_minutes: int = Field(..., description="采集间隔(分钟)")
    is_active: bool = Field(..., description="是否启用")
    last_run_at: Optional[datetime] = Field(default=None, description="上次执行时间")
    created_at: datetime = Field(..., description="创建时间")


class SentimentRecordResponse(BaseModel):
    """舆情记录信息响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="记录ID")
    task_id: int = Field(..., description="监控任务ID")
    source_type: str = Field(..., description="数据来源类型")
    content: str = Field(..., description="舆情文本内容")
    author: Optional[str] = Field(default=None, description="作者")
    sentiment: str = Field(..., description="情感倾向")
    score: float = Field(..., description="情感得分")
    url: Optional[str] = Field(default=None, description="原文链接")
    published_at: Optional[datetime] = Field(
        default=None, description="发布时间"
    )
    created_at: datetime = Field(..., description="创建时间")


class SentimentSummary(BaseModel):
    """舆情汇总统计

    按任务维度统计正/负/中性情感数量与占比。
    """

    task_id: int = Field(..., description="监控任务ID")
    total_count: int = Field(default=0, description="记录总数")
    positive_count: int = Field(default=0, description="正面数量")
    negative_count: int = Field(default=0, description="负面数量")
    neutral_count: int = Field(default=0, description="中性数量")
    positive_rate: float = Field(default=0.0, description="正面占比")
    negative_rate: float = Field(default=0.0, description="负面占比")
