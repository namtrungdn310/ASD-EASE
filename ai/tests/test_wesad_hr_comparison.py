"""Kiểm tra ghép thời gian/mẫu số sai số; không cần WFDB hoặc dataset trong CI."""

import numpy as np
import pytest

from src.evaluation.wesad_hr import compare_rows, metrics, reference_window, summarize


def test_reference_is_computed_on_same_half_open_window():
    ecg = np.sin(np.arange(30 * 700) / 20)
    peaks = np.arange(350, len(ecg), 700)
    runs = [{"start_index": 0, "end_index": len(ecg)}]
    row = reference_window(ecg, peaks, runs, 10000, 20000)
    assert row["ecg_hr_bpm"] == 60
    assert row["qrs_count"] == 10
    assert reference_window(ecg, peaks, runs, 0, 10000)["ecg_hr_bpm"] is None
    assert reference_window(ecg, peaks, runs, 25000, 35000)["ecg_hr_bpm"] is None


def test_reference_does_not_bridge_gap_or_accept_flat_ecg():
    peaks = np.arange(350, 21000, 700)
    runs = [{"start_index": 0, "end_index": 9000}, {"start_index": 10000, "end_index": 21000}]
    assert reference_window(np.sin(np.arange(21000)), peaks, runs, 10000, 20000)["ecg_hr_bpm"] is None
    assert reference_window(np.zeros(21000), peaks, [{"start_index": 0, "end_index": 21000}], 10000, 20000)["ecg_hr_bpm"] is None


def test_missing_hr_is_not_zero_error_and_labels_do_not_change_reference():
    base = {"time_ms": "20000", "window_start_ms": "10000", "window_end_ms": "20000"}
    hr = [{**base, "value": "", "candidate_bpm": "50", "reason": "REJECTED"}]
    label = [{**base, "source_label_code": "2", "target_label": "1"}]
    ecg = np.sin(np.arange(30 * 700) / 20);peaks = np.arange(350, len(ecg), 700)
    r = compare_rows(hr, label, ecg, peaks, [{"start_index": 0, "end_index": len(ecg)}])
    assert r[0]["error_bpm"] is None
    assert r[0]["ungated_error_bpm"] == -10
    m = metrics(r)
    assert m["mae_bpm"] is None and m["paired_windows"] == 0
    assert m["automatic_reference_windows"] == 1
    assert m["paired_coverage_among_reference"] == 0
    label[0]["source_label_code"] = "1"
    assert compare_rows(hr, label, ecg, peaks, [{"start_index": 0, "end_index": len(ecg)}])[0]["ecg_hr_bpm"] == r[0]["ecg_hr_bpm"]


def test_misaligned_rows_rejected():
    with pytest.raises(ValueError, match="time aligned"):
        compare_rows([{"time_ms": "1"}], [{"time_ms": "2"}], np.ones(20), np.array([]), [])


def test_error_metrics_bias_and_label_denominators():
    rows = [{"ecg_hr_bpm": 100, "ppg_hr_bpm": 110, "error_bpm": 10, "ungated_error_bpm": 10,
             "reference_reason": "OK", "source_label_code": "1"},
            {"ecg_hr_bpm": 100, "ppg_hr_bpm": 90, "error_bpm": -10, "ungated_error_bpm": -10,
             "reference_reason": "OK", "source_label_code": "2"},
            {"ecg_hr_bpm": None, "ppg_hr_bpm": 80, "error_bpm": None, "ungated_error_bpm": None,
             "reference_reason": "BAD", "source_label_code": "2"}]
    r = summarize(rows)
    assert r["binary_task"]["mae_bpm"] == 10 and r["binary_task"]["bias_bpm"] == 0
    assert r["binary_task"]["reference_coverage"] == 2 / 3
    assert r["by_source_label"]["2"]["reference_coverage"] == .5
    assert metrics([])["mae_bpm"] is None
