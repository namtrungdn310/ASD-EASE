from fastapi import WebSocket
import asyncio
from collections.abc import Awaitable


class WebSocketManager:
    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def _send(self, websocket: WebSocket, message: Awaitable[None]) -> bool:
        try:
            await asyncio.wait_for(message, timeout=2)
            return True
        except Exception:
            # Bỏ khỏi danh sách thôi có thể để browser mắc kẹt ở trạng thái OPEN.
            self.disconnect(websocket)
            try:
                await asyncio.wait_for(websocket.close(code=1011), timeout=1)
            except Exception:
                pass
            return False

    async def heartbeat(self, websocket: WebSocket) -> bool:
        return await self._send(websocket, websocket.send_text("pong"))

    async def broadcast(self, payload: dict) -> None:
        for connection in tuple(self.connections):
            await self._send(connection, connection.send_json(payload))


manager = WebSocketManager()

