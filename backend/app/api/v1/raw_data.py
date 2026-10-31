from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession
from app.db.database import get_db
from app.db.models import Session
from app.core.security import assert_identity, device_auth
from app.core.wire import read_json, validate
from app.schemas.control import Identifier
from pydantic import TypeAdapter, ValidationError
from app.schemas.raw_batch import RawBatch
from app.services.raw_storage import store_raw_batch

router = APIRouter(tags=["raw data"])


@router.post("/raw-batch", status_code=status.HTTP_202_ACCEPTED)
async def receive_raw_batch(request: Request, db: DBSession = Depends(get_db), identity=Depends(device_auth)) -> dict[str, object]:
    data = await read_json(request, 65536)
    if "data_origin" not in data:
        raise HTTPException(422, "DATA_ORIGIN_REQUIRED")
    payload = validate(RawBatch, data)
    assert_identity(identity, payload.device_id, payload.data_origin.value)
    try:
        TypeAdapter(Identifier).validate_python(payload.session_id)
    except ValidationError:
        raise HTTPException(422, "SCHEMA_INVALID") from None
    session = db.get(Session, payload.session_id)
    if not session:
        raise HTTPException(404, "SESSION_NOT_FOUND")
    if (session.device_id, session.data_origin) != (identity.device_id, identity.data_origin):
        raise HTTPException(403, "IDENTITY_MISMATCH")
    if session.state not in {"RECORDING", "STOPPING"} or session.started_at is None:
        raise HTTPException(409, "SESSION_NOT_ACCEPTING")
    # Nhánh06 thay append JSONL bằng lưu bền/chống trùng và kiểm tra timeline.
    path = store_raw_batch(payload)
    return {"accepted": True, "batch_id": payload.batch_id, "stored_as": path.name}

