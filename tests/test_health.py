"""健康检查接口测试。

测试 GET /health 端点的响应状态码和返回格式。
"""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """测试 GET /health 返回 200 状态码。

    验证健康检查端点能够正常响应，且 HTTP 状态码为 200。
    """
    response = await client.get("/health")

    assert response.status_code == 200, f"健康检查应返回 200，实际返回 {response.status_code}"


@pytest.mark.asyncio
async def test_health_response_format(client):
    """测试 GET /health 返回格式正确。

    验证健康检查端点返回的 JSON 数据包含必要的字段，
    且状态标识为正常（"ok" 或 "healthy"）。
    """
    response = await client.get("/health")

    assert response.status_code == 200

    data = response.json()

    # 兼容两种响应格式：
    # 1. 直接返回 {"status": "ok"}
    # 2. 包装在 ResponseBase 中 {"code": 200, "message": "success", "data": {"status": "ok"}}
    if "data" in data and isinstance(data["data"], dict):
        # ResponseBase 包装格式
        assert data["code"] == 200, f"ResponseBase code 应为 200，实际为 {data['code']}"
        health_data = data["data"]
        assert "status" in health_data, "健康检查数据中应包含 status 字段"
        assert health_data["status"] in ("ok", "healthy"), \
            f"健康状态应为 ok 或 healthy，实际为 {health_data['status']}"
    else:
        # 直接返回格式
        assert "status" in data, "健康检查响应中应包含 status 字段"
        assert data["status"] in ("ok", "healthy"), \
            f"健康状态应为 ok 或 healthy，实际为 {data['status']}"
