"""Thiết bị giả lập để thử phần mềm, không phải dữ liệu người thật."""
import argparse
import asyncio
import json
import os
import time
from uuid import uuid4
from pathlib import Path
import httpx
from synthetic import GeneratorConfig, ParticipantProfile, Scenario, SyntheticGenerator, SyntheticSession


ALIASES = {"normal": Scenario.NORMAL_REST, "movement_only": Scenario.NORMAL_ACTIVITY, "attention_mock": Scenario.ELEVATED_AROUSAL_PROXY, "poor_signal": Scenario.POOR_SIGNAL, "repetitive_movement": Scenario.REPETITIVE_MOVEMENT, "transition": Scenario.TRANSITION, "disconnect_reconnect": Scenario.DISCONNECT_RECONNECT}


async def replay(session: SyntheticSession, backend_url: str, speed: float = 1.0, send_raw: bool = False, disconnect_after: int | None = None, disconnect_seconds: float = 2.0, device_token: str | None = None, operator_token: str | None = None) -> None:
    print("SYNTHETIC TEST DATA — not research, validation, ASD, or clinical data")
    device_token = device_token or os.getenv("DEVICE_HTTP_TOKEN")
    operator_token = operator_token or os.getenv("OPERATOR_TOKEN")
    if not device_token or not operator_token:
        raise ValueError("Cần DEVICE_HTTP_TOKEN và OPERATOR_TOKEN từ file local, không đặt trong mã nguồn")
    if not session.telemetry:
        raise ValueError("Phiên giả lập không có telemetry")
    first = session.telemetry[0]
    common = {"control_version": "1.0", "device_id": first["device_id"], "data_origin": "SYNTHETIC",
              "boot_id": uuid4().hex, "connection_id": uuid4().hex}
    current_ack = None
    last_sync = 0.0
    async with httpx.AsyncClient(base_url=backend_url, timeout=10, headers={"Authorization": f"Bearer {device_token}"}) as client:
        async def synchronize(actual, session_id, timestamp):
            nonlocal current_ack, last_sync
            request_id = uuid4().hex
            if current_ack:
                current_ack = current_ack | {"connection_id": common["connection_id"], "request_id": request_id}
            request = common | {"message_type": "STATE_REQUEST", "request_id": request_id, "actual_state": actual,
                "session_id": session_id, "last_command_id": current_ack["command_id"] if current_ack else None,
                "last_generation": current_ack["generation"] if current_ack else 0, "timestamp_ms": timestamp, "last_ack": current_ack}
            result = await client.post("/api/v1/devices/sync", json=request)
            result.raise_for_status()
            last_sync = time.monotonic()
            return result.json()
        await synchronize("IDLE", None, 0)
        start = await client.post("/api/v1/sessions/start", json={"session_id": first["session_id"], "device_id": first["device_id"]}, headers={"Authorization": f"Bearer {operator_token}"})
        start.raise_for_status()
        state = await synchronize("IDLE", None, 0)
        command = state["pending_command"]
        if not command or command["action"] != "START":
            raise ValueError("Không nhận được Start mới; dùng session_id duy nhất cho mỗi lần replay")
        current_ack = {key: command[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id", "request_id", "command_id", "generation", "session_id", "action")}
        current_ack.update(message_type="ACK", result="STARTED", timestamp_ms=0, reason=None, final_summary=None)
        accepted = await client.post("/api/v1/devices/ack", json=current_ack)
        accepted.raise_for_status()
        state = await synchronize("RECORDING", first["session_id"], 0)
        if state["accepted_command_id"] != current_ack["command_id"]:
            raise ValueError("Backend chưa xác nhận Start ACK")
        if send_raw:
            for batch in session.raw_batches():
                response = await client.post("/api/v1/raw-batch", json=batch); response.raise_for_status()
        previous = 0
        for index, payload in enumerate(session.telemetry):
            if disconnect_after is not None and index == disconnect_after:
                print(f"Simulated network loss ({disconnect_seconds}s); acquisition timeline remains intact")
                await asyncio.sleep(disconnect_seconds)
            delay = max(0, (payload["timestamp_ms"] - previous) / 1000 / max(speed, 0.01))
            await asyncio.sleep(delay); previous = payload["timestamp_ms"]
            if time.monotonic() - last_sync > 10:
                await synchronize("RECORDING", first["session_id"], previous)
            response = await client.post("/api/v1/telemetry", json=payload); response.raise_for_status()
            print(json.dumps({"timestamp_ms": payload["timestamp_ms"], "state": payload["prediction"]["state"], "data_origin": payload["data_origin"]}))
        stopped = await client.post("/api/v1/sessions/stop", json={"session_id": first["session_id"]}, headers={"Authorization": f"Bearer {operator_token}"})
        stopped.raise_for_status()
        state = await synchronize("RECORDING", first["session_id"], previous)
        command = state["pending_command"]
        ack = {key: command[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id", "request_id", "command_id", "generation", "session_id", "action")}
        summary = {"cutoff_timestamp_ms": 0, "final_batch_id": None, "total_generated_batches": 0, "dropped_batches": 0,
            "slot_counts": {"ppg": 0, "imu": 0, "gsr": 0}, "missing_samples": {"ppg": 0, "imu": 0, "gsr": 0},
            "dropped_batch_ranges": [], "loss_ranges_truncated": False, "raw_recording_enabled": False}
        if send_raw:
            batches = list(session.raw_batches())
            last = batches[-1]
            cutoff = last["start_timestamp_ms"] + len(last["ppg"]["red"]) * 1000 // last["ppg"]["sample_rate_hz"]
            summary.update(cutoff_timestamp_ms=cutoff, final_batch_id=len(batches)-1, total_generated_batches=len(batches), raw_recording_enabled=True,
                slot_counts={name: sum(len(batch[name][array]) for batch in batches) for name, array in (("ppg", "red"), ("imu", "ax"), ("gsr", "adc"))},
                missing_samples={name: sum(sum(value is None for value in batch[name][array]) for batch in batches) for name, array in (("ppg", "red"), ("imu", "ax"), ("gsr", "adc"))})
        ack.update(message_type="ACK", result="STOPPED", timestamp_ms=summary["cutoff_timestamp_ms"], reason=None, final_summary=summary)
        result = await client.post("/api/v1/devices/ack", json=ack)
        result.raise_for_status()
        current_ack = ack
        await synchronize("STOPPED", first["session_id"], summary["cutoff_timestamp_ms"])


def build_session(args: argparse.Namespace) -> SyntheticSession:
    if args.replay:
        return SyntheticSession.load(args.replay)
    config = GeneratorConfig(duration_s=args.duration, random_seed=args.seed)
    scenario = ALIASES[args.scenario]
    return SyntheticGenerator(config).generate(ParticipantProfile(), "SYN-" + uuid4().hex, scenario)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate/replay SYNTHETIC TEST DATA")
    parser.add_argument("--scenario", choices=sorted(ALIASES), default="normal")
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--seed", type=int, default=20261004)
    parser.add_argument("--backend-url", default=os.getenv("BACKEND_URL", "http://localhost:8000"))
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--generate-dataset", action="store_true", help="Generate all configured participant/session files without replay")
    parser.add_argument("--send-raw", action="store_true")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()
    if args.generate_dataset:
        config = GeneratorConfig(duration_s=args.duration, random_seed=args.seed)
        paths = SyntheticGenerator(config).generate_dataset(Path(__file__).parents[1] / "data" / "synthetic")
        print(f"Generated {len(paths)} SYNTHETIC TEST DATA sessions")
        return
    session = build_session(args)
    if args.save:
        print(session.save(Path(__file__).parents[1] / "data" / "synthetic")[0])
    disconnect_after = 3 if args.scenario == "disconnect_reconnect" else None
    asyncio.run(replay(session, args.backend_url, args.speed, args.send_raw, disconnect_after))


if __name__ == "__main__":
    main()
