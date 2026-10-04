import json
from pathlib import Path
from app.core.config import get_settings
from app.schemas.raw_batch import RawBatch


def store_raw_batch(batch: RawBatch) -> Path:
    root = Path(get_settings().raw_storage_dir)
    target = root / batch.session_id
    target.mkdir(parents=True, exist_ok=True)
    path = target / "raw_batches.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(batch.model_dump(mode="json"), separators=(",", ":")) + "\n")
    return path

