"""AI 异步任务模块。

包含 AI 相关的异步任务：
- 异步 OCR 任务（光学字符识别）
- 异步情感分析任务
- 批量情感分析任务

任务执行时会更新 TaskRecord 表中的任务状态。
"""

import logging
import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models import TaskRecord

logger = logging.getLogger(__name__)


async def _update_task_status(
    task_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """更新 TaskRecord 表中的任务状态。

    Args:
        task_id: 任务记录 ID
        status: 任务状态（pending / running / success / failed）
        result: 任务执行结果（可选）
        error: 错误信息（可选）
    """
    import json

    try:
        async with AsyncSessionLocal() as db:
            # 查找任务记录（通过 task_id 字段查询，而非主键 id）
            stmt = select(TaskRecord).where(TaskRecord.task_id == task_id)
            res = await db.execute(stmt)
            task_record = res.scalars().first()

            if task_record is None:
                logger.warning("任务记录不存在: task_id=%s", task_id)
                return

            # 更新状态和相关信息
            task_record.status = status
            if status == "running":
                task_record.started_at = datetime.utcnow()
            elif status in ("success", "failed"):
                task_record.finished_at = datetime.utcnow()
            if result is not None:
                task_record.result = json.dumps(result, ensure_ascii=False)
            if error is not None:
                task_record.error = error

            await db.commit()
            logger.info("任务状态已更新: task_id=%s, status=%s", task_id, status)
    except Exception as e:
        logger.error("更新任务状态失败: task_id=%s, error=%s", task_id, e, exc_info=True)


def _do_ocr(image_base64: str) -> dict[str, Any]:
    """执行 OCR 识别的核心逻辑。

    使用模拟的 OCR 实现，实际项目中可替换为 PaddleOCR / Tesseract / 云服务 API。

    Args:
        image_base64: Base64 编码的图片数据

    Returns:
        包含识别文本的字典
    """
    # 模拟 OCR 识别过程
    # 实际项目中可替换为真实 OCR 引擎调用
    if not image_base64 or len(image_base64) < 10:
        raise ValueError("图片数据为空或格式无效")

    # 模拟识别结果
    recognized_text = "这是 OCR 识别出的示例文本内容。"
    confidence = 0.95

    logger.info("OCR 识别完成，置信度: %.2f", confidence)
    return {
        "text": recognized_text,
        "confidence": confidence,
        "engine": "mock-ocr",
    }


@celery_app.task(name="app.tasks.ai_tasks.async_ocr_task")
def async_ocr_task(task_id: str, image_base64: str) -> dict[str, Any]:
    """异步 OCR 任务的 Celery 入口。

    接收 Base64 编码的图片数据，执行光学字符识别，
    并将识别结果更新到 TaskRecord 表中。

    Args:
        task_id: 任务记录 ID，用于追踪任务状态
        image_base64: Base64 编码的图片数据

    Returns:
        包含识别结果的字典
    """
    logger.info("========== 开始执行异步 OCR 任务: task_id=%s ==========", task_id)
    loop = asyncio.new_event_loop()
    try:
        # 更新任务状态为运行中
        loop.run_until_complete(_update_task_status(task_id, "running"))

        # 执行 OCR 识别
        result = _do_ocr(image_base64)

        # 更新任务状态为成功
        loop.run_until_complete(_update_task_status(task_id, "success", result=result))
        logger.info("异步 OCR 任务执行成功: task_id=%s", task_id)
        return result
    except ValueError as e:
        logger.error("OCR 任务参数错误: task_id=%s, error=%s", task_id, e)
        loop.run_until_complete(_update_task_status(task_id, "failed", error=str(e)))
        return {"error": str(e), "text": "", "confidence": 0.0}
    except Exception as e:
        logger.error("OCR 任务执行失败: task_id=%s, error=%s", task_id, e, exc_info=True)
        loop.run_until_complete(_update_task_status(task_id, "failed", error=str(e)))
        return {"error": str(e), "text": "", "confidence": 0.0}
    finally:
        loop.close()


def _do_sentiment(text: str) -> dict[str, Any]:
    """执行情感分析的核心逻辑。

    使用基于关键词的简单情感分析，实际项目中可替换为
    机器学习模型或云服务 API（如百度 AI、阿里云 NLP）。

    Args:
        text: 待分析的文本

    Returns:
        包含情感分析结果的字典
    """
    if not text or not text.strip():
        raise ValueError("待分析的文本为空")

    # 正面情感关键词
    positive_words = ["好", "棒", "优秀", "喜欢", "开心", "满意", "赞", "完美", "推荐", "不错"]
    # 负面情感关键词
    negative_words = ["差", "坏", "糟糕", "讨厌", "失望", "愤怒", "不满", "垃圾", "难用", "差劲"]

    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)

    # 根据关键词匹配数量判定情感倾向
    if positive_count > negative_count:
        sentiment = "positive"
        score = 0.5 + 0.1 * (positive_count - negative_count)
    elif negative_count > positive_count:
        sentiment = "negative"
        score = -(0.5 + 0.1 * (negative_count - positive_count))
    else:
        sentiment = "neutral"
        score = 0.0

    # 限制分数范围在 [-1, 1]
    score = max(-1.0, min(1.0, score))

    logger.info("情感分析完成: sentiment=%s, score=%.2f", sentiment, score)
    return {
        "sentiment": sentiment,
        "score": round(score, 4),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "engine": "keyword-based",
    }


@celery_app.task(name="app.tasks.ai_tasks.async_sentiment_task")
def async_sentiment_task(task_id: str, text: str) -> dict[str, Any]:
    """异步情感分析任务的 Celery 入口。

    接收一段文本，分析其情感倾向（正面/负面/中性），
    并将分析结果更新到 TaskRecord 表中。

    Args:
        task_id: 任务记录 ID，用于追踪任务状态
        text: 待分析的文本

    Returns:
        包含情感分析结果的字典
    """
    logger.info("========== 开始执行异步情感分析任务: task_id=%s ==========", task_id)
    loop = asyncio.new_event_loop()
    try:
        # 更新任务状态为运行中
        loop.run_until_complete(_update_task_status(task_id, "running"))

        # 执行情感分析
        result = _do_sentiment(text)

        # 更新任务状态为成功
        loop.run_until_complete(_update_task_status(task_id, "success", result=result))
        logger.info("异步情感分析任务执行成功: task_id=%s", task_id)
        return result
    except ValueError as e:
        logger.error("情感分析任务参数错误: task_id=%s, error=%s", task_id, e)
        loop.run_until_complete(_update_task_status(task_id, "failed", error=str(e)))
        return {"error": str(e), "sentiment": "unknown", "score": 0.0}
    except Exception as e:
        logger.error("情感分析任务执行失败: task_id=%s, error=%s", task_id, e, exc_info=True)
        loop.run_until_complete(_update_task_status(task_id, "failed", error=str(e)))
        return {"error": str(e), "sentiment": "unknown", "score": 0.0}
    finally:
        loop.close()


@celery_app.task(name="app.tasks.ai_tasks.batch_sentiment_task")
def batch_sentiment_task(task_id: str, texts: list[str]) -> dict[str, Any]:
    """批量情感分析任务的 Celery 入口。

    接收一组文本，逐个分析情感倾向，汇总结果并更新到 TaskRecord 表中。

    Args:
        task_id: 任务记录 ID，用于追踪任务状态
        texts: 待分析的文本列表

    Returns:
        包含批量分析结果的字典
    """
    logger.info("========== 开始执行批量情感分析任务: task_id=%s, 共 %d 条文本 ==========", task_id, len(texts))
    loop = asyncio.new_event_loop()
    try:
        # 更新任务状态为运行中
        loop.run_until_complete(_update_task_status(task_id, "running"))

        results = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        failed_count = 0

        for index, text in enumerate(texts):
            try:
                single_result = _do_sentiment(text)
                single_result["index"] = index
                results.append(single_result)

                if single_result["sentiment"] == "positive":
                    positive_count += 1
                elif single_result["sentiment"] == "negative":
                    negative_count += 1
                else:
                    neutral_count += 1
            except Exception as e:
                failed_count += 1
                results.append({
                    "index": index,
                    "error": str(e),
                    "sentiment": "unknown",
                    "score": 0.0,
                })
                logger.warning("第 %d 条文本分析失败: %s", index, e)

        # 汇总结果
        summary = {
            "total": len(texts),
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
            "failed": failed_count,
            "results": results,
        }

        # 更新任务状态为成功
        loop.run_until_complete(_update_task_status(task_id, "success", result=summary))
        logger.info(
            "批量情感分析任务执行成功: task_id=%s, 正面=%d, 负面=%d, 中性=%d, 失败=%d",
            task_id, positive_count, negative_count, neutral_count, failed_count,
        )
        return summary
    except Exception as e:
        logger.error("批量情感分析任务执行失败: task_id=%s, error=%s", task_id, e, exc_info=True)
        loop.run_until_complete(_update_task_status(task_id, "failed", error=str(e)))
        return {"error": str(e), "total": len(texts), "results": []}
    finally:
        loop.close()
