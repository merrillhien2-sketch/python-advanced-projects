"""接口自动化测试路由

提供测试套件与用例的管理、执行及运行历史查询接口。

接口列表:
    - POST /suites                创建测试套件
    - GET  /suites                分页查询套件
    - GET  /suites/{suite_id}/cases  查询套件下的用例
    - POST /cases                 创建测试用例
    - POST /cases/{case_id}/run   执行单个用例
    - POST /suites/{suite_id}/run 执行整个套件
    - GET  /suites/{suite_id}/history 查询运行历史
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.api_test import (
    SuiteRunResult,
    TestCaseCreate,
    TestCaseResponse,
    TestRunResponse,
    TestSuiteCreate,
    TestSuiteResponse,
)
from app.schemas.common import PaginatedResponse, ResponseBase
from app.services.api_test_service import ApiTestService

router = APIRouter()


@router.post(
    "/suites",
    response_model=ResponseBase[TestSuiteResponse],
    summary="创建测试套件",
)
async def create_suite(
    suite_in: TestSuiteCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[TestSuiteResponse]:
    """创建测试套件

    参数:
        suite_in: 套件创建请求（名称、描述、基础 URL）
        db: 异步数据库会话

    返回:
        包含套件信息的响应
    """
    suite = await ApiTestService.create_suite(suite_in.model_dump(), db)
    return ResponseBase(data=TestSuiteResponse.model_validate(suite))


@router.get(
    "/suites",
    response_model=PaginatedResponse[TestSuiteResponse],
    summary="分页查询套件",
)
async def list_suites(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TestSuiteResponse]:
    """分页查询测试套件列表

    参数:
        page: 页码，从 1 开始
        page_size: 每页条数
        db: 异步数据库会话

    返回:
        分页响应，包含套件列表和分页信息
    """
    result = await ApiTestService.get_suites(page, page_size, db)
    data = [TestSuiteResponse(**item) for item in result["data"]]
    return PaginatedResponse(
        data=data,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/suites/{suite_id}/cases",
    response_model=ResponseBase[list[TestCaseResponse]],
    summary="查询套件下的用例",
)
async def get_cases(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[list[TestCaseResponse]]:
    """查询指定套件下的所有用例

    参数:
        suite_id: 套件 ID
        db: 异步数据库会话

    返回:
        包含用例列表的响应
    """
    data = await ApiTestService.get_cases(suite_id, db)
    cases = [TestCaseResponse(**item) for item in data]
    return ResponseBase(data=cases)


@router.post(
    "/cases",
    response_model=ResponseBase[TestCaseResponse],
    summary="创建测试用例",
)
async def create_case(
    case_in: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[TestCaseResponse]:
    """创建测试用例

    参数:
        case_in: 用例创建请求（套件 ID、名称、方法、URL 等）
        db: 异步数据库会话

    返回:
        包含用例信息的响应
    """
    case = await ApiTestService.create_case(case_in.model_dump(), db)
    return ResponseBase(data=TestCaseResponse.model_validate(case))


@router.post(
    "/cases/{case_id}/run",
    response_model=ResponseBase[TestRunResponse],
    summary="执行单个用例",
)
async def run_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[TestRunResponse]:
    """执行单个测试用例

    使用 httpx 发送 HTTP 请求，记录响应状态码、响应体和耗时，
    与预期比对后保存运行记录。

    参数:
        case_id: 用例 ID
        db: 异步数据库会话

    返回:
        包含运行结果的响应
    """
    result = await ApiTestService.run_case(case_id, db)
    return ResponseBase(data=TestRunResponse(**result))


@router.post(
    "/suites/{suite_id}/run",
    response_model=ResponseBase[SuiteRunResult],
    summary="执行整个套件",
)
async def run_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[SuiteRunResult]:
    """执行整个测试套件

    并发执行套件下的所有用例，汇总统计通过数和失败数。

    参数:
        suite_id: 套件 ID
        db: 异步数据库会话

    返回:
        包含套件运行汇总结果的响应
    """
    result = await ApiTestService.run_suite(suite_id, db)
    # 将 results 中的字典转换为 TestRunResponse 列表
    result["results"] = [
        TestRunResponse(**r) if r.get("id") is not None else TestRunResponse(
            id=0,
            suite_id=r.get("suite_id", 0),
            case_id=r.get("case_id"),
            status=r.get("status", "failed"),
            actual_status=r.get("actual_status"),
            error=r.get("error"),
            duration_ms=r.get("duration_ms"),
            ran_at=r.get("ran_at"),
        )
        for r in result.get("results", [])
    ]
    return ResponseBase(data=SuiteRunResult(**result))


@router.get(
    "/suites/{suite_id}/history",
    response_model=PaginatedResponse[TestRunResponse],
    summary="查询运行历史",
)
async def get_run_history(
    suite_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TestRunResponse]:
    """分页查询指定套件的运行历史

    参数:
        suite_id: 套件 ID
        page: 页码，从 1 开始
        page_size: 每页条数
        db: 异步数据库会话

    返回:
        分页响应，包含运行记录列表和分页信息
    """
    result = await ApiTestService.get_run_history(suite_id, page, page_size, db)
    data = [TestRunResponse(**item) for item in result["data"]]
    return PaginatedResponse(
        data=data,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
