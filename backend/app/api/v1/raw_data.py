from fastapi import APIRouter, status
from app.schemas.raw_batch import RawBatch
from app.services.raw_storage import store_raw_batch

router = APIRouter(tags=["raw data"])


@router.post("/raw-batch", status_code=status.HTTP_202_ACCEPTED)
def receive_raw_batch(payload: RawBatch) -> dict[str, object]:
    path = store_raw_batch(payload)
    return {"accepted": True, "batch_id": payload.batch_id, "stored_as": path.name}

