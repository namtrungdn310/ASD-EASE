from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Device
from app.core.security import operator_auth

router = APIRouter(tags=["devices"], dependencies=[Depends(operator_auth)])


@router.get("/devices")
def devices(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Device).order_by(Device.device_id)).all()
    by_id = {d.device_id: {"device_id": d.device_id, "last_seen_at": d.last_telemetry_at,
              "firmware_version": d.firmware_version, "data_origin": d.data_origin} for d in rows}
    # Thiết bị đã đăng ký vẫn xuất hiện trước gói đo đầu tiên. Không lộ credential.
    for identity in request.app.state.registry.entries:
        by_id.setdefault(identity.device_id, {"device_id": identity.device_id, "last_seen_at": None,
                          "firmware_version": None, "data_origin": identity.data_origin})
    return sorted(by_id.values(), key=lambda row: row["device_id"])

