from pydantic import TypeAdapter
from synthetic import GeneratorConfig, ParticipantProfile, Scenario, SyntheticGenerator
from src.preprocessing import normalize_raw_batch


def session():
    return SyntheticGenerator(GeneratorConfig(duration_s=2, random_seed=11)).generate(ParticipantProfile(), "SYN-SESSION001", Scenario.NORMAL_REST)


def test_raw_batch_serialization_and_preprocessing():
    batch = session().raw_batches()[0]
    normalized = normalize_raw_batch(batch)
    assert normalized["ppg"]["sample_rate_hz"] == 100
    assert normalized["imu"]["ax"].shape == (50,)


def test_contract_marker_is_not_spoofed():
    s = session()
    assert all(x["data_origin"] == "SYNTHETIC" for x in s.telemetry)
    assert all(x["data_origin"] == "SYNTHETIC" for x in s.raw_batches())

