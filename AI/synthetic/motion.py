import numpy as np
from .config import ParticipantProfile


def imu_signals(t: np.ndarray, activity: np.ndarray, periodic: np.ndarray, profile: ParticipantProfile, rng: np.random.Generator) -> dict[str, np.ndarray]:
    orientation = 0.15 * np.sin(2 * np.pi * 0.025 * t)
    periodic_wave = periodic * np.sin(2 * np.pi * 2.2 * t)
    natural = np.sin(2 * np.pi * 0.35 * t + 0.4)
    movement = profile.movement_gain * (activity * natural + 0.55 * periodic_wave)
    noise = lambda scale: rng.normal(0, scale * profile.noise_gain, t.size)
    ax = 0.22 * movement + np.sin(orientation) + noise(0.015)
    ay = 0.15 * movement + noise(0.015)
    az = np.cos(orientation) + 0.12 * movement + noise(0.018)
    gx = 55 * movement + noise(1.2)
    gy = 35 * activity * np.cos(2 * np.pi * 0.35 * t) + noise(1.1)
    gz = 80 * periodic_wave + noise(1.0)
    magnitude = np.sqrt((ax) ** 2 + ay ** 2 + (az - 1) ** 2)
    return {"ax": ax, "ay": ay, "az": az, "gx": gx, "gy": gy, "gz": gz, "motion": np.clip(magnitude, 0, 2)}

