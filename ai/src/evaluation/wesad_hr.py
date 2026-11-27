"""Đối chiếu HR cổ tay với ECG tự động offline; không phải ground truth chuyên gia."""

from __future__ import annotations

from collections import Counter

import numpy as np

REFERENCE_METHOD = "wfdb-xqrs-4.2.0-offline-v1"
REFERENCE_CONFIG = {"sample_rate_hz": 700, "window_seconds": 10,
                    "min_bpm": 30, "max_bpm": 220, "max_rr_cv": 0.25,
                    "min_rr_intervals": 3, "boundary_guard_seconds": 1}


def detect_ecg(ecg: np.ndarray, fs: int = 700) -> tuple[np.ndarray, list[dict]]:
    """XQRS dùng lọc hai chiều/backsearch: chỉ dùng làm nguồn đối chiếu offline."""
    from wfdb.processing import XQRS
    from src.preprocessing.wesad import ranges

    signal = np.asarray(ecg, dtype=float)
    if signal.ndim != 1 or fs != 700:
        raise ValueError("Expected synchronized WESAD ECG at 700 Hz")
    peaks, runs = [], []
    for start, end in ranges(np.isfinite(signal)):
        if end - start < 10 * fs or np.ptp(signal[start:end]) <= 1e-8:
            continue
        detector = XQRS(sig=signal[start:end], fs=fs)
        detector.detect(learn=True, verbose=False)
        peaks.extend((detector.qrs_inds + start).tolist())
        runs.append({"start_index": start, "end_index": end,
                     "learned_initialization": bool(detector.learned_init_params)})
    return np.asarray(peaks, dtype=np.int64), runs


def reference_window(ecg: np.ndarray, peaks: np.ndarray, runs: list[dict],
                     start_ms: int, end_ms: int, fs: int = 700) -> dict:
    result = {"ecg_hr_bpm": None, "reference_reason": "INCOMPLETE_WINDOW",
              "qrs_count": 0, "ecg_rr_cv": None}
    if end_ms - start_ms != 10000:
        return result
    start, end = start_ms * fs // 1000, end_ms * fs // 1000
    if start < 0 or end > len(ecg):
        return result
    guard = REFERENCE_CONFIG["boundary_guard_seconds"] * fs
    if not any(start >= r["start_index"] + guard and end <= r["end_index"] - guard for r in runs):
        result["reference_reason"] = "GAP_OR_BOUNDARY"
        return result
    if not np.isfinite(ecg[start:end]).all() or np.ptp(ecg[start:end]) <= 1e-8:
        result["reference_reason"] = "NONFINITE_OR_FLAT"
        return result
    left, right = np.searchsorted(peaks, [start, end], side="left")
    selected = peaks[left:right]
    rr = np.diff(selected) / fs
    result["qrs_count"] = len(selected)
    if len(rr) < REFERENCE_CONFIG["min_rr_intervals"]:
        result["reference_reason"] = "TOO_FEW_QRS"
        return result
    cv = float(np.std(rr) / np.mean(rr))
    bpm = float(60 / np.median(rr))
    result["ecg_rr_cv"] = cv
    if np.any((rr < 60 / REFERENCE_CONFIG["max_bpm"]) | (rr > 60 / REFERENCE_CONFIG["min_bpm"])):
        result["reference_reason"] = "RR_OUTSIDE_REFERENCE_RANGE"
    elif cv > REFERENCE_CONFIG["max_rr_cv"]:
        result["reference_reason"] = "IRREGULAR_QRS_INTERVALS"
    else:
        result.update(ecg_hr_bpm=bpm, reference_reason="AUTOMATIC_REFERENCE_NOT_EXPERT_ANNOTATED")
    return result


def compare_rows(hr_rows: list[dict], label_rows: list[dict], ecg: np.ndarray,
                 peaks: np.ndarray, runs: list[dict]) -> list[dict]:
    if len(hr_rows) != len(label_rows):
        raise ValueError("HR and label rows have different counts")
    compared = []
    for h, label in zip(hr_rows, label_rows):
        if any(h[k] != label[k] for k in ("time_ms", "window_start_ms", "window_end_ms")):
            raise ValueError("HR and labels are not time aligned")
        start, end = int(h["window_start_ms"]), int(h["window_end_ms"])
        ref = reference_window(ecg, peaks, runs, start, end)
        accepted = float(h["value"]) if h["value"] != "" else None
        raw_candidate = float(h["candidate_bpm"]) if h["candidate_bpm"] != "" else None
        value = ref["ecg_hr_bpm"]
        compared.append({"time_ms": int(h["time_ms"]), "window_start_ms": start, "window_end_ms": end,
                         "source_label_code": label["source_label_code"],
                         "target_label": label["target_label"], "ppg_hr_bpm": accepted,
                         "ungated_candidate_bpm": raw_candidate, "ppg_reason": h["reason"], **ref,
                         "error_bpm": accepted - value if accepted is not None and value is not None else None,
                         "ungated_error_bpm": raw_candidate - value if raw_candidate is not None and value is not None else None})
    return compared


def metrics(rows: list[dict]) -> dict:
    """Độ phủ dùng đúng mẫu số; sai số chỉ trên cặp có cả hai kết quả."""
    reference = [r for r in rows if r["ecg_hr_bpm"] is not None]
    pairs = [r for r in reference if r["error_bpm"] is not None]
    errors = np.asarray([r["error_bpm"] for r in pairs], dtype=float)
    ungated = np.asarray([r["ungated_error_bpm"] for r in reference if r["ungated_error_bpm"] is not None])
    return {"windows": len(rows), "automatic_reference_windows": len(reference),
            "reference_coverage": len(reference) / len(rows) if rows else None,
            "paired_windows": len(pairs),
            "paired_coverage_among_reference": len(pairs) / len(reference) if reference else None,
            "ppg_candidate_coverage_all_windows": sum(r["ppg_hr_bpm"] is not None for r in rows) / len(rows) if rows else None,
            "mae_bpm": float(np.abs(errors).mean()) if len(errors) else None,
            "median_absolute_error_bpm": float(np.median(np.abs(errors))) if len(errors) else None,
            "p90_absolute_error_bpm": float(np.percentile(np.abs(errors), 90)) if len(errors) else None,
            "bias_bpm": float(errors.mean()) if len(errors) else None,
            "within_5_bpm_fraction": float(np.mean(np.abs(errors) <= 5)) if len(errors) else None,
            "ungated_paired_windows": len(ungated),
            "ungated_mae_bpm": float(np.abs(ungated).mean()) if len(ungated) else None,
            "reference_reasons": dict(Counter(r["reference_reason"] for r in rows))}


def summarize(rows: list[dict]) -> dict:
    return {"all_labels": metrics(rows),
            "binary_task": metrics([r for r in rows if str(r["source_label_code"]) in ("1", "2", "3")]),
            "by_source_label": {str(c): metrics([r for r in rows if str(r["source_label_code"]) == str(c)])
                                for c in (1, 2, 3)}}
