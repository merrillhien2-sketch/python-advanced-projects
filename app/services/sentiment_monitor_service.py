"""舆情监控服务

提供监控任务的创建与启停、舆情记录的分页查询、情感汇总统计、
手动情感分析及舆情记录添加（自动分析情感）等核心业务逻辑。
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessException,
    NotFoundException,
    ValidationException,
)
from app.models.sentiment_monitor import MonitorTask, SentimentRecord
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class SentimentMonitorService:
    """舆情监控服务类

    以静态方法形式提供舆情监控能力，无需实例化。
    """

    @staticmethod
    async def create_monitor_task(
        task_data: dict, db: AsyncSession
    ) -> MonitorTask:
        """创建监控任务

        参数:
            task_data: 任务数据字典，包含名称、来源、关键词等
            db: 异步数据库会话

        返回:
            创建后的 MonitorTask 对象

        异常:
            ValidationException: 关键字段缺失或来源类型非法时
            BusinessException: 创建失败时
        """
        # 校验来源类型
        valid_sources = {"weibo", "xiaohongshu", "douyin"}
        source_type = task_data.get("source_type")
        if not source_type or source_type not in valid_sources:
            raise ValidationException(
                f"数据来源类型非法，仅支持: {', '.join(sorted(valid_sources))}"
            )

        if not task_data.get("name"):
            raise ValidationException("任务名称不能为空")
        if not task_data.get("keywords"):
            raise ValidationException("监控关键词不能为空")

        try:
            task = MonitorTask(
                name=task_data["name"],
                source_type=source_type,
                keywords=task_data["keywords"],
                interval_minutes=int(task_data.get("interval_minutes", 30)),
                is_active=True,
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)

            logger.info(
                "监控任务创建成功: id=%s, name=%s, source=%s",
                task.id,
                task.name,
                task.source_type,
            )
            return task
        except (ValidationException,):
            raise
        except Exception as e:
            await db.rollback()
            logger.error("创建监控任务失败: %s", e, exc_info=True)
            raise BusinessException(message=f"创建监控任务失败: {e}")

    @staticmethod
    async def get_monitor_tasks(
        page: int, page_size: int, db: AsyncSession
    ) -> dict[str, Any]:
        """分页查询监控任务列表

        参数:
            page: 页码，从 1 开始
            page_size: 每页条数
            db: 异步数据库会话

        返回:
            包含 data（任务列表）、total、page、page_size 的字典
        """
        if page < 1:
            raise ValidationException("页码必须大于 0")
        if page_size < 1 or page_size > 100:
            raise ValidationException("每页条数必须在 1-100 之间")

        try:
            # 查询总数
            count_result = await db.execute(select(func.count(MonitorTask.id)))
            total = int(count_result.scalar() or 0)

            # 查询当前页数据
            offset = (page - 1) * page_size
            result = await db.execute(
                select(MonitorTask)
                .order_by(MonitorTask.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            tasks = result.scalars().all()

            data = [
                {
                    "id": t.id,
                    "name": t.name,
                    "source_type": t.source_type,
                    "keywords": t.keywords,
                    "interval_minutes": t.interval_minutes,
                    "is_active": t.is_active,
                    "last_run_at": t.last_run_at,
                    "created_at": t.created_at,
                }
                for t in tasks
            ]

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        except (ValidationException,):
            raise
        except Exception as e:
            logger.error("查询监控任务列表失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询监控任务列表失败: {e}")

    @staticmethod
    async def get_sentiment_records(
        task_id: int, page: int, page_size: int, db: AsyncSession
    ) -> dict[str, Any]:
        """分页查询某任务下的舆情记录

        参数:
            task_id: 监控任务 ID
            page: 页码
            page_size: 每页条数
            db: 异步数据库会话

        返回:
            包含 data、total、page、page_size 的字典

        异常:
            NotFoundException: 任务不存在时
        """
        if page < 1:
            raise ValidationException("页码必须大于 0")
        if page_size < 1 or page_size > 100:
            raise ValidationException("每页条数必须在 1-100 之间")

        try:
            # 校验任务是否存在
            task_result = await db.execute(
                select(MonitorTask.id).where(MonitorTask.id == task_id)
            )
            if task_result.first() is None:
                raise NotFoundException(f"监控任务不存在: id={task_id}")

            # 查询总数
            count_result = await db.execute(
                select(func.count(SentimentRecord.id)).where(
                    SentimentRecord.task_id == task_id
                )
            )
            total = int(count_result.scalar() or 0)

            # 查询当前页数据
            offset = (page - 1) * page_size
            result = await db.execute(
                select(SentimentRecord)
                .where(SentimentRecord.task_id == task_id)
                .order_by(SentimentRecord.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            records = result.scalars().all()

            data = [
                {
                    "id": r.id,
                    "task_id": r.task_id,
                    "source_type": r.source_type,
                    "content": r.content,
                    "author": r.author,
                    "sentiment": r.sentiment,
                    "score": r.score,
                    "url": r.url,
                    "published_at": r.published_at,
                    "created_at": r.created_at,
                }
                for r in records
            ]

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error("查询舆情记录失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询舆情记录失败: {e}")

    @staticmethod
    async def get_sentiment_summary(
        task_id: int, db: AsyncSession
    ) -> dict[str, Any]:
        """获取任务舆情汇总统计

        统计该任务下正/负/中性情感数量及占比。

        参数:
            task_id: 监控任务 ID
            db: 异步数据库会话

        返回:
            舆情汇总字典，结构同 SentimentSummary

        异常:
            NotFoundException: 任务不存在时
        """
        try:
            # 校验任务是否存在
            task_result = await db.execute(
                select(MonitorTask.id).where(MonitorTask.id == task_id)
            )
            if task_result.first() is None:
                raise NotFoundException(f"监控任务不存在: id={task_id}")

            # 按情感倾向分组统计
            result = await db.execute(
                select(
                    SentimentRecord.sentiment,
                    func.count(SentimentRecord.id).label("cnt"),
                )
                .where(SentimentRecord.task_id == task_id)
                .group_by(SentimentRecord.sentiment)
            )
            rows = result.all()

            # 构建情感计数映射
            counts = {row.sentiment: int(row.cnt) for row in rows}
            total_count = sum(counts.values())
            positive_count = counts.get("positive", 0)
            negative_count = counts.get("negative", 0)
            neutral_count = counts.get("neutral", 0)

            positive_rate = (
                round(positive_count / total_count, 4) if total_count > 0 else 0.0
            )
            negative_rate = (
                round(negative_count / total_count, 4) if total_count > 0 else 0.0
            )

            return {
                "task_id": task_id,
                "total_count": total_count,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "positive_rate": positive_rate,
                "negative_rate": negative_rate,
            }
        except (NotFoundException,):
            raise
        except Exception as e:
            logger.error("获取舆情汇总失败: %s", e, exc_info=True)
            raise BusinessException(message=f"获取舆情汇总失败: {e}")

    @staticmethod
    async def analyze_sentiment_for_task(
        task_id: int, db: AsyncSession
    ) -> dict[str, Any]:
        """对任务下的舆情记录执行情感分析

        遍历任务下的舆情记录，调用 AIService.sentiment_analyze 对内容进行
        情感分析，并更新记录的情感倾向与得分。

        参数:
            task_id: 监控任务 ID
            db: 异步数据库会话

        返回:
            包含 task_id、analyzed（分析数量）与 summary（汇总）的字典

        异常:
            NotFoundException: 任务不存在时
        """
        try:
            # 校验任务是否存在
            task_result = await db.execute(
                select(MonitorTask).where(MonitorTask.id == task_id)
            )
            task = task_result.scalar_one_or_none()
            if task is None:
                raise NotFoundException(f"监控任务不存在: id={task_id}")

            # 查询任务下所有舆情记录
            result = await db.execute(
                select(SentimentRecord).where(
                    SentimentRecord.task_id == task_id
                )
            )
            records = result.scalars().all()

            analyzed = 0
            for record in records:
                # 调用 AI 服务进行情感分析
                analysis = await AIService.sentiment_analyze(record.content)
                record.sentiment = analysis.get("sentiment", "neutral")
                record.score = float(analysis.get("score", 0.0))
                analyzed += 1

            # 更新任务上次执行时间
            task.last_run_at = datetime.now()
            await db.commit()

            # 返回最新汇总
            summary = await SentimentMonitorService.get_sentiment_summary(
                task_id, db
            )

            logger.info(
                "任务 %s 情感分析完成: 共分析 %d 条记录", task_id, analyzed
            )
            return {
                "task_id": task_id,
                "analyzed": analyzed,
                "summary": summary,
            }
        except (NotFoundException,):
            raise
        except Exception as e:
            await db.rollback()
            logger.error("情感分析失败: %s", e, exc_info=True)
            raise BusinessException(message=f"情感分析失败: {e}")

    @staticmethod
    async def toggle_monitor_task(
        task_id: int, is_active: bool, db: AsyncSession
    ) -> MonitorTask:
        """启用或停用监控任务

        参数:
            task_id: 监控任务 ID
            is_active: 目标状态，True 启用 / False 停用
            db: 异步数据库会话

        返回:
            更新后的 MonitorTask 对象

        异常:
            NotFoundException: 任务不存在时
            BusinessException: 更新失败时
        """
        try:
            result = await db.execute(
                select(MonitorTask).where(MonitorTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task is None:
                raise NotFoundException(f"监控任务不存在: id={task_id}")

            task.is_active = is_active
            await db.commit()
            await db.refresh(task)

            logger.info(
                "监控任务 %s 状态已更新为: %s", task_id, is_active
            )
            return task
        except (NotFoundException,):
            raise
        except Exception as e:
            await db.rollback()
            logger.error("更新监控任务状态失败: %s", e, exc_info=True)
            raise BusinessException(message=f"更新监控任务状态失败: {e}")

    @staticmethod
    async def add_sentiment_record(
        record_data: dict, db: AsyncSession
    ) -> SentimentRecord:
        """添加舆情记录（自动分析情感）

        创建舆情记录时自动调用 AIService.sentiment_analyze 对内容进行
        情感分析，并将结果写入 sentiment 与 score 字段。

        参数:
            record_data: 记录数据字典，包含 task_id、content、author 等
            db: 异步数据库会话

        返回:
            创建后的 SentimentRecord 对象

        异常:
            ValidationException: 关键字段缺失时
            NotFoundException: 关联任务不存在时
            BusinessException: 创建失败时
        """
        if not record_data or not record_data.get("content"):
            raise ValidationException("舆情内容(content)不能为空")
        if not record_data.get("task_id"):
            raise ValidationException("监控任务ID(task_id)不能为空")

        task_id = int(record_data["task_id"])

        try:
            # 校验任务是否存在
            task_result = await db.execute(
                select(MonitorTask).where(MonitorTask.id == task_id)
            )
            task = task_result.scalar_one_or_none()
            if task is None:
                raise NotFoundException(f"监控任务不存在: id={task_id}")

            # 自动执行情感分析
            content = record_data["content"]
            analysis = await AIService.sentiment_analyze(content)
            sentiment = analysis.get("sentiment", "neutral")
            score = float(analysis.get("score", 0.0))

            record = SentimentRecord(
                task_id=task_id,
                source_type=record_data.get(
                    "source_type", task.source_type
                ),
                content=content,
                author=record_data.get("author"),
                sentiment=sentiment,
                score=score,
                url=record_data.get("url"),
                published_at=record_data.get("published_at"),
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)

            logger.info(
                "舆情记录添加成功: id=%s, task_id=%s, sentiment=%s",
                record.id,
                task_id,
                sentiment,
            )
            return record
        except (ValidationException, NotFoundException):
            raise
        except Exception as e:
            await db.rollback()
            logger.error("添加舆情记录失败: %s", e, exc_info=True)
            raise BusinessException(message=f"添加舆情记录失败: {e}")
