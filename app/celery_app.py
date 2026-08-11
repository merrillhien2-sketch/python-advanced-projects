"""Celery 应用入口（兼容层）。

为兼容 ``from app.celery_app import celery_app`` 的引用路径，
重新导出 ``app.tasks.celery_app`` 中配置完成的 Celery 实例。

真正的 Celery 配置（broker、结果后端、Beat 调度计划、任务自动发现）
统一在 ``app.tasks.celery_app`` 模块中维护，确保全局只有一个 Celery 实例，
避免出现多个实例导致任务派发与调度不一致的问题。

CLI 启动方式（与本地部署文档一致）::

    celery -A app.tasks.celery_app worker --loglevel=info
    celery -A app.tasks.celery_app beat --loglevel=info
"""

from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]
