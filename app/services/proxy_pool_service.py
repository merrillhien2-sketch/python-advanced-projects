"""代理 IP 池服务

提供代理 IP 的添加、批量导入、随机获取、分页查询、健康检查、
删除及统计等核心业务逻辑。健康检查使用 httpx 实际请求目标 URL，
测量响应时间；批量检查通过 asyncio.Semaphore 控制并发。
"""

import asyncio
import logging
import random
import time
from typing import Any

import httpx
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessException,
    NotFoundException,
    ValidationException,
)
from app.models.proxy_pool import ProxyIP

logger = logging.getLogger(__name__)

# 健康检查目标 URL，用于测试代理可用性
PROXY_CHECK_URL: str = "https://httpbin.org/ip"
# 健康检查超时时间（秒）
PROXY_CHECK_TIMEOUT: float = 10.0
# 批量检查最大并发数
BATCH_CHECK_CONCURRENCY: int = 5


class ProxyPoolService:
    """代理 IP 池服务类

    以静态方法形式提供代理池管理能力，无需实例化。
    """

    @staticmethod
    async def add_proxy(proxy_data: dict, db: AsyncSession) -> ProxyIP:
        """添加单个代理 IP

        参数:
            proxy_data: 代理数据字典，包含 ip、port、protocol 等
            db: 异步数据库会话

        返回:
            创建后的 ProxyIP 对象

        异常:
            ValidationException: 关键字段缺失或协议非法时
            BusinessException: 创建失败时
        """
        valid_protocols = {"http", "https", "socks5"}
        protocol = proxy_data.get("protocol", "http")
        if protocol not in valid_protocols:
            raise ValidationException(
                f"代理协议非法，仅支持: {', '.join(sorted(valid_protocols))}"
            )

        if not proxy_data.get("ip"):
            raise ValidationException("代理IP(ip)不能为空")
        if not proxy_data.get("port"):
            raise ValidationException("代理端口(port)不能为空")

        try:
            proxy = ProxyIP(
                ip=proxy_data["ip"],
                port=int(proxy_data["port"]),
                protocol=protocol,
                region=proxy_data.get("region"),
                is_anonymous=bool(proxy_data.get("is_anonymous", True)),
                is_available=True,
                fail_count=0,
            )
            db.add(proxy)
            await db.commit()
            await db.refresh(proxy)

            logger.info(
                "代理IP添加成功: id=%s, %s://%s:%s",
                proxy.id,
                proxy.protocol,
                proxy.ip,
                proxy.port,
            )
            return proxy
        except (ValidationException,):
            raise
        except Exception as e:
            await db.rollback()
            logger.error("添加代理IP失败: %s", e, exc_info=True)
            raise BusinessException(message=f"添加代理IP失败: {e}")

    @staticmethod
    async def batch_add_proxies(
        proxies: list[dict], db: AsyncSession
    ) -> dict[str, Any]:
        """批量导入代理 IP

        逐条添加代理，单条失败不影响其他，返回成功与失败统计。

        参数:
            proxies: 代理数据字典列表
            db: 异步数据库会话

        返回:
            包含 total、success、failed、errors 的统计字典
        """
        if not proxies:
            raise ValidationException("导入代理列表不能为空")

        total = len(proxies)
        success_count = 0
        errors: list[dict[str, Any]] = []

        for index, proxy_data in enumerate(proxies):
            try:
                await ProxyPoolService.add_proxy(proxy_data, db)
                success_count += 1
            except Exception as e:
                errors.append(
                    {
                        "index": index,
                        "ip": proxy_data.get("ip"),
                        "error": str(e),
                    }
                )
                logger.warning(
                    "第 %d 条代理导入失败: ip=%s, error=%s",
                    index,
                    proxy_data.get("ip"),
                    e,
                )

        result = {
            "total": total,
            "success": success_count,
            "failed": total - success_count,
            "errors": errors,
        }
        logger.info(
            "批量导入代理完成: 共 %d 条, 成功 %d 条, 失败 %d 条",
            total,
            success_count,
            total - success_count,
        )
        return result

    @staticmethod
    async def get_proxy(
        protocol: str | None = None,
        region: str | None = None,
        db: AsyncSession = None,
    ) -> dict[str, Any]:
        """随机获取一个可用代理（优先返回速度快的）

        从可用代理中按响应速度升序取若干个，再随机挑选一个返回，
        兼顾速度与负载均衡。

        参数:
            protocol: 可选，按协议筛选
            region: 可选，按地区筛选
            db: 异步数据库会话

        返回:
            代理信息字典

        异常:
            NotFoundException: 无可用代理时
        """
        try:
            stmt = select(ProxyIP).where(ProxyIP.is_available.is_(True))

            # 可选筛选条件
            if protocol:
                stmt = stmt.where(ProxyIP.protocol == protocol)
            if region:
                stmt = stmt.where(ProxyIP.region == region)

            result = await db.execute(stmt)
            proxies = result.scalars().all()

            if not proxies:
                raise NotFoundException("无可用代理IP")

            # 按响应速度升序排序（速度为空者排后），优先取速度较快的若干个
            proxies.sort(
                key=lambda p: (p.speed is None, p.speed if p.speed is not None else 0)
            )
            # 从速度最快的若干个中随机挑选，兼顾负载均衡
            top_n = proxies[: min(10, len(proxies))]
            chosen = random.choice(top_n)

            return {
                "id": chosen.id,
                "ip": chosen.ip,
                "port": chosen.port,
                "protocol": chosen.protocol,
                "region": chosen.region,
                "is_anonymous": chosen.is_anonymous,
                "speed": chosen.speed,
                "is_available": chosen.is_available,
                "fail_count": chosen.fail_count,
            }
        except (NotFoundException,):
            raise
        except Exception as e:
            logger.error("获取代理IP失败: %s", e, exc_info=True)
            raise BusinessException(message=f"获取代理IP失败: {e}")

    @staticmethod
    async def get_proxies(
        page: int,
        page_size: int,
        protocol: str | None,
        region: str | None,
        available_only: bool,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """分页查询代理 IP 列表

        参数:
            page: 页码
            page_size: 每页条数
            protocol: 可选，按协议筛选
            region: 可选，按地区筛选
            available_only: 是否仅查询可用代理
            db: 异步数据库会话

        返回:
            包含 data、total、page、page_size 的字典
        """
        if page < 1:
            raise ValidationException("页码必须大于 0")
        if page_size < 1 or page_size > 100:
            raise ValidationException("每页条数必须在 1-100 之间")

        try:
            # 构建查询条件
            stmt = select(ProxyIP)
            count_stmt = select(func.count(ProxyIP.id))

            if protocol:
                stmt = stmt.where(ProxyIP.protocol == protocol)
                count_stmt = count_stmt.where(ProxyIP.protocol == protocol)
            if region:
                stmt = stmt.where(ProxyIP.region == region)
                count_stmt = count_stmt.where(ProxyIP.region == region)
            if available_only:
                stmt = stmt.where(ProxyIP.is_available.is_(True))
                count_stmt = count_stmt.where(ProxyIP.is_available.is_(True))

            # 查询总数
            count_result = await db.execute(count_stmt)
            total = int(count_result.scalar() or 0)

            # 查询当前页数据
            offset = (page - 1) * page_size
            result = await db.execute(
                stmt.order_by(ProxyIP.id.desc()).offset(offset).limit(page_size)
            )
            proxies = result.scalars().all()

            data = [
                {
                    "id": p.id,
                    "ip": p.ip,
                    "port": p.port,
                    "protocol": p.protocol,
                    "region": p.region,
                    "is_anonymous": p.is_anonymous,
                    "speed": p.speed,
                    "is_available": p.is_available,
                    "last_check_at": p.last_check_at,
                    "fail_count": p.fail_count,
                    "created_at": p.created_at,
                }
                for p in proxies
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
            logger.error("查询代理列表失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询代理列表失败: {e}")

    @staticmethod
    async def check_proxy(proxy_id: int, db: AsyncSession) -> dict[str, Any]:
        """检查单个代理可用性

        使用 httpx 通过代理请求目标 URL，测量响应时间，并更新代理状态。
        成功时重置失败计数并记录响应时间；失败时失败计数 +1，超过阈值标记不可用。

        参数:
            proxy_id: 代理 ID
            db: 异步数据库会话

        返回:
            检查结果字典，包含 id、is_available、speed、fail_count

        异常:
            NotFoundException: 代理不存在时
            BusinessException: 检查失败时
        """
        try:
            result = await db.execute(
                select(ProxyIP).where(ProxyIP.id == proxy_id)
            )
            proxy = result.scalar_one_or_none()
            if proxy is None:
                raise NotFoundException(f"代理IP不存在: id={proxy_id}")

            # 构建代理 URL
            proxy_url = ProxyPoolService._build_proxy_url(proxy)

            # 通过代理实际请求目标 URL，测量响应时间
            start_time = time.perf_counter()
            is_ok = False
            try:
                async with httpx.AsyncClient(
                    proxy=proxy_url,
                    timeout=PROXY_CHECK_TIMEOUT,
                    verify=False,
                ) as http_client:
                    resp = await http_client.get(PROXY_CHECK_URL)
                    is_ok = resp.status_code < 400
            except Exception as e:
                logger.debug("代理 %s 请求失败: %s", proxy_id, e)
                is_ok = False

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # 更新代理状态
            from datetime import datetime

            proxy.last_check_at = datetime.now()
            if is_ok:
                proxy.is_available = True
                proxy.speed = elapsed_ms
                proxy.fail_count = 0
            else:
                proxy.fail_count = (proxy.fail_count or 0) + 1
                # 连续失败超过 5 次标记为不可用
                if proxy.fail_count >= 5:
                    proxy.is_available = False

            await db.commit()

            logger.info(
                "代理 %s 检查完成: available=%s, speed=%sms",
                proxy_id,
                proxy.is_available,
                proxy.speed,
            )
            return {
                "id": proxy.id,
                "ip": proxy.ip,
                "port": proxy.port,
                "protocol": proxy.protocol,
                "is_available": proxy.is_available,
                "speed": proxy.speed,
                "fail_count": proxy.fail_count,
            }
        except (NotFoundException,):
            raise
        except Exception as e:
            await db.rollback()
            logger.error("检查代理失败: %s", e, exc_info=True)
            raise BusinessException(message=f"检查代理失败: {e}")

    @staticmethod
    async def delete_proxy(proxy_id: int, db: AsyncSession) -> dict[str, Any]:
        """删除代理 IP

        参数:
            proxy_id: 代理 ID
            db: 异步数据库会话

        返回:
            包含 id 与 deleted 标识的字典

        异常:
            NotFoundException: 代理不存在时
            BusinessException: 删除失败时
        """
        try:
            result = await db.execute(
                select(ProxyIP).where(ProxyIP.id == proxy_id)
            )
            proxy = result.scalar_one_or_none()
            if proxy is None:
                raise NotFoundException(f"代理IP不存在: id={proxy_id}")

            await db.delete(proxy)
            await db.commit()

            logger.info("代理IP已删除: id=%s", proxy_id)
            return {"id": proxy_id, "deleted": True}
        except (NotFoundException,):
            raise
        except Exception as e:
            await db.rollback()
            logger.error("删除代理失败: %s", e, exc_info=True)
            raise BusinessException(message=f"删除代理失败: {e}")

    @staticmethod
    async def get_proxy_stats(db: AsyncSession) -> dict[str, Any]:
        """获取代理池统计信息

        统计总数、可用数、不可用数及按协议分组的明细。

        参数:
            db: 异步数据库会话

        返回:
            统计字典，包含 total、available、unavailable、by_protocol
        """
        try:
            # 总数
            total_result = await db.execute(select(func.count(ProxyIP.id)))
            total = int(total_result.scalar() or 0)

            # 可用数
            avail_result = await db.execute(
                select(func.count(ProxyIP.id)).where(
                    ProxyIP.is_available.is_(True)
                )
            )
            available = int(avail_result.scalar() or 0)

            unavailable = total - available

            # 按协议分组统计（使用 case 兼容 SQLite/MySQL）
            proto_result = await db.execute(
                select(
                    ProxyIP.protocol,
                    func.count(ProxyIP.id).label("total"),
                    func.sum(
                        case(
                            (ProxyIP.is_available.is_(True), 1),
                            else_=0,
                        )
                    ).label("available"),
                ).group_by(ProxyIP.protocol)
            )
            rows = proto_result.all()

            by_protocol = []
            for row in rows:
                by_protocol.append(
                    {
                        "protocol": row.protocol,
                        "total": int(row.total or 0),
                        "available": int(row.available or 0),
                    }
                )

            return {
                "total": total,
                "available": available,
                "unavailable": unavailable,
                "by_protocol": by_protocol,
            }
        except Exception as e:
            logger.error("获取代理统计失败: %s", e, exc_info=True)
            raise BusinessException(message=f"获取代理统计失败: {e}")

    @staticmethod
    async def batch_check_proxies(db: AsyncSession) -> dict[str, Any]:
        """批量检查所有代理可用性

        使用 asyncio.Semaphore 控制并发数为 5，对所有代理并发执行健康检查。

        参数:
            db: 异步数据库会话

        返回:
            包含 total、checked、available、unavailable、results 的字典
        """
        try:
            # 查询所有代理 ID
            result = await db.execute(select(ProxyIP.id))
            proxy_ids = [row[0] for row in result.all()]

            if not proxy_ids:
                return {
                    "total": 0,
                    "checked": 0,
                    "available": 0,
                    "unavailable": 0,
                    "results": [],
                }

            # 使用信号量控制并发数
            semaphore = asyncio.Semaphore(BATCH_CHECK_CONCURRENCY)

            async def _check_with_limit(pid: int) -> dict[str, Any]:
                async with semaphore:
                    return await ProxyPoolService.check_proxy(pid, db)

            # 并发执行所有检查
            check_results = await asyncio.gather(
                *[_check_with_limit(pid) for pid in proxy_ids],
                return_exceptions=True,
            )

            # 统计结果
            results: list[dict[str, Any]] = []
            available_count = 0
            for res in check_results:
                if isinstance(res, Exception):
                    # 单个检查异常，记录错误
                    results.append({"error": str(res)})
                else:
                    results.append(res)
                    if res.get("is_available"):
                        available_count += 1

            checked = len(proxy_ids)
            summary = {
                "total": checked,
                "checked": checked,
                "available": available_count,
                "unavailable": checked - available_count,
                "results": results,
            }
            logger.info(
                "批量检查完成: 共 %d 个, 可用 %d 个, 不可用 %d 个",
                checked,
                available_count,
                checked - available_count,
            )
            return summary
        except Exception as e:
            logger.error("批量检查代理失败: %s", e, exc_info=True)
            raise BusinessException(message=f"批量检查代理失败: {e}")

    @staticmethod
    def _build_proxy_url(proxy: ProxyIP) -> str:
        """根据代理记录构建 httpx 使用的代理 URL

        HTTP/HTTPS 代理使用 http:// 前缀（HTTPS 目标通过 CONNECT 隧道），
        SOCKS5 代理使用 socks5:// 前缀。

        参数:
            proxy: ProxyIP 对象

        返回:
            代理 URL 字符串
        """
        if proxy.protocol == "socks5":
            return f"socks5://{proxy.ip}:{proxy.port}"
        # http 与 https 协议的代理均使用 http:// 前缀
        return f"http://{proxy.ip}:{proxy.port}"
