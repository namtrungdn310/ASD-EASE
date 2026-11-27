"""Kiểm kê WESAD gốc; không sửa tín hiệu, tạo feature hoặc huấn luyện."""

from __future__ import annotations

import argparse
import gc
import hashlib
import io
import json
import pickle
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA256 = "5e15d2606adf16d819ba535c1786d92e94bae5ff5392f7ae01fb63f9938fd71c"
SUBJECTS = tuple(f"S{i}" for i in range(2, 18) if i != 12)
RATES = {"ACC": 32, "BVP": 64, "EDA": 4, "TEMP": 4}
LABEL_RATE = 700
LABEL_NAMES = {0: "transient", 1: "baseline", 2: "stress", 3: "amusement",
               4: "meditation", 5: "ignore_5", 6: "ignore_6", 7: "ignore_7"}


def label_intervals(labels: np.ndarray) -> list[dict]:
    """Giữ khoảng nhãn nửa mở, không nội suy mã hoặc trộn ranh giới task."""
    labels = np.asarray(labels)
    if labels.ndim != 1 or not len(labels) or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("Labels must be a nonempty 1-D integer array")
    if not set(np.unique(labels).tolist()).issubset(LABEL_NAMES):
        raise ValueError("Unexpected WESAD label code")
    edges = np.r_[0, np.flatnonzero(labels[1:] != labels[:-1]) + 1, len(labels)]
    return [{"start_index": int(a), "end_index": int(b),
             "start_ms": float(a * 1000 / LABEL_RATE),
             "end_ms": float(b * 1000 / LABEL_RATE),
             "source_label_code": int(labels[a])}
            for a, b in zip(edges[:-1], edges[1:])]


def signal_stats(values: np.ndarray, columns: int, rate: int) -> dict:
    a = np.asarray(values)
    if a.ndim != 2 or a.shape[1] != columns or not len(a):
        raise ValueError(f"Expected nonempty (N, {columns}) signal, got {a.shape}")
    if not np.issubdtype(a.dtype, np.number) or np.issubdtype(a.dtype, np.complexfloating):
        raise ValueError("Signal must contain real numbers")
    finite = np.isfinite(a)
    stats = []
    for c in range(columns):
        v = a[finite[:, c], c]
        stats.append({"finite_count": int(len(v)), "nonfinite_count": int(len(a) - len(v)),
                      "min": float(v.min()) if len(v) else None,
                      "max": float(v.max()) if len(v) else None,
                      "median": float(np.median(v)) if len(v) else None,
                      "std": float(v.std()) if len(v) else None,
                      "zero_count": int(np.count_nonzero(v == 0))})
    return {"shape": list(a.shape), "dtype": str(a.dtype), "nominal_rate_hz": rate,
            "implied_duration_seconds": len(a) / rate, "columns": stats,
            "timing": "reconstructed_from_nominal_rate_not_measured_timestamps"}


def find_raw_match(raw: np.ndarray, synced: np.ndarray, length: int = 128) -> int | None:
    """Đối chiếu chuỗi ACC thô để xác minh scale của .pkl, không đoán từ biên độ."""
    if len(synced) < length:
        raise ValueError("Too few samples for unit comparison")
    for start in np.flatnonzero(np.all(raw == synced[0], axis=1)):
        if start + length <= len(raw) and np.array_equal(raw[start:start + length], synced[:length]):
            return int(start)
    return None


def inspect_subject(z: zipfile.ZipFile, subject: str) -> dict:
    base = f"WESAD/{subject}/{subject}"
    # Chỉ gọi sau khi hash toàn archive đã khớp bản gốc được kiểm tra.
    with z.open(base + ".pkl") as f:
        data = pickle.load(f, encoding="latin1")
    if data.get("subject") != subject or set(data.get("signal", {}).get("wrist", {})) != set(RATES):
        raise ValueError(f"Unexpected subject or wrist channels: {subject}")
    wrist = data["signal"]["wrist"]
    labels = np.asarray(data["label"])
    intervals = label_intervals(labels)
    duration = len(labels) / LABEL_RATE
    channels = {name: signal_stats(wrist[name], 3 if name == "ACC" else 1, rate)
                for name, rate in RATES.items()}
    codes, counts = np.unique(labels, return_counts=True)
    histogram = {str(int(c)): {"name": LABEL_NAMES[int(c)], "samples": int(n),
                              "seconds": int(n) / LABEL_RATE} for c, n in zip(codes, counts)}
    with zipfile.ZipFile(io.BytesIO(z.read(base + "_E4_Data.zip"))) as raw_zip:
        with raw_zip.open("ACC.csv") as f:
            f.readline()  # UTC gốc: không ghép trực tiếp với thời gian nhãn.
            header_rate = [float(x) for x in f.readline().decode().strip().split(",")]
            if header_rate != [32.0, 32.0, 32.0]:
                raise ValueError(f"Unexpected raw ACC rate: {header_rate}")
            raw_acc = np.loadtxt(f, delimiter=",")
        match = find_raw_match(raw_acc, wrist["ACC"])
    issues = []
    if match is None:
        issues.append("ACC_RAW_SCALE_NOT_CONFIRMED")
    for name, stats in channels.items():
        if abs(stats["implied_duration_seconds"] - duration) > 1 / RATES[name] + 1 / LABEL_RATE:
            issues.append(f"{name}_DURATION_MISMATCH")
        if any(c["nonfinite_count"] for c in stats["columns"]):
            issues.append(f"{name}_NONFINITE_VALUES")
        if any(c["std"] == 0 for c in stats["columns"]):
            issues.append(f"{name}_CONSTANT_CHANNEL")
    acc = wrist["ACC"]
    norm = np.linalg.norm(acc / 64, axis=1)
    channels["ACC"].update({"raw_unit": "1/64 g" if match is not None else "UNCONFIRMED",
                            "raw_prefix_match_rows": 128 if match is not None else 0,
                            "raw_match_start_index": match,
                            "conversion_to_ms2": "value / 64 * 9.80665" if match is not None else None,
                            "median_norm_g": float(np.median(norm)),
                            "rail_sample_rows": int(np.count_nonzero(np.any((acc <= -128) | (acc >= 127), axis=1)))})
    channels["EDA"].update({"unit": "microsiemens", "negative_sample_count": int(np.count_nonzero(wrist["EDA"] < 0))})
    channels["BVP"]["unit"] = "source_arbitrary_units_not_MAX30102_RED_IR_counts"
    channels["TEMP"]["unit"] = "degC_not_in_first_model"
    result = {"subject": subject, "duration_seconds": duration, "channels": channels,
              "labels": histogram, "label_intervals": intervals,
              "binary_seconds": {"NON_STRESS": sum(histogram.get(str(k), {}).get("seconds", 0) for k in (1, 3)),
                                 "STRESS": histogram.get("2", {}).get("seconds", 0)},
              "hr_present_in_synced": "HR" in wrist, "issues": issues}
    del data, wrist, labels, acc, norm, raw_acc
    gc.collect()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "ai/data/external/wesad/archives/WESAD.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "ai/data/interim/wesad/audit-v1.json")
    parser.add_argument("--subjects", nargs="+", choices=SUBJECTS, default=list(SUBJECTS))
    args = parser.parse_args()
    if len(set(args.subjects)) != len(args.subjects):
        parser.error("Duplicate subjects are not allowed")
    with args.archive.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != ARCHIVE_SHA256:
        raise SystemExit("Archive checksum mismatch; refusing to load pickle")
    records = []
    with zipfile.ZipFile(args.archive) as z:
        for subject in args.subjects:
            record = inspect_subject(z, subject)
            records.append(record)
            print(f"{subject}: {record['duration_seconds']:.1f}s; issues={record['issues']}", flush=True)
    totals = {str(k): sum(r["labels"].get(str(k), {}).get("seconds", 0) for r in records) for k in LABEL_NAMES}
    report = {"audit_version": "wesad-audit-v1", "verified_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
              "archive_sha256": digest, "label_mapping": "wesad-binary-v1", "subject_count": len(records),
              "all_15_subjects": set(args.subjects) == set(SUBJECTS),
              "total_duration_seconds": sum(r["duration_seconds"] for r in records),
              "label_seconds": totals, "subjects": records,
              "limits": ["Finite values do not prove physiological quality or no packet loss",
                         "No measured per-sample timestamps in synchronized arrays",
                         "No HR computed, no windows/features/model or train/test scores produced"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Report: {args.output}; total_seconds={report['total_duration_seconds']:.1f}")
    if any(r["issues"] for r in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
