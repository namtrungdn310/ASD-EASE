import numpy as np
from .config import ParticipantProfile


def heart_rate(t: np.ndarray, profile: ParticipantProfile, activation: np.ndarray, activity: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    slow = 1.2 * np.sin(2 * np.pi * 0.035 * t + rng.uniform(0, 2 * np.pi))
    variation = rng.normal(0, profile.hr_variability_bpm * 0.12, t.size)
    return np.clip(profile.resting_hr_bpm + 21 * activation + 18 * activity + slow + variation, 40, 190)


def ppg_waveforms(t: np.ndarray, hr: np.ndarray, contact: np.ndarray, motion: np.ndarray, profile: ParticipantProfile, artifact_events_per_s: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    phase = np.cumsum((hr / 60) / max(1, len(t) / max(t[-1], 1e-6)))
    cycle = phase % 1.0
    systolic = np.exp(-((cycle - 0.12) / 0.055) ** 2)
    dicrotic = 0.28 * np.exp(-((cycle - 0.34) / 0.08) ** 2)
    pulse = systolic + dicrotic
    drift = 450 * np.sin(2 * np.pi * 0.04 * t)
    rate = max(1.0, len(t) / max(t[-1], 1e-6))
    starts = rng.random(t.size) < max(0, artifact_events_per_s) / rate
    decay = np.exp(-np.arange(max(2, int(rate * 0.7))) / (rate * 0.18))
    bursts = np.convolve(starts.astype(float), decay, mode="full")[:t.size]
    artifact = motion * (0.2 + bursts) * rng.normal(0, 1500 * profile.noise_gain, t.size)
    red = 72000 + contact * 7500 * pulse + drift + artifact + rng.normal(0, 140 * profile.noise_gain, t.size)
    ir = 90000 + contact * 10500 * pulse + 1.2 * drift + 1.15 * artifact + rng.normal(0, 170 * profile.noise_gain, t.size)
    return np.clip(red, 0, 262143), np.clip(ir, 0, 262143)


def gsr_signal(t: np.ndarray, profile: ParticipantProfile, activation: np.ndarray, contact: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    delayed = np.interp(np.maximum(0, t - profile.response_delay_s), t, activation)
    tonic = profile.gsr_baseline_adc + 35 * np.sin(2 * np.pi * 0.008 * t + 0.5)
    response = profile.gsr_response_gain * delayed
    impulses = rng.random(t.size) < (0.012 / max(1, len(t) / max(t[-1], 1e-6)))
    kernel_t = np.arange(max(2, int(8 * len(t) / max(t[-1], 1e-6)))) / max(1, len(t) / max(t[-1], 1e-6))
    kernel = (1 - np.exp(-kernel_t / 0.7)) * np.exp(-kernel_t / 3.5)
    phasic = np.convolve(impulses.astype(float), kernel, mode="full")[:t.size] * profile.gsr_response_gain * 0.4
    contact_offset = (1 - contact) * rng.normal(0, 280, t.size)
    return np.clip(tonic + response + phasic + contact_offset + rng.normal(0, 4 * profile.noise_gain, t.size), 0, 4095)
