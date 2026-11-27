"""Chuẩn hóa WESAD đã kiểm checksum vào thư mục local; không train hoặc sửa firmware."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import pickle
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
from src.preprocessing.wesad import HR_CONFIG, HR_METHOD, VERSION, normalize_subject, write_json
from audit_wesad import ARCHIVE_SHA256, SUBJECTS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "ai/data/external/wesad/archives/WESAD.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "ai/data/interim/wesad/normalized-v1")
    parser.add_argument("--subjects", nargs="+", choices=SUBJECTS, default=list(SUBJECTS))
    args = parser.parse_args()
    if len(set(args.subjects)) != len(args.subjects):
        parser.error("Duplicate subjects")
    # Chỉ cho tạo mới, không xóa/ghi đè kết quả một lượt cũ hoặc thư mục dataset gốc.
    if args.output.exists():
        parser.error("Output exists; choose a new --output to preserve prior results")
    with args.archive.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != ARCHIVE_SHA256:
        raise SystemExit("Archive checksum mismatch; refusing to load pickle")
    args.output.mkdir(parents=True)
    results = []
    started = datetime.now(timezone(timedelta(hours=7))).isoformat()
    run = {"version": VERSION, "export_layout": "signals_and_labels_separate", "started_at": started, "status": "RUNNING", "archive_sha256": digest,
           "subjects_requested": args.subjects, "hr_method": HR_METHOD, "hr_config": HR_CONFIG,
           "limits": ["HR candidate not ECG-reference-validated", "No trained model or accuracy score",
                      "No stress labels used to compute HR", "No imputation or held/interpolated HR",
                      "EDA transfer to Grove ADC not validated"], "subjects": results}
    try:
        with zipfile.ZipFile(args.archive) as z:
            for subject in args.subjects:
                with z.open(f"WESAD/{subject}/{subject}.pkl") as f:
                    data = pickle.load(f, encoding="latin1")
                if data.get("subject") != subject:
                    raise ValueError("Subject identity mismatch")
                result = normalize_subject(data, args.output)
                results.append(result)
                write_json(args.output / "run.json", run)
                print(f"{subject}: HR candidate {result['hr_accepted_candidate_rows']}/{result['hr_total_rows']}; written", flush=True)
                del data
                gc.collect()
    except BaseException as error:
        run.update(status="INTERRUPTED_OR_FAILED", error_type=type(error).__name__)
        write_json(args.output / "run.json", run)
        raise
    with (args.output / "recordings.jsonl").open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps({"subject_id": result["subject"], "recording_id": result["subject"],
                                "metadata": result["metadata"]}, ensure_ascii=False) + "\n")
    run.update(status="COMPLETE", completed_at=datetime.now(timezone(timedelta(hours=7))).isoformat(),
               all_15_subjects=set(args.subjects) == set(SUBJECTS),
               hr_rows=sum(r["hr_total_rows"] for r in results),
               hr_candidate_rows=sum(r["hr_accepted_candidate_rows"] for r in results))
    write_json(args.output / "run.json", run)
    print(f"Complete: {len(results)} subjects; {args.output}")


if __name__ == "__main__":
    main()
