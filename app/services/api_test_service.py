"""接口自动化测试服务

提供测试套件与用例的创建、查询，以及用例和套件的执行能力。

特性:
    - 使用 httpx 异步发送 HTTP 请求执行测试用例
    - 套件运行使用 asyncio.gather 并发执行所有用例
    - 自动比对响应状态码与预期响应内容
    - 记录每次运行的详细信息（状态码、响应体、耗时、错误）
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessException, NotFoundException, ValidationException
from app.models.api_test import ApiTestCase, ApiTestRun, ApiTestSuite

logger = logging.getLogger(__name__)

# HTTP 请求超时时间（秒）
REQUEST_TIMEOUT: float = 30.0

# 支持的 HTTP 方法
ALLOWED_METHODS: set[str] = {"GET", "POST", "PUT", "DELETE"}


class ApiTestService:
    """接口自动化测试服务类

    提供测试套件、用例的管理与执行能力。
    """

    @classmethod
    async def create_suite(
        cls, suite_data: dict[str, Any], db: AsyncSession
    ) -> ApiTestSuite:
        """创建测试套件

        参数:
            suite_data: 套件数据（name、description、base_url）
            db: 异步数据库会话

        返回:
            创建的 ApiTestSuite 对象

        异常:
            ValidationException: 套件名称为空时
            BusinessException: 创建失败时
        """
        name = suite_data.get("name", "")
        if not name or not name.strip():
            raise ValidationException("套件名称不能为空")

        try:
            suite = ApiTestSuite(
                name=name.strip(),
                description=suite_data.get("description"),
                base_url=suite_data.get("base_url"),
            )
            db.add(suite)
            await db.commit()
            await db.refresh(suite)

            logger.info("测试套件创建成功: ID=%s, name=%s", suite.id, suite.name)
            return suite

        except Exception as e:
            await db.rollback()
            logger.error("创建测试套件失败: %s", e, exc_info=True)
            raise BusinessException(message=f"创建测试套件失败: {e}")

    @classmethod
    async def create_case(
        cls, case_data: dict[str, Any], db: AsyncSession
    ) -> ApiTestCase:
        """创建测试用例

        参数:
            case_data: 用例数据（suite_id、name、method、url 等）
            db: 异步数据库会话

        返回:
            创建的 ApiTestCase 对象

        异常:
            ValidationException: 用例名称、方法或 URL 为空，或方法不支持时
            NotFoundException: 所属套件不存在时
            BusinessException: 创建失败时
        """
        name = case_data.get("name", "")
        method = (case_data.get("method", "") or "").upper()
        url = case_data.get("url", "")
        suite_id = case_data.get("suite_id")

        if not name or not name.strip():
            raise ValidationException("用例名称不能为空")
        if not method:
            raise ValidationException("HTTP 方法不能为空")
        if method not in ALLOWED_METHODS:
            raise ValidationException(
                f"不支持的 HTTP 方法: {method}，仅支持 {ALLOWED_METHODS}"
            )
        if not url or not url.strip():
            raise ValidationException("请求 URL 不能为空")
        if suite_id is None:
            raise ValidationException("所属套件 ID 不能为空")

        try:
            # 验证套件是否存在
            result = await db.execute(
                select(ApiTestSuite).where(ApiTestSuite.id == suite_id)
            )
            suite = result.scalar_one_or_none()
            if suite is None:
                raise NotFoundException(f"测试套件不存在: ID={suite_id}")

            case = ApiTestCase(
                suite_id=suite_id,
                name=name.strip(),
                method=method,
                url=url.strip(),
                headers=case_data.get("headers"),
                body=case_data.get("body"),
                expected_status=case_data.get("expected_status", 200),
                expected_response=case_data.get("expected_response"),
            )
            db.add(case)
            await db.commit()
            await db.refresh(case)

            logger.info("测试用例创建成功: ID=%s, name=%s", case.id, case.name)
            return case

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            await db.rollback()
            logger.error("创建测试用例失败: %s", e, exc_info=True)
            raise BusinessException(message=f"创建测试用例失败: {e}")

    @classmethod
    async def get_suites(
        cls, page: int, page_size: int, db: AsyncSession
    ) -> dict[str, Any]:
        """分页查询测试套件

        参数:
            page: 页码，从 1 开始
            page_size: 每页条数
            db: 异步数据库会话

        返回:
            包含 data（套件列表）、total、page、page_size 的字典

        异常:
            ValidationException: 分页参数无效时
            BusinessException: 查询失败时
        """
        if page < 1:
            raise ValidationException("页码必须大于 0")
        if page_size < 1 or page_size > 100:
            raise ValidationException("每页条数必须在 1-100 之间")

        try:
            # 查询总数
            count_result = await db.execute(select(func.count(ApiTestSuite.id)))
            total = count_result.scalar() or 0

            # 查询当前页数据
            offset = (page - 1) * page_size
            result = await db.execute(
                select(ApiTestSuite)
                .order_by(ApiTestSuite.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            suites = result.scalars().all()

            data = [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "base_url": s.base_url,
                    "created_at": s.created_at,
                }
                for s in suites
            ]

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        except Exception as e:
            logger.error("查询测试套件列表失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询测试套件列表失败: {e}")

    @classmethod
    async def get_cases(
        cls, suite_id: int, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """查询套件下的用例列表

        参数:
            suite_id: 套件 ID
            db: 异步数据库会话

        返回:
            用例字典列表

        异常:
            NotFoundException: 套件不存在时
            BusinessException: 查询失败时
        """
        try:
            # 验证套件是否存在
            suite_result = await db.execute(
                select(ApiTestSuite).where(ApiTestSuite.id == suite_id)
            )
            suite = suite_result.scalar_one_or_none()
            if suite is None:
                raise NotFoundException(f"测试套件不存在: ID={suite_id}")

            result = await db.execute(
                select(ApiTestCase)
                .where(ApiTestCase.suite_id == suite_id)
                .order_by(ApiTestCase.id.asc())
            )
            cases = result.scalars().all()

            data = [
                {
                    "id": c.id,
                    "suite_id": c.suite_id,
                    "name": c.name,
                    "method": c.method,
                    "url": c.url,
                    "headers": c.headers,
                    "body": c.body,
                    "expected_status": c.expected_status,
                    "expected_response": c.expected_response,
                    "created_at": c.created_at,
                }
                for c in cases
            ]

            return data

        except NotFoundException:
            raise
        except Exception as e:
            logger.error("查询用例列表失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询用例列表失败: {e}")

    @classmethod
    async def run_case(
        cls, case_id: int, db: AsyncSession
    ) -> dict[str, Any]:
        """执行单个测试用例

        使用 httpx 发送 HTTP 请求，记录响应状态码、响应体和耗时，
        与预期状态码和响应内容比对，保存运行记录。

        参数:
            case_id: 用例 ID
            db: 异步数据库会话

        返回:
            包含运行结果信息的字典

        异常:
            NotFoundException: 用例不存在时
            BusinessException: 执行失败时
        """
        try:
            # 查询用例
            result = await db.execute(
                select(ApiTestCase).where(ApiTestCase.id == case_id)
            )
            case = result.scalar_one_or_none()
            if case is None:
                raise NotFoundException(f"测试用例不存在: ID={case_id}")

            # 查询套件以获取 base_url
            suite_result = await db.execute(
                select(ApiTestSuite).where(ApiTestSuite.id == case.suite_id)
            )
            suite = suite_result.scalar_one_or_none()

            # 拼接完整 URL
            base_url = suite.base_url if suite and suite.base_url else ""
            full_url = cls._build_url(base_url, case.url)

            # 解析请求头和请求体
            headers = cls._parse_json_field(case.headers)
            body = cls._parse_json_field(case.body)

            # 发送请求并记录耗时
            start_time = time.monotonic()
            run_status = "running"

            try:
                async with httpx.AsyncClient(
                    timeout=REQUEST_TIMEOUT, verify=False
                ) as client:
                    response = await cls._send_request(
                        client, case.method, full_url, headers, body
                    )

                duration_ms = int((time.monotonic() - start_time) * 1000)
                actual_status = response.status_code
                response_body = response.text

                # 比对预期
                is_passed = cls._check_result(
                    case, actual_status, response_body
                )
                run_status = "passed" if is_passed else "failed"
                error_msg = None if is_passed else cls._build_error_msg(
                    case, actual_status, response_body
                )

            except httpx.RequestError as e:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                actual_status = None
                response_body = None
                run_status = "failed"
                error_msg = f"请求异常: {e}"

            # 保存运行记录
            run = ApiTestRun(
                suite_id=case.suite_id,
                case_id=case.id,
                status=run_status,
                actual_status=actual_status,
                response_body=response_body,
                error=error_msg,
                duration_ms=duration_ms,
                ran_at=datetime.now(timezone.utc),
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)

            logger.info(
                "用例执行完成: ID=%s, status=%s, duration=%dms",
                case.id,
                run_status,
                duration_ms,
            )

            return {
                "id": run.id,
                "suite_id": run.suite_id,
                "case_id": run.case_id,
                "status": run.status,
                "actual_status": run.actual_status,
                "error": run.error,
                "duration_ms": run.duration_ms,
                "ran_at": run.ran_at,
            }

        except NotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error("执行测试用例失败: %s", e, exc_info=True)
            raise BusinessException(message=f"执行测试用例失败: {e}")

    @classmethod
    async def run_suite(
        cls, suite_id: int, db: AsyncSession
    ) -> dict[str, Any]:
        """执行整个测试套件

        并发执行套件下的所有用例（asyncio.gather），
        汇总统计通过数和失败数。

        参数:
            suite_id: 套件 ID
            db: 异步数据库会话

        返回:
            包含套件运行汇总结果的字典

        异常:
            NotFoundException: 套件不存在时
            BusinessException: 执行失败时
        """
        try:
            # 验证套件是否存在
            suite_result = await db.execute(
                select(ApiTestSuite).where(ApiTestSuite.id == suite_id)
            )
            suite = suite_result.scalar_one_or_none()
            if suite is None:
                raise NotFoundException(f"测试套件不存在: ID={suite_id}")

            # 查询套件下的所有用例
            cases_result = await db.execute(
                select(ApiTestCase).where(ApiTestCase.suite_id == suite_id)
            )
            cases = cases_result.scalars().all()

            if not cases:
                return {
                    "suite_id": suite_id,
                    "suite_name": suite.name,
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "duration_ms": 0,
                    "results": [],
                }

            # 并发执行所有用例
            start_time = time.monotonic()
            tasks = [cls.run_case(case.id, db) for case in cases]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_duration = int((time.monotonic() - start_time) * 1000)

            # 统计结果
            passed = 0
            failed = 0
            run_results: list[dict[str, Any]] = []

            for r in results:
                if isinstance(r, Exception):
                    failed += 1
                    run_results.append(
                        {
                            "id": None,
                            "suite_id": suite_id,
                            "case_id": None,
                            "status": "failed",
                            "actual_status": None,
                            "error": str(r),
                            "duration_ms": None,
                            "ran_at": None,
                        }
                    )
                else:
                    if r["status"] == "passed":
                        passed += 1
                    else:
                        failed += 1
                    run_results.append(r)

            logger.info(
                "套件执行完成: suite_id=%s, total=%d, passed=%d, failed=%d",
                suite_id,
                len(cases),
                passed,
                failed,
            )

            return {
                "suite_id": suite_id,
                "suite_name": suite.name,
                "total": len(cases),
                "passed": passed,
                "failed": failed,
                "duration_ms": total_duration,
                "results": run_results,
            }

        except NotFoundException:
            raise
        except Exception as e:
            logger.error("执行测试套件失败: %s", e, exc_info=True)
            raise BusinessException(message=f"执行测试套件失败: {e}")

    @classmethod
    async def get_run_history(
        cls, suite_id: int, page: int, page_size: int, db: AsyncSession
    ) -> dict[str, Any]:
        """查询运行历史

        参数:
            suite_id: 套件 ID
            page: 页码，从 1 开始
            page_size: 每页条数
            db: 异步数据库会话

        返回:
            包含 data（运行记录列表）、total、page、page_size 的字典

        异常:
            ValidationException: 分页参数无效时
            BusinessException: 查询失败时
        """
        if page < 1:
            raise ValidationException("页码必须大于 0")
        if page_size < 1 or page_size > 100:
            raise ValidationException("每页条数必须在 1-100 之间")

        try:
            # 查询总数
            count_result = await db.execute(
                select(func.count(ApiTestRun.id).where(
                    ApiTestRun.suite_id == suite_id
                ))
            )
            total = count_result.scalar() or 0

            # 查询当前页数据
            offset = (page - 1) * page_size
            result = await db.execute(
                select(ApiTestRun)
                .where(ApiTestRun.suite_id == suite_id)
                .order_by(ApiTestRun.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            runs = result.scalars().all()

            data = [
                {
                    "id": r.id,
                    "suite_id": r.suite_id,
                    "case_id": r.case_id,
                    "status": r.status,
                    "actual_status": r.actual_status,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                    "ran_at": r.ran_at,
                }
                for r in runs
            ]

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        except Exception as e:
            logger.error("查询运行历史失败: %s", e, exc_info=True)
            raise BusinessException(message=f"查询运行历史失败: {e}")

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _build_url(base_url: str, url: str) -> str:
        """拼接完整 URL

        如果 url 已是完整 URL（以 http 开头），直接返回；
        否则将 base_url 与 url 拼接。

        参数:
            base_url: 基础 URL
            url: 请求路径或完整 URL

        返回:
            完整的请求 URL
        """
        if url.lower().startswith(("http://", "https://")):
            return url
        if not base_url:
            return url
        # 去除 base_url 末尾斜杠和 url 开头斜杠后拼接
        return base_url.rstrip("/") + "/" + url.lstrip("/")

    @staticmethod
    def _parse_json_field(value: str | None) -> Any:
        """解析 JSON 字符串字段

        参数:
            value: JSON 字符串，可为 None

        返回:
            解析后的对象，解析失败或为空时返回 None
        """
        if not value:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    async def _send_request(
        client: httpx.AsyncClient,
        method: str,
        url: str,
        headers: dict | None,
        body: Any,
    ) -> httpx.Response:
        """发送 HTTP 请求

        参数:
            client: httpx 异步客户端
            method: HTTP 方法
            url: 请求 URL
            headers: 请求头字典
            body: 请求体

        返回:
            httpx 响应对象
        """
        if method == "GET":
            return await client.get(url, headers=headers, params=None)
        elif method == "POST":
            return await client.post(url, headers=headers, json=body)
        elif method == "PUT":
            return await client.put(url, headers=headers, json=body)
        elif method == "DELETE":
            return await client.delete(url, headers=headers, json=body)
        else:
            raise ValidationException(f"不支持的 HTTP 方法: {method}")

    @staticmethod
    def _check_result(
        case: ApiTestCase, actual_status: int, response_body: str
    ) -> bool:
        """比对测试结果

        比对实际状态码与预期状态码，
        如果设置了预期响应，则检查响应体是否包含预期内容（部分匹配）。

        参数:
            case: 测试用例对象
            actual_status: 实际响应状态码
            response_body: 实际响应体

        返回:
            比对通过返回 True，否则 False
        """
        # 状态码比对
        if actual_status != case.expected_status:
            return False

        # 预期响应内容比对（部分匹配）
        if case.expected_response:
            expected = ApiTestService._parse_json_field(case.expected_response)
            if expected is not None and isinstance(expected, dict):
                # 解析实际响应体
                try:
                    actual = json.loads(response_body)
                except (json.JSONDecodeError, TypeError):
                    return False
                # 检查预期字段是否存在于实际响应中且值匹配
                if not isinstance(actual, dict):
                    return False
                for key, val in expected.items():
                    if key not in actual:
                        return False
                    if actual[key] != val:
                        return False

        return True

    @staticmethod
    def _build_error_msg(
        case: ApiTestCase, actual_status: int, response_body: str
    ) -> str:
        """构建错误信息

        参数:
            case: 测试用例对象
            actual_status: 实际响应状态码
            response_body: 实际响应体

        返回:
            错误描述字符串
        """
        if actual_status != case.expected_status:
            return (
                f"状态码不匹配: 预期 {case.expected_status}, "
                f"实际 {actual_status}"
            )
        if case.expected_response:
            return "响应内容与预期不匹配"
        return "测试未通过"
