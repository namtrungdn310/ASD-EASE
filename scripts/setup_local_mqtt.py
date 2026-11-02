"""Tạo secret ngẫu nhiên local và ACL từ registry; không in secret ra terminal."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "eclipse-mosquitto:2.0.22@sha256:09b62ff32c2e7b64d4b431b9a89236073289b68db273de2b089edeb9b0d92b5c"


def provision(destination, *, http_simulator=False):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError("Thư mục đã có nội dung; không ghi đè credential đang dùng")
    passwords = {name: secrets.token_urlsafe(32) for name in ("backend", "simulator", "simulator-other")}
    registry = [{"device_id": device, "data_origin": "SYNTHETIC", "mqtt_username": username,
                 "http_token": secrets.token_urlsafe(32), "transport": "http" if http_simulator and index == 0 else "mqtt",
                 "acquisition_profile": {"ppg_hz": 100, "imu_hz": 50, "gsr_hz": 20, "window_ms": 1000}}
                for index, (device, username) in enumerate((("SIM-001", "simulator"), ("SIM-OTHER", "simulator-other")))]
    (destination / "device-registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    (destination / "simulator.json").write_text(json.dumps({"username": "simulator", "password": passwords["simulator"],
        "device_id": "SIM-001", "data_origin": "SYNTHETIC", "http_token": registry[0]["http_token"]}, indent=2), encoding="utf-8")
    # Băm mật khẩu bằng stdin; không truyền secret trong command line/process args.
    plain = "".join(f"{username}:{password}\n" for username, password in passwords.items())
    completed = subprocess.run(["docker", "run", "--rm", "-i", "--entrypoint", "sh", IMAGE, "-c",
        "umask 077; cat > /tmp/passwords; mosquitto_passwd -U /tmp/passwords; cat /tmp/passwords"],
        input=plain, text=True, capture_output=True, check=True)
    (destination / "passwords").write_text(completed.stdout, encoding="utf-8")
    acl = []
    for username in passwords:
        acl.append(f"user {username}")
        for entry in registry:
            if username != "backend" and username != entry["mqtt_username"]:
                continue
            prefix = f"asd-ease/v1/{entry['data_origin']}/{entry['device_id']}/"
            for suffix in ("telemetry", "ack", "state/request", "presence"):
                acl.append(f"topic {'read' if username == 'backend' else 'write'} {prefix}{suffix}")
            for suffix in ("command", "state/response"):
                acl.append(f"topic {'write' if username == 'backend' else 'read'} {prefix}{suffix}")
        acl.append("")
    (destination / "acl").write_text("\n".join(acl), encoding="utf-8")
    operator, cookie = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    environment = {"OPERATOR_TOKEN": operator, "COOKIE_SECRET": cookie,
                   "MQTT_PASSWORD": passwords["backend"], "MQTT_USERNAME": "backend",
                   "ALLOW_INSECURE_LOCAL": "true", "COOKIE_SECURE": "false", "MQTT_ENABLED": "true",
                   "MQTT_HOST": "127.0.0.1", "MQTT_PORT": "1883", "DEVICE_REGISTRY_FILE": (destination / "device-registry.json").as_posix()}
    (destination / "backend.env").write_text("\n".join(f"{key}={value}" for key, value in environment.items()) + "\n", encoding="utf-8")
    return environment, registry, passwords


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=ROOT / "infra" / "mosquitto" / "local")
    parser.add_argument("--http-simulator", action="store_true")
    args = parser.parse_args()
    provision(args.directory, http_simulator=args.http_simulator)
    print("Đã tạo file local. Đọc docs/integration/04-SETUP.md; không commit thư mục credential.")
