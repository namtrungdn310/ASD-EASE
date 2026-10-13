from typing import Any
import numpy as np


def normalize_raw_batch(batch: dict[str, Any]) -> dict[str, dict[str, np.ndarray | float]]:
    """Convert API raw-batch payloads to arrays without synthetic-specific behavior."""
    required = {"ppg", "imu", "gsr"}
    if not required.issubset(batch):
        raise ValueError(f"Missing streams: {sorted(required - batch.keys())}")
    result: dict[str, dict[str, np.ndarray | float]] = {}
    for stream, keys in {"ppg": ("red", "ir"), "imu": ("ax", "ay", "az", "gx", "gy", "gz"), "gsr": ("adc",)}.items():
        payload = batch[stream]
        result[stream] = {"sample_rate_hz": float(payload["sample_rate_hz"])}
        for key in keys:
            result[stream][key] = np.array([np.nan if x is None else x for x in payload[key]], dtype=float)
    return result

