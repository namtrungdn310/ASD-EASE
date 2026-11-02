from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from app.db.database import get_db
from app.db.models import Session
from app.schemas.session import SessionResponse, SessionStart, SessionStop
from app.services.session_service import start_session, stop_session
from app.services.session_service import serialize
from app.core.security import operator_auth
from app.core.wire import read_json, validate

router = APIRouter(tags=["sessions"], dependencies=[Depends(operator_auth)])


@router.post("/sessions/start", response_model=SessionResponse)
async def start(request: Request, response: Response, db: DBSession = Depends(get_db)):
    payload = validate(SessionStart, await read_json(request))
    identity = request.app.state.registry.identity(payload.device_id)
    result, response.status_code = start_session(db, payload, identity, request.app.state.settings)
    return result


@router.post("/sessions/stop", response_model=SessionResponse)
async def stop(request: Request, response: Response, db: DBSession = Depends(get_db)):
    payload = validate(SessionStop, await read_json(request))
    result, response.status_code = stop_session(db, payload.session_id, request.app.state.registry, request.app.state.settings)
    return result


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(db: DBSession = Depends(get_db)):
    return [serialize(row) for row in db.scalars(select(Session).order_by(Session.requested_at.desc()))]

