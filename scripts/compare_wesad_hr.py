"""So HR WESAD đã chuẩn hóa với XQRS ECG offline, không tune hoặc train model."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.metadata
import json
import pickle
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
from src.evaluation.wesad_hr import REFERENCE_CONFIG, REFERENCE_METHOD, compare_rows, detect_ecg, summarize
from src.preprocessing.wesad import write_csv, write_json
from audit_wesad import ARCHIVE_SHA256, SUBJECTS


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "ai/data/external/wesad/archives/WESAD.zip")
    parser.add_argument("--normalized", type=Path, default=ROOT / "ai/data/interim/wesad/normalized-v1")
    parser.add_argument("--output", type=Path, default=ROOT / "ai/data/interim/wesad/hr-ecg-review-v1")
    parser.add_argument("--subjects", choices=SUBJECTS, nargs="+", default=list(SUBJECTS))
    args = parser.parse_args()
    if args.output.exists() or len(set(args.subjects)) != len(args.subjects):
        parser.error("Output must be new and subjects must be unique")
    if importlib.metadata.version("wfdb") != "4.2.0":
        parser.error("Install ai/requirements-notebooks.txt (WFDB 4.2.0)")
    with args.archive.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    source_run = json.loads((args.normalized / "run.json").read_text(encoding="utf-8"))
    if digest != ARCHIVE_SHA256 or source_run["status"] != "COMPLETE" or source_run["archive_sha256"] != digest:
        parser.error("Archive/normalization provenance mismatch")
    args.output.mkdir(parents=True)
    report = {"version": "wesad-hr-ecg-comparison-v1", "status": "RUNNING",
              "started_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
              "archive_sha256": digest, "ppg_method": source_run["hr_method"],
              "ppg_config": source_run["hr_config"], "reference_method": REFERENCE_METHOD,
              "reference_config": REFERENCE_CONFIG, "subject_summaries": [],
              "limits": ["ECG reference is automatic, not expert-annotated ground truth",
                         "XQRS is offline/noncausal and never a model input",
                         "Overlapping windows are correlated; no clinical accuracy claim",
                         "No PPG threshold changes, per-person lag tuning, model training or firmware change"],
              "versions": {n: importlib.metadata.version(n) for n in ("numpy", "scipy", "wfdb")}}
    all_rows = []
    try:
        with zipfile.ZipFile(args.archive) as z:
            for subject in args.subjects:
                source = args.normalized / "signals" / subject
                meta = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
                for name in ("hr_bpm.csv", "hr_window_labels.csv", "labels.csv"):
                    with (source / name).open("rb") as f:
                        if hashlib.file_digest(f, "sha256").hexdigest() != meta["output_sha256"][name]:
                            raise ValueError(f"Normalized CSV checksum mismatch: {subject}/{name}")
                with z.open(f"WESAD/{subject}/{subject}.pkl") as f:
                    data = pickle.load(f, encoding="latin1")
                ecg = np.asarray(data["signal"]["chest"]["ECG"], dtype=float)[:, 0]
                if data["subject"] != subject or len(ecg) != len(data["label"]):
                    raise ValueError("ECG identity/timeline mismatch")
                peaks, runs = detect_ecg(ecg)
                hr = read_rows(source / "hr_bpm.csv")
                labels = read_rows(source / "hr_window_labels.csv")
                compared = compare_rows(hr, labels, ecg, peaks, runs)
                target = args.output / subject
                target.mkdir()
                write_csv(target / "comparison.csv", ["subject", *compared[0]],
                          ([subject, *r.values()] for r in compared))
                write_csv(target / "ecg_qrs.csv", ["sample_index_700hz", "time_ms"],
                          ((int(p), float(p * 1000 / 700)) for p in peaks))
                # Các đoạn xem cố định: 30 s sau đầu khoảng baseline/stress/amusement.
                # Không chọn đoạn theo sai số hoặc tối đa độ khớp.
                snippets = {}
                for code in (1, 2, 3):
                    interval = next((r for r in read_rows(source / "labels.csv")
                                     if r["source_label_code"] == str(code) and float(r["end_ms"]) - float(r["start_ms"]) >= 40000), None)
                    if interval is None:
                        continue
                    start_ms = int(float(interval["start_ms"])) + 30000
                    a = start_ms * 700 // 1000
                    b = a + 5 * 700
                    snippets[f"label{code}_ecg"] = ecg[a:b]
                    snippets[f"label{code}_qrs"] = (peaks[(peaks >= a) & (peaks < b)] - a) / 700
                    start_bvp = start_ms * 64 // 1000
                    snippets[f"label{code}_bvp"] = data["signal"]["wrist"]["BVP"][start_bvp:start_bvp + 5 * 64, 0]
                    snippets[f"label{code}_start_ms"] = np.array(start_ms)
                np.savez_compressed(target / "review_snippets.npz", **snippets)
                stats = {"subject": subject, "ecg_qrs_count": len(peaks), "ecg_runs": runs, **summarize(compared)}
                write_json(target / "summary.json", stats)
                report["subject_summaries"].append(stats)
                all_rows.extend({"subject": subject, **r} for r in compared)
                write_json(args.output / "report.json", report)
                print(f"{subject}: QRS={len(peaks)}, paired={stats['binary_task']['paired_windows']}, MAE={stats['binary_task']['mae_bpm']}", flush=True)
                del data, ecg, peaks, snippets, compared
                gc.collect()
    except BaseException as error:
        report.update(status="INTERRUPTED_OR_FAILED", error_type=type(error).__name__)
        write_json(args.output / "report.json", report)
        raise
    subject_mae = [r["binary_task"]["mae_bpm"] for r in report["subject_summaries"]
                   if r["binary_task"]["mae_bpm"] is not None]
    report.update(status="COMPLETE", all_15_subjects=set(args.subjects) == set(SUBJECTS),
                  pooled=summarize(all_rows), macro_subject_mae_bpm=float(np.mean(subject_mae)) if subject_mae else None,
                  completed_at=datetime.now(timezone(timedelta(hours=7))).isoformat())
    write_json(args.output / "report.json", report)
    print(f"Complete: {len(args.subjects)} subjects; {args.output}")


if __name__ == "__main__":
    main()
