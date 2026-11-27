"""Thu thập và trích xuất đặc trưng 36 chiều từ thiết bị thật theo đúng cấu trúc WESAD dataset.csv.

Module độc lập để dễ tháo bỏ khi không cần thu thập thêm dữ liệu huấn luyện.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

WESAD_NEUTRAL_EDA_US = 1.9574

DATASET_COLUMNS = [
    "subject_id",
    "window_start_ms",
    "window_end_ms",
    "source_label_code",
    "label",
    "eda_mean",
    "eda_std",
    "eda_min",
    "eda_max",
    "eda_ptp",
    "eda_slope",
    "eda_tonic_mean",
    "eda_tonic_std",
    "eda_phasic_mean",
    "eda_phasic_max",
    "eda_phasic_std",
    "eda_phasic_auc",
    "eda_scr_count",
    "eda_scr_amp_mean",
    "acc_norm_mean",
    "acc_norm_std",
    "acc_norm_min",
    "acc_norm_max",
    "acc_norm_ptp",
    "acc_norm_energy",
    "acc_motion_intensity",
    "acc_x_mean",
    "acc_x_std",
    "acc_y_mean",
    "acc_y_std",
    "acc_z_mean",
    "acc_z_std",
    "hr_valid_count",
    "hr_valid_ratio",
    "hr_is_valid",
    "hr_mean",
    "hr_std",
    "hr_min",
    "hr_max",
    "hr_ptp",
    "hr_slope",
]


def _mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    m = sum(values) / n
    var = sum((v - m) ** 2 for v in values) / n
    return m, math.sqrt(var)


def _linear_slope(values: list[float], dt_s: float = 1.0) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    t_mean = 0.5 * (n - 1) * dt_s
    num = 0.0
    den = 0.0
    for i, v in enumerate(values):
        tc = i * dt_s - t_mean
        num += tc * v
        den += tc * tc
    return (num / den) if den > 1e-12 else 0.0


def _adc_series_to_eda_us(raw_adcs: list[float]) -> list[float]:
    """Quy đổi chuỗi GSR ADC thô về miền µS quanh nền cá nhân đồng nhất với edge_ai_inference.h."""
    if not raw_adcs:
        return [WESAD_NEUTRAL_EDA_US]
    init_n = min(len(raw_adcs), 15)
    baseline = max(150.0, sum(raw_adcs[:init_n]) / init_n)
    fast = raw_adcs[0]
    out: list[float] = []
    for adc in raw_adcs:
        fast = 0.25 * adc + 0.75 * fast
        rel_shift = abs(fast - baseline) / baseline
        tonic_shift = min(2.20, rel_shift * 3.2)
        phasic_jitter = min(1.50, (abs(adc - fast) / baseline) * 4.0)
        eda = max(0.20, min(15.0, WESAD_NEUTRAL_EDA_US + tonic_shift + phasic_jitter))
        out.append(eda)
    return out


def extract_window_features(samples: list[dict[str, Any]]) -> dict[str, float]:
    """Trích xuất đúng 36 đặc trưng (EDA, ACC, HR) từ danh sách mẫu 1 Hz của một cửa sổ."""
    n = len(samples)
    duration_s = max(1.0, float(n))
    duration_scale = 60.0 / duration_s

    # --- 1. EDA (14 đặc trưng) ---
    raw_adcs: list[float] = []
    last_adc = 1800.0
    for s in samples:
        val = s.get("gsr_raw")
        if isinstance(val, (int, float)) and math.isfinite(val) and 0 < val < 4095:
            last_adc = float(val)
        raw_adcs.append(last_adc)
    eda = _adc_series_to_eda_us(raw_adcs)
    eda_mean, eda_std = _mean_std(eda)
    eda_min = min(eda)
    eda_max = max(eda)
    eda_ptp = eda_max - eda_min
    eda_slope = _linear_slope(eda, dt_s=1.0)

    # Phân rã Tonic/Phasic bằng cửa sổ trượt 5 giây (5 mẫu @ 1 Hz)
    half_win = 2
    tonic: list[float] = []
    phasic: list[float] = []
    for i in range(n):
        lo = max(0, i - half_win)
        hi = min(n, i + half_win + 1)
        t_val = sum(eda[lo:hi]) / (hi - lo)
        tonic.append(t_val)
        phasic.append(max(0.0, eda[i] - t_val))

    eda_tonic_mean, eda_tonic_std = _mean_std(tonic)
    eda_phasic_mean, eda_phasic_std = _mean_std(phasic)
    eda_phasic_max = max(phasic) if phasic else 0.0
    eda_phasic_auc = sum(phasic) * duration_scale

    peaks: list[float] = []
    for i in range(1, n - 1):
        if phasic[i] >= 0.01 and phasic[i] > phasic[i - 1] and phasic[i] >= phasic[i + 1]:
            peaks.append(phasic[i])
    eda_scr_count = float(len(peaks)) * duration_scale
    eda_scr_amp_mean = (sum(peaks) / len(peaks)) if peaks else 0.0

    # --- 2. ACC (13 đặc trưng) ---
    ax_list: list[float] = []
    ay_list: list[float] = []
    az_list: list[float] = []
    norm_list: list[float] = []
    lx, ly, lz = 0.0, 0.0, 9.80665
    for s in samples:
        ax, ay, az = s.get("ax"), s.get("ay"), s.get("az")
        if all(isinstance(v, (int, float)) and math.isfinite(v) for v in (ax, ay, az)):
            lx, ly, lz = float(ax), float(ay), float(az)
        ax_list.append(lx)
        ay_list.append(ly)
        az_list.append(lz)
        norm_list.append(math.sqrt(lx * lx + ly * ly + lz * lz))

    acc_norm_mean, acc_norm_std = _mean_std(norm_list)
    acc_norm_min = min(norm_list)
    acc_norm_max = max(norm_list)
    acc_norm_ptp = acc_norm_max - acc_norm_min
    acc_norm_energy = sum(v * v for v in norm_list) / n
    acc_motion_intensity = sum(abs(v - acc_norm_mean) for v in norm_list) / n
    acc_x_mean, acc_x_std = _mean_std(ax_list)
    acc_y_mean, acc_y_std = _mean_std(ay_list)
    acc_z_mean, acc_z_std = _mean_std(az_list)

    # --- 3. HR (9 đặc trưng) ---
    valid_hrs: list[float] = []
    raw_hrs: list[float | None] = []
    for s in samples:
        hr = s.get("hr_bpm")
        if isinstance(hr, (int, float)) and math.isfinite(hr) and 40.0 <= hr <= 200.0:
            raw_hrs.append(float(hr))
            valid_hrs.append(float(hr))
        else:
            raw_hrs.append(None)

    valid_count = len(valid_hrs)
    hr_valid_ratio = valid_count / n
    hr_is_valid = 1.0 if hr_valid_ratio >= 0.30 else 0.0
    hr_valid_count = hr_valid_ratio * 60.0

    if valid_count == 0:
        hr_mean = 75.0
        hr_std = 0.0
        hr_min = 75.0
        hr_max = 75.0
        hr_ptp = 0.0
        hr_slope = 0.0
    else:
        mean_valid = sum(valid_hrs) / valid_count
        imputed: list[float] = []
        last_v: float | None = None
        stale = 0
        for v in raw_hrs:
            if v is not None:
                last_v = v
                stale = 0
                imputed.append(v)
            elif last_v is not None and stale < 15:
                stale += 1
                imputed.append(last_v)
            else:
                imputed.append(mean_valid)
        hr_mean, hr_std = _mean_std(imputed)
        hr_min = min(valid_hrs)
        hr_max = max(valid_hrs)
        hr_ptp = hr_max - hr_min
        hr_slope = _linear_slope(imputed, dt_s=1.0)

    return {
        "eda_mean": eda_mean,
        "eda_std": eda_std,
        "eda_min": eda_min,
        "eda_max": eda_max,
        "eda_ptp": eda_ptp,
        "eda_slope": eda_slope,
        "eda_tonic_mean": eda_tonic_mean,
        "eda_tonic_std": eda_tonic_std,
        "eda_phasic_mean": eda_phasic_mean,
        "eda_phasic_max": eda_phasic_max,
        "eda_phasic_std": eda_phasic_std,
        "eda_phasic_auc": eda_phasic_auc,
        "eda_scr_count": eda_scr_count,
        "eda_scr_amp_mean": eda_scr_amp_mean,
        "acc_norm_mean": acc_norm_mean,
        "acc_norm_std": acc_norm_std,
        "acc_norm_min": acc_norm_min,
        "acc_norm_max": acc_norm_max,
        "acc_norm_ptp": acc_norm_ptp,
        "acc_norm_energy": acc_norm_energy,
        "acc_motion_intensity": acc_motion_intensity,
        "acc_x_mean": acc_x_mean,
        "acc_x_std": acc_x_std,
        "acc_y_mean": acc_y_mean,
        "acc_y_std": acc_y_std,
        "acc_z_mean": acc_z_mean,
        "acc_z_std": acc_z_std,
        "hr_valid_count": hr_valid_count,
        "hr_valid_ratio": hr_valid_ratio,
        "hr_is_valid": hr_is_valid,
        "hr_mean": hr_mean,
        "hr_std": hr_std,
        "hr_min": hr_min,
        "hr_max": hr_max,
        "hr_ptp": hr_ptp,
        "hr_slope": hr_slope,
    }


def save_labeled_capture(
    output_dir: Path,
    device_id: str,
    session_id: str | None,
    label: int,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cắt cửa sổ 60s (bước 10s, hoặc 1 cửa sổ nếu < 60s) và ghi nối vào device_dataset.csv."""
    ordered = sorted(samples, key=lambda item: int(item["timestamp_ms"]))
    n = len(ordered)
    start_ms = int(ordered[0]["timestamp_ms"])
    end_ms = int(ordered[-1]["timestamp_ms"])
    duration_seconds = max(1, int(round((end_ms - start_ms) / 1000.0)) + 1)

    windows: list[list[dict[str, Any]]] = []
    if n >= 60:
        for idx in range(0, n - 59, 10):
            windows.append(ordered[idx : idx + 60])
        if (n - 60) % 10 != 0:
            windows.append(ordered[n - 60 : n])
    else:
        windows.append(ordered)

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "device_dataset.csv"
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0

    subject_id = f"REAL_{device_id}"
    source_label_code = 2 if label == 1 else 1

    with csv_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DATASET_COLUMNS)
        if write_header:
            writer.writeheader()
        for win in windows:
            feats = extract_window_features(win)
            row = {
                "subject_id": subject_id,
                "window_start_ms": int(win[0]["timestamp_ms"]),
                "window_end_ms": int(win[-1]["timestamp_ms"]),
                "source_label_code": source_label_code,
                "label": int(label),
                **feats,
            }
            writer.writerow(row)

    log_path = output_dir / "captures_log.jsonl"
    log_entry = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "device_id": device_id,
        "session_id": session_id,
        "label": int(label),
        "sample_count": n,
        "window_count": len(windows),
        "duration_seconds": duration_seconds,
        "window_start_ms": start_ms,
        "window_end_ms": end_ms,
    }
    with log_path.open("a", encoding="utf-8") as log_handle:
        log_handle.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return {
        "saved": True,
        "device_id": device_id,
        "label": int(label),
        "sample_count": n,
        "window_count": len(windows),
        "duration_seconds": duration_seconds,
        "dataset_file": str(csv_path.name),
    }
