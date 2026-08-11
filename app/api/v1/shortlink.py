"""短链路由

提供短链创建、跳转和列表查询的接口。

接口列表:
    - POST /        创建短链（需要认证）
    - GET  /{code}  短链跳转（重定向到原始 URL）
    - GET  /        分页查询短链列表
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import PaginatedResponse, ResponseBase
from app.schemas.shortlink import ShortLinkCreate, ShortLinkResponse
from app.services.shortlink_service import ShortLinkService

router = APIRouter()


@router.post(
    "/",
    response_model=ResponseBase[ShortLinkResponse],
    summary="创建短链",
)
async def create_shortlink(
    link_in: ShortLinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[ShortLinkResponse]:
    """创建短链

    将原始长链接转换为 6 位短码，存入数据库并缓存至 Redis。
    需要用户认证。

    参数:
        link_in: 短链创建请求（原始 URL、可选过期时间）
        current_user: 当前登录的 User 对象
        db: 异步数据库会话

    返回:
        包含短链信息的响应
    """
    shortlink = await ShortLinkService.create_shortlink(
        url=str(link_in.original_url),
        user_id=current_user.id,
        db=db,
    )

    return ResponseBase(data=ShortLinkResponse.model_validate(shortlink))


@router.get(
    "/{code}",
    summary="短链跳转",
    description="根据短码重定向到原始 URL",
)
async def redirect_shortlink(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """短链跳转

    根据短码解析原始 URL 并执行 302 重定向。
    优先从 Redis 缓存查询，缓存未命中时回退到数据库。
    每次访问点击数 +1。

    参数:
        code: 短码
        db: 异步数据库会话

    返回:
        302 重定向响应
    """
    original_url = await ShortLinkService.resolve_shortlink(code, db)
    return RedirectResponse(url=original_url, status_code=302)


@router.get(
    "/",
    response_model=PaginatedResponse[ShortLinkResponse],
    summary="分页查询短链列表",
)
async def list_shortlinks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ShortLinkResponse]:
    """分页查询短链列表

    参数:
        page: 页码，从 1 开始
        page_size: 每页条数
        db: 异步数据库会话

    返回:
        分页响应，包含短链列表和分页信息
    """
    result = await ShortLinkService.get_shortlinks(page, page_size, db)

    # 将字典列表转换为 ShortLinkResponse 列表
    data = [ShortLinkResponse(**item) for item in result["data"]]

    return PaginatedResponse(
        data=data,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
