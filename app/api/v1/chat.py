"""WebSocket 聊天路由

提供基于 WebSocket 的实时聊天功能，支持连接管理、消息广播和在线用户统计。

接口列表:
    - WebSocket /ws/{client_id}  WebSocket 连接
    - GET /online                获取在线用户数
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.common import ResponseBase

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器

    维护在线 WebSocket 连接池，支持连接、断开、广播和私聊消息。
    """

    def __init__(self) -> None:
        # 在线连接字典: {client_id: WebSocket}
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """接受新连接并加入连接池

        参数:
            client_id: 客户端唯一标识
            websocket: WebSocket 连接对象
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info("客户端 %s 已连接，当前在线: %d", client_id, len(self.active_connections))

        # 广播上线通知
        await self.broadcast(
            {
                "type": "system",
                "message": f"用户 {client_id} 加入了聊天",
                "online_count": len(self.active_connections),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            exclude=client_id,
        )

    def disconnect(self, client_id: str) -> None:
        """从连接池中移除断开的连接

        参数:
            client_id: 客户端唯一标识
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(
                "客户端 %s 已断开，当前在线: %d",
                client_id,
                len(self.active_connections),
            )

    async def send_personal_message(self, client_id: str, message: dict) -> None:
        """向指定客户端发送私聊消息

        参数:
            client_id: 目标客户端 ID
            message: 消息内容
        """
        websocket = self.active_connections.get(client_id)
        if websocket:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))

    async def broadcast(self, message: dict, exclude: str | None = None) -> None:
        """向所有在线客户端广播消息

        参数:
            message: 消息内容
            exclude: 排除的客户端 ID（不向其发送）
        """
        message_str = json.dumps(message, ensure_ascii=False)
        disconnected: list[str] = []

        for client_id, websocket in self.active_connections.items():
            if exclude and client_id == exclude:
                continue
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.warning("向客户端 %s 发送消息失败: %s", client_id, e)
                disconnected.append(client_id)

        # 清理已断开的连接
        for client_id in disconnected:
            self.disconnect(client_id)

    def get_online_count(self) -> int:
        """获取当前在线用户数

        返回:
            在线连接数
        """
        return len(self.active_connections)


# 全局连接管理器实例
manager = ConnectionManager()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
    """WebSocket 聊天端点

    客户端通过 WebSocket 连接后，可发送和接收实时消息。
    支持群聊广播和私聊消息。

    消息格式（客户端发送）:
        {
            "type": "chat",           # 消息类型: chat/group/private
            "content": "消息内容",
            "target": "目标用户ID"     # 仅 private 类型需要
        }

    参数:
        websocket: WebSocket 连接对象
        client_id: 客户端唯一标识
    """
    await manager.connect(client_id, websocket)

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                # 非 JSON 消息，按普通文本处理
                message = {"type": "chat", "content": data}

            msg_type = message.get("type", "chat")
            content = message.get("content", "")

            if msg_type == "private":
                # 私聊消息
                target_id = message.get("target", "")
                await manager.send_personal_message(
                    target_id,
                    {
                        "type": "private",
                        "from": client_id,
                        "content": content,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                # 发送回执给发送者
                await manager.send_personal_message(
                    client_id,
                    {
                        "type": "private_sent",
                        "to": target_id,
                        "content": content,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            else:
                # 群聊广播
                await manager.broadcast(
                    {
                        "type": "chat",
                        "from": client_id,
                        "content": content,
                        "online_count": manager.get_online_count(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    exclude=client_id,
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        # 广播下线通知
        await manager.broadcast(
            {
                "type": "system",
                "message": f"用户 {client_id} 离开了聊天",
                "online_count": manager.get_online_count(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


@router.get(
    "/online",
    response_model=ResponseBase[dict],
    summary="获取在线用户数",
)
async def get_online_count() -> ResponseBase[dict]:
    """获取当前在线用户数

    返回:
        包含在线用户数量的响应
    """
    return ResponseBase(
        data={
            "online_count": manager.get_online_count(),
            "online_users": list(manager.active_connections.keys()),
        }
    )
