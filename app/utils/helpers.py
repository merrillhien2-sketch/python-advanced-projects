"""通用工具函数模块。

提供项目通用的辅助函数，包括：
- UUID 生成
- 短码生成（base62 编码）
- 时间处理（获取、格式化、解析）
- 敏感信息脱敏
- 安全 JSON 解析
- 列表分块
"""

import json
import random
import string
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, TypeVar

T = TypeVar("T")

# Base62 字符集（0-9, a-z, A-Z），共 62 个字符
BASE62_CHARS = string.digits + string.ascii_lowercase + string.ascii_uppercase

# 默认时区：东八区（中国标准时间）
DEFAULT_TIMEZONE = timezone(timedelta(hours=8))


def generate_uuid() -> str:
    """生成 UUID 字符串。

    使用 uuid4 生成随机 UUID，返回去掉连字符的 32 位字符串。

    Returns:
        32 位 UUID 字符串（不含连字符）
    """
    return uuid.uuid4().hex


def generate_short_code(length: int = 6) -> str:
    """生成短码。

    使用 base62 字符集生成指定长度的随机短码。

    Args:
        length: 短码长度，默认为 6

    Returns:
        指定长度的随机短码字符串
    """
    return "".join(random.choices(BASE62_CHARS, k=length))


def datetime_now() -> datetime:
    """获取当前时间（带时区）。

    返回东八区（UTC+8）的当前时间。

    Returns:
        带时区信息的 datetime 对象
    """
    return datetime.now(DEFAULT_TIMEZONE)


def format_datetime(dt: datetime) -> str:
    """格式化 datetime 为字符串。

    将 datetime 对象格式化为 ISO 8601 标准字符串。

    Args:
        dt: 待格式化的 datetime 对象

    Returns:
        格式化后的时间字符串，如 "2024-01-15T14:30:00+08:00"
    """
    if dt is None:
        return ""
    # 如果 datetime 没有时区信息，默认使用东八区
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
    return dt.isoformat()


def parse_datetime(s: str) -> datetime:
    """解析时间字符串为 datetime 对象。

    支持解析 ISO 8601 格式的时间字符串。

    Args:
        s: 时间字符串，如 "2024-01-15T14:30:00+08:00"

    Returns:
        解析后的 datetime 对象

    Raises:
        ValueError: 当字符串无法解析时抛出
    """
    if not s:
        raise ValueError("时间字符串不能为空")
    # fromisoformat 在 Python 3.11+ 中支持更广泛的 ISO 格式
    dt = datetime.fromisoformat(s)
    # 如果没有时区信息，默认使用东八区
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
    return dt


def mask_sensitive(data: str, visible: int = 4) -> str:
    """敏感信息脱敏。

    保留字符串末尾指定数量的字符可见，其余部分用星号替代。

    Args:
        data: 需要脱敏的原始字符串
        visible: 保留可见的字符数（从末尾算起），默认为 4

    Returns:
        脱敏后的字符串，如 "****1234"

    Examples:
        >>> mask_sensitive("12345678901", 4)
        '*******8901'
        >>> mask_sensitive("test@example.com", 4)
        '************.com'
    """
    if not data:
        return ""
    if visible <= 0:
        return "*" * len(data)
    if len(data) <= visible:
        return "*" * len(data)
    masked_length = len(data) - visible
    return "*" * masked_length + data[-visible:]


def safe_json_loads(s: str, default: Any = None) -> Any:
    """安全 JSON 解析。

    尝试解析 JSON 字符串，解析失败时返回默认值而不是抛出异常。

    Args:
        s: 待解析的 JSON 字符串
        default: 解析失败时返回的默认值，默认为 None

    Returns:
        解析后的 Python 对象，或默认值
    """
    if not s:
        return default
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError) as e:
        import logging
        logging.getLogger(__name__).warning("JSON 解析失败: %s, 原始字符串: %s", e, s[:100])
        return default


def chunk_list(lst: list[T], size: int) -> list[list[T]]:
    """列表分块。

    将一个列表分割成多个固定大小的子列表。

    Args:
        lst: 待分割的原始列表
        size: 每个子列表的大小

    Returns:
        分割后的子列表列表

    Raises:
        ValueError: 当 size 小于等于 0 时抛出

    Examples:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    if size <= 0:
        raise ValueError("分块大小必须大于 0")
    if not lst:
        return []
    return [lst[i : i + size] for i in range(0, len(lst), size)]
