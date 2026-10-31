from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Device
from app.core.security import operator_auth

router = APIRouter(tags=["devices"], dependencies=[Depends(operator_auth)])


@router.get("/devices")
def devices(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Device).order_by(Device.device_id)).all()
    return [{"device_id": d.device_id, "last_seen_at": d.last_telemetry_at, "firmware_version": d.firmware_version, "data_origin": d.data_origin} for d in rows]

