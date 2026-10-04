import numpy as np


def apply_dropout(values: np.ndarray, frequency: float, rng: np.random.Generator) -> list[float | None]:
    mask = rng.random(values.size) < frequency
    return [None if missing else round(float(value), 6) for value, missing in zip(values, mask)]


def quality(contact: np.ndarray, motion: np.ndarray, noise: float) -> np.ndarray:
    return np.clip(contact - 0.35 * np.clip(motion, 0, 1) - 0.025 * noise, 0, 1)

