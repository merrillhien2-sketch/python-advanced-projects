"""短链模型

定义短链接表结构，记录原始 URL、短码、点击次数、过期时间等信息。
短码通过 hashlib + base62 编码生成，并同步缓存至 Redis。
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.models.base import BaseModel


class ShortLink(BaseModel):
    """短链接表模型

    字段说明:
        - original_url: 原始长链接地址
        - short_code: 6 位短码，唯一且建立索引
        - click_count: 短链被点击的总次数，默认 0
        - expires_at: 短链过期时间，可为空表示永不过期
        - is_active: 短链是否启用，默认为 True
        - created_by: 创建者用户 ID，关联 users 表
    """

    __tablename__ = "short_links"

    original_url = Column(Text, nullable=False, comment="原始URL")
    short_code = Column(
        String(10), unique=True, index=True, nullable=False, comment="短码"
    )
    click_count = Column(Integer, default=0, nullable=False, comment="点击次数")
    expires_at = Column(DateTime, nullable=True, comment="过期时间")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_by = Column(
        Integer, ForeignKey("users.id"), nullable=True, comment="创建者ID"
    )
