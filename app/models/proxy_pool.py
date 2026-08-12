"""代理 IP 池模型

定义代理 IP 表结构，存储 IP、端口、协议、匿名性、响应速度、可用性及
失败次数等信息，为代理池的添加、获取、健康检查与统计提供数据支撑。
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
)

from app.models.base import BaseModel


class ProxyIP(BaseModel):
    """代理 IP 表模型

    字段说明:
        - ip: 代理 IP 地址
        - port: 代理端口
        - protocol: 代理协议，取值 http / https / socks5
        - region: 归属地区，可为空
        - is_anonymous: 是否匿名代理，默认 True
        - speed: 响应时间（毫秒），可为空
        - is_available: 是否可用，默认 True
        - last_check_at: 上次健康检查时间，可为空
        - fail_count: 连续失败次数，默认 0
    """

    __tablename__ = "proxy_ips"

    ip = Column(String(50), nullable=False, comment="代理IP地址")
    port = Column(Integer, nullable=False, comment="代理端口")
    protocol = Column(
        String(10), nullable=False, default="http", comment="代理协议"
    )
    region = Column(String(50), nullable=True, comment="归属地区")
    is_anonymous = Column(
        Boolean, nullable=False, default=True, comment="是否匿名"
    )
    speed = Column(Float, nullable=True, comment="响应时间(毫秒)")
    is_available = Column(
        Boolean, nullable=False, default=True, comment="是否可用"
    )
    last_check_at = Column(DateTime, nullable=True, comment="上次检查时间")
    fail_count = Column(
        Integer, nullable=False, default=0, comment="连续失败次数"
    )
