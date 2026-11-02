from fastapi import APIRouter, Depends, Request
from app.core.security import operator_auth

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "local-receiver", "schema_version": "1.0"}


@router.get("/health/mqtt", dependencies=[Depends(operator_auth)])
def mqtt_health(request: Request):
    return request.app.state.mqtt.status()

