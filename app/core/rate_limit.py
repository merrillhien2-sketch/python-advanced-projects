"""接口限流模块。

基于 Redis 有序集合实现滑动窗口限流，作为 FastAPI 依赖使用。
限流维度为「客户端 IP + 路由路径」，配置从 settings 读取。
"""

import time

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitException
from app.core.redis_client import redis_client


class RateLimiter:
    """滑动窗口限流器。

    使用 Redis 有序集合（ZSET）记录窗口内每次请求的时间戳，
    通过清理过期成员并统计当前窗口内请求数判断是否放行。

    Args:
        max_requests: 时间窗口内允许的最大请求数
        window_seconds: 时间窗口大小（秒），默认 60
    """

    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_allowed(self, key: str) -> bool:
        """判断指定 key 的请求是否被允许通过。

        Args:
            key: 限流标识，例如 ``rate_limit:{ip}:{path}``

        Returns:
            True 表示允许通过，False 表示已超限
        """
        now = time.time()
        window_start = now - self.window_seconds

        # 使用 Redis 管道批量执行，减少网络往返
        pipe = redis_client.pipeline()
        # 移除滑动窗口外的过期记录
        pipe.zremrangebyscore(key, 0, window_start)
        # 记录当前请求时间戳
        pipe.zadd(key, {str(now): now})
        # 统计当前窗口内请求数
        pipe.zcard(key)
        # 设置 key 过期时间，避免无效 key 占用内存
        pipe.expire(key, self.window_seconds)
        results = await pipe.execute()

        current_count = results[2]
        return current_count <= self.max_requests


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP。

    优先从反向代理头 X-Forwarded-For / X-Real-IP 获取，
    回退到连接对端地址。
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # 取代理链中第一个地址
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_dependency(request: Request) -> None:
    """FastAPI 依赖：基于 Redis 滑动窗口的接口限流。

    从 settings 读取限流开关与阈值，按「客户端 IP + 路由路径」维度计数。
    超出限制时抛出 RateLimitException。

    用法::

        from fastapi import Depends
        from app.core.rate_limit import rate_limit_dependency

        @router.get("/resource", dependencies=[Depends(rate_limit_dependency)])
        async def get_resource(): ...
    """
    # 限流未启用时直接放行
    if not settings.RATE_LIMIT_ENABLED:
        return

    client_ip = _get_client_ip(request)
    route_path = request.url.path
    # 限流 key 格式: rate_limit:{client_ip}:{route_path}，叠加全局前缀
    limit_key = f"{settings.REDIS_KEY_PREFIX}rate_limit:{client_ip}:{route_path}"

    limiter = RateLimiter(
        max_requests=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    )

    allowed = await limiter.is_allowed(limit_key)
    if not allowed:
        raise RateLimitException()
