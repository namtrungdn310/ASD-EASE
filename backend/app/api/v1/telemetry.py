from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.ingestion import InboundTelemetry
from app.core.security import device_auth
from app.core.wire import read_json, validate
from app.services.telemetry_service import receive_telemetry as ingest

router = APIRouter(tags=["telemetry"])


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def receive_telemetry(request: Request, db: Session = Depends(get_db), identity=Depends(device_auth)):
    if identity.transport != "http":
        raise HTTPException(403, "TRANSPORT_MISMATCH")
    payload = validate(InboundTelemetry, await read_json(request))
    return await ingest(db, payload, identity, request.app.state.mqtt)

