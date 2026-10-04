from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from app.db.database import get_db
from app.db.models import Session
from app.schemas.session import SessionResponse, SessionStart, SessionStop
from app.services.session_service import start_session, stop_session

router = APIRouter(tags=["sessions"])


@router.post("/sessions/start", response_model=SessionResponse)
def start(request: SessionStart, db: DBSession = Depends(get_db)):
    if db.get(Session, request.session_id):
        raise HTTPException(409, "Session already exists")
    return start_session(db, request)


@router.post("/sessions/stop", response_model=SessionResponse)
def stop(request: SessionStop, db: DBSession = Depends(get_db)):
    result = stop_session(db, request.session_id)
    if result is None:
        raise HTTPException(404, "Session not found")
    return result


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(db: DBSession = Depends(get_db)):
    return db.scalars(select(Session).order_by(Session.started_at.desc())).all()

