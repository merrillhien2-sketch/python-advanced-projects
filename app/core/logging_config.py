"""日志配置模块。

提供统一的日志初始化函数，同时配置控制台输出与按大小轮转的文件日志，
自动创建日志目录。
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from app.core.config import settings


# 统一日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging() -> None:
    """初始化全局日志配置。

    - 自动创建日志目录
    - 注册控制台处理器（StreamHandler）
    - 注册按大小轮转的文件处理器（RotatingFileHandler）
    - 清除已有处理器，避免重复输出
    - 调整第三方库日志级别
    """
    # 创建日志目录（若不存在）
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # 解析日志级别
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 统一格式器
    formatter = logging.Formatter(LOG_FORMAT)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # 文件轮转处理器
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # 配置根日志器，先清除已有处理器避免重复
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 调整常用库的日志级别，减少噪音
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    # SQLAlchemy 引擎日志：非调试模式仅记录警告以上
    sqlalchemy_level = level if settings.DEBUG else logging.WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(sqlalchemy_level)
