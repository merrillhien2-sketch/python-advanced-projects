"""短链服务测试。

测试短链的创建、解析和不存在短码的处理。
使用 Mock Redis 替代真实 Redis 连接。

API 路由前缀为 /api/v1/shortlink/。
创建短链需要认证，解析短链返回 302 重定向。
"""

import pytest


@pytest.mark.asyncio
async def test_create_shortlink(client, mock_redis, auth_token):
    """测试创建短链。

    使用认证 token 向短链创建接口发送请求，
    验证返回结果包含短码和原始 URL。
    """
    original_url = "https://www.example.com/very/long/path?param=value"

    response = await client.post(
        "/api/v1/shortlink/",
        json={"original_url": original_url},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code in (200, 201), \
        f"创建短链应返回 200 或 201，实际返回 {response.status_code}"

    data = response.json()

    # 响应使用 ResponseBase 包装: {"code": 200, "message": "success", "data": {...}}
    assert data["code"] == 200, f"ResponseBase code 应为 200，实际为 {data['code']}"
    result = data["data"]

    # 验证返回的短码不为空
    assert "short_code" in result, "返回结果中应包含 short_code 字段"
    assert result["short_code"], "短码不能为空"

    # 验证原始 URL 一致
    assert "original_url" in result, "返回结果中应包含 original_url 字段"
    assert result["original_url"] == original_url, "返回的原始 URL 应与请求一致"


@pytest.mark.asyncio
async def test_resolve_shortlink(client, mock_redis, auth_token):
    """测试短链解析。

    先创建一个短链，然后通过短码访问解析接口，
    验证返回 302 重定向到原始 URL。
    """
    original_url = "https://www.example.com/target/page"

    # 创建短链（需要认证）
    create_response = await client.post(
        "/api/v1/shortlink/",
        json={"original_url": original_url},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert create_response.status_code in (200, 201)

    create_data = create_response.json()
    short_code = create_data["data"]["short_code"]
    assert short_code, "创建短链后应返回有效的短码"

    # 解析短链（返回 302 重定向，不自动跟随）
    resolve_response = await client.get(f"/api/v1/shortlink/{short_code}")

    # 短链解析返回 302 重定向
    assert resolve_response.status_code == 302, \
        f"解析短链应返回 302 重定向，实际返回 {resolve_response.status_code}"

    # 验证重定向目标 URL
    location = resolve_response.headers.get("location", "")
    assert original_url in location or location == original_url, \
        f"重定向目标应为 {original_url}，实际为 {location}"


@pytest.mark.asyncio
async def test_shortlink_not_found(client, mock_redis):
    """测试不存在的短码。

    请求一个不存在的短码，验证返回 404 状态码。
    """
    # 使用一个不存在的短码
    nonexistent_code = "NOTEXIST"

    response = await client.get(f"/api/v1/shortlink/{nonexistent_code}")

    assert response.status_code == 404, \
        f"不存在的短码应返回 404，实际返回 {response.status_code}"

    data = response.json()

    # 异常响应格式: {"code": 404, "message": "...", "data": null}
    assert data["code"] == 404, f"错误响应 code 应为 404，实际为 {data['code']}"
    assert data["message"], "应返回错误消息"
