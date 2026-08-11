"""AI 相关 Schema

定义 OCR、情感分析、目标检测及推荐系统的请求与响应数据模型。
"""

from typing import List

from pydantic import BaseModel, Field


class OCRRequest(BaseModel):
    """OCR 请求（文件上传，无请求体字段）"""

    pass


class OCRResponse(BaseModel):
    """OCR 响应

    属性:
        text: 识别出的文本内容
        confidence: 识别置信度（0-1）
        language: 检测到的语言
    """

    text: str = Field(..., description="识别出的文本")
    confidence: float = Field(..., description="识别置信度")
    language: str = Field(default="unknown", description="检测到的语言")


class SentimentRequest(BaseModel):
    """情感分析请求"""

    text: str = Field(..., min_length=1, description="待分析的文本")


class SentimentResponse(BaseModel):
    """情感分析响应

    属性:
        sentiment: 情感倾向，positive/negative/neutral
        score: 情感得分（-1 到 1）
        keywords: 关键词列表
    """

    sentiment: str = Field(..., description="情感倾向")
    score: float = Field(..., description="情感得分")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")


class DetectionRequest(BaseModel):
    """目标检测请求（文件上传，无请求体字段）"""

    pass


class DetectionItem(BaseModel):
    """单个检测结果项

    属性:
        label: 目标标签
        confidence: 检测置信度（0-1）
        bbox: 边界框坐标 [x, y, width, height]
    """

    label: str = Field(..., description="目标标签")
    confidence: float = Field(..., description="检测置信度")
    bbox: List[float] = Field(..., description="边界框坐标 [x, y, width, height]")


class DetectionResponse(BaseModel):
    """目标检测响应"""

    objects: List[DetectionItem] = Field(default_factory=list, description="检测结果列表")


class RecommendationRequest(BaseModel):
    """推荐请求

    属性:
        user_id: 目标用户 ID
        top_k: 返回的推荐数量，默认 10
    """

    user_id: int = Field(..., description="用户ID")
    top_k: int = Field(default=10, ge=1, le=100, description="推荐数量")


class RecommendationItem(BaseModel):
    """单个推荐项

    属性:
        item_id: 物品 ID
        score: 推荐得分
    """

    item_id: int = Field(..., description="物品ID")
    score: float = Field(..., description="推荐得分")


class RecommendationResponse(BaseModel):
    """推荐响应"""

    items: List[RecommendationItem] = Field(default_factory=list, description="推荐列表")
