"""舆情监控模型

定义监控任务与舆情记录两张表结构，支撑多来源（微博、小红书、抖音）
舆情数据的采集、情感分析、汇总统计与可视化展示。
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.models.base import BaseModel


class MonitorTask(BaseModel):
    """监控任务表模型

    描述一个舆情监控任务的配置信息，包括监控来源、关键词、采集间隔等。

    字段说明:
        - name: 任务名称
        - source_type: 数据来源类型，取值 weibo / xiaohongshu / douyin
        - keywords: 监控关键词（逗号分隔），用于匹配目标内容
        - interval_minutes: 采集间隔（分钟），默认 30
        - is_active: 任务是否启用，默认 True
        - last_run_at: 上次执行时间，可为空
    """

    __tablename__ = "monitor_tasks"

    name = Column(String(100), nullable=False, comment="任务名称")
    source_type = Column(
        String(30), nullable=False, comment="数据来源类型"
    )
    keywords = Column(String(500), nullable=False, comment="监控关键词")
    interval_minutes = Column(
        Integer, nullable=False, default=30, comment="采集间隔(分钟)"
    )
    is_active = Column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    last_run_at = Column(DateTime, nullable=True, comment="上次执行时间")


class SentimentRecord(BaseModel):
    """舆情记录表模型

    存储采集到的单条舆情内容及其情感分析结果。

    字段说明:
        - task_id: 关联的监控任务 ID，外键指向 monitor_tasks.id
        - source_type: 数据来源类型
        - content: 舆情文本内容
        - author: 作者信息
        - sentiment: 情感倾向，取值 positive / negative / neutral
        - score: 情感得分，范围 -1 到 1
        - url: 原文链接，可为空
        - published_at: 内容发布时间，可为空
    """

    __tablename__ = "sentiment_records"

    task_id = Column(
        Integer,
        ForeignKey("monitor_tasks.id"),
        nullable=False,
        index=True,
        comment="监控任务ID",
    )
    source_type = Column(String(30), nullable=False, comment="数据来源类型")
    content = Column(Text, nullable=False, comment="舆情文本内容")
    author = Column(String(100), nullable=True, comment="作者")
    sentiment = Column(
        String(20), nullable=False, default="neutral", comment="情感倾向"
    )
    score = Column(Float, nullable=False, default=0.0, comment="情感得分")
    url = Column(Text, nullable=True, comment="原文链接")
    published_at = Column(DateTime, nullable=True, comment="发布时间")
