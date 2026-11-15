"""Kết nối lỗi phải đóng rõ; heartbeat không cần có dữ liệu cảm biến."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from starlette.websockets import WebSocketDisconnect
from app.services.websocket_manager import WebSocketManager


def test_failed_subscriber_is_closed_and_other_subscribers_keep_receiving():
    async def run():
        manager = WebSocketManager()
        failed = SimpleNamespace(send_json=AsyncMock(side_effect=OSError("closed transport")), close=AsyncMock())
        healthy = SimpleNamespace(send_json=AsyncMock(), close=AsyncMock())
        manager.connections = [failed, healthy]
        frame = {"test": "synthetic transport fixture"}
        await manager.broadcast(frame)
        failed.close.assert_awaited_once()
        healthy.send_json.assert_awaited_once_with(frame)
        assert manager.connections == [healthy]
    asyncio.run(run())


def test_authenticated_websocket_answers_ping_without_telemetry(monkeypatch):
    import app.api.v1.websocket as endpoint
    monkeypatch.setattr(endpoint, "operator_allowed", lambda connection: True)
    socket = SimpleNamespace(accept=AsyncMock(), close=AsyncMock(), send_text=AsyncMock(),
                             receive_text=AsyncMock(side_effect=["ping", WebSocketDisconnect(1000)]))
    asyncio.run(endpoint.live(socket))
    socket.send_text.assert_awaited_once_with("pong")
    assert socket not in endpoint.manager.connections
