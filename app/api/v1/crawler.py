"""爬虫路由

提供网页抓取、批量抓取、数据查询和删除的接口。

接口列表:
    - POST   /crawl       抓取单个 URL
    - POST   /crawl/batch 批量抓取
    - GET    /data        分页查询已抓取数据
    - DELETE /data/{id}   删除抓取记录
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BusinessException, NotFoundException
from app.models.crawl_data import CrawlData
from app.schemas.common import PaginatedResponse, ResponseBase
from app.services.crawler_service import CrawlerService

router = APIRouter()


@router.post("/crawl", response_model=ResponseBase[dict], summary="抓取单个 URL")
async def crawl_url(
    url: str = Query(..., description="待抓取的页面 URL"),
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """抓取单个 URL

    抓取指定 URL 的页面内容，解析后保存到数据库。

    参数:
        url: 目标页面 URL
        db: 异步数据库会话

    返回:
        包含抓取数据（含保存后的记录 ID）的响应
    """
    # 抓取并解析页面
    data = await CrawlerService.crawl_url(url)

    # 保存到数据库
    crawl_data = await CrawlerService.save_crawl_data(data, db)

    # 构造响应数据
    result = {
        "id": crawl_data.id,
        "source_url": crawl_data.source_url,
        "title": crawl_data.title,
        "author": crawl_data.author,
        "tags": crawl_data.tags,
        "status": crawl_data.status,
        "created_at": crawl_data.created_at,
    }

    return ResponseBase(data=result)


@router.post(
    "/crawl/batch",
    response_model=ResponseBase[list[dict]],
    summary="批量抓取",
)
async def crawl_batch(
    urls: list[str] = Query(..., description="待抓取的 URL 列表"),
) -> ResponseBase[list[dict]]:
    """批量抓取多个 URL

    并发抓取多个 URL（最多 5 个并发），单个失败不影响其他任务。

    参数:
        urls: URL 列表

    返回:
        包含所有抓取结果的响应
    """
    results = await CrawlerService.crawl_batch(urls)
    return ResponseBase(data=results)


@router.get(
    "/data",
    response_model=PaginatedResponse[dict],
    summary="分页查询已抓取数据",
)
async def get_crawl_data(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[dict]:
    """分页查询已抓取的数据

    参数:
        page: 页码，从 1 开始
        page_size: 每页条数
        db: 异步数据库会话

    返回:
        分页响应，包含抓取数据列表和分页信息
    """
    # 查询总数
    count_result = await db.execute(select(func.count(CrawlData.id)))
    total = count_result.scalar() or 0

    # 查询当前页数据
    offset = (page - 1) * page_size
    result = await db.execute(
        select(CrawlData)
        .order_by(CrawlData.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.scalars().all()

    # 转换为字典列表
    data = [
        {
            "id": row.id,
            "source_url": row.source_url,
            "title": row.title,
            "content": row.content[:200] + "..." if len(row.content) > 200 else row.content,
            "author": row.author,
            "tags": row.tags,
            "sentiment_score": row.sentiment_score,
            "status": row.status,
            "created_at": row.created_at,
        }
        for row in rows
    ]

    return PaginatedResponse(data=data, total=total, page=page, page_size=page_size)


@router.delete(
    "/data/{item_id}",
    response_model=ResponseBase[dict],
    summary="删除抓取记录",
)
async def delete_crawl_data(
    item_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[dict]:
    """删除指定的抓取记录

    参数:
        item_id: 抓取记录 ID
        db: 异步数据库会话

    返回:
        包含删除结果的响应
    """
    # 查询记录是否存在
    result = await db.execute(select(CrawlData).where(CrawlData.id == item_id))
    crawl_data = result.scalar_one_or_none()

    if crawl_data is None:
        raise NotFoundException(f"抓取记录不存在: ID={item_id}")

    try:
        await db.delete(crawl_data)
        await db.commit()
        return ResponseBase(data={"id": item_id, "deleted": True})
    except Exception as e:
        await db.rollback()
        raise BusinessException(message=f"删除抓取记录失败: {e}")
