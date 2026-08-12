"""舆情监控服务测试。

测试监控任务创建、舆情记录添加（自动情感分析）与舆情汇总统计。
使用 conftest.py 中的 db_session fixture 直接测试服务层。

注：在测试文件顶部导入模型，确保 SQLAlchemy 在建表时
将对应表注册到 Base.metadata。
"""

import pytest

from app.core.exceptions import NotFoundException
from app.models.sentiment_monitor import MonitorTask, SentimentRecord  # noqa: F401
from app.services.sentiment_monitor_service import SentimentMonitorService


@pytest.mark.asyncio
async def test_create_monitor_task(db_session):
    """测试创建监控任务。

    创建一个微博来源的监控任务，验证返回对象字段正确。
    """
    task_data = {
        "name": "品牌舆情监控",
        "source_type": "weibo",
        "keywords": "品牌名,产品名",
        "interval_minutes": 15,
    }

    task = await SentimentMonitorService.create_monitor_task(
        task_data, db_session
    )

    assert task.id is not None
    assert task.name == "品牌舆情监控"
    assert task.source_type == "weibo"
    assert task.keywords == "品牌名,产品名"
    assert task.interval_minutes == 15
    assert task.is_active is True
    assert task.created_at is not None


@pytest.mark.asyncio
async def test_add_sentiment_record(db_session):
    """测试添加舆情记录（自动情感分析）。

    先创建监控任务，再添加一条正面内容的舆情记录，
    验证自动情感分析将 sentiment 标记为 positive。
    """
    # 创建监控任务
    task = await SentimentMonitorService.create_monitor_task(
        {
            "name": "测试任务",
            "source_type": "xiaohongshu",
            "keywords": "测试",
            "interval_minutes": 30,
        },
        db_session,
    )

    # 添加正面内容舆情记录
    record = await SentimentMonitorService.add_sentiment_record(
        {
            "task_id": task.id,
            "content": "这个产品真的很好，非常满意，强烈推荐给大家！",
            "author": "用户A",
        },
        db_session,
    )

    assert record.id is not None
    assert record.task_id == task.id
    assert record.content == "这个产品真的很好，非常满意，强烈推荐给大家！"
    # 自动情感分析应为正面（包含"好""满意""推荐"等正面词）
    assert record.sentiment == "positive"
    assert record.score > 0


@pytest.mark.asyncio
async def test_add_sentiment_record_negative(db_session):
    """测试添加负面舆情记录的自动情感分析。

    添加一条负面内容，验证 sentiment 标记为 negative。
    """
    task = await SentimentMonitorService.create_monitor_task(
        {
            "name": "负面舆情任务",
            "source_type": "douyin",
            "keywords": "差评",
            "interval_minutes": 30,
        },
        db_session,
    )

    record = await SentimentMonitorService.add_sentiment_record(
        {
            "task_id": task.id,
            "content": "这个东西太糟糕了，非常失望，垃圾产品，差评！",
            "author": "用户B",
        },
        db_session,
    )

    assert record.sentiment == "negative"
    assert record.score < 0


@pytest.mark.asyncio
async def test_sentiment_summary(db_session):
    """测试舆情汇总统计。

    创建任务并添加多条不同情感的舆情记录，验证汇总数量与占比正确。
    """
    task = await SentimentMonitorService.create_monitor_task(
        {
            "name": "汇总测试任务",
            "source_type": "weibo",
            "keywords": "汇总",
            "interval_minutes": 30,
        },
        db_session,
    )

    # 添加 2 条正面、1 条负面、1 条中性
    contents = [
        "这个产品很好，非常满意",  # positive
        "很棒，推荐购买",  # positive
        "这个产品太糟糕了，垃圾",  # negative
        "今天收到了这个产品",  # neutral
    ]
    for content in contents:
        await SentimentMonitorService.add_sentiment_record(
            {"task_id": task.id, "content": content},
            db_session,
        )

    summary = await SentimentMonitorService.get_sentiment_summary(
        task.id, db_session
    )

    assert summary["task_id"] == task.id
    assert summary["total_count"] == 4
    assert summary["positive_count"] == 2
    assert summary["negative_count"] == 1
    assert summary["neutral_count"] == 1
    assert summary["positive_rate"] == 0.5
    assert summary["negative_rate"] == 0.25


@pytest.mark.asyncio
async def test_toggle_monitor_task(db_session):
    """测试启用/停用监控任务。"""
    task = await SentimentMonitorService.create_monitor_task(
        {
            "name": "启停测试",
            "source_type": "weibo",
            "keywords": "测试",
            "interval_minutes": 30,
        },
        db_session,
    )

    # 停用
    stopped = await SentimentMonitorService.toggle_monitor_task(
        task.id, False, db_session
    )
    assert stopped.is_active is False

    # 启用
    started = await SentimentMonitorService.toggle_monitor_task(
        task.id, True, db_session
    )
    assert started.is_active is True


@pytest.mark.asyncio
async def test_summary_task_not_found(db_session):
    """测试不存在的任务汇总应抛出 NotFoundException。"""
    with pytest.raises(NotFoundException):
        await SentimentMonitorService.get_sentiment_summary(99999, db_session)
