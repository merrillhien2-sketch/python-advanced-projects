"""FastAPI 应用入口模块。

负责创建应用实例、注册中间件与路由、管理生命周期事件，
并暴露 ASGI 应用对象 ``app`` 供 uvicorn 启动。
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging_config import setup_logging
from app.core.redis_client import redis_client


# 模块级日志器
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理。

    启动时连接并探活 Redis，关闭时优雅断开连接。
    """
    # ---------- 启动阶段 ----------
    try:
        await redis_client.ping()
        logger.info("Redis 连接成功")
    except Exception as exc:  # noqa: BLE001
        logger.error("Redis 连接失败: %s", exc)

    yield

    # ---------- 关闭阶段 ----------
    await redis_client.aclose()
    logger.info("Redis 连接已关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    # 初始化日志系统
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="企业级 Python 平台，提供高性能异步 API 服务、任务队列与实时通信能力。",
        lifespan=lifespan,
    )

    # 注册全局异常处理器
    setup_exception_handlers(app)

    # ---------- CORS 中间件 ----------
    # 允许全部来源时不能开启凭证，避免浏览器拒绝
    if settings.CORS_ORIGINS.strip() == "*":
        allow_origins = ["*"]
        allow_credentials = False
    else:
        allow_origins = [
            origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()
        ]
        allow_credentials = True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------- 注册 API v1 路由 ----------
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ---------- 健康检查端点 ----------
    @app.get("/health", tags=["系统"])
    async def health_check() -> dict:
        """健康检查接口，供负载均衡与监控探活使用。"""
        return {"status": "healthy", "version": __version__}

    # ---------- WebSocket 路由 ----------
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket 通信端点。

        接受客户端连接后回显收到的文本消息，连接断开时记录日志。
        """
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                await websocket.send_text(f"收到消息: {data}")
        except WebSocketDisconnect:
            logger.info("WebSocket 客户端已断开连接")

    return app


# ASGI 应用实例，供 uvicorn 加载：uvicorn app.main:app
app = create_app()
