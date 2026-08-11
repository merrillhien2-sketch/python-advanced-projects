"""推荐服务

提供协同过滤和基于内容的推荐能力。

特性:
    - 协同过滤: 基于用户-物品交互矩阵，计算用户相似度后推荐
    - 基于内容: 基于物品标签/内容的相似度进行推荐
    - 数据来源为 CrawlData 表，数据不足时使用模拟数据兜底
"""

import logging
import math
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessException
from app.models.crawl_data import CrawlData

logger = logging.getLogger(__name__)


class RecommendationService:
    """推荐服务类

    提供协同过滤和基于内容的推荐算法实现。
    """

    @staticmethod
    def _cosine_similarity(vec_a: dict[int, float], vec_b: dict[int, float]) -> float:
        """计算两个向量的余弦相似度

        参数:
            vec_a: 向量 A（字典形式，键为维度，值为权重）
            vec_b: 向量 B（字典形式，键为维度，值为权重）

        返回:
            余弦相似度，范围 [0, 1]
        """
        # 找到两个向量共有的维度
        common_keys = set(vec_a.keys()) & set(vec_b.keys())
        if not common_keys:
            return 0.0

        # 计算点积
        dot_product = sum(vec_a[k] * vec_b[k] for k in common_keys)

        # 计算向量模长
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    @classmethod
    async def collaborative_filter(
        cls,
        user_id: int,
        top_k: int,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """简易协同过滤推荐

        基于 CrawlData 表构建用户-物品交互矩阵（created_by 作为用户，
        id 作为物品），计算用户相似度后推荐相似用户交互过的物品。

        参数:
            user_id: 目标用户 ID
            top_k: 返回的推荐数量
            db: 异步数据库会话

        返回:
            推荐列表，每个元素含 item_id 和 score

        异常:
            BusinessException: 推荐失败时
        """
        try:
            # 查询所有交互数据（用户-物品对）
            result = await db.execute(
                select(CrawlData.id, CrawlData.created_by).limit(500)
            )
            rows = result.all()

            if not rows:
                # 数据不足，返回模拟推荐
                logger.info("协同过滤数据不足，返回模拟推荐")
                return cls._generate_mock_recommendations(top_k)

            # 构建用户-物品交互矩阵: {user_id: {item_id: score}}
            user_item_matrix: dict[int, dict[int, float]] = defaultdict(dict)
            # 物品集合
            all_items: set[int] = set()

            for row in rows:
                if row.created_by is not None:
                    # 每次交互权重为 1.0
                    user_item_matrix[row.created_by][row.id] = 1.0
                    all_items.add(row.id)

            # 如果目标用户无交互记录，返回热门物品
            if user_id not in user_item_matrix:
                logger.info("目标用户 %d 无交互记录，返回热门推荐", user_id)
                return cls._popular_items(user_item_matrix, top_k)

            # 计算目标用户与其他用户的相似度
            target_vector = user_item_matrix[user_id]
            user_similarities: list[tuple[int, float]] = []

            for other_user, other_vector in user_item_matrix.items():
                if other_user == user_id:
                    continue
                similarity = cls._cosine_similarity(target_vector, other_vector)
                if similarity > 0:
                    user_similarities.append((other_user, similarity))

            # 按相似度降序排序
            user_similarities.sort(key=lambda x: x[1], reverse=True)

            # 取相似度最高的前 N 个用户（最多 10 个）
            top_users = user_similarities[:10]

            # 聚合推荐物品及其得分
            item_scores: dict[int, float] = defaultdict(float)
            target_items = set(target_vector.keys())

            for other_user, similarity in top_users:
                for item_id in user_item_matrix[other_user]:
                    # 排除目标用户已交互过的物品
                    if item_id not in target_items:
                        item_scores[item_id] += similarity

            # 按得分降序排序，取 top_k
            sorted_items = sorted(
                item_scores.items(), key=lambda x: x[1], reverse=True
            )[:top_k]

            recommendations = [
                {"item_id": item_id, "score": round(score, 4)}
                for item_id, score in sorted_items
            ]

            # 推荐数量不足时补充热门物品
            if len(recommendations) < top_k:
                existing_ids = {r["item_id"] for r in recommendations}
                popular = cls._popular_items(user_item_matrix, top_k)
                for item in popular:
                    if item["item_id"] not in existing_ids:
                        recommendations.append(item)
                    if len(recommendations) >= top_k:
                        break

            return recommendations

        except BusinessException:
            raise
        except Exception as e:
            logger.error("协同过滤推荐失败: %s", e, exc_info=True)
            raise BusinessException(message=f"协同过滤推荐失败: {e}")

    @classmethod
    async def content_based(
        cls,
        item_id: int,
        top_k: int,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """基于内容的推荐

        根据目标物品的标签，查找标签相似度最高的其他物品进行推荐。

        参数:
            item_id: 目标物品 ID
            top_k: 返回的推荐数量
            db: 异步数据库会话

        返回:
            推荐列表，每个元素含 item_id 和 score

        异常:
            BusinessException: 推荐失败时
        """
        try:
            # 查询目标物品
            result = await db.execute(
                select(CrawlData).where(CrawlData.id == item_id)
            )
            target_item = result.scalar_one_or_none()

            if target_item is None:
                logger.info("目标物品 %d 不存在，返回模拟推荐", item_id)
                return cls._generate_mock_recommendations(top_k)

            # 解析目标物品的标签
            target_tags: set[str] = set()
            if target_item.tags:
                target_tags = {
                    t.strip().lower()
                    for t in target_item.tags.split(",")
                    if t.strip()
                }

            if not target_tags:
                # 目标物品无标签，返回模拟推荐
                return cls._generate_mock_recommendations(top_k)

            # 查询所有其他物品
            result = await db.execute(
                select(CrawlData.id, CrawlData.tags)
                .where(CrawlData.id != item_id)
                .limit(200)
            )
            rows = result.all()

            # 计算每个物品与目标物品的标签相似度（Jaccard 相似度）
            scored_items: list[tuple[int, float]] = []
            for row in rows:
                if not row.tags:
                    continue
                other_tags = {
                    t.strip().lower()
                    for t in row.tags.split(",")
                    if t.strip()
                }
                if not other_tags:
                    continue

                # Jaccard 相似度 = 交集 / 并集
                intersection = target_tags & other_tags
                union = target_tags | other_tags
                similarity = len(intersection) / len(union) if union else 0.0

                if similarity > 0:
                    scored_items.append((row.id, similarity))

            # 按相似度降序排序，取 top_k
            scored_items.sort(key=lambda x: x[1], reverse=True)
            recommendations = [
                {"item_id": item_id_val, "score": round(score, 4)}
                for item_id_val, score in scored_items[:top_k]
            ]

            # 推荐数量不足时补充模拟数据
            if len(recommendations) < top_k:
                existing_ids = {r["item_id"] for r in recommendations}
                mock = cls._generate_mock_recommendations(top_k)
                for item in mock:
                    if item["item_id"] not in existing_ids:
                        recommendations.append(item)
                    if len(recommendations) >= top_k:
                        break

            return recommendations

        except BusinessException:
            raise
        except Exception as e:
            logger.error("基于内容的推荐失败: %s", e, exc_info=True)
            raise BusinessException(message=f"基于内容的推荐失败: {e}")

    # ------------------------------------------------------------------ #
    # 辅助方法
    # ------------------------------------------------------------------ #
    @staticmethod
    def _generate_mock_recommendations(top_k: int) -> list[dict[str, Any]]:
        """生成模拟推荐列表（数据不足时的兜底方案）

        参数:
            top_k: 推荐数量

        返回:
            模拟推荐列表
        """
        return [
            {"item_id": i + 1, "score": round(1.0 / (i + 1), 4)}
            for i in range(top_k)
        ]

    @staticmethod
    def _popular_items(
        user_item_matrix: dict[int, dict[int, float]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """从交互矩阵中提取热门物品

        统计每个物品被多少用户交互过，按热度排序。

        参数:
            user_item_matrix: 用户-物品交互矩阵
            top_k: 推荐数量

        返回:
            热门物品推荐列表
        """
        item_popularity: dict[int, int] = defaultdict(int)
        for user_vector in user_item_matrix.values():
            for item_id in user_vector:
                item_popularity[item_id] += 1

        sorted_items = sorted(
            item_popularity.items(), key=lambda x: x[1], reverse=True
        )[:top_k]

        max_count = sorted_items[0][1] if sorted_items else 1
        return [
            {
                "item_id": item_id,
                "score": round(count / max_count, 4),
            }
            for item_id, count in sorted_items
        ]
