"""数据分析可视化模型

定义订单记录与用户画像两张表结构，为数据分析仪表盘、营收趋势、
品类分布及用户消费画像等功能提供数据持久化支撑。
"""

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.models.base import BaseModel


class OrderRecord(BaseModel):
    """订单记录表模型

    存储每笔订单的关键信息，用于后续营收统计、趋势分析与品类分布计算。

    字段说明:
        - order_id: 业务订单号，唯一且建立索引，便于按订单号快速检索
        - product_name: 商品名称
        - category: 商品品类，用于品类分布统计
        - amount: 订单金额（元）
        - quantity: 购买数量
        - user_id: 下单用户 ID，用于关联用户画像
        - region: 下单地区，用于地区营收统计
        - payment_method: 支付方式
        - order_date: 下单时间，用于按日期聚合营收趋势
    """

    __tablename__ = "order_records"

    order_id = Column(
        String(64), unique=True, index=True, nullable=False, comment="业务订单号"
    )
    product_name = Column(
        String(200), nullable=False, comment="商品名称"
    )
    category = Column(String(50), nullable=False, comment="商品品类")
    amount = Column(Float, nullable=False, comment="订单金额")
    quantity = Column(Integer, nullable=False, default=1, comment="购买数量")
    user_id = Column(Integer, nullable=False, index=True, comment="下单用户ID")
    region = Column(String(50), nullable=False, comment="下单地区")
    payment_method = Column(String(30), nullable=False, comment="支付方式")
    order_date = Column(DateTime, nullable=False, comment="下单时间")


class UserProfile(BaseModel):
    """用户画像表模型

    基于用户历史订单数据聚合生成的消费行为画像，包含基础属性与消费统计标签。

    字段说明:
        - user_id: 用户 ID，建立索引便于按用户查询画像
        - age: 年龄，可为空
        - gender: 性别，可为空
        - region: 主要消费地区
        - total_orders: 累计订单数，默认 0
        - total_amount: 累计消费金额，默认 0
        - tags: 消费行为标签（逗号分隔），可为空
    """

    __tablename__ = "user_profiles"

    user_id = Column(
        Integer, nullable=False, index=True, comment="用户ID"
    )
    age = Column(Integer, nullable=True, comment="年龄")
    gender = Column(String(10), nullable=True, comment="性别")
    region = Column(String(50), nullable=False, comment="主要消费地区")
    total_orders = Column(
        Integer, nullable=False, default=0, comment="累计订单数"
    )
    total_amount = Column(
        Float, nullable=False, default=0, comment="累计消费金额"
    )
    tags = Column(String(500), nullable=True, comment="消费行为标签")
