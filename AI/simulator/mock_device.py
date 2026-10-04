"""Synthetic test device for development only; never represents human research data."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import httpx
from synthetic import GeneratorConfig, ParticipantProfile, Scenario, SyntheticGenerator, SyntheticSession


ALIASES = {"normal": Scenario.NORMAL_REST, "movement_only": Scenario.NORMAL_ACTIVITY, "attention_mock": Scenario.ELEVATED_AROUSAL_PROXY, "poor_signal": Scenario.POOR_SIGNAL, "repetitive_movement": Scenario.REPETITIVE_MOVEMENT, "transition": Scenario.TRANSITION, "disconnect_reconnect": Scenario.DISCONNECT_RECONNECT}


async def replay(session: SyntheticSession, backend_url: str, speed: float = 1.0, send_raw: bool = False, disconnect_after: int | None = None, disconnect_seconds: float = 2.0) -> None:
    print("SYNTHETIC TEST DATA — not research, validation, ASD, or clinical data")
    async with httpx.AsyncClient(base_url=backend_url, timeout=10) as client:
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
            response = await client.post("/api/v1/telemetry", json=payload); response.raise_for_status()
            print(json.dumps({"timestamp_ms": payload["timestamp_ms"], "state": payload["prediction"]["state"], "data_origin": payload["data_origin"]}))


def build_session(args: argparse.Namespace) -> SyntheticSession:
    if args.replay:
        return SyntheticSession.load(args.replay)
    config = GeneratorConfig(duration_s=args.duration, random_seed=args.seed)
    scenario = ALIASES[args.scenario]
    return SyntheticGenerator(config).generate(ParticipantProfile(), "SYN-SESSION001", scenario)


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
