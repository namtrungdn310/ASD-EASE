"""Các phương pháp PPG đã công bố để đối chiếu offline với WESAD; không thay firmware.

Bao gồm:
1. MSPTDfast v2 (Multi-Scale Peak and Trough Detection):
   Nguồn: Peter H. Charlton, ppg-beats, source/msptdfastv2_beat_detector.m,
   commit c397be7afc0d8a1601a85cd673718372e40f1f59.
   Bản chuyển Python/NumPy giữ nguyên cấu trúc toán học scalogram đa thang đo.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

PUBLISHED_METHOD_NAME = "msptdfastv2-charlton"
PUBLISHED_UPSTREAM_COMMIT = "c397be7afc0d8a1601a85cd673718372e40f1f59"
PUBLISHED_UPSTREAM_URL = (
    f"https://github.com/peterhcharlton/ppg-beats/blob/{PUBLISHED_UPSTREAM_COMMIT}/source/msptdfastv2_beat_detector.m"
)

MSPTD_DEFAULT_CONFIG = {
    "window_seconds": 10,
    "hop_seconds": 1,
    "filter_warmup_seconds": 2,
    "band_hz": [0.5, 5.0],
    "butter_prototype_order": 2,
    "min_bpm": 40.0,
    "max_bpm": 200.0,
    "min_peaks": 3,
    "gated_max_rr_cv": 0.35,
}


def scalogram_extrema(values: np.ndarray, fs: float, *, literal: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Tính cực đại/cực tiểu cục bộ qua các thang đo scalogram (MSPTD)."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < 6:
        return np.array([], dtype=int), np.array([], dtype=int)
    axis = np.arange(n, dtype=float) - (n - 1) / 2
    denominator = np.dot(axis, axis)
    if denominator <= 1e-12:
        return np.array([], dtype=int), np.array([], dtype=int)
    x = values - values.mean() - axis * np.dot(axis, values) / denominator
    length = int(np.ceil(n / 2) - 1)
    scales = np.arange(1, length + 1)
    keep = (length / scales) / (n / fs) >= 0.5  # 30 bpm: mặc định nguồn
    if not keep.any():
        return np.array([], dtype=int), np.array([], dtype=int)
    max_scale = int(scales[keep][-1])
    maxima = np.zeros((max_scale, n), dtype=bool)
    minima = np.zeros_like(maxima)
    for k in range(1, max_scale + 1):
        if literal:
            for j in range(k, n - k):
                maxima[k - 1, j] = x[j] > x[j - k] and x[j] > x[j + k]
                minima[k - 1, j] = x[j] < x[j - k] and x[j] < x[j + k]
        else:
            center = x[k : n - k]
            maxima[k - 1, k : n - k] = (center > x[: n - 2 * k]) & (center > x[2 * k :])
            minima[k - 1, k : n - k] = (center < x[: n - 2 * k]) & (center < x[2 * k :])
    peak_scale = int(np.argmax(maxima.sum(axis=1)))
    onset_scale = int(np.argmax(minima.sum(axis=1)))
    return (
        np.flatnonzero(maxima[: peak_scale + 1].all(axis=0)),
        np.flatnonzero(minima[: onset_scale + 1].all(axis=0)),
    )


def detect_msptd(values: np.ndarray, fs: float = 64.0, *, literal: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Phát hiện đỉnh (peaks) và chân sóng (onsets) bằng MSPTDfast v2 trên đoạn hữu hạn."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("MSPTD yêu cầu một đoạn liên tục, hữu hạn")
    if fs <= 0:
        raise ValueError("Sampling frequency must be positive")
    n = len(values)
    window = int(round(6 * fs))
    if n <= window:
        spans = [(0, n)]
    else:
        offset = int(np.floor(window * 0.8 + 0.5))
        starts = list(range(0, n - window, offset))
        spans = [(start, start + window + 1) for start in starts]
        if spans[-1][1] < n:
            spans.append((n - window - 1, n))
    factor = max(1, int(np.floor(fs / 20)))
    tolerance = int(np.ceil(fs * (0.2 if fs / factor < 10 else 0.1 if fs / factor < 20 else 0.05)))
    peaks, onsets = [], []
    for start, end in spans:
        signal = values[start:end]
        p, t = scalogram_extrema(signal[::factor], fs / factor, literal=literal)
        for indices, output, maximum in [(p, peaks, True), (t, onsets, False)]:
            for index in indices * factor + (factor - 1):
                left, right = int(index) - tolerance, int(index) + tolerance + 1
                if left < 0 or right > len(signal):
                    continue
                chunk = signal[left:right]
                refined = np.argmax(chunk) if maximum else np.argmin(chunk)
                output.append(start + left + int(refined))
    return np.unique(peaks).astype(int), np.unique(onsets).astype(int)


def msptd_window_hr(window: np.ndarray, fs: float = 64.0, config: dict | None = None) -> dict:
    """Tính nhịp tim từ cửa sổ BVP 10 s bằng MSPTDfast v2, báo cả bản raw và bản có cổng sinh lý."""
    cfg = MSPTD_DEFAULT_CONFIG if config is None else {**MSPTD_DEFAULT_CONFIG, **config}
    y = np.asarray(window, dtype=float)
    result = {
        "raw_bpm": None,
        "mean_ibi_bpm": None,
        "gated_bpm": None,
        "reason": "INSUFFICIENT_SAMPLES",
        "peak_count": 0,
        "rr_cv": None,
        "median_interval_s": None,
    }
    if y.ndim != 1 or len(y) < int(cfg["window_seconds"] * fs):
        return result
    if not np.isfinite(y).all():
        result["reason"] = "NONFINITE"
        return result
    if np.ptp(y) <= 1e-8 or np.std(y) <= 1e-8:
        result["reason"] = "FLAT_SIGNAL"
        return result

    peaks, _ = detect_msptd(y, fs=fs)
    result["peak_count"] = len(peaks)
    if len(peaks) < 2:
        result["reason"] = "TOO_FEW_PEAKS"
        return result

    intervals = np.diff(peaks) / fs
    median_ibi = float(np.median(intervals))
    raw_bpm = float(60.0 / median_ibi) if median_ibi > 0 else None
    duration_s = float((peaks[-1] - peaks[0]) / fs)
    mean_ibi_bpm = float(60.0 * (len(peaks) - 1) / duration_s) if duration_s > 0 else None

    # Bản raw: chỉ yêu cầu dải bpm chuẩn
    if raw_bpm is not None and cfg["min_bpm"] <= raw_bpm <= cfg["max_bpm"]:
        result["raw_bpm"] = raw_bpm
    if mean_ibi_bpm is not None and cfg["min_bpm"] <= mean_ibi_bpm <= cfg["max_bpm"]:
        result["mean_ibi_bpm"] = mean_ibi_bpm

    result["median_interval_s"] = median_ibi
    cv = float(np.std(intervals) / np.mean(intervals)) if np.mean(intervals) > 0 else None
    result["rr_cv"] = cv

    # Cổng kỹ thuật sinh lý (gated)
    if len(peaks) < cfg["min_peaks"]:
        result["reason"] = "TOO_FEW_PEAKS_FOR_GATING"
    elif raw_bpm is None or not (cfg["min_bpm"] <= raw_bpm <= cfg["max_bpm"]):
        result["reason"] = "OUTSIDE_METHOD_RANGE"
    elif np.any((intervals < 60.0 / cfg["max_bpm"]) | (intervals > 60.0 / cfg["min_bpm"])):
        result["reason"] = "INTERVAL_OUTSIDE_METHOD_RANGE"
    elif cfg["gated_max_rr_cv"] is not None and cv is not None and cv > cfg["gated_max_rr_cv"]:
        result["reason"] = "IRREGULAR_PEAKS"
    else:
        result["gated_bpm"] = raw_bpm
        result["reason"] = "ACCEPTED"

    return result


def estimate_hr_msptd(bvp: np.ndarray, fs: float = 64.0, config: dict | None = None) -> list[dict]:
    """Lọc nhân quả và xuất HR từng giây cho toàn bộ chuỗi BVP bằng MSPTDfast v2."""
    cfg = MSPTD_DEFAULT_CONFIG if config is None else {**MSPTD_DEFAULT_CONFIG, **config}
    x = np.asarray(bvp, dtype=float)
    if x.ndim != 1 or fs <= 0:
        raise ValueError("Invalid BVP signal or sampling frequency")

    from src.preprocessing.wesad import ranges

    filtered = np.full(len(x), np.nan)
    run_start = np.full(len(x), -1, dtype=np.int64)
    sos = butter(
        cfg["butter_prototype_order"],
        cfg["band_hz"],
        btype="bandpass",
        fs=fs,
        output="sos",
    )
    for start, end in ranges(np.isfinite(x)):
        filtered[start:end], _ = sosfilt(sos, x[start:end], zi=sosfilt_zi(sos) * x[start])
        run_start[start:end] = start

    width = int(cfg["window_seconds"] * fs)
    hop = int(cfg["hop_seconds"] * fs)
    warmup = int(cfg["filter_warmup_seconds"] * fs)
    rows = []
    for end in range(int(fs), len(x) + 1, hop):
        start = end - width
        reason = "WARMUP" if start < 0 else "MISSING_OR_FILTER_WARMUP"
        candidate = {
            "raw_bpm": None,
            "mean_ibi_bpm": None,
            "gated_bpm": None,
            "reason": reason,
            "peak_count": 0,
            "rr_cv": None,
            "median_interval_s": None,
        }
        if start >= 0 and run_start[end - 1] >= 0 and start >= run_start[end - 1] + warmup:
            candidate = msptd_window_hr(filtered[start:end], fs=fs, config=cfg)
        rows.append({
            "time_ms": int(end * 1000 // fs),
            "window_start_ms": int(max(0, start * 1000 // fs)),
            "window_end_ms": int(end * 1000 // fs),
            **candidate,
        })
    return rows
