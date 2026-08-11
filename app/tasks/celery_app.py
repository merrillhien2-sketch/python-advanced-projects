"""Celery 应用配置模块。

负责创建并配置 Celery 应用实例，包括消息代理、结果后端、
任务序列化方式、任务超时限制以及 Beat 定时任务调度计划。
"""

from celery import Celery

from app.core.config import settings

# 创建 Celery 应用实例
celery_app = Celery(
    "enterprise_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# 更新 Celery 全局配置
celery_app.conf.update(
    # 时区配置
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    # 序列化配置
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 任务执行配置
    task_track_started=True,  # 任务开始时记录状态
    task_time_limit=30 * 60,  # 硬超时：30 分钟
    task_soft_time_limit=25 * 60,  # 软超时：25 分钟
    # Worker 配置
    worker_prefetch_multiplier=1,  # 每次只预取一个任务，避免长任务阻塞
    worker_max_tasks_per_child=1000,  # 每个子进程最多执行 1000 个任务后重启，防止内存泄漏
    # Beat 定时任务调度计划
    beat_schedule={
        # 每小时清理一次过期短链
        "clean-expired-shortlinks": {
            "task": "app.tasks.scheduled_tasks.clean_expired_shortlinks",
            "schedule": 3600.0,
        },
        # 每 30 分钟执行一次定时爬取
        "crawl-scheduled": {
            "task": "app.tasks.scheduled_tasks.scheduled_crawl",
            "schedule": 1800.0,
        },
        # 每 5 分钟执行一次系统健康检查
        "system-health-check": {
            "task": "app.tasks.scheduled_tasks.health_check",
            "schedule": 300.0,
        },
    },
)

# 自动发现任务模块（确保 Beat 调度的任务能被正确注册）
celery_app.autodiscover_tasks(
    [
        "app.tasks.scheduled_tasks",
        "app.tasks.ai_tasks",
    ]
)
