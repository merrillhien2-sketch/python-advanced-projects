"""数据分析服务

提供订单记录的创建与批量导入、仪表盘统计、营收趋势、品类分布、
用户画像生成等核心业务逻辑，基于订单数据聚合计算运营指标。
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessException,
    NotFoundException,
    ValidationException,
)
from app.models.data_analysis import OrderRecord, UserProfile

logger = logging.getLogger(__name__)


class DataAnalysisService:
    """数据分析服务类

    以静态方法形式提供数据分析能力，无需实例化。
    """

    @staticmethod
    async def create_order(order_data: dict, db: AsyncSession) -> OrderRecord:
        """创建单笔订单记录

        参数:
            order_data: 订单数据字典，包含订单号、商品、金额等字段
            db: 异步数据库会话

        返回:
            创建后的 OrderRecord 对象

        异常:
            ValidationException: 订单数据缺失关键字段时
            BusinessException: 订单号重复或创建失败时
        """
        # 校验订单号（业务唯一标识）必填
        if not order_data or not order_data.get("order_id"):
            raise ValidationException("订单号(order_id)不能为空")

        try:
            order = OrderRecord(
                order_id=order_data["order_id"],
                product_name=order_data["product_name"],
                category=order_data["category"],
                amount=float(order_data["amount"]),
                quantity=int(order_data.get("quantity", 1)),
                user_id=int(order_data["user_id"]),
                region=order_data["region"],
                payment_method=order_data["payment_method"],
                order_date=order_data["order_date"],
            )
            db.add(order)
            await db.commit()
            await db.refresh(order)

            logger.info("订单创建成功: order_id=%s, id=%s", order.order_id, order.id)
            return order
        except IntegrityError as e:
            await db.rollback()
            logger.warning("订单号重复: %s", order_data.get("order_id"))
            raise BusinessException(message=f"订单号已存在: {order_data.get('order_id')}")
        except (KeyError, TypeError, ValueError) as e:
            await db.rollback()
            logger.warning("订单数据格式错误: %s", e)
            raise ValidationException(f"订单数据格式错误: {e}")
        except BusinessException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error("创建订单失败: %s", e, exc_info=True)
            raise BusinessException(message=f"创建订单失败: {e}")

    @staticmethod
    async def batch_import_orders(
        orders: list[dict], db: AsyncSession
    ) -> dict[str, Any]:
        """批量导入订单记录

        逐条插入订单，单条失败不影响其他订单，最终返回成功与失败统计。

        参数:
            orders: 订单数据字典列表
            db: 异步数据库会话

        返回:
            包含 total、success、failed、errors 的统计字典
        """
        if not orders:
            raise ValidationException("导入订单列表不能为空")

        total = len(orders)
        success_count = 0
        errors: list[dict[str, Any]] = []

        for index, order_data in enumerate(orders):
            try:
                await DataAnalysisService.create_order(order_data, db)
                success_count += 1
            except Exception as e:
                # 单条失败记录原因，继续处理后续订单
                errors.append(
                    {
                        "index": index,
                        "order_id": order_data.get("order_id"),
                        "error": str(e),
                    }
                )
                logger.warning(
                    "第 %d 条订单导入失败: order_id=%s, error=%s",
                    index,
                    order_data.get("order_id"),
                    e,
                )

        result = {
            "total": total,
            "success": success_count,
            "failed": total - success_count,
            "errors": errors,
        }
        logger.info(
            "批量导入完成: 共 %d 条, 成功 %d 条, 失败 %d 条",
            total,
            success_count,
            total - success_count,
        )
        return result

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> dict[str, Any]:
        """获取仪表盘统计数据

        聚合全量订单，计算总营收、总订单数、客单价、品类 TOP5 与地区营收分布。
        无数据时返回零值与空列表。

        参数:
            db: 异步数据库会话

        返回:
            仪表盘统计字典，结构同 DashboardStats
        """
        try:
            # 总营收
            revenue_result = await db.execute(
                select(func.sum(OrderRecord.amount))
            )
            total_revenue = float(revenue_result.scalar() or 0.0)

            # 总订单数
            count_result = await db.execute(select(func.count(OrderRecord.id)))
            total_orders = int(count_result.scalar() or 0)

            # 客单价
            avg_order_amount = (
                round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0
            )

            # 品类 TOP5（按营收降序）
            category_result = await db.execute(
                select(
                    OrderRecord.category,
                    func.sum(OrderRecord.amount).label("revenue"),
                )
                .group_by(OrderRecord.category)
                .order_by(func.sum(OrderRecord.amount).desc())
                .limit(5)
            )
            top_categories = [
                {"category": row.category, "revenue": float(row.revenue)}
                for row in category_result.all()
            ]

            # 地区营收分布（按营收降序）
            region_result = await db.execute(
                select(
                    OrderRecord.region,
                    func.sum(OrderRecord.amount).label("revenue"),
                )
                .group_by(OrderRecord.region)
                .order_by(func.sum(OrderRecord.amount).desc())
            )
            revenue_by_region = [
                {"region": row.region, "revenue": float(row.revenue)}
                for row in region_result.all()
            ]

            return {
                "total_revenue": round(total_revenue, 2),
                "total_orders": total_orders,
                "avg_order_amount": avg_order_amount,
                "top_categories": top_categories,
                "revenue_by_region": revenue_by_region,
            }
        except Exception as e:
            logger.error("获取仪表盘统计失败: %s", e, exc_info=True)
            raise BusinessException(message=f"获取仪表盘统计失败: {e}")

    @staticmethod
    async def get_revenue_trend(days: int, db: AsyncSession) -> list[dict[str, Any]]:
        """获取营收趋势（按日期聚合）

        统计最近指定天数内每日的营收与订单数。

        参数:
            days: 统计天数
            db: 异步数据库会话

        返回:
            每日营收趋势列表，元素含 date、revenue、order_count
        """
        if days < 1:
            raise ValidationException("统计天数必须大于 0")

        try:
            # 计算起始日期（向前推 days 天）
            start_date = datetime.now() - timedelta(days=days)

            result = await db.execute(
                select(
                    func.date(OrderRecord.order_date).label("date"),
                    func.sum(OrderRecord.amount).label("revenue"),
                    func.count(OrderRecord.id).label("order_count"),
                )
                .where(OrderRecord.order_date >= start_date)
                .group_by(func.date(OrderRecord.order_date))
                .order_by(func.date(OrderRecord.order_date))
            )
            rows = result.all()

            trend = [
                {
                    "date": str(row.date),
                    "revenue": float(row.revenue or 0.0),
                    "order_count": int(row.order_count or 0),
                }
                for row in rows
            ]
            return trend
        except (ValidationException,):
            raise
        except Exception as e:
            logger.error("获取营收趋势失败: %s", e, exc_info=True)
            raise BusinessException(message=f"获取营收趋势失败: {e}")

    @staticmethod
    async def get_category_distribution(db: AsyncSession) -> list[dict[str, Any]]:
        """获取品类分布

        统计各品类的订单数量与营收，用于品类占比分析。

        参数:
            db: 异步数据库会话

        返回:
            品类分布列表，元素含 category、count、revenue
        """
        try:
            result = await db.execute(
                select(
                    OrderRecord.category,
                    func.count(OrderRecord.id).label("count"),
                    func.sum(OrderRecord.amount).label("revenue"),
                )
                .group_by(OrderRecord.category)
                .order_by(func.count(OrderRecord.id).desc())
            )
            rows = result.all()

            distribution = [
                {
                    "category": row.category,
                    "count": int(row.count or 0),
                    "revenue": float(row.revenue or 0.0),
                }
                for row in rows
            ]
            return distribution
        except Exception as e:
            logger.error("获取品类分布失败: %s", e, exc_info=True)
            raise BusinessException(message=f"获取品类分布失败: {e}")

    @staticmethod
    async def get_user_profile(user_id: int, db: AsyncSession) -> dict[str, Any]:
        """获取用户画像（消费行为标签）

        基于用户历史订单实时聚合消费数据，生成消费行为标签。

        参数:
            user_id: 用户 ID
            db: 异步数据库会话

        返回:
            用户画像字典，含 user_id、total_orders、total_amount、
            avg_order_amount、top_category、top_payment、tags 等

        异常:
            NotFoundException: 用户无任何订单记录时
        """
        try:
            # 聚合该用户的订单总数与总金额
            agg_result = await db.execute(
                select(
                    func.count(OrderRecord.id).label("total_orders"),
                    func.sum(OrderRecord.amount).label("total_amount"),
                ).where(OrderRecord.user_id == user_id)
            )
            agg_row = agg_result.one_or_none()

            total_orders = int(getattr(agg_row, "total_orders", 0) or 0)
            total_amount = float(getattr(agg_row, "total_amount", 0) or 0.0)

            if total_orders == 0:
                raise NotFoundException(f"用户 {user_id} 无订单记录")

            avg_order_amount = round(total_amount / total_orders, 2)

            # 最常购买的品类
            category_result = await db.execute(
                select(
                    OrderRecord.category,
                    func.count(OrderRecord.id).label("cnt"),
                )
                .where(OrderRecord.user_id == user_id)
                .group_by(OrderRecord.category)
                .order_by(func.count(OrderRecord.id).desc())
                .limit(1)
            )
            category_row = category_result.first()
            top_category = category_row.category if category_row else None

            # 最常用的支付方式
            payment_result = await db.execute(
                select(
                    OrderRecord.payment_method,
                    func.count(OrderRecord.id).label("cnt"),
                )
                .where(OrderRecord.user_id == user_id)
                .group_by(OrderRecord.payment_method)
                .order_by(func.count(OrderRecord.id).desc())
                .limit(1)
            )
            payment_row = payment_result.first()
            top_payment = payment_row.payment_method if payment_row else None

            # 主要消费地区（取最近一次订单地区）
            region_result = await db.execute(
                select(OrderRecord.region)
                .where(OrderRecord.user_id == user_id)
                .order_by(OrderRecord.order_date.desc())
                .limit(1)
            )
            region_row = region_result.first()
            region = region_row[0] if region_row else "未知"

            tags = DataAnalysisService._build_tags(
                total_orders, total_amount, top_category, top_payment
            )

            return {
                "user_id": user_id,
                "region": region,
                "total_orders": total_orders,
                "total_amount": round(total_amount, 2),
                "avg_order_amount": avg_order_amount,
                "top_category": top_category,
                "top_payment": top_payment,
                "tags": tags,
            }
        except (NotFoundException,):
            raise
        except Exception as e:
            logger.error("获取用户画像失败: %s", e, exc_info=True)
            raise BusinessException(message=f"获取用户画像失败: {e}")

    @staticmethod
    async def generate_user_profiles(db: AsyncSession) -> dict[str, Any]:
        """批量生成用户画像

        遍历所有下过单的用户，聚合其订单数据并写入或更新用户画像表。

        参数:
            db: 异步数据库会话

        返回:
            包含 generated（生成数量）与 users（用户画像摘要列表）的字典
        """
        try:
            # 查询所有有订单记录的用户 ID
            user_result = await db.execute(
                select(OrderRecord.user_id).distinct()
            )
            user_ids = [row[0] for row in user_result.all()]

            generated = 0
            users: list[dict[str, Any]] = []

            for user_id in user_ids:
                # 聚合该用户的订单数据
                agg_result = await db.execute(
                    select(
                        func.count(OrderRecord.id).label("total_orders"),
                        func.sum(OrderRecord.amount).label("total_amount"),
                    ).where(OrderRecord.user_id == user_id)
                )
                agg_row = agg_result.one()
                total_orders = int(agg_row.total_orders or 0)
                total_amount = float(agg_row.total_amount or 0.0)

                # 最常购买的品类
                cat_result = await db.execute(
                    select(OrderRecord.category)
                    .where(OrderRecord.user_id == user_id)
                    .group_by(OrderRecord.category)
                    .order_by(func.count(OrderRecord.id).desc())
                    .limit(1)
                )
                cat_row = cat_result.first()
                top_category = cat_row[0] if cat_row else None

                # 最常用的支付方式
                pay_result = await db.execute(
                    select(OrderRecord.payment_method)
                    .where(OrderRecord.user_id == user_id)
                    .group_by(OrderRecord.payment_method)
                    .order_by(func.count(OrderRecord.id).desc())
                    .limit(1)
                )
                pay_row = pay_result.first()
                top_payment = pay_row[0] if pay_row else None

                # 主要消费地区
                region_result = await db.execute(
                    select(OrderRecord.region)
                    .where(OrderRecord.user_id == user_id)
                    .order_by(OrderRecord.order_date.desc())
                    .limit(1)
                )
                region_row = region_result.first()
                region = region_row[0] if region_row else "未知"

                tags = DataAnalysisService._build_tags(
                    total_orders, total_amount, top_category, top_payment
                )

                # 查询是否已存在画像记录，存在则更新，否则新建
                existing_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == user_id)
                )
                profile = existing_result.scalar_one_or_none()

                if profile is None:
                    profile = UserProfile(
                        user_id=user_id,
                        region=region,
                        total_orders=total_orders,
                        total_amount=round(total_amount, 2),
                        tags=tags,
                    )
                    db.add(profile)
                else:
                    profile.region = region
                    profile.total_orders = total_orders
                    profile.total_amount = round(total_amount, 2)
                    profile.tags = tags

                generated += 1
                users.append(
                    {
                        "user_id": user_id,
                        "total_orders": total_orders,
                        "total_amount": round(total_amount, 2),
                        "tags": tags,
                    }
                )

            await db.commit()

            logger.info("批量生成用户画像完成: 共 %d 个用户", generated)
            return {"generated": generated, "users": users}
        except Exception as e:
            await db.rollback()
            logger.error("批量生成用户画像失败: %s", e, exc_info=True)
            raise BusinessException(message=f"批量生成用户画像失败: {e}")

    @staticmethod
    def _build_tags(
        total_orders: int,
        total_amount: float,
        top_category: str | None,
        top_payment: str | None,
    ) -> str:
        """根据消费数据生成用户行为标签

        参数:
            total_orders: 累计订单数
            total_amount: 累计消费金额
            top_category: 最常购买品类
            top_payment: 最常用支付方式

        返回:
            逗号分隔的标签字符串
        """
        tags: list[str] = []

        # 消费金额分层
        if total_amount >= 10000:
            tags.append("高价值用户")
        elif total_amount >= 5000:
            tags.append("中价值用户")
        else:
            tags.append("普通用户")

        # 消费频次分层
        if total_orders >= 20:
            tags.append("高频消费")
        elif total_orders >= 5:
            tags.append("中频消费")
        else:
            tags.append("低频消费")

        # 品类偏好
        if top_category:
            tags.append(f"偏好:{top_category}")

        # 支付偏好
        if top_payment:
            tags.append(f"常用支付:{top_payment}")

        return ",".join(tags)
