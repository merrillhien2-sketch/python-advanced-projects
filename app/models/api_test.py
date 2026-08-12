"""接口自动化测试模型

定义接口测试套件、测试用例、测试运行记录的表结构，
用于管理 API 自动化测试的全生命周期数据。
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.models.base import BaseModel


class ApiTestSuite(BaseModel):
    """接口测试套件表模型

    字段说明:
        - name: 套件名称
        - description: 套件描述，可为空
        - base_url: 基础 URL，用例中的相对路径会拼接此前缀，可为空
    """

    __tablename__ = "api_test_suites"

    name = Column(String(100), nullable=False, comment="套件名称")
    description = Column(Text, nullable=True, comment="套件描述")
    base_url = Column(String(500), nullable=True, comment="基础URL")


class ApiTestCase(BaseModel):
    """接口测试用例表模型

    字段说明:
        - suite_id: 所属套件 ID，关联 api_test_suites 表
        - name: 用例名称
        - method: HTTP 方法（GET/POST/PUT/DELETE）
        - url: 请求 URL
        - headers: 请求头（JSON 字符串），可为空
        - body: 请求体（JSON 字符串），可为空
        - expected_status: 预期响应状态码，默认 200
        - expected_response: 预期响应内容（JSON 字符串，用于部分匹配），可为空
    """

    __tablename__ = "api_test_cases"

    suite_id = Column(
        Integer,
        ForeignKey("api_test_suites.id"),
        nullable=False,
        comment="所属套件ID",
    )
    name = Column(String(200), nullable=False, comment="用例名称")
    method = Column(String(10), nullable=False, comment="HTTP方法")
    url = Column(Text, nullable=False, comment="请求URL")
    headers = Column(Text, nullable=True, comment="请求头(JSON字符串)")
    body = Column(Text, nullable=True, comment="请求体(JSON字符串)")
    expected_status = Column(
        Integer, default=200, nullable=False, comment="预期状态码"
    )
    expected_response = Column(
        Text, nullable=True, comment="预期响应(JSON字符串,部分匹配)"
    )


class ApiTestRun(BaseModel):
    """接口测试运行记录表模型

    字段说明:
        - suite_id: 所属套件 ID
        - case_id: 所属用例 ID，可为空（套件级运行时记录）
        - status: 运行状态（pending/running/passed/failed）
        - actual_status: 实际响应状态码
        - response_body: 实际响应体
        - error: 错误信息
        - duration_ms: 耗时（毫秒）
        - ran_at: 运行时间
    """

    __tablename__ = "api_test_runs"

    suite_id = Column(Integer, nullable=False, comment="所属套件ID")
    case_id = Column(Integer, nullable=True, comment="所属用例ID")
    status = Column(
        String(20), default="pending", nullable=False, comment="运行状态"
    )
    actual_status = Column(Integer, nullable=True, comment="实际状态码")
    response_body = Column(Text, nullable=True, comment="响应体")
    error = Column(Text, nullable=True, comment="错误信息")
    duration_ms = Column(Integer, nullable=True, comment="耗时(毫秒)")
    ran_at = Column(DateTime, nullable=True, comment="运行时间")
