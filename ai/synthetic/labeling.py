from .scenarios import Scenario


EXPERIMENTAL_STATE_MAPPING = {
    Scenario.NORMAL_REST: "NORMAL",
    Scenario.NORMAL_ACTIVITY: "NORMAL",
    Scenario.REPETITIVE_MOVEMENT: "NORMAL",
    Scenario.ELEVATED_AROUSAL_PROXY: "ATTENTION",
    Scenario.POOR_SIGNAL: "UNCERTAIN",
    Scenario.TRANSITION: "CALIBRATING",
    Scenario.DISCONNECT_RECONNECT: "NORMAL",
}


LEAKAGE_FIELDS = {"scenario", "participant_id", "session_id", "prediction_state", "prediction_probability", "random_seed"}


def experimental_state(scenario: Scenario, minimum_quality: float) -> str:
    if minimum_quality < 0.35:
        return "UNCERTAIN"
    return EXPERIMENTAL_STATE_MAPPING[scenario]

