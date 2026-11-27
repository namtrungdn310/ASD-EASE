"""Kiểm thử phương pháp MSPTDfast v2 trong ai/src/preprocessing/ppg_published.py."""

import numpy as np
import pytest

from src.preprocessing.ppg_published import (
    MSPTD_DEFAULT_CONFIG,
    detect_msptd,
    estimate_hr_msptd,
    msptd_window_hr,
    scalogram_extrema,
)


def test_scalogram_extrema_edge_cases():
    # Mảng quá ngắn (< 6)
    p, o = scalogram_extrema(np.ones(5), fs=64)
    assert len(p) == 0 and len(o) == 0

    # Mảng phẳng
    p, o = scalogram_extrema(np.zeros(100), fs=64)
    assert len(p) == 0 and len(o) == 0


def test_detect_msptd_validation():
    with pytest.raises(ValueError, match="liên tục, hữu hạn"):
        detect_msptd(np.array([1.0, np.nan, 2.0]), fs=64)
    with pytest.raises(ValueError, match="positive"):
        detect_msptd(np.ones(100), fs=0)


def test_msptd_sine_wave_accuracy():
    fs = 64.0
    t = np.arange(10 * fs) / fs
    # 60 bpm = 1.0 Hz
    s60 = np.sin(2 * np.pi * 1.0 * t)
    res60 = msptd_window_hr(s60, fs=fs)
    assert res60["reason"] == "ACCEPTED"
    assert res60["gated_bpm"] is not None
    assert abs(res60["gated_bpm"] - 60.0) < 1.0
    assert abs(res60["raw_bpm"] - 60.0) < 1.0

    # 90 bpm = 1.5 Hz
    s90 = np.sin(2 * np.pi * 1.5 * t)
    res90 = msptd_window_hr(s90, fs=fs)
    assert res90["reason"] == "ACCEPTED"
    assert abs(res90["gated_bpm"] - 90.0) < 1.0


def test_msptd_window_hr_rejection_reasons():
    fs = 64.0
    # Ngắn hơn 10 s
    assert msptd_window_hr(np.ones(5 * 64), fs=fs)["reason"] == "INSUFFICIENT_SAMPLES"
    # Phẳng
    assert msptd_window_hr(np.zeros(10 * 64), fs=fs)["reason"] == "FLAT_SIGNAL"
    # Non-finite
    arr = np.sin(np.arange(10 * 64))
    arr[50] = np.nan
    assert msptd_window_hr(arr, fs=fs)["reason"] == "NONFINITE"


def test_msptd_gating_cv():
    fs = 64.0
    # Tạo chuỗi đỉnh giả lập có khoảng cách không đều (CV lớn)
    # Tín hiệu tổng hợp gồm nhịp không đều
    t = np.arange(10 * fs) / fs
    s = np.sin(2 * np.pi * 1.0 * t) + 0.8 * np.sin(2 * np.pi * 2.7 * t)
    res = msptd_window_hr(s, fs=fs, config={"gated_max_rr_cv": 0.10})
    # Với ngưỡng CV khắt khe 0.10, tín hiệu hỗn hợp này sẽ bị loại khỏi gated_bpm
    assert res["raw_bpm"] is not None
    assert res["gated_bpm"] is None
    assert res["reason"] in ("IRREGULAR_PEAKS", "INTERVAL_OUTSIDE_METHOD_RANGE")


def test_estimate_hr_msptd_timeline_and_causality():
    fs = 64.0
    duration_s = 20
    t = np.arange(duration_s * fs) / fs
    clean_bvp = np.sin(2 * np.pi * 1.2 * t)  # 72 bpm

    rows = estimate_hr_msptd(clean_bvp, fs=fs)
    # Xuất mỗi giây từ giây 1 đến 20: 20 cửa sổ
    assert len(rows) == duration_s
    assert rows[0]["time_ms"] == 1000
    assert rows[-1]["time_ms"] == 20000

    # Kiểm tra tính nhân quả: đổi tương lai ở giây 18..20 không đổi kết quả ở giây 15
    corrupted_bvp = clean_bvp.copy()
    corrupted_bvp[int(17 * fs):] = 999.0
    rows_corrupted = estimate_hr_msptd(corrupted_bvp, fs=fs)

    idx_15 = next(i for i, r in enumerate(rows) if r["time_ms"] == 15000)
    assert rows[idx_15]["raw_bpm"] == rows_corrupted[idx_15]["raw_bpm"]
    assert rows[idx_15]["gated_bpm"] == rows_corrupted[idx_15]["gated_bpm"]
    assert rows[idx_15]["reason"] == rows_corrupted[idx_15]["reason"]
