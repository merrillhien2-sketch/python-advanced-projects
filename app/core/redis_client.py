"""Redis 异步客户端模块。

提供全局 Redis 连接实例及 FastAPI 依赖注入函数，
连接地址从 settings.REDIS_URL 读取。
"""

import redis.asyncio as redis

from app.core.config import settings


# 全局 Redis 异步客户端实例
# decode_responses=True 使返回值自动解码为字符串
redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    encoding="utf-8",
)


async def get_redis() -> redis.Redis:
    """FastAPI 依赖：返回全局 Redis 客户端实例。

    路由处理函数通过 ``Depends(get_redis)`` 注入 Redis 客户端。
    """
    return redis_client
