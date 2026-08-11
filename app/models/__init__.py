"""模型层包

统一导入所有模型类，以便 SQLAlchemy 在 metadata 中注册所有表，
同时方便 Alembic 迁移脚本和其他模块引用。
"""

from app.models.base import BaseModel, TimestampMixin
from app.models.crawl_data import CrawlData
from app.models.shortlink import ShortLink
from app.models.task import TaskRecord
from app.models.user import User

__all__ = [
    "BaseModel",
    "TimestampMixin",
    "User",
    "ShortLink",
    "TaskRecord",
    "CrawlData",
]
