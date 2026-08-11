"""爬虫服务

提供网页抓取与解析能力，支持单页和批量抓取，并保存抓取数据到数据库。

特性:
    - 使用 httpx 异步 HTTP 客户端
    - 使用 BeautifulSoup4 解析 HTML
    - User-Agent 轮换，降低被反爬风险
    - asyncio.Semaphore 控制并发数（最多 5）
"""

import asyncio
import logging
import random
from typing import Any

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessException, ValidationException
from app.models.crawl_data import CrawlData

logger = logging.getLogger(__name__)


class CrawlerService:
    """爬虫服务类

    提供网页抓取、解析和数据持久化能力。
    """

    # User-Agent 轮换池
    USER_AGENTS: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
        "Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]

    # 请求超时时间（秒）
    REQUEST_TIMEOUT: float = 30.0

    # 批量抓取最大并发数
    MAX_CONCURRENCY: int = 5

    @classmethod
    def _get_random_user_agent(cls) -> str:
        """随机获取一个 User-Agent"""
        return random.choice(cls.USER_AGENTS)

    @classmethod
    async def crawl_url(cls, url: str) -> dict[str, Any]:
        """抓取单个 URL 页面

        使用 httpx 异步请求页面，BeautifulSoup 解析 HTML，
        提取标题、正文、作者等关键信息。

        参数:
            url: 目标页面 URL

        返回:
            包含 source_url、title、content、author、tags 的字典

        异常:
            ValidationException: URL 为空时
            BusinessException: 抓取失败时
        """
        if not url or not url.strip():
            raise ValidationException("URL 不能为空")

        headers = {
            "User-Agent": cls._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                timeout=cls.REQUEST_TIMEOUT,
                follow_redirects=True,
                verify=False,
            ) as client:
                logger.info("开始抓取页面: %s", url)
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                # 自动检测编码
                response.encoding = response.charset_encoding or "utf-8"
                html = response.text

            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(html, "html.parser")

            # 提取标题
            title_tag = soup.find("title")
            h1_tag = soup.find("h1")
            title = ""
            if title_tag and title_tag.get_text(strip=True):
                title = title_tag.get_text(strip=True)
            elif h1_tag and h1_tag.get_text(strip=True):
                title = h1_tag.get_text(strip=True)

            # 提取正文：优先 article 标签，其次 main，最后 body
            article = soup.find("article") or soup.find("main") or soup.find("body")
            if article:
                # 移除 script 和 style 标签
                for tag in article.find_all(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                content = article.get_text(separator="\n", strip=True)
            else:
                content = ""

            # 提取作者：优先 meta 标签
            author = ""
            author_meta = soup.find("meta", attrs={"name": "author"}) or soup.find(
                "meta", attrs={"property": "article:author"}
            )
            if author_meta and author_meta.get("content"):
                author = author_meta.get("content", "").strip()

            # 提取关键词/标签
            tags = ""
            keywords_meta = soup.find("meta", attrs={"name": "keywords"})
            if keywords_meta and keywords_meta.get("content"):
                tags = keywords_meta.get("content", "").strip()

            result = {
                "source_url": url,
                "title": title or "无标题",
                "content": content[:10000] if content else "",  # 限制正文长度
                "author": author or None,
                "tags": tags or None,
            }

            logger.info("成功抓取页面: %s, 标题: %s", url, title)
            return result

        except httpx.HTTPStatusError as e:
            logger.error("抓取页面失败（HTTP %s）: %s", e.response.status_code, url)
            raise BusinessException(message=f"页面返回错误状态码: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error("请求异常: %s, URL: %s", e, url)
            raise BusinessException(message=f"请求失败: {e}")
        except Exception as e:
            logger.error("抓取页面失败: %s, URL: %s", e, url, exc_info=True)
            raise BusinessException(message=f"抓取页面失败: {e}")

    @classmethod
    async def crawl_batch(cls, urls: list[str]) -> list[dict[str, Any]]:
        """批量抓取多个 URL

        使用 asyncio.Semaphore 控制并发数（最多 5 个），
        并发抓取所有 URL，单个失败不影响其他任务。

        参数:
            urls: URL 列表

        返回:
            抓取结果列表，每个元素为成功抓取的数据或包含 error 信息的字典
        """
        if not urls:
            return []

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(cls.MAX_CONCURRENCY)

        async def _crawl_with_semaphore(url: str) -> dict[str, Any]:
            """带并发控制的单个抓取任务"""
            async with semaphore:
                try:
                    return await cls.crawl_url(url)
                except BusinessException as e:
                    # 单个失败不影响整体，记录错误信息
                    logger.warning("批量抓取中 URL 失败: %s, 错误: %s", url, e)
                    return {
                        "source_url": url,
                        "title": "",
                        "content": "",
                        "error": str(e),
                    }

        # 并发执行所有抓取任务
        tasks = [_crawl_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        logger.info("批量抓取完成，共 %d 个 URL", len(urls))
        return list(results)

    @staticmethod
    async def save_crawl_data(data: dict[str, Any], db: AsyncSession) -> CrawlData:
        """保存抓取数据到数据库

        参数:
            data: 抓取的数据字典（包含 source_url、title、content 等）
            db: 异步数据库会话

        返回:
            保存后的 CrawlData 对象

        异常:
            BusinessException: 保存失败时
        """
        try:
            crawl_data = CrawlData(
                source_url=data.get("source_url", ""),
                title=data.get("title", "无标题"),
                content=data.get("content", ""),
                author=data.get("author"),
                tags=data.get("tags"),
                status="active",
            )
            db.add(crawl_data)
            await db.commit()
            await db.refresh(crawl_data)

            logger.info("抓取数据已保存，ID: %s", crawl_data.id)
            return crawl_data
        except Exception as e:
            await db.rollback()
            logger.error("保存抓取数据失败: %s", e, exc_info=True)
            raise BusinessException(message=f"保存抓取数据失败: {e}")
