from synthetic import GeneratorConfig, ParticipantProfile, Scenario, SyntheticGenerator


def generate(seed):
    return SyntheticGenerator(GeneratorConfig(duration_s=2, random_seed=seed)).generate(ParticipantProfile(), "SYN-SESSION001", Scenario.NORMAL_ACTIVITY)


def test_identical_seed_reproduces_signals():
    assert generate(42).streams == generate(42).streams


def test_different_seed_changes_signals():
    assert generate(42).streams != generate(43).streams


def test_sessions_are_not_identical_with_seed_offset():
    generator = SyntheticGenerator(GeneratorConfig(duration_s=2, random_seed=42))
    a = generator.generate(ParticipantProfile(), "S1", Scenario.NORMAL_REST, seed_offset=0)
    b = generator.generate(ParticipantProfile(), "S2", Scenario.NORMAL_REST, seed_offset=1)
    assert a.streams != b.streams

