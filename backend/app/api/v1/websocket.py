from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager
from app.core.security import operator_allowed

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/live")
async def live(websocket: WebSocket) -> None:
    if not operator_allowed(websocket):
        await websocket.close(code=1008)
        return
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping" and not await manager.heartbeat(websocket):
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

