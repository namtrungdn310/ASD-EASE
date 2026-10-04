from enum import StrEnum
import numpy as np


class Scenario(StrEnum):
    NORMAL_REST = "NORMAL_REST"
    NORMAL_ACTIVITY = "NORMAL_ACTIVITY"
    REPETITIVE_MOVEMENT = "REPETITIVE_MOVEMENT"
    ELEVATED_AROUSAL_PROXY = "ELEVATED_AROUSAL_PROXY"
    POOR_SIGNAL = "POOR_SIGNAL"
    TRANSITION = "TRANSITION"
    DISCONNECT_RECONNECT = "DISCONNECT_RECONNECT"


def latent_variables(scenario: Scenario, timeline: np.ndarray, transition_s: float) -> dict[str, np.ndarray]:
    n = timeline.size
    activity = np.full(n, 0.08)
    activation = np.full(n, 0.10)
    contact = np.full(n, 0.95)
    periodic = np.zeros(n)
    if scenario == Scenario.NORMAL_ACTIVITY:
        activity = 0.42 + 0.12 * np.sin(2 * np.pi * 0.12 * timeline)
        activation = 0.20 + 0.06 * np.sin(2 * np.pi * 0.03 * timeline)
    elif scenario == Scenario.REPETITIVE_MOVEMENT:
        activity[:] = 0.38
        periodic[:] = 0.85
        activation[:] = 0.16
    elif scenario == Scenario.ELEVATED_AROUSAL_PROXY:
        onset = max(1.0, timeline[-1] * 0.25 if n > 1 else 1.0)
        activation = 0.15 + 0.62 / (1 + np.exp(-(timeline - onset) / 2.2))
        activity = 0.10 + 0.12 / (1 + np.exp(-(timeline - onset - 4) / 2.5))
    elif scenario == Scenario.POOR_SIGNAL:
        activity = 0.30 + 0.18 * np.sin(2 * np.pi * 0.25 * timeline)
        contact = 0.25 + 0.12 * np.sin(2 * np.pi * 0.07 * timeline)
    elif scenario == Scenario.TRANSITION:
        midpoint = timeline[-1] / 2 if n > 1 else 0
        width = max(0.5, transition_s / 5)
        ramp = 1 / (1 + np.exp(-(timeline - midpoint) / width))
        activity = 0.08 + 0.22 * ramp
        activation = 0.10 + 0.52 * ramp
        contact = 0.95 - 0.12 * ramp
    elif scenario == Scenario.DISCONNECT_RECONNECT:
        activity[:] = 0.12
    return {"activity": np.clip(activity, 0, 1), "activation": np.clip(activation, 0, 1), "contact": np.clip(contact, 0, 1), "periodic": periodic}

