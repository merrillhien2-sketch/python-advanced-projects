"""数据分析服务测试。

测试订单创建、批量导入、仪表盘统计（空数据情况）与用户画像生成。
使用 conftest.py 中的 db_session fixture 直接测试服务层。

注：在测试文件顶部导入模型，确保 SQLAlchemy 在建表时
将对应表注册到 Base.metadata。
"""

from datetime import datetime

import pytest

from app.core.exceptions import NotFoundException
from app.models.data_analysis import OrderRecord, UserProfile  # noqa: F401
from app.services.data_analysis_service import DataAnalysisService


def _make_order(order_id: str, user_id: int = 1001) -> dict:
    """构造一条订单数据字典，用于测试。"""
    return {
        "order_id": order_id,
        "product_name": "测试商品",
        "category": "电子产品",
        "amount": 999.0,
        "quantity": 2,
        "user_id": user_id,
        "region": "华东",
        "payment_method": "支付宝",
        "order_date": datetime.now(),
    }


@pytest.mark.asyncio
async def test_create_order(db_session):
    """测试创建订单。

    通过服务创建一条订单记录，验证返回对象包含主键且字段正确。
    """
    order_data = _make_order("ORD-TEST-001")

    order = await DataAnalysisService.create_order(order_data, db_session)

    assert order.id is not None, "创建订单后应返回主键 ID"
    assert order.order_id == "ORD-TEST-001"
    assert order.product_name == "测试商品"
    assert order.amount == 999.0
    assert order.quantity == 2
    assert order.user_id == 1001
    assert order.created_at is not None


@pytest.mark.asyncio
async def test_batch_import_orders(db_session):
    """测试批量导入订单。

    导入 3 条订单，其中 1 条订单号与前一条重复（应失败），
    验证成功 2 条、失败 1 条。
    """
    orders = [
        _make_order("BATCH-001", user_id=1),
        _make_order("BATCH-002", user_id=1),
        _make_order("BATCH-001", user_id=1),  # 重复订单号，应导入失败
    ]

    result = await DataAnalysisService.batch_import_orders(orders, db_session)

    assert result["total"] == 3
    assert result["success"] == 2, "应有 2 条导入成功"
    assert result["failed"] == 1, "应有 1 条因订单号重复而失败"
    assert len(result["errors"]) == 1


@pytest.mark.asyncio
async def test_dashboard_stats_empty(db_session):
    """测试仪表盘统计（空数据情况）。

    无任何订单数据时，统计结果应为零值与空列表。
    """
    stats = await DataAnalysisService.get_dashboard_stats(db_session)

    assert stats["total_revenue"] == 0.0
    assert stats["total_orders"] == 0
    assert stats["avg_order_amount"] == 0.0
    assert stats["top_categories"] == []
    assert stats["revenue_by_region"] == []


@pytest.mark.asyncio
async def test_user_profile(db_session):
    """测试用户画像。

    为同一用户创建 3 条订单，验证画像聚合结果（订单数、总金额、标签）。
    """
    user_id = 2001
    # 创建 3 条订单，金额合计 300
    for i, amount in enumerate([100.0, 80.0, 120.0], start=1):
        order_data = _make_order(f"PROFILE-{i}", user_id=user_id)
        order_data["amount"] = amount
        order_data["category"] = "电子产品"
        order_data["payment_method"] = "支付宝"
        await DataAnalysisService.create_order(order_data, db_session)

    profile = await DataAnalysisService.get_user_profile(user_id, db_session)

    assert profile["user_id"] == user_id
    assert profile["total_orders"] == 3
    assert profile["total_amount"] == 300.0
    assert profile["avg_order_amount"] == 100.0
    assert profile["top_category"] == "电子产品"
    assert profile["top_payment"] == "支付宝"
    assert profile["tags"], "用户画像标签不应为空"
    assert "偏好:电子产品" in profile["tags"]


@pytest.mark.asyncio
async def test_user_profile_not_found(db_session):
    """测试无订单用户的画像查询应抛出 NotFoundException。"""
    with pytest.raises(NotFoundException):
        await DataAnalysisService.get_user_profile(99999, db_session)
