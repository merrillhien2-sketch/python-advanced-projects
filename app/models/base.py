"""基础模型模块

提供所有数据模型共享的基础结构，包含自增主键 ID 与时间戳字段。
所有业务模型应继承 ``BaseModel``，从而自动获得主键和创建/更新时间。
"""

from sqlalchemy import Column, DateTime, Integer, func

from app.core.database import Base


class TimestampMixin:
    """时间戳混入类

    为模型自动添加 ``created_at`` 和 ``updated_at`` 字段，
    用于记录数据的创建时间与最后更新时间。
    """

    # 创建时间，由数据库 now() 函数自动填充
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    # 更新时间，每次记录更新时由数据库 now() 函数自动刷新
    updated_at = Column(
        DateTime,
        nullable=True,
        onupdate=func.now(),
        comment="更新时间",
    )


class BaseModel(Base, TimestampMixin):
    """所有数据模型的基类

    包含自增主键 ``id`` 以及时间戳字段。
    设为 ``__abstract__``，SQLAlchemy 不会为此类单独建表，
    仅为子类提供公共字段定义。
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
