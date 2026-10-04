from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Annotation
from app.schemas.annotation import AnnotationCreate

router = APIRouter(tags=["annotations"])


@router.post("/annotations", status_code=status.HTTP_201_CREATED)
def create_annotation(payload: AnnotationCreate, db: Session = Depends(get_db)) -> dict[str, int]:
    row = Annotation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}

