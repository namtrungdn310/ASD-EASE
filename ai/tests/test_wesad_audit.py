"""Kiểm tra phép thống kê/thời gian; fixture không phải bằng chứng chất lượng WESAD."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("wesad_audit", Path(__file__).resolve().parents[2] / "scripts/audit_wesad.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_label_intervals_preserve_unknown_and_boundaries():
    intervals = audit.label_intervals(np.repeat(np.array([0, 1, 2, 7]), 700))
    assert [i["source_label_code"] for i in intervals] == [0, 1, 2, 7]
    assert [i["start_ms"] for i in intervals] == [0, 1000, 2000, 3000]
    assert [i["end_ms"] for i in intervals] == [1000, 2000, 3000, 4000]
    assert sum(i["end_index"] - i["start_index"] for i in intervals) == 2800


@pytest.mark.parametrize("labels", [np.array([]), np.array([1.5]), np.array([8]), np.array([[1]])])
def test_invalid_labels_not_silently_coerced(labels):
    with pytest.raises(ValueError):
        audit.label_intervals(labels)


def test_missing_values_are_counted_without_replacing_zero():
    stats = audit.signal_stats(np.array([[0.], [2.], [np.nan], [np.inf]]), 1, 4)
    assert stats["columns"][0] == {"finite_count": 2, "nonfinite_count": 2,
                                   "min": 0., "max": 2., "median": 1., "std": 1., "zero_count": 1}
    assert stats["implied_duration_seconds"] == 1


def test_acc_unit_proof_requires_raw_sequence_match():
    raw = np.arange(600).reshape(200, 3)
    assert audit.find_raw_match(raw, raw[12:]) == 12
    assert audit.find_raw_match(raw, raw[12:] / 64) is None


def test_wrong_channel_shape_rejected():
    with pytest.raises(ValueError):
        audit.signal_stats(np.zeros((32, 1)), 3, 32)
