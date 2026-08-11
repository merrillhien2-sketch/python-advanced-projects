"""短链服务

提供短链接的创建、解析和分页查询功能。

特性:
    - 使用 hashlib + base62 编码生成 6 位短码
    - Redis 缓存短码与原始 URL 的映射，加速解析
    - 点击数统计
    - 过期时间支持
"""

import hashlib
import logging
import string
import time
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.core.redis_client import redis_client
from app.models.shortlink import ShortLink

logger = logging.getLogger(__name__)

# base62 字符集：0-9 + a-z + A-Z
BASE62_CHARS: str = string.digits + string.ascii_lowercase + string.ascii_uppercase
BASE62_BASE: int = len(BASE62_CHARS)  # 62

# Redis 短链缓存键前缀
SHORTLINK_REDIS_PREFIX: str = "shortlink:"

# 短链缓存过期时间（秒），默认 7 天
SHORTLINK_CACHE_TTL: int = 7 * 24 * 60 * 60


class ShortLinkService:
    """短链服务类

    提供短链创建、解析、分页查询等核心业务逻辑。
    """

    @staticmethod
    def _encode_base62(num: int) -> str:
        """将整数编码为 base62 字符串

        参数:
            num: 待编码的非负整数

        返回:
            base62 编码字符串
        """
        if num == 0:
            return BASE62_CHARS[0]

        chars: list[str] = []
        while num > 0:
            num, remainder = divmod(num, BASE62_BASE)
            chars.append(BASE62_CHARS[remainder])

        return "".join(reversed(chars))

    @classmethod
    def _generate_short_code(cls, url: str) -> str:
        """生成 6 位短码

        使用 URL + 当前时间戳生成 MD5 哈希，再进行 base62 编码，
        截取前 6 位作为短码。

        参数:
            url: 原始 URL

        返回:
            6 位短码字符串
        """
        # 组合 URL 和时间戳，增加随机性
        raw = f"{url}:{time.time()}:{url[-8:]}"
        hash_bytes = hashlib.md5(raw.encode("utf-8")).digest()
        hash_int = int.from_bytes(hash_bytes, byteorder="big")
        code = cls._encode_base62(hash_int)
        # 截取前 6 位作为短码
        return code[:6]

    @classmethod
    async def create_shortlink(
        cls, url: str, user_id: int | None, db: AsyncSession
    ) -> ShortLink:
        """创建短链

        生成 6 位短码，确保唯一性后存入数据库，并同步缓存至 Redis。

        参数:
            url: 原始长链接
            user_id: 创建者用户 ID（可为 None）
            db: 异步数据库会话

        返回:
            创建的 ShortLink 对象

        异常:
            ValidationException: URL 为空时
            BusinessException: 创建失败或短码冲突时
        """
        if not url or not url.strip():
            raise ValidationException("原始 URL 不能为空")

        try:
            # 生成短码，最多重试 5 次以避免冲突
            max_retries = 5
            short_code = ""
            for attempt in range(max_retries):
                short_code = cls._generate_short_code(url)
                # 检查短码是否已存在
                existing = await db.execute(
                    select(ShortLink.id).where(ShortLink.short_code == short_code)
                )
                if existing.first() is None:
                    break
                logger.warning("短码冲突，重试生成（第 %d 次）", attempt + 1)
            else:
                raise BusinessException(message="短码生成失败，多次冲突，请重试")

            # 创建短链记录
            shortlink = ShortLink(
                original_url=str(url),
                short_code=short_code,
                click_count=0,
                is_active=True,
                created_by=user_id,
            )
            db.add(shortlink)
            await db.commit()
            await db.refresh(shortlink)

            # 同步缓存至 Redis
            cache_key = f"{SHORTLINK_REDIS_PREFIX}{short_code}"
            await redis_client.set(
                cache_key, str(url), ex=SHORTLINK_CACHE_TTL
            )

            logger.info(
                "短链创建成功: %s -> %s (ID: %s)",
                short_code,
                url,
                shortlink.id,
            )
            return shortlink

        except BusinessException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error("创建短链失败: %s", e, exc_info=True)
            raise BusinessException(message=f"创建短链失败: {e}")

    @classmethod
    async def resolve_shortlink(
        cls, code: str, db: AsyncSession
    ) -> str:
        """解析短链，返回原始 URL

        优先从 Redis 缓存查询，缓存未命中时回退到数据库查询，
        查询成功后点击数 +1 并回填缓存。

        参数:
            code: 短码
            db: 异步数据库会话

        返回:
            原始 URL 字符串

        异常:
            ValidationException: 短码为空时
            NotFoundException: 短链不存在或已失效时
            BusinessException: 解析失败时
        """
        if not code or not code.strip():
            raise ValidationException("短码不能为空")

        code = code.strip()
        cache_key = f"{SHORTLINK_REDIS_PREFIX}{code}"

        try:
            # 第一步：优先查询 Redis 缓存
            cached_url = await redis_client.get(cache_key)
            if cached_url:
                # 缓存命中，异步更新点击数（不阻塞响应）
                await cls._increment_click_count(code, db)
                logger.info("短链缓存命中: %s", code)
                return cached_url

            # 第二步：缓存未命中，查询数据库
            result = await db.execute(
                select(ShortLink).where(ShortLink.short_code == code)
            )
            shortlink = result.scalar_one_or_none()

            if shortlink is None:
                raise NotFoundException(f"短码不存在: {code}")

            if not shortlink.is_active:
                raise BusinessException(message="该短链已被禁用")

            # 检查是否过期
            if shortlink.expires_at is not None:
                from datetime import datetime, timezone

                # 处理 naive 和 aware datetime
                now = datetime.now(timezone.utc)
                expires = shortlink.expires_at
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if now > expires:
                    raise BusinessException(message="该短链已过期")

            # 回填 Redis 缓存
            await redis_client.set(
                cache_key, shortlink.original_url, ex=SHORTLINK_CACHE_TTL
            )

            # 点击数 +1
            await cls._increment_click_count(code, db)

            logger.info("短链解析成功: %s -> %s", code, shortlink.original_url)
            return shortlink.original_url

        except (NotFoundException, BusinessException, ValidationException):
            raise
        except Exception as e:
            logger.error("解析短链失败: %s, 短码: %s", e, code, exc_info=True)
            raise BusinessException(message=f"解析短链失败: {e}")

    @staticmethod
    async def _increment_click_count(code: str, db: AsyncSession) -> None:
        """增加短链点击计数

        参数:
            code: 短码
            db: 异步数据库会话
        """
        try:
            await db.execute(
                update(ShortLink)
                .where(ShortLink.short_code == code)
                .values(click_count=ShortLink.click_count + 1)
            )
            await db.commit()
        except Exception as e:
            logger.warning("更新点击数失败（不影响跳转）: %s", e)
            await db.rollback()

    @classmethod
    async def get_shortlinks(
        cls,
        page: int,
        page_size: int,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """分页查询短链列表

        参数:
            page: 页码，从 1 开始
            page_size: 每页条数
            db: 异步数据库会话

        返回:
            包含 data（短链列表）、total、page、page_size 的字典

        异常:
            ValidationException: 分页参数无效时
            BusinessException: 查询失败时
        """
        if page < 1:
            raise ValidationException("页码必须大于 0")
        if page_size < 1 or page_size > 100:
            raise ValidationException("每页条数必须在 1-100 之间")

        try:
            # 查询总数
            count_result = await db.execute(select(func.count(ShortLink.id)))
            total = count_result.scalar() or 0

            # 查询当前页数据
            offset = (page - 1) * page_size
            result = await db.execute(
                select(ShortLink)
                .order_by(ShortLink.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            shortlinks = result.scalars().all()

            # 转换为字典列表
            data = [
                {
                    "id": sl.id,
                    "original_url": sl.original_url,
                    "short_code": sl.short_code,
                    "click_count": sl.click_count,
                    "is_active": sl.is_active,
                    "expires_at": sl.expires_at,
                    "created_at": sl.created_at,
                }
                for sl in shortlinks
            ]

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        except Exception as e:
            logger.error("查询短链列表失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询短链列表失败: {e}")
