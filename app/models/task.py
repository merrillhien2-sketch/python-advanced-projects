"""任务记录模型

定义异步任务记录表结构，用于跟踪 Celery 等异步任务的执行状态与结果。
"""

from sqlalchemy import Column, DateTime, String, Text

from app.models.base import BaseModel


class TaskRecord(BaseModel):
    """异步任务记录表模型

    字段说明:
        - task_id: 任务唯一标识（通常为 Celery 返回的 task id），唯一且建立索引
        - task_type: 任务类型，如 crawl、ocr、sentiment 等
        - status: 任务状态，默认 "pending"，可为 success/failed/running 等
        - result: 任务执行结果（JSON 字符串或文本）
        - error: 任务失败时的错误信息
        - started_at: 任务实际开始执行的时间
        - finished_at: 任务执行完成的时间
    """

    __tablename__ = "task_records"

    task_id = Column(
        String(64), unique=True, index=True, nullable=False, comment="任务ID"
    )
    task_type = Column(String(50), nullable=False, comment="任务类型")
    status = Column(
        String(20), default="pending", nullable=False, comment="任务状态"
    )
    result = Column(Text, nullable=True, comment="任务结果")
    error = Column(Text, nullable=True, comment="错误信息")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="完成时间")
