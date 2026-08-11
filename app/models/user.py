"""用户模型

定义用户表结构，存储用户名、邮箱、加密密码、激活状态及角色等信息。
"""

from sqlalchemy import Boolean, Column, String

from app.models.base import BaseModel


class User(BaseModel):
    """用户表模型

    字段说明:
        - username: 用户名，唯一且建立索引，便于快速查找
        - email: 邮箱地址，唯一
        - hashed_password: 经过哈希加密的密码（不存储明文）
        - is_active: 账户是否激活，默认为 True
        - role: 用户角色，默认为 "user"，可扩展为 admin 等
    """

    __tablename__ = "users"

    username = Column(
        String(50), unique=True, index=True, nullable=False, comment="用户名"
    )
    email = Column(
        String(100), unique=True, nullable=False, comment="邮箱"
    )
    hashed_password = Column(
        String(255), nullable=False, comment="加密后的密码"
    )
    is_active = Column(
        Boolean, default=True, nullable=False, comment="是否激活"
    )
    role = Column(
        String(20), default="user", nullable=False, comment="用户角色"
    )
