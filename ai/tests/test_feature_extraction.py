"""Kiểm thử trích xuất đặc trưng đa cảm biến trong ai/src/feature_extraction/stress_features.py."""

import numpy as np
import pytest

from src.feature_extraction.stress_features import (
    DEFAULT_FEATURE_CONFIG,
    extract_acc_features,
    extract_eda_features,
    extract_hr_features,
    extract_window_features,
)


def test_extract_eda_features():
    fs = 4.0
    # 60s
    t = np.arange(60 * fs) / fs
    # Tín hiệu EDA có mức nền tăng dần và 2 đỉnh SCR
    eda = 0.5 + 0.005 * t + 0.1 * np.exp(-((t - 15) ** 2) / 4) + 0.15 * np.exp(-((t - 40) ** 2) / 4)

    feats = extract_eda_features(eda, fs=fs)
    assert feats["eda_mean"] > 0.5
    assert feats["eda_slope"] > 0.0  # xu hướng dốc lên
    assert feats["eda_scr_count"] >= 2.0  # bắt được ít nhất 2 đỉnh SCR
    assert feats["eda_tonic_mean"] > 0.0

    # Trường hợp suy biến (mảng rỗng hoặc chứa NaN)
    degenerate = extract_eda_features(np.array([np.nan, 1.0]))
    assert degenerate["eda_mean"] == 0.0
    assert degenerate["eda_scr_count"] == 0.0


def test_extract_acc_features():
    fs = 32.0
    n = int(60 * fs)
    # Tĩnh (chỉ có trọng lực Z = 9.80665)
    x = np.zeros(n)
    y = np.zeros(n)
    z = np.full(n, 9.80665)
    norm = np.full(n, 9.80665)

    quiet_feats = extract_acc_features(x, y, z, norm, fs=fs)
    assert abs(quiet_feats["acc_norm_mean"] - 9.80665) < 1e-3
    assert quiet_feats["acc_norm_std"] < 1e-4
    assert quiet_feats["acc_motion_intensity"] == 0.0

    # Chuyển động rung lắc
    noise = np.random.RandomState(42).randn(n) * 2.0
    active_norm = 9.80665 + noise
    active_feats = extract_acc_features(noise, noise, z, active_norm, fs=fs)
    assert active_feats["acc_norm_std"] > 1.5
    assert active_feats["acc_motion_intensity"] > 0.5


def test_extract_hr_features():
    # 60 giây HR
    # Ca 1: Toàn bộ hợp lệ 80 bpm
    clean_hr = np.full(60, 80.0)
    feats = extract_hr_features(clean_hr, fs=1.0)
    assert feats["hr_valid_ratio"] == 1.0
    assert feats["hr_is_valid"] == 1.0
    assert abs(feats["hr_mean"] - 80.0) < 1e-4

    # Ca 2: Mất toàn bộ (toàn NaN)
    missing_hr = np.full(60, np.nan)
    missing_feats = extract_hr_features(missing_hr, fs=1.0, subject_median_hr=72.0)
    assert missing_feats["hr_valid_ratio"] == 0.0
    assert missing_feats["hr_is_valid"] == 0.0
    assert missing_feats["hr_mean"] == 72.0

    # Ca 3: Có 30 giây đầu hợp lệ 70 bpm, 30 giây sau mất
    half_hr = np.full(60, np.nan)
    half_hr[:30] = 70.0
    half_feats = extract_hr_features(half_hr, fs=1.0)
    assert half_feats["hr_valid_ratio"] == 0.5
    assert half_feats["hr_is_valid"] == 1.0
    assert abs(half_feats["hr_mean"] - 70.0) < 1e-4


def test_extract_window_features_composition():
    # Kiểm tra ghép toàn bộ 34 đặc trưng
    eda = np.full(240, 0.5)
    acc = np.full(1920, 9.81)
    hr = np.full(60, 75.0)

    feats = extract_window_features(eda, acc, acc, acc, acc, hr)
    assert len(feats) == 36
    for k, v in feats.items():
        assert isinstance(v, float)
        assert np.isfinite(v)
