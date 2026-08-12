"""接口自动化测试服务测试。

测试测试套件创建、测试用例创建和用例列表查询。
使用 conftest.py 中的 db_session fixture 提供测试数据库会话。
"""

import pytest

# 导入服务会自动注册模型到 Base.metadata，确保测试时表能被创建
from app.services.api_test_service import ApiTestService  # noqa: F401


@pytest.mark.asyncio
async def test_create_suite(db_session):
    """测试创建测试套件。

    向服务层传入套件数据，验证返回的套件对象包含正确的字段值。
    """
    suite = await ApiTestService.create_suite(
        {
            "name": "用户接口测试套件",
            "description": "覆盖用户注册、登录等接口",
            "base_url": "https://api.example.com",
        },
        db_session,
    )

    assert suite.id is not None, "套件 ID 不应为空"
    assert suite.name == "用户接口测试套件", "套件名称应一致"
    assert suite.description == "覆盖用户注册、登录等接口", "套件描述应一致"
    assert suite.base_url == "https://api.example.com", "基础 URL 应一致"
    assert suite.created_at is not None, "创建时间不应为空"


@pytest.mark.asyncio
async def test_create_case(db_session):
    """测试创建测试用例。

    先创建套件，再在套件下创建用例，验证返回的用例对象字段正确。
    """
    # 先创建套件
    suite = await ApiTestService.create_suite(
        {"name": "订单接口测试", "base_url": "https://api.example.com"},
        db_session,
    )

    # 创建用例
    case = await ApiTestService.create_case(
        {
            "suite_id": suite.id,
            "name": "获取订单列表",
            "method": "GET",
            "url": "/api/orders",
            "headers": '{"Authorization": "Bearer test-token"}',
            "body": None,
            "expected_status": 200,
            "expected_response": '{"code": 200}',
        },
        db_session,
    )

    assert case.id is not None, "用例 ID 不应为空"
    assert case.suite_id == suite.id, "用例所属套件 ID 应一致"
    assert case.name == "获取订单列表", "用例名称应一致"
    assert case.method == "GET", "HTTP 方法应为 GET"
    assert case.url == "/api/orders", "请求 URL 应一致"
    assert case.expected_status == 200, "预期状态码应为 200"
    assert case.headers == '{"Authorization": "Bearer test-token"}', "请求头应一致"


@pytest.mark.asyncio
async def test_get_cases(db_session):
    """测试查询用例列表。

    创建套件和多个用例后，查询套件下的用例列表，验证返回数量和内容正确。
    """
    # 创建套件
    suite = await ApiTestService.create_suite(
        {"name": "商品接口测试", "base_url": "https://api.example.com"},
        db_session,
    )

    # 创建两个用例
    await ApiTestService.create_case(
        {
            "suite_id": suite.id,
            "name": "获取商品列表",
            "method": "GET",
            "url": "/api/products",
            "expected_status": 200,
        },
        db_session,
    )
    await ApiTestService.create_case(
        {
            "suite_id": suite.id,
            "name": "创建商品",
            "method": "POST",
            "url": "/api/products",
            "body": '{"name": "test"}',
            "expected_status": 201,
        },
        db_session,
    )

    # 查询用例列表
    cases = await ApiTestService.get_cases(suite.id, db_session)

    assert isinstance(cases, list), "结果应为列表"
    assert len(cases) == 2, f"应返回 2 个用例，实际 {len(cases)}"
    assert cases[0]["name"] == "获取商品列表", "第一个用例名称应一致"
    assert cases[1]["name"] == "创建商品", "第二个用例名称应一致"
    assert cases[1]["method"] == "POST", "第二个用例方法应为 POST"
