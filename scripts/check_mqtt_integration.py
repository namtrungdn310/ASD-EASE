"""Kiểm thử broker thật, DB/HTTP/WS riêng; không sửa dịch vụ hoặc DB đang dùng."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import time
from uuid import uuid4
import httpx
import paho.mqtt.client as mqtt
import websockets

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "ai"))
from setup_local_mqtt import IMAGE, provision
from simulator.mqtt_device import SyntheticDevice


def docker(*arguments):
    return subprocess.run(["docker", *arguments], check=True, capture_output=True, text=True).stdout.strip()


async def wait_until(predicate, *, timeout=15, message="condition"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await predicate():
            return
        await asyncio.sleep(0.1)
    raise AssertionError(f"Timeout: {message}")


async def verify(base, environment, directory, port, passwords, container, backend_start, backend_stop):
    headers = {"Authorization": f"Bearer {environment['OPERATOR_TOKEN']}"}
    device = SyntheticDevice(json.loads((directory / "simulator.json").read_text()), port=port)
    device.start()
    stop_pump = False
    async def pump():
        while not stop_pump:
            device.step()
            await asyncio.sleep(0.02)
    pump_task = asyncio.create_task(pump())
    async with httpx.AsyncClient(base_url=base, headers=headers) as client:
        async def synchronized():
            result = await client.get("/api/v1/health/mqtt")
            return result.status_code == 200 and result.json()["synchronized_devices"] == 1
        async def state_is(state):
            result = await client.get("/api/v1/sessions")
            return result.status_code == 200 and result.json() and result.json()[0]["state"] == state
        try:
            await wait_until(synchronized, message="sync broker/device/backend")
            for password in (None, "invalid-password-for-test"):
                denied = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="denied-" + uuid4().hex[:8], clean_session=True, reconnect_on_failure=False)
                if password is not None:
                    denied.username_pw_set("simulator", password)
                rejected = threading.Event()
                denied.on_connect = lambda client, userdata, flags, reason, properties: rejected.set() if reason.is_failure else None
                denied.connect("127.0.0.1", port)
                denied.loop_start()
                try:
                    assert await asyncio.to_thread(rejected.wait, 5), "Anonymous/wrong password unexpectedly accepted"
                finally:
                    denied.disconnect()
                    await asyncio.to_thread(denied.loop_stop)
            print("PASS broker authentication: anonymous and wrong password rejected")
            async with websockets.connect(base.replace("http", "ws") + "/api/v1/ws/live", additional_headers=headers) as ws:
                body = {"session_id": "SYN-BROKER-" + uuid4().hex, "device_id": "SIM-001"}
                started = await client.post("/api/v1/sessions/start", json=body)
                assert started.status_code == 202 and started.json()["state"] == "STARTING", started.text
                await wait_until(lambda: state_is("RECORDING"), message="STARTED ACK")
                while True:
                    frame = json.loads(await asyncio.wait_for(ws.recv(), 5))
                    if frame["session_id"] == body["session_id"]:
                        break
                assert frame["data_origin"] == "SYNTHETIC"
                print("PASS real broker: HTTP Start -> MQTT command/ACK -> DB RECORDING -> WebSocket telemetry")
                epoch = device.epoch
                generation = device.generation
                repeated = await client.post("/api/v1/sessions/start", json=body)
                assert repeated.status_code == 200 and repeated.json()["generation"] == generation
                assert device.epoch == epoch
                print("PASS repeated Start: same command/generation, acquisition epoch unchanged")
                # QoS1 thật và ACL: tài khoản thiết bị khác không được gửi telemetry của SIM-001.
                attacker = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="acl-check-" + uuid4().hex[:8], clean_session=True)
                attacker.username_pw_set("simulator-other", passwords["simulator-other"])
                connected = threading.Event()
                attacker.on_connect = lambda *args: connected.set()
                attacker.connect("127.0.0.1", port)
                attacker.loop_start()
                try:
                    assert await asyncio.to_thread(connected.wait, 5)
                    minimum_timestamp = device.timestamp() + 1000
                    poisoned = dict(frame, timestamp_ms=2**52)
                    info = attacker.publish(device.prefix + "telemetry", json.dumps(poisoned), qos=1)
                    await asyncio.to_thread(info.wait_for_publish, 3)
                    await asyncio.sleep(0.3)
                finally:
                    attacker.disconnect()
                    await asyncio.to_thread(attacker.loop_stop)
                # Frame cực lớn nếu lọt ACL sẽ khoá cursor; telemetry hợp lệ sau đó phải tiếp tục tới WS.
                while True:
                    next_frame = json.loads(await asyncio.wait_for(ws.recv(), 5))
                    if next_frame["timestamp_ms"] >= minimum_timestamp:
                        break
                assert next_frame["timestamp_ms"] < 2**52
                print("PASS broker ACL: cross-device publish denied; subsequent valid telemetry accepted")
                # Backend restart: DB giữ phiên/ACK, live map phải được đồng bộ lại.
                await asyncio.to_thread(backend_stop)
                await asyncio.to_thread(backend_start)
                device.next_sync = 0
                await wait_until(synchronized, message="backend restart state sync")
                await wait_until(lambda: state_is("RECORDING"), message="same recording after backend restart")
                assert device.epoch == epoch and device.generation == generation
                print("PASS backend restart: durable session/ACK restored, periodic state synchronization")
                # Broker lỗi không làm mất API tra cứu; reconnect không reset epoch.
                await asyncio.to_thread(docker, "stop", container)
                result = await client.get("/api/v1/sessions")
                assert result.status_code == 200
                await asyncio.to_thread(docker, "start", container)
                await wait_until(synchronized, timeout=45, message="broker restart reconnect")
                assert device.epoch == epoch and device.generation == generation
                print("PASS broker restart: HTTP lookup remains available, clean reconnect preserves acquisition epoch")
                result = await client.post("/api/v1/sessions/stop", json={"session_id": body["session_id"]})
                assert result.status_code == 202
                await wait_until(lambda: state_is("STOPPED"), message="STOPPED ACK")
                row = (await client.get("/api/v1/sessions")).json()[0]
                assert not row["recording_complete"] and row["incomplete_reasons"] == ["RAW_RECORDING_DISABLED"]
                print("PASS real Stop ACK: STOPPED, zero-batch telemetry-only, no false raw completeness")
        finally:
            stop_pump = True
            await pump_task
            await asyncio.to_thread(device.stop)


def main():
    with TemporaryDirectory(prefix="asd-ease-broker-test-") as temporary:
        scratch = Path(temporary)
        local = scratch / "local"
        environment, registry, passwords = provision(local)
        name = "asd-ease-check-" + uuid4().hex[:10]
        backend = None
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            api_port = reservation.getsockname()[1]
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            broker_port = reservation.getsockname()[1]
        log = (scratch / "backend.log").open("w+", encoding="utf-8")
        try:
            docker("run", "--detach", "--name", name, "-p", f"127.0.0.1:{broker_port}:1883", "--mount",
                f"type=bind,source={local},target=/mosquitto/config/local,readonly", "--mount",
                f"type=bind,source={ROOT / 'infra/mosquitto/mosquitto.conf'},target=/mosquitto/config/mosquitto.conf,readonly", IMAGE)
            port = int(docker("port", name, "1883/tcp").rsplit(":", 1)[1])
            environment.update(MQTT_PORT=str(port), DATABASE_URL=f"sqlite:///{(scratch / 'integration.db').as_posix()}",
                RAW_STORAGE_DIR=str(scratch / "raw"), MQTT_LOCK_FILE=str(scratch / "receiver.lock"),
                CORS_ORIGINS="http://localhost:5173", PYTHONIOENCODING="utf-8")
            base = f"http://127.0.0.1:{api_port}"
            def start_backend():
                nonlocal backend
                backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(api_port)],
                    cwd=ROOT / "backend", env={**os.environ, **environment}, stdout=log, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if backend.poll() is not None:
                        raise RuntimeError("Backend kiểm thử dừng khi khởi động")
                    try:
                        if httpx.get(base + "/api/v1/health", timeout=0.5).status_code == 200:
                            return
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                raise TimeoutError("Backend startup")
            def stop_backend():
                nonlocal backend
                if backend and backend.poll() is None:
                    backend.terminate()
                    backend.wait(timeout=10)
            start_backend()
            asyncio.run(verify(base, environment, local, port, passwords, name, start_backend, stop_backend))
        except BaseException:
            log.flush()
            print((scratch / "backend.log").read_text(encoding="utf-8")[-10000:], file=sys.stderr)
            try:
                print(docker("logs", "--tail", "30", name), file=sys.stderr)
            except subprocess.CalledProcessError:
                pass
            raise
        finally:
            if backend and backend.poll() is None:
                backend.terminate()
                backend.wait(timeout=10)
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
            log.close()


if __name__ == "__main__":
    main()
