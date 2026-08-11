"""AI 服务测试。

测试情感分析（正面/负面/中性）和 OCR 功能。
直接测试 AIService 类的静态方法，无需数据库或 Redis 连接。

AIService 位于 app/services/ai_service.py，提供：
- sentiment_analyze(text): 基于关键词词典的情感分析
- ocr_extract(image_bytes): OCR 文字识别
"""

import pytest

from app.services.ai_service import AIService
from app.core.exceptions import BusinessException


@pytest.mark.asyncio
async def test_sentiment_positive():
    """测试正面情感分析。

    输入包含正面情感关键词的文本，验证分析结果为 positive。
    """
    text = "这个产品真的太棒了，我非常满意，强烈推荐给大家！"

    result = await AIService.sentiment_analyze(text)

    assert isinstance(result, dict), "情感分析结果应为字典"
    assert "sentiment" in result, "结果中应包含 sentiment 字段"
    assert result["sentiment"] == "positive", \
        f"正面文本的情感应为 positive，实际为 {result['sentiment']}"
    assert "score" in result, "结果中应包含 score 字段"
    assert result["score"] > 0, f"正面情感的分数应大于 0，实际为 {result['score']}"


@pytest.mark.asyncio
async def test_sentiment_negative():
    """测试负面情感分析。

    输入包含负面情感关键词的文本，验证分析结果为 negative。
    """
    text = "这个东西太差劲了，非常失望，真是垃圾产品。"

    result = await AIService.sentiment_analyze(text)

    assert isinstance(result, dict), "情感分析结果应为字典"
    assert "sentiment" in result, "结果中应包含 sentiment 字段"
    assert result["sentiment"] == "negative", \
        f"负面文本的情感应为 negative，实际为 {result['sentiment']}"
    assert "score" in result, "结果中应包含 score 字段"
    assert result["score"] < 0, f"负面情感的分数应小于 0，实际为 {result['score']}"


@pytest.mark.asyncio
async def test_sentiment_neutral():
    """测试中性情感分析。

    输入不包含明显情感倾向的文本，验证分析结果为 neutral。
    """
    text = "今天天气晴朗，我去了超市买了一瓶水。"

    result = await AIService.sentiment_analyze(text)

    assert isinstance(result, dict), "情感分析结果应为字典"
    assert "sentiment" in result, "结果中应包含 sentiment 字段"
    assert result["sentiment"] == "neutral", \
        f"中性文本的情感应为 neutral，实际为 {result['sentiment']}"
    assert "score" in result, "结果中应包含 score 字段"
    assert result["score"] == 0, f"中性情感的分数应为 0，实际为 {result['score']}"


@pytest.mark.asyncio
async def test_ocr_no_image():
    """测试 OCR 空输入。

    传入空的图片数据，验证函数能够优雅处理：
    - 如果 OCR 依赖未安装，返回空文本和零置信度的结果
    - 如果 OCR 依赖已安装，抛出 BusinessException
    """
    # 传入空字节数据
    empty_bytes = b""

    try:
        result = await AIService.ocr_extract(empty_bytes)

        # 如果 OCR 依赖未安装，返回降级结果
        assert isinstance(result, dict), "OCR 结果应为字典"
        assert result.get("text", "") == "", "空图片的识别文本应为空"
        assert result.get("confidence", 0) == 0, "空图片的置信度应为 0"

    except BusinessException:
        # 如果 OCR 依赖已安装，空图片会触发 BusinessException
        # 这是预期行为，测试通过
        pass
