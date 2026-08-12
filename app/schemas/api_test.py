"""接口自动化测试相关 Schema

定义测试套件、测试用例的创建请求与响应，
以及测试运行结果的数据模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TestSuiteCreate(BaseModel):
    """测试套件创建请求

    属性:
        name: 套件名称
        description: 套件描述
        base_url: 基础 URL
    """

    name: str = Field(..., description="套件名称")
    description: Optional[str] = Field(default=None, description="套件描述")
    base_url: Optional[str] = Field(default=None, description="基础URL")


class TestSuiteResponse(BaseModel):
    """测试套件响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="套件ID")
    name: str = Field(..., description="套件名称")
    description: Optional[str] = Field(default=None, description="套件描述")
    base_url: Optional[str] = Field(default=None, description="基础URL")
    created_at: datetime = Field(..., description="创建时间")


class TestCaseCreate(BaseModel):
    """测试用例创建请求

    属性:
        suite_id: 所属套件 ID
        name: 用例名称
        method: HTTP 方法（GET/POST/PUT/DELETE）
        url: 请求 URL
        headers: 请求头（JSON 字符串），可为空
        body: 请求体（JSON 字符串），可为空
        expected_status: 预期状态码，默认 200
        expected_response: 预期响应（JSON 字符串），可为空
    """

    suite_id: int = Field(..., description="所属套件ID")
    name: str = Field(..., description="用例名称")
    method: str = Field(..., description="HTTP方法")
    url: str = Field(..., description="请求URL")
    headers: Optional[str] = Field(default=None, description="请求头(JSON字符串)")
    body: Optional[str] = Field(default=None, description="请求体(JSON字符串)")
    expected_status: int = Field(default=200, description="预期状态码")
    expected_response: Optional[str] = Field(
        default=None, description="预期响应(JSON字符串)"
    )


class TestCaseResponse(BaseModel):
    """测试用例响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="用例ID")
    suite_id: int = Field(..., description="所属套件ID")
    name: str = Field(..., description="用例名称")
    method: str = Field(..., description="HTTP方法")
    url: str = Field(..., description="请求URL")
    headers: Optional[str] = Field(default=None, description="请求头(JSON字符串)")
    body: Optional[str] = Field(default=None, description="请求体(JSON字符串)")
    expected_status: int = Field(..., description="预期状态码")
    expected_response: Optional[str] = Field(
        default=None, description="预期响应(JSON字符串)"
    )
    created_at: datetime = Field(..., description="创建时间")


class TestRunResponse(BaseModel):
    """测试运行结果响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="运行记录ID")
    suite_id: int = Field(..., description="所属套件ID")
    case_id: Optional[int] = Field(default=None, description="所属用例ID")
    status: str = Field(..., description="运行状态")
    actual_status: Optional[int] = Field(default=None, description="实际状态码")
    error: Optional[str] = Field(default=None, description="错误信息")
    duration_ms: Optional[int] = Field(default=None, description="耗时(毫秒)")
    ran_at: Optional[datetime] = Field(default=None, description="运行时间")


class SuiteRunResult(BaseModel):
    """套件运行结果

    属性:
        suite_id: 套件 ID
        suite_name: 套件名称
        total: 总用例数
        passed: 通过数
        failed: 失败数
        duration_ms: 总耗时（毫秒）
        results: 各用例运行结果列表
    """

    suite_id: int = Field(..., description="套件ID")
    suite_name: str = Field(..., description="套件名称")
    total: int = Field(0, description="总用例数")
    passed: int = Field(0, description="通过数")
    failed: int = Field(0, description="失败数")
    duration_ms: int = Field(0, description="总耗时(毫秒)")
    results: list[TestRunResponse] = Field(
        default_factory=list, description="各用例运行结果列表"
    )
