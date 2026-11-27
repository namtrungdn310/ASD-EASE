"""Trích xuất đặc trưng đa cảm biến (EDA, ACC, HR) theo cửa sổ trượt cho bài toán nhận diện Stress.

Quy tắc:
- Hoàn toàn nhân quả trên cửa sổ trượt (mặc định 60 s, bước trượt 10 s).
- Chỉ lấy các cửa sổ tinh khiết (100% nằm trong cùng 1 nhãn), không lấy cửa sổ cắt qua ranh giới đổi nhãn.
- Ánh xạ nhãn nhị phân: Baseline (1) và Amusement (3) -> 0 (Non-stress); Stress (2) -> 1 (Stress).
- Giữ cờ hr_is_valid để mô hình học máy biết mức độ tin cậy của kênh HR.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, find_peaks, sosfilt, sosfilt_zi

DEFAULT_FEATURE_CONFIG = {
    "window_seconds": 60,
    "step_seconds": 10,
    "eda_fs": 4.0,
    "acc_fs": 32.0,
    "hr_fs": 1.0,
    "min_hr_valid_ratio": 0.30,
    "max_hr_forward_fill_s": 10,
    "scr_min_height_us": 0.01,
    "scr_min_distance_s": 1.0,
}


def extract_eda_features(eda: np.ndarray, fs: float = 4.0, config: dict | None = None) -> dict[str, float]:
    """Trích xuất đặc trưng thống kê và phân rã Tonic/Phasic từ tín hiệu EDA (µS)."""
    cfg = DEFAULT_FEATURE_CONFIG if config is None else {**DEFAULT_FEATURE_CONFIG, **config}
    y = np.asarray(eda, dtype=float)
    if y.ndim != 1 or len(y) < 4 or not np.isfinite(y).all():
        return {
            "eda_mean": 0.0,
            "eda_std": 0.0,
            "eda_min": 0.0,
            "eda_max": 0.0,
            "eda_ptp": 0.0,
            "eda_slope": 0.0,
            "eda_tonic_mean": 0.0,
            "eda_tonic_std": 0.0,
            "eda_phasic_mean": 0.0,
            "eda_phasic_max": 0.0,
            "eda_phasic_std": 0.0,
            "eda_phasic_auc": 0.0,
            "eda_scr_count": 0.0,
            "eda_scr_amp_mean": 0.0,
        }

    mean_val = float(np.mean(y))
    std_val = float(np.std(y))
    min_val = float(np.min(y))
    max_val = float(np.max(y))
    ptp_val = max_val - min_val

    # Xu hướng tuyến tính (slope µS/s)
    t = np.arange(len(y), dtype=float) / fs
    t_center = t - np.mean(t)
    denom = np.dot(t_center, t_center)
    slope = float(np.dot(t_center, y) / denom) if denom > 1e-12 else 0.0

    # Phân rã Tonic / Phasic bằng moving average cửa sổ 5 giây
    tonic_win = max(3, int(round(5.0 * fs)))
    # Dùng mode='edge' đệm biên để bảo toàn kích thước
    tonic = np.convolve(y, np.ones(tonic_win) / tonic_win, mode="same")
    phasic = np.maximum(0.0, y - tonic)

    tonic_mean = float(np.mean(tonic))
    tonic_std = float(np.std(tonic))
    phasic_mean = float(np.mean(phasic))
    phasic_max = float(np.max(phasic))
    phasic_std = float(np.std(phasic))
    phasic_auc = float(np.sum(phasic) / fs)

    # Đếm đỉnh SCR trên thành phần Phasic
    min_dist = max(1, int(round(cfg["scr_min_distance_s"] * fs)))
    peaks, properties = find_peaks(
        phasic,
        height=cfg["scr_min_height_us"],
        distance=min_dist,
    )
    scr_count = float(len(peaks))
    peak_heights = properties.get("peak_heights", [])
    scr_amp_mean = float(np.mean(peak_heights)) if len(peak_heights) > 0 else 0.0

    return {
        "eda_mean": mean_val,
        "eda_std": std_val,
        "eda_min": min_val,
        "eda_max": max_val,
        "eda_ptp": ptp_val,
        "eda_slope": slope,
        "eda_tonic_mean": tonic_mean,
        "eda_tonic_std": tonic_std,
        "eda_phasic_mean": phasic_mean,
        "eda_phasic_max": phasic_max,
        "eda_phasic_std": phasic_std,
        "eda_phasic_auc": phasic_auc,
        "eda_scr_count": scr_count,
        "eda_scr_amp_mean": scr_amp_mean,
    }


def extract_acc_features(
    acc_x: np.ndarray,
    acc_y: np.ndarray,
    acc_z: np.ndarray,
    acc_norm: np.ndarray,
    fs: float = 32.0,
) -> dict[str, float]:
    """Trích xuất đặc trưng vận động và rung lắc từ gia tốc ba trục và độ lớn gia tốc (m/s²)."""
    norm = np.asarray(acc_norm, dtype=float)
    x = np.asarray(acc_x, dtype=float)
    y = np.asarray(acc_y, dtype=float)
    z = np.asarray(acc_z, dtype=float)

    if len(norm) < 4 or not (np.isfinite(norm).all() and np.isfinite(x).all()):
        return {
            "acc_norm_mean": 9.81,
            "acc_norm_std": 0.0,
            "acc_norm_min": 9.81,
            "acc_norm_max": 9.81,
            "acc_norm_ptp": 0.0,
            "acc_norm_energy": 9.81**2,
            "acc_motion_intensity": 0.0,
            "acc_x_mean": 0.0,
            "acc_x_std": 0.0,
            "acc_y_mean": 0.0,
            "acc_y_std": 0.0,
            "acc_z_mean": 0.0,
            "acc_z_std": 0.0,
        }

    norm_mean = float(np.mean(norm))
    norm_std = float(np.std(norm))
    norm_min = float(np.min(norm))
    norm_max = float(np.max(norm))
    norm_ptp = norm_max - norm_min
    norm_energy = float(np.mean(norm**2))

    # Tỷ lệ thời gian có chuyển động đáng kể (lệch khỏi trọng lực 9.8 m/s² vượt 0.5 m/s²)
    motion_intensity = float(np.mean(np.abs(norm - 9.80665) > 0.5))

    return {
        "acc_norm_mean": norm_mean,
        "acc_norm_std": norm_std,
        "acc_norm_min": norm_min,
        "acc_norm_max": norm_max,
        "acc_norm_ptp": norm_ptp,
        "acc_norm_energy": norm_energy,
        "acc_motion_intensity": motion_intensity,
        "acc_x_mean": float(np.mean(x)),
        "acc_x_std": float(np.std(x)),
        "acc_y_mean": float(np.mean(y)),
        "acc_y_std": float(np.std(y)),
        "acc_z_mean": float(np.mean(z)),
        "acc_z_std": float(np.std(z)),
    }


def extract_hr_features(
    hr_bpm: np.ndarray,
    fs: float = 1.0,
    config: dict | None = None,
    subject_median_hr: float = 75.0,
) -> dict[str, float]:
    """Trích xuất đặc trưng nhịp tim và chất lượng từ chuỗi nhịp tim (1 mẫu/giây)."""
    cfg = DEFAULT_FEATURE_CONFIG if config is None else {**DEFAULT_FEATURE_CONFIG, **config}
    raw = np.asarray(hr_bpm, dtype=float)
    valid_mask = np.isfinite(raw) & (raw >= 40.0) & (raw <= 200.0)
    valid_count = int(np.sum(valid_mask))
    total_len = len(raw)
    valid_ratio = float(valid_count / total_len) if total_len > 0 else 0.0
    is_valid = float(1.0 if valid_ratio >= cfg["min_hr_valid_ratio"] else 0.0)

    if valid_count == 0:
        # Toàn bộ cửa sổ không có HR: điền bằng subject median HR, cờ is_valid = 0
        return {
            "hr_valid_count": 0.0,
            "hr_valid_ratio": 0.0,
            "hr_is_valid": 0.0,
            "hr_mean": float(subject_median_hr),
            "hr_std": 0.0,
            "hr_min": float(subject_median_hr),
            "hr_max": float(subject_median_hr),
            "hr_ptp": 0.0,
            "hr_slope": 0.0,
        }

    # Nội suy forward-fill có giới hạn
    imputed = raw.copy()
    last_val = np.nan
    stale_count = 0
    max_stale = int(cfg["max_hr_forward_fill_s"])

    for i in range(len(imputed)):
        if valid_mask[i]:
            last_val = imputed[i]
            stale_count = 0
        elif not np.isnan(last_val) and stale_count < max_stale:
            imputed[i] = last_val
            stale_count += 1
        else:
            imputed[i] = np.nan

    # Nếu đầu mảng bị khuyết, điền ngược từ mẫu hợp lệ đầu tiên
    first_valid_idx = np.where(valid_mask)[0][0]
    imputed[:first_valid_idx] = raw[first_valid_idx]

    # Còn lại các ô NaN (nếu khuyết quá dài): điền bằng trung bình các mẫu hợp lệ
    mean_valid = float(np.mean(raw[valid_mask]))
    imputed[np.isnan(imputed)] = mean_valid

    hr_mean = float(np.mean(imputed))
    hr_std = float(np.std(imputed)) if valid_count >= 2 else 0.0
    hr_min = float(np.min(imputed))
    hr_max = float(np.max(imputed))
    hr_ptp = hr_max - hr_min

    # Trend slope
    t = np.arange(len(imputed), dtype=float) / fs
    t_center = t - np.mean(t)
    denom = np.dot(t_center, t_center)
    hr_slope = float(np.dot(t_center, imputed) / denom) if denom > 1e-12 else 0.0

    return {
        "hr_valid_count": float(valid_count),
        "hr_valid_ratio": valid_ratio,
        "hr_is_valid": is_valid,
        "hr_mean": hr_mean,
        "hr_std": hr_std,
        "hr_min": hr_min,
        "hr_max": hr_max,
        "hr_ptp": hr_ptp,
        "hr_slope": hr_slope,
    }


def extract_window_features(
    eda_chunk: np.ndarray,
    acc_x_chunk: np.ndarray,
    acc_y_chunk: np.ndarray,
    acc_z_chunk: np.ndarray,
    acc_norm_chunk: np.ndarray,
    hr_bpm_chunk: np.ndarray,
    config: dict | None = None,
    subject_median_hr: float = 75.0,
) -> dict[str, float]:
    """Tổng hợp toàn bộ đặc trưng đa cảm biến trên cùng một cửa sổ phân loại."""
    cfg = DEFAULT_FEATURE_CONFIG if config is None else {**DEFAULT_FEATURE_CONFIG, **config}

    eda_feats = extract_eda_features(eda_chunk, fs=cfg["eda_fs"], config=cfg)
    acc_feats = extract_acc_features(
        acc_x_chunk, acc_y_chunk, acc_z_chunk, acc_norm_chunk, fs=cfg["acc_fs"]
    )
    hr_feats = extract_hr_features(
        hr_bpm_chunk, fs=cfg["hr_fs"], config=cfg, subject_median_hr=subject_median_hr
    )

    return {**eda_feats, **acc_feats, **hr_feats}
