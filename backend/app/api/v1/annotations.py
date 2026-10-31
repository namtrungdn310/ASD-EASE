from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Annotation, Session as RecordingSession
from app.schemas.annotation import AnnotationCreate
from app.core.security import operator_auth

router = APIRouter(tags=["annotations"], dependencies=[Depends(operator_auth)])


@router.post("/annotations", status_code=status.HTTP_201_CREATED)
def create_annotation(payload: AnnotationCreate, db: Session = Depends(get_db)) -> dict[str, int]:
    if db.get(RecordingSession, payload.session_id) is None:
        raise HTTPException(404, "SESSION_NOT_FOUND")
    row = Annotation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}

