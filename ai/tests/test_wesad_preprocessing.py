"""Kiểm tra thời gian/đơn vị/nhân quả; sóng giả không chứng minh độ chính xác HR thật."""

import json

import numpy as np
import pytest

from src.preprocessing.wesad import (
    annotate_window, estimate_hr, hr_candidate, label_rows, normalize_subject,
    normalize_wrist, quality_rows,
)


def recording(seconds=30):
    t = np.arange(seconds * 64) / 64
    return {"subject": "S2", "signal": {"wrist": {
        "BVP": (5 + np.sin(2 * np.pi * 1.25 * t))[:, None],
        "EDA": np.ones((seconds * 4, 1)) * 2,
        "ACC": np.tile([0, 0, 64.], (seconds * 32, 1)),
        "TEMP": np.ones((seconds * 4, 1)) * 33}},
        "label": np.ones(seconds * 700, dtype=np.int32)}


def test_acc_scale_norm_and_source_not_modified():
    d = recording()
    n = normalize_wrist(d)
    assert np.allclose(n["signals"]["acc_z_ms2"], 9.80665)
    assert np.allclose(n["signals"]["acc_norm_ms2"], 9.80665)
    assert np.all(n["signals"]["eda_us"] == 2)
    assert np.all(d["signal"]["wrist"]["ACC"][:, 2] == 64)
    assert len(n["signals"]["bvp"]) == 1920
    assert len(n["signals"]["eda_us"]) == 120


def test_missing_preserved_instead_of_zero_or_time_compression():
    d = recording()
    d["signal"]["wrist"]["EDA"][3] = np.inf
    d["signal"]["wrist"]["ACC"][7, 0] = np.nan
    n = normalize_wrist(d)
    assert np.isnan(n["signals"]["eda_us"][3])
    assert np.isnan(n["signals"]["acc_norm_ms2"][7])
    assert len(n["signals"]["eda_us"]) == 120


def test_wrong_duration_rejected():
    d = recording()
    d["signal"]["wrist"]["EDA"] = np.zeros((100, 1))
    with pytest.raises(ValueError, match="timeline"):
        normalize_wrist(d)


def test_label_boundaries_are_half_open_and_not_majority_vote():
    labels = np.r_[np.ones(7000, dtype=int), np.full(7000, 2)]
    assert annotate_window(labels, 0, 10000) == (1, 0)
    assert annotate_window(labels, 10000, 20000) == (2, 1)
    assert annotate_window(labels, 9000, 11000) == (None, None)
    assert annotate_window(labels, 0, 21000) == (None, None)
    assert label_rows(labels)[0]["end_ms"] == 10000
    assert annotate_window(np.zeros(7000, dtype=int), 0, 10000) == (0, None)


@pytest.mark.parametrize("bpm", [45, 60, 75, 105, 150, 180])
def test_clean_periodic_fixture_recovers_rate_without_target_prior(bpm):
    t = np.arange(40 * 64) / 64
    x = 100 + 2 * np.sin(2 * np.pi * bpm / 60 * t)
    rows = estimate_hr(x)
    accepted = [r["value"] for r in rows[-10:] if r["value"] is not None]
    assert len(accepted) >= 9
    assert abs(np.median(accepted) - bpm) < 4


def test_causal_results_unchanged_by_future_samples():
    d = recording(40)
    bvp = d["signal"]["wrist"]["BVP"][:, 0]
    prefix = estimate_hr(bvp[:25 * 64])
    changed = bvp.copy()
    changed[25 * 64:] = np.random.default_rng(11).normal(0, 1000, 15 * 64)
    assert estimate_hr(changed)[:25] == prefix


def test_nan_gap_resets_filter_and_hr_does_not_hold_last_value():
    t = np.arange(50 * 64) / 64
    x = np.sin(2 * np.pi * 1.25 * t)
    x[25 * 64:26 * 64] = np.nan
    rows = estimate_hr(x)
    assert rows[23]["value"] is not None
    assert all(r["value"] is None for r in rows[25:37])
    assert rows[-1]["value"] is not None


def test_flat_signal_and_noisy_fixture_do_not_create_full_quality():
    rows = estimate_hr(np.ones(30 * 64))
    assert all(r["value"] is None for r in rows)
    assert rows[-1]["reason"] == "FLAT_SIGNAL"
    result = hr_candidate(np.random.default_rng(18).normal(size=640))
    assert result["value"] is None


def test_detector_independent_of_stress_labels():
    a, b = recording(), recording()
    b["label"][:] = 2
    x = estimate_hr(normalize_wrist(a)["signals"]["bvp"])
    y = estimate_hr(normalize_wrist(b)["signals"]["bvp"])
    assert x == y


def test_export_missing_csv_units_metadata_flags_and_no_overwrite(tmp_path):
    d = recording()
    d["signal"]["wrist"]["EDA"][1] = np.nan
    d["signal"]["wrist"]["ACC"][0, 0] = -128
    result = normalize_subject(d, tmp_path)
    target = tmp_path / "signals/S2"
    assert "250.000000000,\n" in (target / "eda_us.csv").read_text()
    meta = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
    assert meta["channels"]["acc_z_ms2"]["unit"] == "m/s^2"
    assert meta["channels"]["hr_bpm"]["reference_validated"] is False
    assert "source_label_code" not in (target / "hr_bpm.csv").read_text().splitlines()[0]
    assert "target_label" in (target / "hr_window_labels.csv").read_text().splitlines()[0]
    assert result["acc_rail_rows"] == 1
    assert meta["channels"]["eda_us"]["missing_count"] == 1
    with pytest.raises(FileExistsError):
        normalize_subject(d, tmp_path)


def test_quality_rows_count_raw_samples_not_telemetry_or_hr():
    n = normalize_wrist(recording())
    rows = quality_rows(n, estimate_hr(n["signals"]["bvp"]))
    assert rows[-1]["eda_samples"] == 40
    assert rows[-1]["acc_samples"] == 320
    assert rows[-1]["eda_flat"] == 1
