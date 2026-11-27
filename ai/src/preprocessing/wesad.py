"""Chuẩn hóa WESAD cổ tay; HR baseline thử nghiệm, không thay HR firmware."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import scipy
from scipy.signal import butter, find_peaks, sosfilt, sosfilt_zi

VERSION = "wesad-normalization-v1"
HR_METHOD = "bvp-causal-peaks-v1-experimental"
RATES = {"BVP": 64, "EDA": 4, "ACC": 32, "TEMP": 4}
HR_CONFIG = {"window_seconds": 10, "hop_seconds": 1, "filter_warmup_seconds": 2,
             "band_hz": [0.5, 5.0], "butter_prototype_order": 2,
             "min_bpm": 40, "max_bpm": 200, "prominence_std_factor": 0.5,
             "max_rr_cv": 0.30, "min_periodicity": 0.25, "min_intervals": 3}
LABEL_NAMES = {0: "transient", 1: "baseline", 2: "stress", 3: "amusement",
               4: "meditation", 5: "ignore_5", 6: "ignore_6", 7: "ignore_7"}


def ranges(mask: np.ndarray) -> list[tuple[int, int]]:
    """Các khoảng True nửa mở, giữ nguyên gap thay vì dồn mẫu."""
    mask = np.asarray(mask, dtype=bool)
    edges = np.diff(np.r_[False, mask, False].astype(np.int8))
    return list(zip(np.flatnonzero(edges == 1).tolist(), np.flatnonzero(edges == -1).tolist()))


def normalize_wrist(data: dict) -> dict:
    wrist = data["signal"]["wrist"]
    if set(wrist) != set(RATES):
        raise ValueError("Unexpected wrist channels")
    arrays = {}
    for name, rate in RATES.items():
        a = np.asarray(wrist[name], dtype=float)
        if a.ndim != 2 or a.shape[1] != (3 if name == "ACC" else 1) or not len(a):
            raise ValueError(f"Unexpected {name} shape: {a.shape}")
        arrays[name] = a
    labels = np.asarray(data["label"])
    if labels.ndim != 1 or not len(labels) or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("Expected 1-D integer labels")
    if not set(np.unique(labels).tolist()).issubset(LABEL_NAMES):
        raise ValueError("Unknown source label")
    duration = len(labels) / 700
    for name, a in arrays.items():
        if abs(len(a) / RATES[name] - duration) > 1 / RATES[name] + 1 / 700:
            raise ValueError(f"{name} timeline does not match labels")
    acc = arrays["ACC"] / 64 * 9.80665
    acc[~np.isfinite(acc)] = np.nan
    signals = {"bvp": arrays["BVP"][:, 0].copy(), "eda_us": arrays["EDA"][:, 0].copy(),
               **{f"acc_{axis}_ms2": acc[:, i] for i, axis in enumerate("xyz")},
               "acc_norm_ms2": np.linalg.norm(acc, axis=1)}
    for values in signals.values():
        values[~np.isfinite(values)] = np.nan
    return {"signals": signals, "labels": labels, "duration_seconds": duration,
            "acc_rail": np.any((arrays["ACC"] <= -128) | (arrays["ACC"] >= 127), axis=1)}


def label_rows(labels: np.ndarray) -> list[dict]:
    boundaries = np.r_[0, np.flatnonzero(labels[1:] != labels[:-1]) + 1, len(labels)]
    return [{"start_label_index": int(a), "end_label_index": int(b),
             "start_ms": float(a * 1000 / 700), "end_ms": float(b * 1000 / 700),
             "source_label_code": int(labels[a]), "source_label_name": LABEL_NAMES[int(labels[a])],
             "target_label": binary_label(int(labels[a]))}
            for a, b in zip(boundaries[:-1], boundaries[1:])]


def binary_label(code: int) -> int | None:
    return 1 if code == 2 else 0 if code in (1, 3) else None


def annotate_window(labels: np.ndarray, start_ms: int, end_ms: int) -> tuple[int | None, int | None]:
    """Chỉ gắn nhãn khi toàn bộ cửa sổ cùng một mã; không lấy đa số nhãn."""
    start = (int(start_ms) * 700 + 999) // 1000
    end = (int(end_ms) * 700 + 999) // 1000
    if start < 0 or end > len(labels) or end <= start:
        return None, None
    chunk = labels[start:end]
    code = int(chunk[0])
    return (code, binary_label(code)) if np.all(chunk == code) else (None, None)


def hr_candidate(window: np.ndarray, fs: int = 64) -> dict:
    """Nhận BVP đã lọc từ quá khứ; không dùng nhãn hoặc HR mong muốn."""
    y = np.asarray(window, dtype=float)
    result = {"value": None, "candidate_bpm": None, "reason": "INSUFFICIENT_SAMPLES",
              "peak_count": 0, "rr_cv": None, "periodicity": None}
    if y.ndim != 1 or len(y) < int(HR_CONFIG["window_seconds"] * fs):
        return result
    if not np.isfinite(y).all():
        result["reason"] = "NONFINITE"
        return result
    y = y - np.mean(y)
    std = float(np.std(y))
    if std <= 1e-8:
        result["reason"] = "FLAT_SIGNAL"
        return result
    peaks, _ = find_peaks(y, distance=int(np.ceil(fs * 60 / HR_CONFIG["max_bpm"])),
                          prominence=HR_CONFIG["prominence_std_factor"] * std)
    result["peak_count"] = len(peaks)
    intervals = np.diff(peaks) / fs
    if len(intervals) < HR_CONFIG["min_intervals"]:
        result["reason"] = "TOO_FEW_PEAKS"
        return result
    bpm = float(60 / np.median(intervals))
    cv = float(np.std(intervals) / np.mean(intervals))
    lag = int(round(fs * 60 / bpm))
    x1, x2 = y[:-lag], y[lag:]
    denominator = float(np.linalg.norm(x1) * np.linalg.norm(x2))
    periodicity = float(np.dot(x1, x2) / denominator) if denominator > 0 else 0.0
    result.update(candidate_bpm=bpm, rr_cv=cv, periodicity=periodicity)
    if not HR_CONFIG["min_bpm"] <= bpm <= HR_CONFIG["max_bpm"]:
        result["reason"] = "OUTSIDE_METHOD_RANGE"
    elif np.any((intervals < 60 / HR_CONFIG["max_bpm"]) | (intervals > 60 / HR_CONFIG["min_bpm"])):
        result["reason"] = "RR_OUTSIDE_METHOD_RANGE"
    elif cv > HR_CONFIG["max_rr_cv"]:
        result["reason"] = "IRREGULAR_PEAKS"
    elif periodicity < HR_CONFIG["min_periodicity"]:
        result["reason"] = "WEAK_PERIODICITY"
    else:
        result.update(value=bpm, reason="CANDIDATE_NOT_REFERENCE_VALIDATED")
    return result


def estimate_hr(bvp: np.ndarray, fs: int = 64) -> list[dict]:
    """Lọc nhân quả, reset sau gap; cửa sổ lùi 10 s, xuất mỗi 1 s, không giữ số cũ."""
    x = np.asarray(bvp, dtype=float)
    if x.ndim != 1 or fs != 64:
        raise ValueError("This version expects WESAD BVP at 64 Hz")
    filtered = np.full(len(x), np.nan)
    run_start = np.full(len(x), -1, dtype=np.int64)
    sos = butter(HR_CONFIG["butter_prototype_order"], HR_CONFIG["band_hz"], btype="bandpass", fs=fs, output="sos")
    for start, end in ranges(np.isfinite(x)):
        filtered[start:end], _ = sosfilt(sos, x[start:end], zi=sosfilt_zi(sos) * x[start])
        run_start[start:end] = start
    width = HR_CONFIG["window_seconds"] * fs
    warmup = HR_CONFIG["filter_warmup_seconds"] * fs
    rows = []
    for end in range(fs, len(x) + 1, fs * HR_CONFIG["hop_seconds"]):
        start = end - width
        reason = "WARMUP" if start < 0 else "MISSING_OR_FILTER_WARMUP"
        candidate = {"value": None, "candidate_bpm": None, "reason": reason,
                     "peak_count": 0, "rr_cv": None, "periodicity": None}
        if start >= 0 and run_start[end - 1] >= 0 and start >= run_start[end - 1] + warmup:
            candidate = hr_candidate(filtered[start:end], fs)
        rows.append({"time_ms": end * 1000 // fs, "window_start_ms": max(0, start * 1000 // fs),
                     "window_end_ms": end * 1000 // fs, **candidate})
    return rows


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, columns: list[str], rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)


def signal_csv(path: Path, values: np.ndarray, rate: int) -> None:
    write_csv(path, ["time_ms", "value"],
              ((format(i * 1000 / rate, ".9f"), format(float(v), ".12g") if np.isfinite(v) else "")
               for i, v in enumerate(values)))


def quality_rows(normalized: dict, hr: list[dict]) -> list[dict]:
    """Thống kê kỹ thuật từng cửa sổ, không tạo % chất lượng sinh lý giả."""
    rows = []
    signals = normalized["signals"]
    for h in hr:
        start_ms, end_ms = h["window_start_ms"], h["window_end_ms"]
        eda = signals["eda_us"][(start_ms * 4 + 999) // 1000:(end_ms * 4 + 999) // 1000]
        a, b = (start_ms * 32 + 999) // 1000, (end_ms * 32 + 999) // 1000
        acc = np.column_stack([signals[f"acc_{axis}_ms2"][a:b] for axis in "xyz"])
        finite_eda = eda[np.isfinite(eda)]
        rows.append({"window_start_ms": start_ms, "window_end_ms": end_ms,
                     "full_window": int(end_ms - start_ms == 10000),
                     "eda_samples": len(eda), "eda_nonfinite": int(np.count_nonzero(~np.isfinite(eda))),
                     "eda_negative": int(np.count_nonzero(eda < 0)),
                     "eda_zero": int(np.count_nonzero(eda == 0)),
                     "eda_flat": int(len(finite_eda) > 1 and np.ptp(finite_eda) == 0),
                     "acc_samples": len(acc),
                     "acc_nonfinite_rows": int(np.count_nonzero(~np.all(np.isfinite(acc), axis=1))),
                     "acc_rail_rows": int(normalized["acc_rail"][a:b].sum())})
    return rows


def normalize_subject(data: dict, output: Path) -> dict:
    subject = data["subject"]
    normalized = normalize_wrist(data)
    target = output / "signals" / subject
    target.mkdir(parents=True, exist_ok=False)
    meta = {"dataset_id": "WESAD", "subject_id": subject, "recording_id": subject,
            "normalization_version": VERSION, "hr_method": HR_METHOD,
            "archive_member": f"WESAD/{subject}/{subject}.pkl",
            "timestamp_kind": "reconstructed_from_synchronized_nominal_rate",
            "time_origin": "author_synchronized_recording_start", "channels": {}}
    for channel, values in normalized["signals"].items():
        rate = 64 if channel == "bvp" else 4 if channel == "eda_us" else 32
        unit = "source_arbitrary_units" if channel == "bvp" else "microsiemens" if channel == "eda_us" else "m/s^2"
        path = target / f"{channel}.csv"
        signal_csv(path, values, rate)
        meta["channels"][channel] = {"file": path.relative_to(output).as_posix(), "unit": unit,
                                     "sample_rate_nominal_hz": rate, "sample_rate_measured_hz": None,
                                     "count": len(values), "missing_count": int(np.count_nonzero(~np.isfinite(values))),
                                     "includes_gravity": channel.startswith("acc_"),
                                     "processing": "raw_source" if channel in ("bvp", "eda_us") else "ACC_div64_times_9.80665",
                                     "axis_convention": "source_E4_non_dominant_wrist" if channel.startswith("acc_") else None}
    labels = label_rows(normalized["labels"])
    write_csv(target / "labels.csv", ["recording_id", *labels[0].keys(), "label_method", "label_mapping_version"],
              ([subject, *row.values(), "study_protocol", "wesad-binary-v1"] for row in labels))
    hr = estimate_hr(normalized["signals"]["bvp"])
    columns = ["time_ms", "value", "candidate_bpm", "window_start_ms", "window_end_ms", "reason", "peak_count", "rr_cv", "periodicity"]
    for row in hr:
        code, binary = annotate_window(normalized["labels"], row["window_start_ms"], row["window_end_ms"])
        row.update(source_label_code=code, target_label=binary)
    write_csv(target / "hr_bpm.csv", columns, ([row[k] for k in columns] for row in hr))
    label_columns = ["time_ms", "window_start_ms", "window_end_ms", "source_label_code", "target_label"]
    write_csv(target / "hr_window_labels.csv", label_columns,
              ([row[k] for k in label_columns] for row in hr))
    quality = quality_rows(normalized, hr)
    if not quality:
        raise ValueError("Recording too short to produce diagnostic windows")
    write_csv(target / "window_quality.csv", list(quality[0]), (row.values() for row in quality))
    accepted = [r for r in hr if r["value"] is not None]
    from collections import Counter
    stats = {"subject": subject, "duration_seconds": normalized["duration_seconds"],
             "hr_total_rows": len(hr), "hr_accepted_candidate_rows": len(accepted),
             "hr_candidate_coverage": len(accepted) / len(hr) if hr else 0,
             "hr_candidate_median_bpm": float(np.median([r["value"] for r in accepted])) if accepted else None,
             "hr_reasons": dict(Counter(r["reason"] for r in hr)),
             "binary_hr_rows": sum(r["target_label"] is not None and r["value"] is not None for r in hr),
             "acc_rail_rows": int(normalized["acc_rail"].sum()),
             "eda_flat_windows": sum(q["full_window"] and q["eda_flat"] for q in quality),
             "windows_with_acc_rail": sum(q["acc_rail_rows"] > 0 for q in quality)}
    write_csv(target / "acc_flags.csv", ["time_ms", "at_source_rail"],
              ((format(i * 1000 / 32, ".9f"), int(flag)) for i, flag in enumerate(normalized["acc_rail"])))
    meta["channels"]["hr_bpm"] = {"file": (target / "hr_bpm.csv").relative_to(output).as_posix(),
                                  "unit": "bpm", "output_rate_hz": 1, "independent_samples": False,
                                  "available_at": "window_end_ms", "window_ms": 10000,
                                  "method": HR_METHOD, "reference_validated": False,
                                  "processing": "causal_SOS_peaks", "config": HR_CONFIG}
    meta.update(label_file=(target / "labels.csv").relative_to(output).as_posix(),
                hr_window_label_file=(target / "hr_window_labels.csv").relative_to(output).as_posix(),
                label_sampling_hz=700,
                quality_flags_file=(target / "acc_flags.csv").relative_to(output).as_posix(),
                window_quality_file=(target / "window_quality.csv").relative_to(output).as_posix(),
                dataset_site="non_dominant_wrist", eda_device_transfer_validated=False)
    # Hash các file xuất, không ghi lại dữ liệu ngoài các thư mục local bị ignore.
    meta["output_sha256"] = {}
    for path in sorted(target.glob("*.csv")):
        with path.open("rb") as f:
            meta["output_sha256"][path.name] = hashlib.file_digest(f, "sha256").hexdigest()
    write_json(target / "metadata.json", meta)
    stats["metadata"] = (target / "metadata.json").relative_to(output).as_posix()
    stats["dependencies"] = {"numpy": np.__version__, "scipy": scipy.__version__}
    return stats
