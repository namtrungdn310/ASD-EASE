from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
from . import physiology
from .artifacts import apply_dropout, quality
from .config import GeneratorConfig, ParticipantProfile
from .labeling import experimental_state
from .motion import imu_signals
from .scenarios import Scenario, latent_variables

GENERATOR_VERSION = "0.1.0"


@dataclass
class SyntheticSession:
    metadata: dict
    streams: dict
    telemetry: list[dict]

    def raw_batches(self, window_s: float = 1.0) -> list[dict]:
        rates = self.metadata["sampling_rates"]
        duration = self.metadata["duration_s"]
        batches = []
        for batch_id, start in enumerate(np.arange(0, duration, window_s)):
            def segment(stream: str, key: str):
                rate = rates[f"{stream}_hz"]
                lo, hi = int(start * rate), int(min(duration, start + window_s) * rate)
                return self.streams[stream][key][lo:hi]
            batches.append({
                "schema_version": self.metadata["schema_version"], "device_id": "SIM-001",
                "session_id": self.metadata["session_id"], "batch_id": batch_id,
                "start_timestamp_ms": int(start * 1000), "data_origin": "SYNTHETIC",
                "ppg": {"sample_rate_hz": rates["ppg_hz"], "red": segment("ppg", "red"), "ir": segment("ppg", "ir")},
                "imu": {"sample_rate_hz": rates["imu_hz"], **{key: segment("imu", key) for key in ("ax", "ay", "az", "gx", "gy", "gz")}},
                "gsr": {"sample_rate_hz": rates["gsr_hz"], "adc": segment("gsr", "adc")},
            })
        return batches

    def save(self, root: str | Path) -> tuple[Path, Path]:
        root = Path(root)
        raw_dir, manifest_dir = root / "raw", root / "manifests"
        raw_dir.mkdir(parents=True, exist_ok=True); manifest_dir.mkdir(parents=True, exist_ok=True)
        session_path = raw_dir / f"{self.metadata['session_id']}.json"
        manifest_path = manifest_dir / f"{self.metadata['session_id']}.manifest.json"
        session_path.write_text(json.dumps({"metadata": self.metadata, "streams": self.streams, "telemetry": self.telemetry}, indent=2), encoding="utf-8")
        manifest_path.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")
        return session_path, manifest_path

    @classmethod
    def load(cls, path: str | Path) -> "SyntheticSession":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**payload)


class SyntheticGenerator:
    def __init__(self, config: GeneratorConfig):
        self.config = config

    def generate(self, profile: ParticipantProfile, session_id: str, scenario: Scenario, seed_offset: int = 0) -> SyntheticSession:
        rng = np.random.default_rng(self.config.random_seed + seed_offset)
        effective_profile = replace(profile, noise_gain=profile.noise_gain * self.config.noise_intensity)
        duration, rates = self.config.duration_s, self.config.sampling
        master_rate = max(rates.ppg_hz, rates.imu_hz, rates.gsr_hz, rates.telemetry_hz)
        master_t = np.arange(0, duration, 1 / master_rate)
        latent = latent_variables(scenario, master_t, self.config.transition_duration_s)

        def at(rate: int, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            t = np.arange(0, duration, 1 / rate)
            if self.config.sampling_jitter_fraction:
                jitter = rng.normal(0, self.config.sampling_jitter_fraction / rate, t.size); jitter[0] = 0
                t = np.maximum.accumulate(np.clip(t + jitter, 0, duration - 1e-9))
            return t, np.interp(t, master_t, values)

        ppg_t, ppg_activity = at(rates.ppg_hz, latent["activity"])
        _, ppg_activation = at(rates.ppg_hz, latent["activation"]); _, ppg_contact = at(rates.ppg_hz, latent["contact"])
        hr = physiology.heart_rate(ppg_t, effective_profile, ppg_activation, ppg_activity, rng)

        imu_t, imu_activity = at(rates.imu_hz, latent["activity"]); _, imu_periodic = at(rates.imu_hz, latent["periodic"])
        imu = imu_signals(imu_t, imu_activity, imu_periodic, effective_profile, rng)
        ppg_motion = np.interp(ppg_t, imu_t, imu["motion"])
        red, ir = physiology.ppg_waveforms(ppg_t, hr, ppg_contact * effective_profile.contact_quality, ppg_motion, effective_profile, self.config.artifact_frequency, rng)

        gsr_t, gsr_activation = at(rates.gsr_hz, latent["activation"]); _, gsr_contact = at(rates.gsr_hz, latent["contact"])
        gsr = physiology.gsr_signal(gsr_t, effective_profile, gsr_activation, gsr_contact * effective_profile.contact_quality, rng)
        ppg_q = quality(ppg_contact * effective_profile.contact_quality, ppg_motion, self.config.noise_intensity)
        imu_q = np.clip(0.99 - 0.08 * imu["motion"], 0, 1)
        gsr_q = np.clip(gsr_contact * effective_profile.contact_quality - 0.02 * self.config.noise_intensity, 0, 1)

        dropout = self.config.sensor_dropout_frequency * (4 if scenario == Scenario.POOR_SIGNAL else 1)
        streams = {
            "ppg": {"timestamps_ms": np.rint(ppg_t * 1000).astype(int).tolist(), "red": apply_dropout(red, dropout, rng), "ir": apply_dropout(ir, dropout, rng), "hr_bpm_reference": hr.round(4).tolist()},
            "imu": {"timestamps_ms": np.rint(imu_t * 1000).astype(int).tolist(), **{k: apply_dropout(imu[k], dropout, rng) for k in ("ax", "ay", "az", "gx", "gy", "gz")}},
            "gsr": {"timestamps_ms": np.rint(gsr_t * 1000).astype(int).tolist(), "adc": apply_dropout(gsr, dropout, rng)},
        }
        telemetry = []
        for index, time_s in enumerate(np.arange(0, duration, 1 / rates.telemetry_hz)):
            ppg_idx = min(int(time_s * rates.ppg_hz), len(hr) - 1); imu_idx = min(int(time_s * rates.imu_hz), len(imu["motion"]) - 1); gsr_idx = min(int(time_s * rates.gsr_hz), len(gsr) - 1)
            q = {"ppg": float(ppg_q[ppg_idx]), "gsr": float(gsr_q[gsr_idx]), "imu": float(imu_q[imu_idx])}
            state = experimental_state(scenario, min(q.values()))
            probability = None if state in {"UNCERTAIN", "CALIBRATING"} else float(np.clip(0.12 + 0.68 * ppg_activation[ppg_idx] + rng.normal(0, 0.04), 0.02, 0.95))
            telemetry.append({"schema_version": self.config.schema_version, "device_id": "SIM-001", "session_id": session_id, "timestamp_ms": int(time_s * 1000), "data_origin": "SYNTHETIC", "hr_bpm": round(float(hr[ppg_idx]), 3), "gsr": {"raw": int(gsr[gsr_idx]), "delta": round(float((gsr[gsr_idx] - profile.gsr_baseline_adc) / max(profile.gsr_baseline_adc, 1)), 5)}, "movement": {"score": round(float(np.clip(imu["motion"][imu_idx], 0, 1)), 5)}, "signal_quality": {k: round(v, 5) for k, v in q.items()}, "prediction": {"probability": None if probability is None else round(probability, 5), "state": state}, "firmware_version": "simulator-0.1.0", "model_version": "none"})
        metadata = {"data_origin": "SYNTHETIC", "generator_version": GENERATOR_VERSION, "generator_config": self.config.to_dict(), "random_seed": self.config.random_seed + seed_offset, "schema_version": self.config.schema_version, "participant_id": profile.participant_id, "session_id": session_id, "scenario": scenario.value, "sampling_rates": asdict(rates), "duration_s": duration, "created_at": datetime.now(timezone.utc).isoformat(), "scientific_limit": "Engineering approximation; not real ASD data or clinical evidence."}
        return SyntheticSession(metadata, streams, telemetry)

    def generate_dataset(self, root: str | Path) -> list[tuple[Path, Path]]:
        """Generate configured participants/trials with distinct profiles and seeds."""
        scenario_names = list(self.config.scenario_distribution)
        weights = np.array(list(self.config.scenario_distribution.values()), dtype=float)
        if not scenario_names or np.any(weights < 0) or weights.sum() <= 0:
            raise ValueError("scenario_distribution must contain positive total weight")
        weights /= weights.sum()
        selector = np.random.default_rng(self.config.random_seed)
        outputs: list[tuple[Path, Path]] = []
        for participant_index in range(self.config.participants):
            profile_rng = np.random.default_rng(self.config.random_seed + 10_000 + participant_index)
            profile = ParticipantProfile(
                participant_id=f"SYN-P{participant_index + 1:03d}",
                resting_hr_bpm=float(np.clip(profile_rng.normal(72, 72 * self.config.baseline_variation * 0.75), 50, 100)),
                hr_variability_bpm=float(np.clip(profile_rng.normal(3, 0.8), 1, 6)),
                gsr_baseline_adc=float(np.clip(profile_rng.normal(1800, 1800 * self.config.baseline_variation), 700, 3200)),
                gsr_response_gain=float(np.clip(profile_rng.normal(130, 30), 50, 240)),
                movement_gain=float(np.clip(profile_rng.normal(1, 0.18), 0.6, 1.5)),
                contact_quality=float(np.clip(profile_rng.normal(0.9, 0.06), 0.65, 1.0)),
                noise_gain=float(np.clip(profile_rng.normal(1, 0.15), 0.6, 1.5)),
                response_delay_s=float(np.clip(profile_rng.normal(2.2, 0.7), 0.5, 5.0)),
            )
            for trial in range(self.config.sessions_per_participant):
                ordinal = participant_index * self.config.sessions_per_participant + trial
                scenario = Scenario(str(selector.choice(scenario_names, p=weights)))
                session_id = f"SYN-SESSION{ordinal + 1:03d}"
                outputs.append(self.generate(profile, session_id, scenario, seed_offset=ordinal).save(root))
        return outputs
