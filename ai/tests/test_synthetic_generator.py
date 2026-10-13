import numpy as np
from pathlib import Path
import json
from synthetic import GeneratorConfig, ParticipantProfile, Scenario, SyntheticGenerator
from synthetic.validation import validate_session


def make(scenario=Scenario.NORMAL_REST, seed=7, participant="SYN-P001"):
    config = GeneratorConfig(duration_s=5, random_seed=seed)
    return SyntheticGenerator(config).generate(ParticipantProfile(participant_id=participant), "SYN-SESSION001", scenario)


def test_all_required_scenarios_generate():
    for scenario in (Scenario.NORMAL_REST, Scenario.NORMAL_ACTIVITY, Scenario.REPETITIVE_MOVEMENT, Scenario.ELEVATED_AROUSAL_PROXY, Scenario.POOR_SIGNAL, Scenario.TRANSITION):
        assert not validate_session(make(scenario))


def test_counts_rates_and_timestamp_order():
    session = make(); rates = session.metadata["sampling_rates"]
    assert len(session.streams["ppg"]["red"]) == 5 * rates["ppg_hz"]
    assert len(session.streams["imu"]["ax"]) == 5 * rates["imu_hz"]
    assert len(session.streams["gsr"]["adc"]) == 5 * rates["gsr_hz"]
    assert np.all(np.diff(session.streams["ppg"]["timestamps_ms"]) >= 0)


def test_ppg_hr_internal_consistency():
    session = make(); hr = np.array(session.streams["ppg"]["hr_bpm_reference"])
    assert 40 <= hr.mean() <= 190
    assert max(x for x in session.streams["ppg"]["ir"] if x is not None) > min(x for x in session.streams["ppg"]["ir"] if x is not None)


def test_movement_couples_to_ppg_quality():
    rest = make(Scenario.NORMAL_REST); movement = make(Scenario.REPETITIVE_MOVEMENT)
    rest_q = np.mean([x["signal_quality"]["ppg"] for x in rest.telemetry])
    movement_q = np.mean([x["signal_quality"]["ppg"] for x in movement.telemetry])
    assert movement_q < rest_q


def test_individual_baselines_differ():
    a = SyntheticGenerator(GeneratorConfig(duration_s=3, random_seed=3)).generate(ParticipantProfile(participant_id="SYN-P001", resting_hr_bpm=65), "S1", Scenario.NORMAL_REST)
    b = SyntheticGenerator(GeneratorConfig(duration_s=3, random_seed=3)).generate(ParticipantProfile(participant_id="SYN-P002", resting_hr_bpm=85), "S2", Scenario.NORMAL_REST)
    assert np.mean(a.streams["ppg"]["hr_bpm_reference"]) < np.mean(b.streams["ppg"]["hr_bpm_reference"])


def test_configured_dataset_has_distinct_participants_and_sessions(tmp_path: Path):
    config = GeneratorConfig(participants=2, sessions_per_participant=2, duration_s=1, random_seed=19)
    paths = SyntheticGenerator(config).generate_dataset(tmp_path)
    assert len(paths) == 4
    manifests = [path.read_text(encoding="utf-8") for _, path in paths]
    assert any("SYN-P001" in value for value in manifests)
    assert any("SYN-P002" in value for value in manifests)


def test_ranges_and_invalid_representation():
    session = make(Scenario.POOR_SIGNAL)
    for key in ("red", "ir"):
        valid = [x for x in session.streams["ppg"][key] if x is not None]
        assert valid and all(np.isfinite(valid)) and min(valid) >= 0 and max(valid) <= 262143
    valid_gsr = [x for x in session.streams["gsr"]["adc"] if x is not None]
    assert valid_gsr and all(np.isfinite(valid_gsr)) and min(valid_gsr) >= 0 and max(valid_gsr) <= 4095


def test_transition_is_gradual():
    session = make(Scenario.TRANSITION)
    hr = np.array(session.streams["ppg"]["hr_bpm_reference"])
    assert abs(np.diff(hr)).max() < 15


def test_config_can_load_from_json(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"duration_s": 7, "random_seed": 123, "sampling": {"ppg_hz": 80, "imu_hz": 40, "gsr_hz": 10, "telemetry_hz": 1}}), encoding="utf-8")
    loaded = GeneratorConfig.from_json(path)
    assert loaded.duration_s == 7 and loaded.sampling.ppg_hz == 80
