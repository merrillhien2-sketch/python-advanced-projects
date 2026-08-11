"""认证服务测试。

测试用户注册、登录（成功和密码错误）、以及无 token 访问受保护接口。

API 路由前缀为 /api/v1/auth/。
响应格式为 ResponseBase: {"code": 200, "message": "success", "data": {...}}。
"""

import pytest


@pytest.mark.asyncio
async def test_register(client):
    """测试用户注册。

    向注册接口发送请求，验证返回成功状态和用户信息。
    注册需要提供用户名、邮箱和密码。
    """
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "password": "SecurePass123",
            "email": "newuser@example.com",
        },
    )

    # 验证状态码（200 表示成功）
    assert response.status_code == 200, \
        f"用户注册应返回 200，实际返回 {response.status_code}"

    data = response.json()

    # 响应使用 ResponseBase 包装
    assert data["code"] == 200, f"ResponseBase code 应为 200，实际为 {data['code']}"
    result = data["data"]

    # 验证返回的用户信息
    assert "username" in result, "返回结果中应包含 username 字段"
    assert result["username"] == "newuser", "返回的用户名应与注册时一致"
    assert "email" in result, "返回结果中应包含 email 字段"

    # 验证不返回密码
    assert "password" not in result, "返回结果中不应包含密码字段"
    assert "hashed_password" not in result, "返回结果中不应包含哈希密码字段"


@pytest.mark.asyncio
async def test_login_success(client):
    """测试登录成功。

    先注册用户，然后使用正确的凭据登录，验证返回 token。
    """
    # 先注册用户
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "loginuser",
            "password": "CorrectPass123",
            "email": "loginuser@example.com",
        },
    )

    # 使用正确密码登录
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "loginuser",
            "password": "CorrectPass123",
        },
    )

    assert response.status_code == 200, \
        f"登录成功应返回 200，实际返回 {response.status_code}"

    data = response.json()

    # 响应使用 ResponseBase 包装
    assert data["code"] == 200, f"ResponseBase code 应为 200，实际为 {data['code']}"
    result = data["data"]

    # 验证返回了访问令牌
    assert "access_token" in result, "登录成功应返回 access_token"
    assert result["access_token"], "access_token 不能为空"

    # 验证令牌类型
    assert "token_type" in result, "结果中应包含 token_type 字段"
    assert result["token_type"] == "bearer", \
        f"token_type 应为 bearer，实际为 {result['token_type']}"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """测试密码错误。

    先注册用户，然后使用错误密码登录，验证返回 401 状态码。
    """
    # 先注册用户
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "wrongpassuser",
            "password": "CorrectPass123",
            "email": "wrongpass@example.com",
        },
    )

    # 使用错误密码登录
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "wrongpassuser",
            "password": "WrongPassword456",
        },
    )

    # 验证返回 401 未授权
    assert response.status_code == 401, \
        f"密码错误应返回 401，实际返回 {response.status_code}"

    data = response.json()
    assert data["code"] == 401, f"错误响应 code 应为 401，实际为 {data['code']}"


@pytest.mark.asyncio
async def test_get_me_without_token(client):
    """测试无 token 访问受保护接口。

    不携带 Authorization 头访问 /api/v1/auth/me 接口，
    验证返回 401 未授权状态码。
    """
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401, \
        f"无 token 访问应返回 401，实际返回 {response.status_code}"

    data = response.json()
    assert data["code"] == 401, f"错误响应 code 应为 401，实际为 {data['code']}"
    assert data["message"], "应返回错误消息"
