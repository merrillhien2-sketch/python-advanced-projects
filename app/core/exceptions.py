"""全局异常处理模块。

定义应用自定义异常类层次，并注册 FastAPI 全局异常处理器，
统一错误响应格式为::

    {"code": 404, "message": "资源不存在", "data": null}

对外不暴露内部错误细节。
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppException(Exception):
    """应用异常基类。

    Attributes:
        code: 业务错误码（同时作为 HTTP 状态码）
        message: 面向用户的错误描述
    """

    def __init__(self, code: int = 500, message: str = "服务器内部错误") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class NotFoundException(AppException):
    """资源不存在异常（404）。"""

    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(code=404, message=message)


class ValidationException(AppException):
    """数据校验异常（422）。"""

    def __init__(self, message: str = "数据校验失败") -> None:
        super().__init__(code=422, message=message)


class AuthenticationException(AppException):
    """认证失败异常（401）。"""

    def __init__(self, message: str = "认证失败，请重新登录") -> None:
        super().__init__(code=401, message=message)


class RateLimitException(AppException):
    """接口限流异常（429）。"""

    def __init__(self, message: str = "请求过于频繁，请稍后再试") -> None:
        super().__init__(code=429, message=message)


class BusinessException(AppException):
    """业务逻辑异常。

    允许自定义错误码与描述，code 默认 400。
    """

    def __init__(self, code: int = 400, message: str = "业务处理失败") -> None:
        super().__init__(code=code, message=message)


def _build_response(code: int, message: str, data=None) -> JSONResponse:
    """构建统一格式的 JSON 响应。

    Args:
        code: 业务错误码
        message: 错误描述
        data: 可选的业务数据，默认为 None

    Returns:
        统一格式的 JSONResponse
    """
    # 限定 HTTP 状态码合法范围
    http_status = code if 100 <= code < 600 else 500
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": data},
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器到 FastAPI 应用。

    处理顺序：自定义应用异常 -> HTTP 异常 -> 参数校验异常 -> 未捕获异常。
    更具体的异常类型优先匹配。
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """处理自定义应用异常，直接返回其携带的 code 与 message。"""
        return _build_response(exc.code, exc.message, None)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """处理 Starlette/FastAPI HTTP 异常。"""
        detail = exc.detail if isinstance(exc.detail, str) else "请求错误"
        return _build_response(exc.status_code, detail, None)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """处理请求参数校验异常，不暴露内部字段细节。"""
        return _build_response(422, "数据校验失败", None)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """处理未捕获的异常，记录完整堆栈但不向前端暴露细节。"""
        logger.exception("未捕获的异常: %s", exc)
        return _build_response(500, "服务器内部错误", None)
