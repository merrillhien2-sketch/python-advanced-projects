"""AI 服务路由

提供 OCR 文字识别、情感分析、目标检测和推荐系统的接口。

接口列表:
    - POST /ocr       上传图片进行 OCR 文字识别
    - POST /sentiment 文本情感分析
    - POST /detect    图片目标检测
    - POST /recommend 推荐系统
"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.ai import (
    DetectionResponse,
    OCRResponse,
    RecommendationRequest,
    RecommendationResponse,
    SentimentRequest,
    SentimentResponse,
)
from app.schemas.common import ResponseBase
from app.services.ai_service import AIService

router = APIRouter()


@router.post("/ocr", response_model=ResponseBase[OCRResponse], summary="OCR 文字识别")
async def ocr(
    file: UploadFile = File(..., description="待识别的图片文件"),
) -> ResponseBase[OCRResponse]:
    """OCR 文字识别

    上传图片文件，使用 pytesseract 提取图片中的文字内容。
    支持中文和英文识别。

    参数:
        file: 上传的图片文件

    返回:
        包含识别文本、置信度和语言的响应
    """
    # 读取图片二进制数据
    image_bytes = await file.read()
    result = await AIService.ocr_extract(image_bytes)
    return ResponseBase(data=OCRResponse(**result))


@router.post(
    "/sentiment",
    response_model=ResponseBase[SentimentResponse],
    summary="文本情感分析",
)
async def sentiment(
    request: SentimentRequest,
) -> ResponseBase[SentimentResponse]:
    """文本情感分析

    对输入文本进行情感倾向分析，返回正面/负面/中性的判断及得分。
    基于关键词词典的规则匹配实现。

    参数:
        request: 包含待分析文本的请求

    返回:
        包含情感倾向、得分和关键词的响应
    """
    result = await AIService.sentiment_analyze(request.text)
    return ResponseBase(data=SentimentResponse(**result))


@router.post(
    "/detect",
    response_model=ResponseBase[DetectionResponse],
    summary="图片目标检测",
)
async def detect(
    file: UploadFile = File(..., description="待检测的图片文件"),
) -> ResponseBase[DetectionResponse]:
    """图片目标检测

    上传图片文件，进行目标检测。
    当前为 demo 模式，返回模拟检测结果，后续可集成 YOLO 模型。

    参数:
        file: 上传的图片文件

    返回:
        包含检测到的目标列表的响应
    """
    image_bytes = await file.read()
    result = await AIService.object_detect(image_bytes)
    return ResponseBase(data=DetectionResponse(**result))


@router.post(
    "/recommend",
    response_model=ResponseBase[RecommendationResponse],
    summary="推荐系统",
)
async def recommend(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[RecommendationResponse]:
    """推荐系统

    基于用户行为的协同过滤推荐，返回个性化推荐物品列表。

    参数:
        request: 包含用户 ID 和推荐数量的请求
        db: 异步数据库会话

    返回:
        包含推荐物品列表的响应
    """
    result = await AIService.recommend(request.user_id, request.top_k, db)
    return ResponseBase(data=RecommendationResponse(**result))
