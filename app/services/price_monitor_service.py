"""电商价格监控服务

提供商品的添加、查询、价格记录、价格统计、告警管理与批量检查能力。

特性:
    - 记录价格时自动更新商品当前价格并检查告警条件
    - 价格统计支持最低/最高/均价/涨跌幅计算
    - 告警类型包括目标价降价、涨幅超过阈值、跌幅超过阈值
    - 批量检查价格模拟爬取并更新所有启用商品的价格
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.models.price_monitor import PriceAlert, PriceHistory, Product

logger = logging.getLogger(__name__)

# 支持的平台
ALLOWED_PLATFORMS: set[str] = {"jd", "tmall", "pdd", "amazon"}

# 涨跌幅告警阈值（百分比）
PRICE_CHANGE_ALERT_THRESHOLD: float = 10.0


class PriceMonitorService:
    """电商价格监控服务类

    提供商品管理、价格记录、统计查询、告警管理、批量检查等能力。
    """

    @classmethod
    async def add_product(
        cls, product_data: dict[str, Any], db: AsyncSession
    ) -> Product:
        """添加监控商品

        参数:
            product_data: 商品数据（name、url、platform、target_price、image_url）
            db: 异步数据库会话

        返回:
            创建的 Product 对象

        异常:
            ValidationException: 商品名称、URL 或平台为空，或平台不支持时
            BusinessException: 创建失败时
        """
        name = product_data.get("name", "")
        url = product_data.get("url", "")
        platform = (product_data.get("platform", "") or "").lower()

        if not name or not name.strip():
            raise ValidationException("商品名称不能为空")
        if not url or not url.strip():
            raise ValidationException("商品链接不能为空")
        if not platform:
            raise ValidationException("商品平台不能为空")
        if platform not in ALLOWED_PLATFORMS:
            raise ValidationException(
                f"不支持的平台: {platform}，仅支持 {ALLOWED_PLATFORMS}"
            )

        try:
            product = Product(
                name=name.strip(),
                url=url.strip(),
                platform=platform,
                target_price=product_data.get("target_price"),
                image_url=product_data.get("image_url"),
                is_active=True,
            )
            db.add(product)
            await db.commit()
            await db.refresh(product)

            logger.info("商品添加成功: ID=%s, name=%s", product.id, product.name)
            return product

        except Exception as e:
            await db.rollback()
            logger.error("添加商品失败: %s", e, exc_info=True)
            raise BusinessException(message=f"添加商品失败: {e}")

    @classmethod
    async def get_products(
        cls,
        page: int,
        page_size: int,
        platform: str | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """分页查询商品

        参数:
            page: 页码，从 1 开始
            page_size: 每页条数
            platform: 可选，按平台筛选
            db: 异步数据库会话

        返回:
            包含 data（商品列表）、total、page、page_size 的字典

        异常:
            ValidationException: 分页参数无效时
            BusinessException: 查询失败时
        """
        if page < 1:
            raise ValidationException("页码必须大于 0")
        if page_size < 1 or page_size > 100:
            raise ValidationException("每页条数必须在 1-100 之间")

        try:
            # 构建查询条件
            conditions = []
            if platform:
                conditions.append(Product.platform == platform.lower())

            # 查询总数
            count_query = select(func.count(Product.id))
            for cond in conditions:
                count_query = count_query.where(cond)
            count_result = await db.execute(count_query)
            total = count_result.scalar() or 0

            # 查询当前页数据
            offset = (page - 1) * page_size
            data_query = (
                select(Product)
                .order_by(Product.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            for cond in conditions:
                data_query = data_query.where(cond)
            result = await db.execute(data_query)
            products = result.scalars().all()

            data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "url": p.url,
                    "platform": p.platform,
                    "current_price": p.current_price,
                    "target_price": p.target_price,
                    "image_url": p.image_url,
                    "is_active": p.is_active,
                    "created_at": p.created_at,
                }
                for p in products
            ]

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        except Exception as e:
            logger.error("查询商品列表失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询商品列表失败: {e}")

    @classmethod
    async def record_price(
        cls, product_id: int, price: float, db: AsyncSession
    ) -> PriceHistory:
        """记录商品价格

        记录价格历史，同时更新商品当前价格，并检查是否触发告警。

        参数:
            product_id: 商品 ID
            price: 记录的价格
            db: 异步数据库会话

        返回:
            创建的 PriceHistory 对象

        异常:
            ValidationException: 价格无效时
            NotFoundException: 商品不存在时
            BusinessException: 记录失败时
        """
        if price is None or price < 0:
            raise ValidationException("价格必须为非负数")

        try:
            # 验证商品是否存在
            result = await db.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()
            if product is None:
                raise NotFoundException(f"商品不存在: ID={product_id}")

            # 记录价格历史
            history = PriceHistory(
                product_id=product_id,
                price=price,
                recorded_at=datetime.now(timezone.utc),
            )
            db.add(history)

            # 更新商品当前价格
            product.current_price = price
            await db.commit()
            await db.refresh(history)

            # 检查价格告警（不影响主流程）
            try:
                await cls.check_price_alerts(product_id, price, db)
            except Exception as alert_err:
                logger.warning("价格告警检查失败（不影响价格记录）: %s", alert_err)

            logger.info(
                "价格记录成功: product_id=%s, price=%.2f", product_id, price
            )
            return history

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            await db.rollback()
            logger.error("记录价格失败: %s", e, exc_info=True)
            raise BusinessException(message=f"记录价格失败: {e}")

    @classmethod
    async def get_price_history(
        cls, product_id: int, days: int, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """查询价格历史

        参数:
            product_id: 商品 ID
            days: 查询最近多少天的数据
            db: 异步数据库会话

        返回:
            价格历史字典列表

        异常:
            ValidationException: 天数无效时
            NotFoundException: 商品不存在时
            BusinessException: 查询失败时
        """
        if days < 1:
            raise ValidationException("查询天数必须大于 0")

        try:
            # 验证商品是否存在
            product_result = await db.execute(
                select(Product).where(Product.id == product_id)
            )
            product = product_result.scalar_one_or_none()
            if product is None:
                raise NotFoundException(f"商品不存在: ID={product_id}")

            # 计算起始时间
            since = datetime.now(timezone.utc) - timedelta(days=days)

            result = await db.execute(
                select(PriceHistory)
                .where(
                    PriceHistory.product_id == product_id,
                    PriceHistory.recorded_at >= since,
                )
                .order_by(PriceHistory.recorded_at.asc())
            )
            histories = result.scalars().all()

            data = [
                {
                    "id": h.id,
                    "product_id": h.product_id,
                    "price": h.price,
                    "recorded_at": h.recorded_at,
                }
                for h in histories
            ]

            return data

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error("查询价格历史失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询价格历史失败: {e}")

    @classmethod
    async def get_price_stats(
        cls, product_id: int, db: AsyncSession
    ) -> dict[str, Any]:
        """价格统计

        计算商品的最低价、最高价、均价和涨跌幅。

        参数:
            product_id: 商品 ID
            db: 异步数据库会话

        返回:
            包含统计信息的字典

        异常:
            NotFoundException: 商品不存在时
            BusinessException: 统计失败时
        """
        try:
            # 查询商品信息
            product_result = await db.execute(
                select(Product).where(Product.id == product_id)
            )
            product = product_result.scalar_one_or_none()
            if product is None:
                raise NotFoundException(f"商品不存在: ID={product_id}")

            # 查询价格历史统计
            stats_result = await db.execute(
                select(
                    func.min(PriceHistory.price),
                    func.max(PriceHistory.price),
                    func.avg(PriceHistory.price),
                    func.count(PriceHistory.id),
                ).where(PriceHistory.product_id == product_id)
            )
            row = stats_result.one()

            lowest_price = row[0]
            highest_price = row[1]
            avg_price = round(row[2], 2) if row[2] is not None else None
            total_records = row[3] or 0

            # 计算涨跌幅：以第一条记录为基准
            price_change_rate = None
            if total_records > 0:
                first_result = await db.execute(
                    select(PriceHistory.price)
                    .where(PriceHistory.product_id == product_id)
                    .order_by(PriceHistory.recorded_at.asc())
                    .limit(1)
                )
                first_price = first_result.scalar()
                if first_price and first_price > 0 and product.current_price is not None:
                    price_change_rate = round(
                        ((product.current_price - first_price) / first_price) * 100,
                        2,
                    )

            return {
                "product_id": product_id,
                "name": product.name,
                "current_price": product.current_price,
                "lowest_price": lowest_price,
                "highest_price": highest_price,
                "avg_price": avg_price,
                "price_change_rate": price_change_rate,
                "total_records": total_records,
            }

        except NotFoundException:
            raise
        except Exception as e:
            logger.error("价格统计失败: %s", e, exc_info=True)
            raise BusinessException(message=f"价格统计失败: {e}")

    @classmethod
    async def get_alerts(
        cls,
        page: int,
        page_size: int,
        unread_only: bool,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """分页查询告警

        参数:
            page: 页码，从 1 开始
            page_size: 每页条数
            unread_only: 是否仅查询未读告警
            db: 异步数据库会话

        返回:
            包含 data（告警列表）、total、page、page_size 的字典

        异常:
            ValidationException: 分页参数无效时
            BusinessException: 查询失败时
        """
        if page < 1:
            raise ValidationException("页码必须大于 0")
        if page_size < 1 or page_size > 100:
            raise ValidationException("每页条数必须在 1-100 之间")

        try:
            # 构建查询条件
            conditions = []
            if unread_only:
                conditions.append(PriceAlert.is_read == False)  # noqa: E712

            # 查询总数
            count_query = select(func.count(PriceAlert.id))
            for cond in conditions:
                count_query = count_query.where(cond)
            count_result = await db.execute(count_query)
            total = count_result.scalar() or 0

            # 查询当前页数据
            offset = (page - 1) * page_size
            data_query = (
                select(PriceAlert)
                .order_by(PriceAlert.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            for cond in conditions:
                data_query = data_query.where(cond)
            result = await db.execute(data_query)
            alerts = result.scalars().all()

            data = [
                {
                    "id": a.id,
                    "product_id": a.product_id,
                    "alert_type": a.alert_type,
                    "threshold": a.threshold,
                    "message": a.message,
                    "is_read": a.is_read,
                    "created_at": a.created_at,
                }
                for a in alerts
            ]

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        except Exception as e:
            logger.error("查询告警列表失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询告警列表失败: {e}")

    @classmethod
    async def mark_alert_read(
        cls, alert_id: int, db: AsyncSession
    ) -> dict[str, Any]:
        """标记告警已读

        参数:
            alert_id: 告警 ID
            db: 异步数据库会话

        返回:
            包含更新结果的字典

        异常:
            NotFoundException: 告警不存在时
            BusinessException: 更新失败时
        """
        try:
            result = await db.execute(
                select(PriceAlert).where(PriceAlert.id == alert_id)
            )
            alert = result.scalar_one_or_none()
            if alert is None:
                raise NotFoundException(f"告警不存在: ID={alert_id}")

            alert.is_read = True
            await db.commit()

            logger.info("告警已标记已读: ID=%s", alert_id)
            return {"id": alert_id, "is_read": True}

        except NotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error("标记告警已读失败: %s", e, exc_info=True)
            raise BusinessException(message=f"标记告警已读失败: {e}")

    @classmethod
    async def check_price_alerts(
        cls, product_id: int, new_price: float, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """检查价格告警

        检查条件:
            - target_drop: 当前价格低于或等于目标价格
            - price_increase: 价格涨幅超过阈值（10%）
            - price_decrease: 价格跌幅超过阈值（10%）

        参数:
            product_id: 商品 ID
            new_price: 新记录的价格
            db: 异步数据库会话

        返回:
            触发的告警字典列表

        异常:
            BusinessException: 检查失败时
        """
        try:
            # 查询商品信息
            result = await db.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()
            if product is None:
                raise NotFoundException(f"商品不存在: ID={product_id}")

            alerts_created: list[dict[str, Any]] = []

            # 检查目标价降价
            if (
                product.target_price is not None
                and new_price <= product.target_price
            ):
                alert = PriceAlert(
                    product_id=product_id,
                    alert_type="target_drop",
                    threshold=product.target_price,
                    message=(
                        f"商品「{product.name}」已降至目标价格 "
                        f"{new_price:.2f}（目标价: {product.target_price:.2f}）"
                    ),
                    is_read=False,
                )
                db.add(alert)
                alerts_created.append(
                    {
                        "product_id": product_id,
                        "alert_type": "target_drop",
                        "threshold": product.target_price,
                        "message": alert.message,
                    }
                )

            # 查询上一条价格记录用于计算涨跌幅
            prev_result = await db.execute(
                select(PriceHistory)
                .where(PriceHistory.product_id == product_id)
                .order_by(PriceHistory.recorded_at.desc())
                .limit(2)
            )
            histories = prev_result.scalars().all()
            # histories[0] 是刚记录的，histories[1] 是上一条
            if len(histories) >= 2:
                prev_price = histories[1].price
                if prev_price and prev_price > 0:
                    change_rate = (
                        (new_price - prev_price) / prev_price
                    ) * 100

                    # 涨幅超过阈值
                    if change_rate >= PRICE_CHANGE_ALERT_THRESHOLD:
                        alert = PriceAlert(
                            product_id=product_id,
                            alert_type="price_increase",
                            threshold=PRICE_CHANGE_ALERT_THRESHOLD,
                            message=(
                                f"商品「{product.name}」价格上涨 "
                                f"{change_rate:.2f}%（"
                                f"{prev_price:.2f} -> {new_price:.2f}）"
                            ),
                            is_read=False,
                        )
                        db.add(alert)
                        alerts_created.append(
                            {
                                "product_id": product_id,
                                "alert_type": "price_increase",
                                "threshold": PRICE_CHANGE_ALERT_THRESHOLD,
                                "message": alert.message,
                            }
                        )

                    # 跌幅超过阈值
                    elif change_rate <= -PRICE_CHANGE_ALERT_THRESHOLD:
                        alert = PriceAlert(
                            product_id=product_id,
                            alert_type="price_decrease",
                            threshold=PRICE_CHANGE_ALERT_THRESHOLD,
                            message=(
                                f"商品「{product.name}」价格下跌 "
                                f"{abs(change_rate):.2f}%（"
                                f"{prev_price:.2f} -> {new_price:.2f}）"
                            ),
                            is_read=False,
                        )
                        db.add(alert)
                        alerts_created.append(
                            {
                                "product_id": product_id,
                                "alert_type": "price_decrease",
                                "threshold": PRICE_CHANGE_ALERT_THRESHOLD,
                                "message": alert.message,
                            }
                        )

            if alerts_created:
                await db.commit()
                logger.info(
                    "价格告警触发: product_id=%s, alerts=%d",
                    product_id,
                    len(alerts_created),
                )

            return alerts_created

        except NotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error("检查价格告警失败: %s", e, exc_info=True)
            raise BusinessException(message=f"检查价格告警失败: {e}")

    @classmethod
    async def batch_check_prices(cls, db: AsyncSession) -> dict[str, Any]:
        """批量检查价格

        模拟爬取所有启用监控商品的价格，更新当前价格并记录历史，
        返回更新统计信息。

        参数:
            db: 异步数据库会话

        返回:
            包含更新统计信息的字典

        异常:
            BusinessException: 批量检查失败时
        """
        try:
            # 查询所有启用的商品
            result = await db.execute(
                select(Product).where(Product.is_active == True)  # noqa: E712
            )
            products = result.scalars().all()

            total = len(products)
            updated = 0
            alerts_triggered = 0

            for product in products:
                # 模拟爬取价格：在当前价格基础上随机波动 ±5%
                if product.current_price is not None and product.current_price > 0:
                    fluctuation = random.uniform(-0.05, 0.05)
                    new_price = round(
                        product.current_price * (1 + fluctuation), 2
                    )
                else:
                    # 无当前价格时模拟一个随机价格
                    new_price = round(random.uniform(50.0, 500.0), 2)

                # 记录价格
                try:
                    await cls.record_price(product.id, new_price, db)
                    updated += 1
                except Exception as record_err:
                    logger.warning(
                        "批量检查中记录价格失败: product_id=%s, error=%s",
                        product.id,
                        record_err,
                    )

            logger.info(
                "批量价格检查完成: total=%d, updated=%d", total, updated
            )

            return {
                "total": total,
                "updated": updated,
                "alerts_triggered": alerts_triggered,
            }

        except Exception as e:
            logger.error("批量检查价格失败: %s", e, exc_info=True)
            raise BusinessException(message=f"批量检查价格失败: {e}")
