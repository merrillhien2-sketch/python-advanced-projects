"""模型层包

统一导入所有模型类，以便 SQLAlchemy 在 metadata 中注册所有表，
同时方便 Alembic 迁移脚本和其他模块引用。
"""

from app.models.base import BaseModel, TimestampMixin
from app.models.crawl_data import CrawlData
from app.models.shortlink import ShortLink
from app.models.task import TaskRecord
from app.models.user import User

# 新增项目模块模型
from app.models.data_analysis import OrderRecord, UserProfile
from app.models.sentiment_monitor import MonitorTask, SentimentRecord
from app.models.proxy_pool import ProxyIP
from app.models.api_test import ApiTestSuite, ApiTestCase, ApiTestRun
from app.models.price_monitor import Product, PriceHistory, PriceAlert

__all__ = [
    "BaseModel",
    "TimestampMixin",
    "User",
    "ShortLink",
    "TaskRecord",
    "CrawlData",
    # 数据分析
    "OrderRecord",
    "UserProfile",
    # 舆情监控
    "MonitorTask",
    "SentimentRecord",
    # 代理IP池
    "ProxyIP",
    # 接口测试
    "ApiTestSuite",
    "ApiTestCase",
    "ApiTestRun",
    # 价格监控
    "Product",
    "PriceHistory",
    "PriceAlert",
]
