"""电商价格监控服务测试。

测试商品添加、价格记录、价格统计和告警查询。
使用 conftest.py 中的 db_session fixture 提供测试数据库会话。
"""

import pytest

# 导入服务会自动注册模型到 Base.metadata，确保测试时表能被创建
from app.services.price_monitor_service import PriceMonitorService  # noqa: F401


@pytest.mark.asyncio
async def test_add_product(db_session):
    """测试添加监控商品。

    向服务层传入商品数据，验证返回的商品对象包含正确的字段值。
    """
    product = await PriceMonitorService.add_product(
        {
            "name": "Test Product",
            "url": "https://item.jd.com/12345.html",
            "platform": "jd",
            "target_price": 99.9,
            "image_url": "https://img.example.com/p.jpg",
        },
        db_session,
    )

    assert product.id is not None, "商品 ID 不应为空"
    assert product.name == "Test Product", "商品名称应一致"
    assert product.url == "https://item.jd.com/12345.html", "商品链接应一致"
    assert product.platform == "jd", "商品平台应为 jd"
    assert product.target_price == 99.9, "目标价格应一致"
    assert product.is_active is True, "默认应启用监控"
    assert product.created_at is not None, "创建时间不应为空"


@pytest.mark.asyncio
async def test_record_price(db_session):
    """测试记录价格。

    先添加商品，然后记录价格，验证价格历史记录和商品当前价格更新正确。
    """
    # 添加商品
    product = await PriceMonitorService.add_product(
        {
            "name": "Price Test Product",
            "url": "https://item.tmall.com/67890.html",
            "platform": "tmall",
        },
        db_session,
    )

    # 记录价格
    history = await PriceMonitorService.record_price(
        product.id, 199.0, db_session
    )

    assert history.id is not None, "价格历史 ID 不应为空"
    assert history.product_id == product.id, "商品 ID 应一致"
    assert history.price == 199.0, "价格应一致"
    assert history.recorded_at is not None, "记录时间不应为空"

    # 验证商品当前价格已更新
    from sqlalchemy import select
    from app.models.price_monitor import Product

    result = await db_session.execute(
        select(Product).where(Product.id == product.id)
    )
    updated_product = result.scalar_one_or_none()
    assert updated_product is not None, "商品应存在"
    assert updated_product.current_price == 199.0, "商品当前价格应已更新为 199.0"


@pytest.mark.asyncio
async def test_price_stats(db_session):
    """测试价格统计。

    添加商品并记录多次价格，验证统计信息包含最低/最高/均价和涨跌幅。
    """
    # 添加商品
    product = await PriceMonitorService.add_product(
        {
            "name": "Stats Product",
            "url": "https://item.pdd.com/11111.html",
            "platform": "pdd",
        },
        db_session,
    )

    # 记录多次价格
    await PriceMonitorService.record_price(product.id, 100.0, db_session)
    await PriceMonitorService.record_price(product.id, 120.0, db_session)
    await PriceMonitorService.record_price(product.id, 80.0, db_session)

    # 查询统计
    stats = await PriceMonitorService.get_price_stats(product.id, db_session)

    assert stats["product_id"] == product.id, "商品 ID 应一致"
    assert stats["name"] == "Stats Product", "商品名称应一致"
    assert stats["total_records"] == 3, f"总记录数应为 3，实际 {stats['total_records']}"
    assert stats["lowest_price"] == 80.0, f"最低价应为 80.0，实际 {stats['lowest_price']}"
    assert stats["highest_price"] == 120.0, f"最高价应为 120.0，实际 {stats['highest_price']}"
    assert stats["avg_price"] is not None, "平均价不应为空"
    assert stats["current_price"] == 80.0, "当前价格应为最后记录的 80.0"


@pytest.mark.asyncio
async def test_alerts(db_session):
    """测试价格告警。

    添加带目标价格的商品，记录低于目标价的价格，验证告警被触发并可查询。
    """
    # 添加商品，设置目标价为 100
    product = await PriceMonitorService.add_product(
        {
            "name": "Alert Product",
            "url": "https://www.amazon.com/dp/B123",
            "platform": "amazon",
            "target_price": 100.0,
        },
        db_session,
    )

    # 记录低于目标价的价格，应触发 target_drop 告警
    await PriceMonitorService.record_price(product.id, 89.9, db_session)

    # 查询告警
    result = await PriceMonitorService.get_alerts(
        page=1, page_size=20, unread_only=False, db=db_session
    )

    assert result["total"] >= 1, f"应至少有 1 条告警，实际 {result['total']}"
    alert = result["data"][0]
    assert alert["product_id"] == product.id, "告警的商品 ID 应一致"
    assert alert["alert_type"] == "target_drop", "告警类型应为 target_drop"
    assert alert["is_read"] is False, "新告警应为未读状态"
    assert alert["message"] is not None, "告警消息不应为空"
    assert "89.9" in alert["message"], "告警消息应包含价格 89.9"

    # 标记告警已读
    read_result = await PriceMonitorService.mark_alert_read(
        alert["id"], db_session
    )
    assert read_result["is_read"] is True, "标记后应为已读状态"
