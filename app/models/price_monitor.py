"""电商价格监控模型

定义商品、价格历史、价格告警的表结构，
用于管理电商商品的价格监控与告警通知。
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.models.base import BaseModel


class Product(BaseModel):
    """商品表模型

    字段说明:
        - name: 商品名称
        - url: 商品链接地址
        - platform: 商品平台（jd/tmall/pdd/amazon）
        - current_price: 当前价格，可为空
        - target_price: 目标价格，可为空
        - image_url: 商品图片链接，可为空
        - is_active: 是否启用监控，默认 True
    """

    __tablename__ = "products"

    name = Column(String(200), nullable=False, comment="商品名称")
    url = Column(Text, nullable=False, comment="商品链接")
    platform = Column(String(30), nullable=False, comment="商品平台")
    current_price = Column(Float, nullable=True, comment="当前价格")
    target_price = Column(Float, nullable=True, comment="目标价格")
    image_url = Column(Text, nullable=True, comment="商品图片链接")
    is_active = Column(
        Boolean, default=True, nullable=False, comment="是否启用监控"
    )


class PriceHistory(BaseModel):
    """价格历史表模型

    字段说明:
        - product_id: 商品 ID，关联 products 表
        - price: 记录时的价格
        - recorded_at: 记录时间
    """

    __tablename__ = "price_histories"

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        comment="商品ID",
    )
    price = Column(Float, nullable=False, comment="价格")
    recorded_at = Column(DateTime, nullable=False, comment="记录时间")


class PriceAlert(BaseModel):
    """价格告警表模型

    字段说明:
        - product_id: 商品 ID，关联 products 表
        - alert_type: 告警类型（target_drop/price_increase/price_decrease）
        - threshold: 告警阈值，可为空
        - message: 告警消息内容，可为空
        - is_read: 是否已读，默认 False
    """

    __tablename__ = "price_alerts"

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        comment="商品ID",
    )
    alert_type = Column(String(20), nullable=False, comment="告警类型")
    threshold = Column(Float, nullable=True, comment="告警阈值")
    message = Column(Text, nullable=True, comment="告警消息")
    is_read = Column(
        Boolean, default=False, nullable=False, comment="是否已读"
    )
