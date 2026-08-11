"""pytest 全局配置文件。

配置 pytest-asyncio 自动模式，并定义测试用 fixtures：
- 测试用 FastAPI app（通过依赖注入覆盖 get_db 和 get_redis）
- 测试用异步数据库 session（SQLite 内存数据库）
- 测试用 HTTP 客户端（httpx AsyncClient）
- Mock Redis 客户端

测试不需要真实的 Redis / MySQL 连接。
"""

import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# 导入应用和共享模块
# ---------------------------------------------------------------------------
from app.main import app  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.redis_client import get_redis  # noqa: E402

# 导入所有模型，确保它们被注册到 Base.metadata
from app.models import User, ShortLink, TaskRecord, CrawlData  # noqa: E402, F401


# ---------------------------------------------------------------------------
# 测试数据库配置（SQLite 内存数据库）
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 创建测试用异步引擎，使用 StaticPool 确保所有连接共享同一个内存数据库
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# 创建测试用会话工厂
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Mock Redis 客户端
# ---------------------------------------------------------------------------
class MockRedis:
    """内存 Redis 模拟客户端。

    使用字典模拟 Redis 的基本操作，用于测试环境，
    无需连接真实的 Redis 服务器。
    """

    def __init__(self):
        self._data: dict[str, str] = {}
        self._expire: dict[str, float] = {}

    async def get(self, key: str):
        """获取键对应的值。"""
        return self._data.get(key)

    async def set(self, key: str, value, ex=None, **kwargs):
        """设置键值对。"""
        self._data[key] = value
        return True

    async def setex(self, key: str, time: int, value):
        """设置键值对并指定过期时间（秒）。"""
        self._data[key] = value
        self._expire[key] = float(time)
        return True

    async def delete(self, *keys):
        """删除一个或多个键。"""
        deleted = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                self._expire.pop(key, None)
                deleted += 1
        return deleted

    async def exists(self, key: str):
        """检查键是否存在。"""
        return 1 if key in self._data else 0

    async def ping(self):
        """模拟 PING 命令。"""
        return True

    async def expire(self, key: str, time: int):
        """设置键的过期时间。"""
        if key in self._data:
            self._expire[key] = float(time)
            return True
        return False

    async def incr(self, key: str):
        """递增键的值。"""
        current = int(self._data.get(key, 0))
        current += 1
        self._data[key] = str(current)
        return current

    async def ttl(self, key: str):
        """获取键的剩余过期时间。"""
        if key not in self._data:
            return -2
        if key not in self._expire:
            return -1
        return int(self._expire[key])

    async def keys(self, pattern: str = "*"):
        """获取匹配模式的所有键。"""
        if pattern == "*":
            return list(self._data.keys())
        # 简单的前缀匹配
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self._data.keys() if k.startswith(prefix)]
        return [k for k in self._data.keys() if k == pattern]

    async def close(self):
        """关闭连接（空操作）。"""
        pass

    async def aclose(self):
        """异步关闭连接（空操作，兼容 redis.asyncio.Redis.aclose）。"""
        pass

    def flushdb(self):
        """清空所有数据。"""
        self._data.clear()
        self._expire.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def db_session():
    """创建测试用数据库会话。

    每个测试函数都会获得一个干净的数据库（先创建所有表，
    测试结束后删除所有表）。

    Yields:
        AsyncSession: 异步数据库会话
    """
    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 提供会话
    async with TestSessionLocal() as session:
        yield session

    # 清理：删除所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def mock_redis():
    """创建 Mock Redis 客户端。

    每个测试函数都会获得一个空的 MockRedis 实例。

    Yields:
        MockRedis: 内存 Redis 模拟客户端
    """
    redis = MockRedis()
    yield redis


@pytest_asyncio.fixture(scope="function")
async def client(db_session, mock_redis, monkeypatch):
    """创建测试用 HTTP 异步客户端。

    覆盖 FastAPI 应用的 get_db 和 get_redis 依赖，
    使其使用测试数据库和 Mock Redis。

    同时通过 monkeypatch 替换模块级 redis_client 引用，
    确保直接使用 redis_client 的服务（如 ShortLinkService）也能使用 Mock。

    Yields:
        AsyncClient: httpx 异步客户端
    """
    # 替换模块级 redis_client 引用，覆盖所有直接导入 redis_client 的模块
    # 包括 app.main（lifespan 中的 ping/aclose）和 app.services.shortlink_service
    monkeypatch.setattr("app.core.redis_client.redis_client", mock_redis)
    monkeypatch.setattr("app.main.redis_client", mock_redis)
    monkeypatch.setattr("app.services.shortlink_service.redis_client", mock_redis)

    # 覆盖 get_db 依赖，使用测试数据库会话
    async def override_get_db():
        yield db_session

    # 覆盖 get_redis 依赖，使用 Mock Redis（原函数 return 而非 yield）
    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    # 创建 httpx 异步客户端（不自动跟随重定向，便于测试 302 跳转）
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac

    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_token(client):
    """创建已认证用户的 token。

    先注册一个测试用户，然后登录获取 token，
    供需要认证的测试使用。

    Returns:
        str: JWT 访问令牌
    """
    # 注册测试用户（API 前缀为 /api/v1）
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "Test123456",
            "email": "test@example.com",
        },
    )

    # 登录获取 token
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "Test123456",
        },
    )

    # 从 ResponseBase 包装的响应中提取 token
    data = response.json()
    token = None
    if "data" in data and isinstance(data["data"], dict):
        token = data["data"].get("access_token")
    elif "access_token" in data:
        token = data["access_token"]

    return token
