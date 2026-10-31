from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Event
from app.schemas.event import EventResponse
from app.core.security import operator_auth

router = APIRouter(tags=["events"], dependencies=[Depends(operator_auth)])


@router.get("/events", response_model=list[EventResponse])
def events(db: Session = Depends(get_db)):
    return db.scalars(select(Event).order_by(Event.created_at.desc()).limit(100)).all()

