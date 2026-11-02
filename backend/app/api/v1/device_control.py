"""HTTP tương thích cho simulator; thiết bị MQTT không dùng các đường này."""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.security import assert_identity, device_auth
from app.core.wire import read_json, validate
from app.schemas.control import Ack, StateRequest

router = APIRouter(tags=["HTTP simulator control"])


@router.post("/devices/sync")
async def synchronize(request: Request, identity=Depends(device_auth)):
    if identity.transport != "http":
        raise HTTPException(403, "TRANSPORT_MISMATCH")
    payload = validate(StateRequest, await read_json(request))
    assert_identity(identity, payload.device_id, payload.data_origin)
    return request.app.state.mqtt.sync(identity, payload)


@router.post("/devices/ack")
async def acknowledge(request: Request, identity=Depends(device_auth)):
    if identity.transport != "http":
        raise HTTPException(403, "TRANSPORT_MISMATCH")
    payload = validate(Ack, await read_json(request))
    assert_identity(identity, payload.device_id, payload.data_origin)
    request.app.state.mqtt.ack(identity, payload)
    return {"accepted": True}
