from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Event
from app.schemas.event import EventResponse
from app.core.security import operator_auth

router = APIRouter(tags=["events"], dependencies=[Depends(operator_auth)])


@router.get("/events", response_model=list[EventResponse])
def events(device_id: str | None = None, attention_only: bool = False, db: Session = Depends(get_db)):
    query = select(Event)
    if device_id is not None:
        query = query.where(Event.device_id == device_id)
    if attention_only:
        query = query.where(Event.state == "ATTENTION", Event.probability.is_not(None))
    return db.scalars(query.order_by(Event.created_at.desc(), Event.id.desc()).limit(100)).all()


@router.get("/reports/ai")
def ai_report(device_id: str, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
              db: Session = Depends(get_db)):
    query = (select(Event).where(Event.device_id == device_id, Event.state == "ATTENTION",
                                Event.probability.between(0, 1))
             .order_by(Event.created_at.desc(), Event.id.desc()).execution_options(yield_per=500))
    items = []
    total = 0
    group = None
    previous = None

    def finish():
        nonlocal total
        if group is None:
            return
        if (page - 1) * page_size <= total < page * page_size:
            items.append(group)
        total += 1

    for row in db.scalars(query):
        continuation = (previous is not None and row.session_id == previous.session_id
                        and 0 <= (previous.created_at - row.created_at).total_seconds() <= 5
                        and 0 <= previous.timestamp_ms - row.timestamp_ms <= 5000)
        if continuation:
            group["created_at"] = row.created_at
            group["timestamp_ms"] = row.timestamp_ms
            group["probability"] = max(group["probability"], row.probability)
            group["record_count"] += 1
        else:
            finish()
            group = {"id": row.id, "device_id": row.device_id, "session_id": row.session_id,
                     "state": "ATTENTION", "probability": row.probability, "timestamp_ms": row.timestamp_ms,
                     "created_at": row.created_at, "ended_at": row.created_at, "record_count": 1,
                     "reason": None}
        previous = row
    finish()
    return {"items": items, "page": page, "page_size": page_size, "total": total}

