"""Phát simulator qua HTTP -> backend -> WebSocket với DB kiểm thử riêng.

Chạy bằng môi trường Python dự án từ thư mục bất kỳ. Không sửa DB, raw
hoặc dịch vụ đang dùng. Đây không phải kiểm thử trình duyệt.
"""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import secrets

import httpx
import websockets

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai"))
from simulator.mock_device import replay  # noqa: E402
from synthetic import GeneratorConfig, ParticipantProfile, Scenario, SyntheticGenerator  # noqa: E402


async def verify(base_url: str, ws_url: str, device_token: str, operator_token: str) -> None:
    generator = SyntheticGenerator(GeneratorConfig(duration_s=6, random_seed=20261004))
    scenarios = [Scenario.NORMAL_REST, Scenario.POOR_SIGNAL, Scenario.DISCONNECT_RECONNECT]
    headers = {"Authorization": f"Bearer {operator_token}"}
    async with httpx.AsyncClient(base_url=base_url, timeout=10, headers={"Authorization": f"Bearer {device_token}"}) as client:
        async with websockets.connect(ws_url, additional_headers=headers) as connection:
            # Gói sai schema phải bị từ chối, không phát sang WebSocket.
            invalid = await client.post("/api/v1/telemetry", json={"schema_version": "broken"})
            assert invalid.status_code == 422, invalid.text
            try:
                await asyncio.wait_for(connection.recv(), timeout=0.2)
            except asyncio.TimeoutError:
                pass
            else:
                raise AssertionError("invalid payload was broadcast")

            for index, scenario in enumerate(scenarios):
                session = generator.generate(ParticipantProfile(), f"SYN-TRANSPORT-{index}", scenario)
                expected = session.telemetry
                received = []
                receipt_times = []

                async def collect() -> None:
                    for _ in expected:
                        received.append(json.loads(await asyncio.wait_for(connection.recv(), timeout=15)))
                        receipt_times.append(time.monotonic())

                collector = asyncio.create_task(collect())
                try:
                    await replay(
                        session, base_url, speed=20,
                        disconnect_after=3 if scenario == Scenario.DISCONNECT_RECONNECT else None,
                        disconnect_seconds=2,
                        device_token=device_token, operator_token=operator_token,
                    )
                    await collector
                finally:
                    if not collector.done():
                        collector.cancel()
                        await asyncio.gather(collector, return_exceptions=True)
                assert received == expected, f"wire payload mismatch: {scenario.value}"
                assert all(item["data_origin"] == "SYNTHETIC" for item in received)
                assert [item["timestamp_ms"] for item in received] == sorted(item["timestamp_ms"] for item in received)
                if scenario == Scenario.DISCONNECT_RECONNECT:
                    assert receipt_times[3] - receipt_times[2] >= 1.8, "transport pause missing"
                    assert received[3]["timestamp_ms"] - received[2]["timestamp_ms"] == 1000, "acquisition timeline changed by pause"
                print(f"PASS {scenario.value}: {len(received)} HTTP payloads exactly matched live WebSocket messages")

        # Mở lại kết nối nhận và kiểm tra có dữ liệu mới.
        async with websockets.connect(ws_url, additional_headers=headers) as reconnected:
            session = SyntheticGenerator(GeneratorConfig(duration_s=1)).generate(ParticipantProfile(), "SYN-RECONNECTED", Scenario.NORMAL_REST)
            expected = session.telemetry[0]
            await replay(session, base_url, speed=20, device_token=device_token, operator_token=operator_token)
            assert json.loads(await asyncio.wait_for(reconnected.recv(), timeout=5)) == expected
            print("PASS subscriber reconnect: HTTP 202 and exact WebSocket payload")


def main() -> None:
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with TemporaryDirectory(prefix="asd-ease-transport-") as temporary:
        scratch = Path(temporary)
        device_token, operator_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        registry = scratch / "registry.json"
        registry.write_text(json.dumps([{"device_id": "SIM-001", "data_origin": "SYNTHETIC", "mqtt_username": "simulator",
            "http_token": device_token, "transport": "http", "acquisition_profile": {"ppg_hz": 100, "imu_hz": 50, "gsr_hz": 20, "window_ms": 1000}}]))
        environment = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{(scratch / 'transport.db').as_posix()}",
            "RAW_STORAGE_DIR": str(scratch / "raw"),
            "PYTHONIOENCODING": "utf-8",
            "OPERATOR_TOKEN": operator_token, "COOKIE_SECRET": secrets.token_urlsafe(32), "COOKIE_SECURE": "false",
            "ALLOW_INSECURE_LOCAL": "true", "MQTT_ENABLED": "false", "DEVICE_REGISTRY_FILE": str(registry),
        }
        backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=ROOT / "backend", env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 20
            while True:
                if backend.poll() is not None:
                    raise RuntimeError("isolated backend exited during startup")
                try:
                    if httpx.get(f"{base_url}/api/v1/health", timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError("isolated backend health check timed out")
                time.sleep(0.1)
            asyncio.run(verify(base_url, f"ws://127.0.0.1:{port}/api/v1/ws/live", device_token, operator_token))
            print("PASS transport integration; temporary backend stopped, browser behavior NOT VERIFIED")
        finally:
            backend.terminate()
            try:
                output, _ = backend.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                backend.kill()
                output, _ = backend.communicate(timeout=5)
            if sys.exc_info()[0] is not None:
                print(output.decode("utf-8", errors="replace"), file=sys.stderr)


if __name__ == "__main__":
    main()
