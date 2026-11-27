"""Trích xuất tập feature 60s cho bài toán phân loại Stress trên toàn bộ 15 đối tượng WESAD.

Kết hợp đa cảm biến: EDA (14 đặc trưng), ACC (13 đặc trưng), HR MSPTD Gated + Validity (9 đặc trưng).
Hoàn toàn nhân quả, không dùng dữ liệu tương lai, giữ nguyên nhãn tinh khiết.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))

from src.feature_extraction.stress_features import (
    DEFAULT_FEATURE_CONFIG,
    extract_window_features,
)
from src.preprocessing.wesad import write_csv, write_json
from audit_wesad import ARCHIVE_SHA256, SUBJECTS


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_float_column(rows: list[dict], column: str) -> np.ndarray:
    return np.array(
        [float(r[column]) if r[column] != "" else np.nan for r in rows],
        dtype=float,
    )


def find_pure_label_windows(
    label_rows: list[dict],
    total_ms: int,
    window_ms: int,
    step_ms: int,
) -> list[tuple[int, int, str, int]]:
    """Tìm các cửa sổ [start_ms, end_ms) nằm trọn vẹn trong một khoảng nhãn (1, 2 hoặc 3)."""
    intervals = []
    for r in label_rows:
        code = str(r["source_label_code"])
        if code in ("1", "2", "3"):
            intervals.append((int(float(r["start_ms"])), int(float(r["end_ms"])), code))

    windows = []
    for start in range(0, total_ms - window_ms + 1, step_ms):
        end = start + window_ms
        # Kiểm tra xem [start, end) có nằm hoàn toàn bên trong 1 khoảng nhãn đơn lẻ không
        matched = [
            code for s, e, code in intervals if s <= start and end <= e
        ]
        if len(matched) == 1:
            code = matched[0]
            # 1 (baseline) và 3 (amusement) -> 0; 2 (stress) -> 1
            binary_label = 1 if code == "2" else 0
            windows.append((start, end, code, binary_label))

    return windows


def extract_subject_features(
    subject: str,
    norm_dir: Path,
    hr_dir: Path,
    config: dict,
) -> list[dict]:
    # Đọc nhãn
    label_rows = read_csv_rows(norm_dir / "labels.csv")
    total_ms = int(float(label_rows[-1]["end_ms"]))
    window_ms = int(config["window_seconds"] * 1000)
    step_ms = int(config["step_seconds"] * 1000)

    windows = find_pure_label_windows(label_rows, total_ms, window_ms, step_ms)
    if not windows:
        return []

    # Đọc tín hiệu
    eda = parse_float_column(read_csv_rows(norm_dir / "eda_us.csv"), "value")
    acc_norm = parse_float_column(read_csv_rows(norm_dir / "acc_norm_ms2.csv"), "value")
    acc_x = parse_float_column(read_csv_rows(norm_dir / "acc_x_ms2.csv"), "value")
    acc_y = parse_float_column(read_csv_rows(norm_dir / "acc_y_ms2.csv"), "value")
    acc_z = parse_float_column(read_csv_rows(norm_dir / "acc_z_ms2.csv"), "value")

    # Đọc HR từ MSPTD Gated
    comp_rows = read_csv_rows(hr_dir / "comparison_published.csv")
    # Lập bản đồ time_ms -> msptd_gated_bpm
    hr_map = {}
    for r in comp_rows:
        t = int(r["time_ms"])
        val = float(r["msptd_gated_bpm"]) if r["msptd_gated_bpm"] != "" else np.nan
        hr_map[t] = val

    # Tính median HR của đối tượng từ các cửa sổ baseline có HR hợp lệ để làm fallback an toàn
    baseline_hrs = [
        val for r in comp_rows
        if str(r["source_label_code"]) == "1" and r["msptd_gated_bpm"] != ""
        for val in [float(r["msptd_gated_bpm"])]
    ]
    subj_median_hr = float(np.median(baseline_hrs)) if baseline_hrs else 75.0

    fs_eda = config["eda_fs"]
    fs_acc = config["acc_fs"]

    extracted_rows = []
    for start_ms, end_ms, code, target_label in windows:
        # Cắt EDA (4 Hz)
        e_start = int(start_ms * fs_eda // 1000)
        e_end = int(end_ms * fs_eda // 1000)
        eda_chunk = eda[e_start:e_end]

        # Cắt ACC (32 Hz)
        a_start = int(start_ms * fs_acc // 1000)
        a_end = int(end_ms * fs_acc // 1000)
        acc_norm_chunk = acc_norm[a_start:a_end]
        acc_x_chunk = acc_x[a_start:a_end]
        acc_y_chunk = acc_y[a_start:a_end]
        acc_z_chunk = acc_z[a_start:a_end]

        # Cắt HR (mỗi giây một mẫu, từ start_ms + 1000 đến end_ms)
        hr_chunk = np.array(
            [hr_map.get(t, np.nan) for t in range(start_ms + 1000, end_ms + 1, 1000)],
            dtype=float,
        )

        feats = extract_window_features(
            eda_chunk=eda_chunk,
            acc_x_chunk=acc_x_chunk,
            acc_y_chunk=acc_y_chunk,
            acc_z_chunk=acc_z_chunk,
            acc_norm_chunk=acc_norm_chunk,
            hr_bpm_chunk=hr_chunk,
            config=config,
            subject_median_hr=subj_median_hr,
        )

        row = {
            "subject_id": subject,
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
            "source_label_code": code,
            "label": target_label,
            **feats,
        }
        extracted_rows.append(row)

    return extracted_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized", type=Path, default=ROOT / "ai/data/interim/wesad/normalized-v1")
    parser.add_argument("--hr_review", type=Path, default=ROOT / "ai/data/interim/wesad/hr-published-review-v1")
    parser.add_argument("--output", type=Path, default=ROOT / "ai/data/processed/wesad/features-v1")
    parser.add_argument("--subjects", choices=SUBJECTS, nargs="+", default=list(SUBJECTS))
    parser.add_argument("--window_seconds", type=int, default=60)
    parser.add_argument("--step_seconds", type=int, default=10)
    args = parser.parse_args()

    if args.output.exists():
        parser.error(f"Output directory {args.output} already exists; choose a new path.")

    config = {
        **DEFAULT_FEATURE_CONFIG,
        "window_seconds": args.window_seconds,
        "step_seconds": args.step_seconds,
    }

    args.output.mkdir(parents=True)
    started = datetime.now(timezone(timedelta(hours=7))).isoformat()

    all_subject_rows = []
    subject_stats = {}

    for subject in args.subjects:
        print(f"Extracting features for subject {subject}...", flush=True)
        norm_subj = args.normalized / "signals" / subject
        hr_subj = args.hr_review / subject

        rows = extract_subject_features(subject, norm_subj, hr_subj, config)
        if not rows:
            print(f"Warning: Subject {subject} produced 0 windows!")
            continue

        subj_target = args.output / subject
        subj_target.mkdir(parents=True)
        write_csv(subj_target / "features.csv", list(rows[0].keys()), (r.values() for r in rows))

        stress_count = sum(r["label"] == 1 for r in rows)
        non_stress_count = sum(r["label"] == 0 for r in rows)
        subject_stats[subject] = {
            "total_windows": len(rows),
            "stress_windows": stress_count,
            "non_stress_windows": non_stress_count,
            "stress_ratio": float(stress_count / len(rows)),
        }
        print(f"  {subject}: {len(rows)} windows (Non-stress: {non_stress_count}, Stress: {stress_count})")

        all_subject_rows.extend(rows)
        gc.collect()

    # Lưu tập dataset gộp toàn bộ
    print("Writing combined dataset...", flush=True)
    write_csv(
        args.output / "dataset.csv",
        list(all_subject_rows[0].keys()),
        (r.values() for r in all_subject_rows),
    )

    total_windows = len(all_subject_rows)
    total_stress = sum(r["label"] == 1 for r in all_subject_rows)
    total_non_stress = sum(r["label"] == 0 for r in all_subject_rows)

    feature_names = [
        k for k in all_subject_rows[0].keys()
        if k not in ("subject_id", "window_start_ms", "window_end_ms", "source_label_code", "label")
    ]

    report = {
        "version": "wesad-features-v1",
        "status": "COMPLETE",
        "started_at": started,
        "completed_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "config": config,
        "total_windows": total_windows,
        "total_stress_windows": total_stress,
        "total_non_stress_windows": total_non_stress,
        "stress_prevalence": float(total_stress / total_windows) if total_windows else 0.0,
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "subject_statistics": subject_stats,
    }
    write_json(args.output / "report.json", report)
    print(f"Feature extraction complete! Total windows: {total_windows}. Output: {args.output}")


if __name__ == "__main__":
    main()
