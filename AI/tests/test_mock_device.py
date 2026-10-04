from argparse import Namespace
from simulator.mock_device import ALIASES, build_session


def args(scenario: str):
    return Namespace(replay=None, duration=2, seed=5, scenario=scenario)


def test_named_mock_scenarios_follow_contract():
    expected = {"normal": "NORMAL", "movement_only": "NORMAL", "attention_mock": "ATTENTION", "poor_signal": "UNCERTAIN"}
    for name, state in expected.items():
        session = build_session(args(name))
        assert session.telemetry[0]["data_origin"] == "SYNTHETIC"
        assert session.telemetry[-1]["prediction"]["state"] == state

