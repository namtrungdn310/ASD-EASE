from dataclasses import asdict, dataclass, field
import json
from pathlib import Path


@dataclass(frozen=True)
class SamplingRates:
    ppg_hz: int = 100
    imu_hz: int = 50
    gsr_hz: int = 20
    telemetry_hz: int = 1


@dataclass(frozen=True)
class ParticipantProfile:
    participant_id: str = "SYN-P001"
    resting_hr_bpm: float = 72.0
    hr_variability_bpm: float = 2.5
    gsr_baseline_adc: float = 1800.0
    gsr_response_gain: float = 120.0
    movement_gain: float = 1.0
    contact_quality: float = 0.95
    noise_gain: float = 1.0
    response_delay_s: float = 2.0


@dataclass(frozen=True)
class GeneratorConfig:
    participants: int = 2
    sessions_per_participant: int = 2
    duration_s: float = 30.0
    sampling: SamplingRates = field(default_factory=SamplingRates)
    scenario_distribution: dict[str, float] = field(default_factory=lambda: {
        "NORMAL_REST": 0.25, "NORMAL_ACTIVITY": 0.2, "REPETITIVE_MOVEMENT": 0.2,
        "ELEVATED_AROUSAL_PROXY": 0.2, "POOR_SIGNAL": 0.1, "TRANSITION": 0.05,
    })
    noise_intensity: float = 1.0
    artifact_frequency: float = 0.03
    sensor_dropout_frequency: float = 0.005
    baseline_variation: float = 0.15
    transition_duration_s: float = 8.0
    sampling_jitter_fraction: float = 0.0
    random_seed: int = 20261004
    schema_version: str = "1.0"

    @classmethod
    def from_json(cls, path: str | Path) -> "GeneratorConfig":
        values = json.loads(Path(path).read_text(encoding="utf-8"))
        if "sampling" in values:
            values["sampling"] = SamplingRates(**values["sampling"])
        return cls(**values)

    def to_dict(self) -> dict:
        return asdict(self)

