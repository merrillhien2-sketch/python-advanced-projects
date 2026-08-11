"""定时任务模块。

包含系统级别的定时任务：
- 清理过期短链
- 定时爬取配置的 URL 列表
- 系统健康检查（检查 Redis、MySQL 连接）

所有任务均包含完善的异常处理和日志记录。
"""

import logging
import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis_client import redis_client
from app.models import ShortLink, CrawlData, TaskRecord

logger = logging.getLogger(__name__)


async def _clean_expired_shortlinks_async() -> dict[str, Any]:
    """异步执行清理过期短链的实际逻辑。

    Returns:
        包含清理结果统计的字典
    """
    cleaned_count = 0
    async with AsyncSessionLocal() as db:
        # 查询所有已过期的短链（expires_at 早于当前时间）
        now = datetime.utcnow()
        stmt = select(ShortLink).where(ShortLink.expires_at.isnot(None)).where(
            ShortLink.expires_at < now
        )
        result = await db.execute(stmt)
        expired_links = result.scalars().all()

        if not expired_links:
            logger.info("没有发现过期的短链，无需清理")
            return {"cleaned": 0, "message": "没有过期短链"}

        # 逐个删除过期短链，并清理 Redis 缓存
        for link in expired_links:
            try:
                # 删除 Redis 中的短链缓存
                cache_key = f"shortlink:{link.short_code}"
                await redis_client.delete(cache_key)
                # 删除数据库记录
                await db.delete(link)
                cleaned_count += 1
                logger.debug("已清理过期短链: short_code=%s, 原始URL=%s", link.short_code, link.original_url)
            except Exception as e:
                logger.error("清理短链 %s 时发生错误: %s", link.short_code, e, exc_info=True)

        await db.commit()

    logger.info("过期短链清理完成，共清理 %d 条", cleaned_count)
    return {"cleaned": cleaned_count, "message": f"已清理 {cleaned_count} 条过期短链"}


@celery_app.task(name="app.tasks.scheduled_tasks.clean_expired_shortlinks")
def clean_expired_shortlinks() -> dict[str, Any]:
    """清理过期短链的 Celery 任务。

    定时扫描数据库中所有已过期的短链记录，将其从数据库和 Redis 缓存中删除。
    每小时执行一次。

    Returns:
        包含清理结果统计的字典
    """
    logger.info("========== 开始执行清理过期短链任务 ==========")
    try:
        result = asyncio.get_event_loop().run_until_complete(
            _clean_expired_shortlinks_async()
        )
        logger.info("清理过期短链任务执行成功: %s", result)
        return result
    except Exception as e:
        logger.error("清理过期短链任务执行失败: %s", e, exc_info=True)
        return {"error": str(e), "cleaned": 0, "message": "任务执行失败"}


async def _scheduled_crawl_async() -> dict[str, Any]:
    """异步执行定时爬取的实际逻辑。

    从配置中读取需要爬取的 URL 列表，逐个抓取并存储结果。

    Returns:
        包含爬取结果统计的字典
    """
    # 从配置中获取待爬取的 URL 列表
    crawl_urls = getattr(settings, "CRAWL_URLS", []) or []
    if not crawl_urls:
        logger.info("未配置待爬取的 URL 列表，跳过爬取任务")
        return {"total": 0, "success": 0, "failed": 0, "message": "未配置爬取 URL"}

    total = len(crawl_urls)
    success_count = 0
    failed_count = 0
    crawled_data = []

    # 尝试导入 httpx 进行异步 HTTP 请求
    try:
        import httpx
    except ImportError:
        logger.error("httpx 未安装，无法执行爬取任务")
        return {"total": total, "success": 0, "failed": total, "message": "httpx 未安装"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for url in crawl_urls:
            try:
                logger.info("开始爬取 URL: %s", url)
                resp = await client.get(url)
                resp.raise_for_status()

                # 尝试从 HTML 中提取标题
                title = url
                try:
                    # 简单从 HTML 中提取 <title> 标签内容
                    text = resp.text
                    start = text.find("<title>")
                    end = text.find("</title>")
                    if start != -1 and end != -1 and end > start:
                        title = text[start + 7 : end].strip()[:500] or url
                except Exception:
                    pass

                # 存储爬取结果（使用 CrawlData 模型的正确字段）
                crawl_record = CrawlData(
                    source_url=url,
                    title=title,
                    content=resp.text[:10000],  # 限制存储长度，避免过大
                    status="active",
                )
                crawled_data.append(crawl_record)
                success_count += 1
                logger.info("爬取成功: %s (状态码: %d)", url, resp.status_code)
            except httpx.HTTPStatusError as e:
                failed_count += 1
                logger.error("爬取 HTTP 错误: %s, 状态码: %s", url, e.response.status_code)
            except Exception as e:
                failed_count += 1
                logger.error("爬取失败: %s, 错误: %s", url, e, exc_info=True)

    # 批量保存爬取结果到数据库
    if crawled_data:
        try:
            async with AsyncSessionLocal() as db:
                db.add_all(crawled_data)
                await db.commit()
            logger.info("已保存 %d 条爬取记录到数据库", len(crawled_data))
        except Exception as e:
            logger.error("保存爬取记录到数据库失败: %s", e, exc_info=True)

    logger.info("定时爬取任务完成: 总计 %d, 成功 %d, 失败 %d", total, success_count, failed_count)
    return {
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "message": f"爬取完成: 成功 {success_count}/{total}",
    }


@celery_app.task(name="app.tasks.scheduled_tasks.scheduled_crawl")
def scheduled_crawl() -> dict[str, Any]:
    """定时爬取的 Celery 任务。

    从配置中读取 URL 列表，逐个发起 HTTP 请求抓取页面内容，
    并将结果存储到数据库的 crawl_data 表中。每 30 分钟执行一次。

    Returns:
        包含爬取结果统计的字典
    """
    logger.info("========== 开始执行定时爬取任务 ==========")
    try:
        result = asyncio.get_event_loop().run_until_complete(_scheduled_crawl_async())
        logger.info("定时爬取任务执行成功: %s", result)
        return result
    except Exception as e:
        logger.error("定时爬取任务执行失败: %s", e, exc_info=True)
        return {"error": str(e), "total": 0, "success": 0, "failed": 0, "message": "任务执行失败"}


async def _health_check_async() -> dict[str, Any]:
    """异步执行系统健康检查的实际逻辑。

    检查 Redis 和 MySQL 数据库的连接状态。

    Returns:
        包含各组件健康状态的字典
    """
    result = {
        "redis": "ok",
        "mysql": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # 检查 Redis 连接
    try:
        await redis_client.ping()
        logger.info("Redis 连接正常")
    except Exception as e:
        result["redis"] = f"error: {e}"
        logger.error("Redis 连接异常: %s", e, exc_info=True)

    # 检查 MySQL 连接
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
        logger.info("MySQL 连接正常")
    except Exception as e:
        result["mysql"] = f"error: {e}"
        logger.error("MySQL 连接异常: %s", e, exc_info=True)

    # 将健康检查结果写入 Redis（供 API 读取）
    try:
        import json
        await redis_client.setex(
            "system:health:latest",
            300,  # 5 分钟过期
            json.dumps(result),
        )
    except Exception as e:
        logger.warning("写入健康检查结果到 Redis 失败: %s", e)

    return result


@celery_app.task(name="app.tasks.scheduled_tasks.health_check")
def health_check() -> dict[str, Any]:
    """系统健康检查的 Celery 任务。

    定期检查 Redis 和 MySQL 数据库的连接状态，
    将检查结果写入 Redis 缓存供 API 接口读取。每 5 分钟执行一次。

    Returns:
        包含各组件健康状态的字典
    """
    logger.info("========== 开始执行系统健康检查任务 ==========")
    try:
        result = asyncio.get_event_loop().run_until_complete(_health_check_async())
        logger.info("系统健康检查完成: %s", result)
        return result
    except Exception as e:
        logger.error("系统健康检查任务执行失败: %s", e, exc_info=True)
        return {"error": str(e), "redis": "unknown", "mysql": "unknown", "message": "任务执行失败"}
