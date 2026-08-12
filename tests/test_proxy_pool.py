"""代理 IP 池服务测试。

测试代理添加、随机获取、统计与删除。
使用 conftest.py 中的 db_session fixture 直接测试服务层。

注：在测试文件顶部导入模型，确保 SQLAlchemy 在建表时
将对应表注册到 Base.metadata。
"""

import pytest

from app.core.exceptions import NotFoundException
from app.models.proxy_pool import ProxyIP  # noqa: F401
from app.services.proxy_pool_service import ProxyPoolService


@pytest.mark.asyncio
async def test_add_proxy(db_session):
    """测试添加代理 IP。

    添加一个 HTTP 代理，验证返回对象字段正确。
    """
    proxy_data = {
        "ip": "192.168.1.100",
        "port": 8080,
        "protocol": "http",
        "region": "华东",
        "is_anonymous": True,
    }

    proxy = await ProxyPoolService.add_proxy(proxy_data, db_session)

    assert proxy.id is not None
    assert proxy.ip == "192.168.1.100"
    assert proxy.port == 8080
    assert proxy.protocol == "http"
    assert proxy.region == "华东"
    assert proxy.is_anonymous is True
    assert proxy.is_available is True
    assert proxy.fail_count == 0
    assert proxy.created_at is not None


@pytest.mark.asyncio
async def test_get_proxy(db_session):
    """测试随机获取可用代理。

    添加多个代理后，验证 get_proxy 能返回一个可用代理。
    """
    # 添加两个可用代理
    await ProxyPoolService.add_proxy(
        {"ip": "10.0.0.1", "port": 3128, "protocol": "http", "region": "华北"},
        db_session,
    )
    await ProxyPoolService.add_proxy(
        {"ip": "10.0.0.2", "port": 3128, "protocol": "http", "region": "华南"},
        db_session,
    )

    proxy = await ProxyPoolService.get_proxy(db=db_session)

    assert proxy is not None
    assert proxy["ip"] in ("10.0.0.1", "10.0.0.2")
    assert proxy["is_available"] is True
    assert proxy["port"] == 3128


@pytest.mark.asyncio
async def test_get_proxy_with_filter(db_session):
    """测试按协议筛选获取代理。"""
    await ProxyPoolService.add_proxy(
        {"ip": "10.0.0.3", "port": 1080, "protocol": "socks5", "region": "华北"},
        db_session,
    )
    await ProxyPoolService.add_proxy(
        {"ip": "10.0.0.4", "port": 8080, "protocol": "http", "region": "华北"},
        db_session,
    )

    # 仅获取 socks5 代理
    proxy = await ProxyPoolService.get_proxy(protocol="socks5", db=db_session)
    assert proxy["ip"] == "10.0.0.3"
    assert proxy["protocol"] == "socks5"


@pytest.mark.asyncio
async def test_get_proxy_not_found(db_session):
    """测试无可用代理时抛出 NotFoundException。"""
    with pytest.raises(NotFoundException):
        await ProxyPoolService.get_proxy(db=db_session)


@pytest.mark.asyncio
async def test_proxy_stats(db_session):
    """测试代理统计。

    添加 3 个代理（其中 1 个不可用），验证统计总数、可用数与协议分组。
    """
    # 添加 2 个 http 代理
    await ProxyPoolService.add_proxy(
        {"ip": "172.16.0.1", "port": 8080, "protocol": "http", "region": "华东"},
        db_session,
    )
    await ProxyPoolService.add_proxy(
        {"ip": "172.16.0.2", "port": 8080, "protocol": "http", "region": "华南"},
        db_session,
    )
    # 添加 1 个 socks5 代理
    await ProxyPoolService.add_proxy(
        {"ip": "172.16.0.3", "port": 1080, "protocol": "socks5", "region": "华北"},
        db_session,
    )

    stats = await ProxyPoolService.get_proxy_stats(db_session)

    assert stats["total"] == 3
    assert stats["available"] == 3
    assert stats["unavailable"] == 0

    # 按协议分组应包含 http 与 socks5
    protocols = {item["protocol"]: item for item in stats["by_protocol"]}
    assert "http" in protocols
    assert "socks5" in protocols
    assert protocols["http"]["total"] == 2
    assert protocols["http"]["available"] == 2
    assert protocols["socks5"]["total"] == 1
    assert protocols["socks5"]["available"] == 1


@pytest.mark.asyncio
async def test_delete_proxy(db_session):
    """测试删除代理 IP。"""
    proxy = await ProxyPoolService.add_proxy(
        {"ip": "10.5.0.1", "port": 8888, "protocol": "http", "region": "西南"},
        db_session,
    )

    result = await ProxyPoolService.delete_proxy(proxy.id, db_session)

    assert result["id"] == proxy.id
    assert result["deleted"] is True

    # 删除后再获取代理应抛出 NotFoundException
    with pytest.raises(NotFoundException):
        await ProxyPoolService.delete_proxy(proxy.id, db_session)
