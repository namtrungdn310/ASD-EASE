from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.telemetry import Telemetry
from app.services.telemetry_service import persist_telemetry
from app.services.websocket_manager import manager

router = APIRouter(tags=["telemetry"])


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def receive_telemetry(payload: Telemetry, db: Session = Depends(get_db)) -> dict[str, bool]:
    persist_telemetry(db, payload)
    await manager.broadcast(payload.model_dump(mode="json"))
    return {"accepted": True}

