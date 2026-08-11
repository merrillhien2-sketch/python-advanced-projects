"""异步数据库连接模块。

基于 SQLAlchemy 2.0 异步引擎，提供 ORM 声明性基类、异步会话工厂
以及 FastAPI 依赖注入函数。所有连接参数从 settings 读取。
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明性基类。

    业务模型继承本类后即可被 ``Base.metadata`` 管理，
    便于统一的建表与迁移操作。
    """

    pass


# 异步引擎：配置连接池大小、溢出上限与回收时长，启用连接前探活
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# 异步会话工厂：提交后不过期，避免异步场景下的懒加载问题
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供数据库异步会话。

    请求结束后自动关闭会话；发生异常时自动回滚。
    路由处理函数通过 ``Depends(get_db)`` 注入会话。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
