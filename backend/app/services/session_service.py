from datetime import datetime, timezone
from sqlalchemy.orm import Session as DBSession
from app.db.models import Session
from app.schemas.session import SessionStart


def start_session(db: DBSession, request: SessionStart) -> Session:
    session = Session(**request.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def stop_session(db: DBSession, session_id: str) -> Session | None:
    session = db.get(Session, session_id)
    if session:
        session.stopped_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
    return session

