from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from .generator import SyntheticSession


def validate_session(session: SyntheticSession) -> list[str]:
    errors: list[str] = []
    for stream_name, stream in session.streams.items():
        timestamps = stream["timestamps_ms"]
        if any(b < a for a, b in zip(timestamps, timestamps[1:])):
            errors.append(f"{stream_name}: timestamps are not ordered")
    for batch in session.raw_batches():
        if len(batch["ppg"]["red"]) != len(batch["ppg"]["ir"]): errors.append("PPG length mismatch")
    return errors


def diagnostic_plot(session: SyntheticSession, output: str | Path) -> Path:
    fig, axes = plt.subplots(7, 1, figsize=(12, 14), sharex=False)
    ppg, imu, gsr = session.streams["ppg"], session.streams["imu"], session.streams["gsr"]
    axes[0].plot(np.array(ppg["timestamps_ms"]) / 1000, [np.nan if x is None else x for x in ppg["ir"]]); axes[0].set_ylabel("IR counts")
    axes[1].plot(np.array(ppg["timestamps_ms"]) / 1000, ppg["hr_bpm_reference"]); axes[1].set_ylabel("HR bpm")
    axes[2].plot(np.array(gsr["timestamps_ms"]) / 1000, [np.nan if x is None else x for x in gsr["adc"]]); axes[2].set_ylabel("GSR ADC")
    accel = np.sqrt(sum(np.square([np.nan if x is None else x for x in imu[k]]) for k in ("ax", "ay", "az")))
    gyro = np.sqrt(sum(np.square([np.nan if x is None else x for x in imu[k]]) for k in ("gx", "gy", "gz")))
    axes[3].plot(np.array(imu["timestamps_ms"]) / 1000, accel); axes[3].set_ylabel("accel |g|")
    axes[4].plot(np.array(imu["timestamps_ms"]) / 1000, gyro); axes[4].set_ylabel("gyro |dps|")
    telemetry_t = [x["timestamp_ms"] / 1000 for x in session.telemetry]
    axes[5].step(telemetry_t, [1] * len(telemetry_t), where="post"); axes[5].set_yticks([1], [session.metadata["scenario"]]); axes[5].set_ylabel("scenario")
    axes[6].plot(telemetry_t, [x["signal_quality"]["ppg"] for x in session.telemetry], label="PPG"); axes[6].plot(telemetry_t, [x["signal_quality"]["gsr"] for x in session.telemetry], label="GSR"); axes[6].plot(telemetry_t, [x["signal_quality"]["imu"] for x in session.telemetry], label="IMU"); axes[6].legend(); axes[6].set_ylabel("quality")
    fig.suptitle(f"{session.metadata['scenario']} — SYNTHETIC diagnostic only"); fig.tight_layout()
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True); fig.savefig(output, dpi=140); plt.close(fig); return output
