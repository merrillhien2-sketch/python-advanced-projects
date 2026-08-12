"""路由聚合模块

将所有 v1 版本的路由模块聚合到一个 APIRouter 中，
由主应用统一挂载到 /api/v1 前缀下。
"""

from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.crawler import router as crawler_router
from app.api.v1.shortlink import router as shortlink_router
from app.api.v1.tasks import router as tasks_router

# 新增项目模块路由
from app.api.v1.data_analysis import router as data_analysis_router
from app.api.v1.sentiment_monitor import router as sentiment_monitor_router
from app.api.v1.proxy_pool import router as proxy_pool_router
from app.api.v1.office import router as office_router
from app.api.v1.api_test import router as api_test_router
from app.api.v1.price_monitor import router as price_monitor_router

# 创建聚合路由器
api_router = APIRouter()

# 注册各业务模块路由，统一设置前缀和标签
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(ai_router, prefix="/ai", tags=["AI 服务"])
api_router.include_router(crawler_router, prefix="/crawler", tags=["爬虫"])
api_router.include_router(shortlink_router, prefix="/shortlink", tags=["短链"])
api_router.include_router(chat_router, prefix="/chat", tags=["聊天"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["任务"])

# 新增项目模块路由
api_router.include_router(data_analysis_router, prefix="/data-analysis", tags=["数据分析"])
api_router.include_router(sentiment_monitor_router, prefix="/sentiment", tags=["舆情监控"])
api_router.include_router(proxy_pool_router, prefix="/proxy-pool", tags=["代理IP池"])
api_router.include_router(office_router, prefix="/office", tags=["办公工具"])
api_router.include_router(api_test_router, prefix="/api-test", tags=["接口测试"])
api_router.include_router(price_monitor_router, prefix="/price-monitor", tags=["价格监控"])
