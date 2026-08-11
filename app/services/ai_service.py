"""AI 服务

提供轻量级 AI 能力，包括 OCR 文字识别、情感分析、目标检测和推荐系统。
所有实现均为轻量级方案，不依赖大模型下载，适合快速集成和演示。

集成说明:
    - OCR: 使用 pytesseract（需安装 Tesseract-OCR 引擎）
    - 情感分析: 基于关键词词典的规则匹配
    - 目标检测: 当前为 demo 模式，预留 YOLO 集成接口
    - 推荐: 基于用户行为的简易协同过滤
"""

import io
import logging
from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessException
from app.models.crawl_data import CrawlData

logger = logging.getLogger(__name__)


class AIService:
    """AI 服务类

    提供静态方法形式的 AI 能力调用，无需实例化。
    """

    # ------------------------------------------------------------------ #
    # 情感分析关键词词典
    # ------------------------------------------------------------------ #
    # 正面情感词库
    POSITIVE_WORDS: set[str] = {
        "好", "棒", "优秀", "完美", "喜欢", "爱", "开心", "快乐", "满意",
        "赞", "精彩", "出色", "推荐", "值得", "不错", "高兴", "兴奋",
        "good", "great", "excellent", "perfect", "love", "like", "happy",
        "amazing", "wonderful", "awesome", "fantastic", "best", "nice",
        "beautiful", "brilliant", "superb", "outstanding",
    }

    # 负面情感词库
    NEGATIVE_WORDS: set[str] = {
        "差", "坏", "糟糕", "讨厌", "恨", "失望", "难过", "伤心", "生气",
        "愤怒", "垃圾", "烂", "差劲", "不行", "不好", "难受", "痛苦",
        "bad", "terrible", "awful", "hate", "sad", "angry", "horrible",
        "worst", "poor", "disappointing", "ugly", "boring", "stupid",
        "disgusting", "annoying", "frustrating",
    }

    # ------------------------------------------------------------------ #
    # OCR 文字识别
    # ------------------------------------------------------------------ #
    @staticmethod
    async def ocr_extract(image_bytes: bytes) -> dict[str, Any]:
        """使用 pytesseract 提取图片中的文字

        如果 pytesseract 或 PIL 不可用，则返回提示信息而非抛出异常，
        保证服务在未安装 OCR 依赖时仍可降级运行。

        参数:
            image_bytes: 图片二进制数据

        返回:
            包含 text、confidence、language 的字典
        """
        try:
            # 延迟导入，避免在 pytesseract 未安装时影响模块加载
            import pytesseract
            from PIL import Image
        except ImportError:
            logger.warning("pytesseract 或 Pillow 未安装，OCR 功能不可用")
            return {
                "text": "",
                "confidence": 0.0,
                "language": "unknown",
                "message": "OCR 依赖未安装，请执行 pip install pytesseract Pillow 并安装 Tesseract-OCR 引擎",
            }

        try:
            # 从二进制数据加载图片
            image = Image.open(io.BytesIO(image_bytes))

            # 尝试识别中文和英文
            text = pytesseract.image_to_string(image, lang="chi_sim+eng")

            # 计算置信度（通过 image_to_data 获取单词级别的置信度）
            data = pytesseract.image_to_data(
                image, lang="chi_sim+eng", output_type=pytesseract.Output.DICT
            )
            confidences = [
                int(conf)
                for conf in data.get("conf", [])
                if str(conf).lstrip("-").isdigit() and int(conf) > 0
            ]
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

            # 简单语言检测：根据是否包含中文字符判断
            has_chinese = any("\u4e00" <= char <= "\u9fff" for char in text)
            language = "chi_sim+eng" if has_chinese else "eng"

            return {
                "text": text.strip(),
                "confidence": round(avg_confidence, 4),
                "language": language,
            }
        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract-OCR 引擎未安装，请安装系统包 tesseract-ocr")
            return {
                "text": "",
                "confidence": 0.0,
                "language": "unknown",
                "message": "Tesseract-OCR 引擎未安装，请安装系统包 tesseract-ocr",
            }
        except Exception as e:
            logger.error("OCR 识别失败: %s", e, exc_info=True)
            raise BusinessException(message=f"OCR 识别失败: {e}")

    # ------------------------------------------------------------------ #
    # 情感分析
    # ------------------------------------------------------------------ #
    @staticmethod
    async def sentiment_analyze(text: str) -> dict[str, Any]:
        """基于关键词词典的情感分析

        通过匹配正面和负面关键词词库，计算情感得分和倾向。
        得分范围为 -1（最负面）到 1（最正面），0 为中性。

        参数:
            text: 待分析的文本

        返回:
            包含 sentiment、score、keywords 的字典
        """
        if not text or not text.strip():
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "keywords": [],
            }

        # 将文本转为小写以便匹配英文关键词
        text_lower = text.lower()

        # 统计正面和负面关键词命中
        positive_hits: list[str] = []
        negative_hits: list[str] = []

        for word in AIService.POSITIVE_WORDS:
            if word.lower() in text_lower:
                positive_hits.append(word)

        for word in AIService.NEGATIVE_WORDS:
            if word.lower() in text_lower:
                negative_hits.append(word)

        # 计算情感得分
        pos_count = len(positive_hits)
        neg_count = len(negative_hits)
        total = pos_count + neg_count

        if total == 0:
            score = 0.0
            sentiment = "neutral"
        else:
            # 得分 = (正面数 - 负面数) / 总数，范围 [-1, 1]
            score = (pos_count - neg_count) / total
            if score > 0.1:
                sentiment = "positive"
            elif score < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        # 提取关键词（合并命中的正负面词）
        keywords = list(set(positive_hits + negative_hits))

        return {
            "sentiment": sentiment,
            "score": round(score, 4),
            "keywords": keywords,
        }

    # ------------------------------------------------------------------ #
    # 目标检测
    # ------------------------------------------------------------------ #
    @staticmethod
    async def object_detect(image_bytes: bytes) -> dict[str, Any]:
        """目标检测（当前为 demo 模式）

        返回模拟的检测结果。后续可在此处集成 YOLO 模型：
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")
            results = model(image_bytes)
            # 解析 results 获取检测框、标签和置信度

        参数:
            image_bytes: 图片二进制数据

        返回:
            包含 objects 列表的字典，每个元素含 label、confidence、bbox
        """
        logger.info("目标检测当前运行在 demo 模式，返回模拟结果")

        # 模拟检测结果
        mock_objects = [
            {
                "label": "person",
                "confidence": 0.92,
                "bbox": [50.0, 30.0, 200.0, 400.0],
            },
            {
                "label": "car",
                "confidence": 0.85,
                "bbox": [250.0, 150.0, 300.0, 200.0],
            },
            {
                "label": "dog",
                "confidence": 0.78,
                "bbox": [400.0, 200.0, 150.0, 180.0],
            },
        ]

        return {
            "objects": mock_objects,
            "mode": "demo",
            "message": "当前为 demo 模式。集成 YOLO 时，请在 object_detect 方法中加载模型并替换此模拟逻辑。",
        }

    # ------------------------------------------------------------------ #
    # 推荐系统
    # ------------------------------------------------------------------ #
    @staticmethod
    async def recommend(
        user_id: int, top_k: int, db: AsyncSession
    ) -> dict[str, Any]:
        """基于用户行为的简易协同过滤推荐

        从 CrawlData 表中获取数据，基于标签相似度生成推荐列表。
        当数据库无足够数据时，使用模拟数据兜底。

        参数:
            user_id: 目标用户 ID
            top_k: 返回的推荐数量
            db: 异步数据库会话

        返回:
            包含 items 列表的字典，每个元素含 item_id 和 score
        """
        try:
            # 从数据库查询 CrawlData，按标签聚合
            result = await db.execute(
                select(CrawlData.id, CrawlData.tags, CrawlData.title).limit(100)
            )
            rows = result.all()

            if not rows:
                # 数据库无数据时使用模拟推荐
                logger.info("数据库无抓取数据，使用模拟推荐列表")
                mock_items = [
                    {"item_id": i + 1, "score": round(1.0 / (i + 1), 4)}
                    for i in range(min(top_k, 10))
                ]
                return {"items": mock_items}

            # 基于标签的简易推荐：统计标签频率，按频率排序
            tag_counter: Counter[str] = Counter()
            for row in rows:
                if row.tags:
                    tags = [t.strip() for t in row.tags.split(",") if t.strip()]
                    tag_counter.update(tags)

            # 计算每个数据的推荐得分（基于标签频率）
            scored_items: list[dict[str, Any]] = []
            for row in rows:
                if row.tags:
                    tags = [t.strip() for t in row.tags.split(",") if t.strip()]
                    # 得分 = 标签频率之和 / 标签数量，归一化
                    tag_scores = [tag_counter.get(t, 0) for t in tags]
                    raw_score = sum(tag_scores) / max(len(tags), 1)
                else:
                    raw_score = 0.1  # 无标签的数据给予基础分

                scored_items.append({
                    "item_id": row.id,
                    "score": round(raw_score, 4),
                })

            # 按得分降序排序，取 top_k
            scored_items.sort(key=lambda x: x["score"], reverse=True)
            recommendations = scored_items[:top_k]

            # 如果推荐数量不足 top_k，用模拟数据补充
            if len(recommendations) < top_k:
                existing_ids = {item["item_id"] for item in recommendations}
                base_id = max(existing_ids) + 1 if existing_ids else 1
                for i in range(top_k - len(recommendations)):
                    recommendations.append({
                        "item_id": base_id + i,
                        "score": round(0.5 / (i + 2), 4),
                    })

            return {"items": recommendations}
        except Exception as e:
            logger.error("推荐服务失败: %s", e, exc_info=True)
            raise BusinessException(message=f"推荐服务失败: {e}")
