"""加密工具模块。

提供基于 Fernet 对称加密的数据加解密功能：
- AES 加密（使用 cryptography 库的 Fernet 实现）
- AES 解密
- 加密密钥生成

密钥从 settings.SECRET_KEY 派生，确保加密密钥与应用密钥关联。
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)


def _derive_key(secret: str) -> bytes:
    """从应用密钥派生 Fernet 加密密钥。

    使用 SHA-256 对原始密钥进行哈希，然后进行 base64 编码，
    生成符合 Fernet 要求的 32 字节 URL-safe base64 编码密钥。

    Args:
        secret: 原始密钥字符串（通常为 settings.SECRET_KEY）

    Returns:
        Fernet 兼容的 base64 编码密钥字节串
    """
    # 使用 SHA-256 哈希确保密钥长度固定为 32 字节
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    # base64 编码为 Fernet 要求的 URL-safe 格式
    return base64.urlsafe_b64encode(digest)


def generate_key() -> str:
    """生成加密密钥。

    生成一个新的 Fernet 加密密钥并返回其字符串形式。

    Returns:
        base64 编码的加密密钥字符串
    """
    return Fernet.generate_key().decode("utf-8")


def _get_fernet(key: str | None = None) -> Fernet:
    """获取 Fernet 实例。

    如果未提供密钥，则从 settings.SECRET_KEY 派生。

    Args:
        key: 可选的密钥字符串。如果为 None，则使用 settings.SECRET_KEY

    Returns:
        Fernet 加密实例
    """
    if key:
        # 如果提供了完整的 Fernet 密钥，直接使用
        try:
            return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
        except Exception:
            # 如果不是有效的 Fernet 密钥，则作为普通密钥派生
            return Fernet(_derive_key(key))
    else:
        # 从 settings.SECRET_KEY 派生密钥
        secret = getattr(settings, "SECRET_KEY", "default-secret-key")
        return Fernet(_derive_key(secret))


async def encrypt_data(data: str, key: str | None = None) -> str:
    """AES 加密数据。

    使用 Fernet 对称加密算法加密字符串数据，
    返回 base64 编码的加密结果。

    Args:
        data: 待加密的明文字符串
        key: 可选的加密密钥。如果为 None，则使用 settings.SECRET_KEY 派生

    Returns:
        base64 编码的加密字符串

    Raises:
        ValueError: 当待加密数据为空时抛出

    Examples:
        >>> encrypted = await encrypt_data("hello world")
        >>> isinstance(encrypted, str)
        True
    """
    if not data:
        raise ValueError("待加密数据不能为空")

    try:
        fernet = _get_fernet(key)
        # 将字符串编码为字节后加密
        encrypted_bytes = fernet.encrypt(data.encode("utf-8"))
        # 返回字符串形式
        return encrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.error("数据加密失败: %s", e, exc_info=True)
        raise


async def decrypt_data(encrypted: str, key: str | None = None) -> str:
    """AES 解密数据。

    使用 Fernet 对称加密算法解密 base64 编码的加密字符串，
    返回原始明文。

    Args:
        encrypted: base64 编码的加密字符串
        key: 可选的解密密钥。如果为 None，则使用 settings.SECRET_KEY 派生

    Returns:
        解密后的明文字符串

    Raises:
        ValueError: 当加密数据为空时抛出
        InvalidToken: 当密钥不匹配或数据被篡改时抛出

    Examples:
        >>> encrypted = await encrypt_data("hello world")
        >>> await decrypt_data(encrypted)
        'hello world'
    """
    if not encrypted:
        raise ValueError("加密数据不能为空")

    try:
        fernet = _get_fernet(key)
        # 将字符串编码为字节后解密
        decrypted_bytes = fernet.decrypt(encrypted.encode("utf-8"))
        # 返回解密后的字符串
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        logger.error("解密失败：密钥不匹配或数据已被篡改")
        raise
    except Exception as e:
        logger.error("数据解密失败: %s", e, exc_info=True)
        raise
