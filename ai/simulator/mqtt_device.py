"""Thiết bị MQTT giả: ACK Start/Stop, giữ epoch qua reconnect, không ghi raw."""
import argparse
import copy
import json
import queue
import time
from pathlib import Path
from uuid import uuid4
import paho.mqtt.client as mqtt


class SyntheticDevice:
    def __init__(self, credentials, *, host="127.0.0.1", port=1883, ca_file=None):
        if credentials.get("data_origin") != "SYNTHETIC":
            raise ValueError("Simulator chỉ được dùng SYNTHETIC")
        self.credentials = credentials
        self.device_id = credentials["device_id"]
        self.boot_id, self.connection_id = uuid4().hex, uuid4().hex
        self.actual_state, self.session_id = "IDLE", None
        self.generation, self.last_ack = 0, None
        self.accepted = False
        self.epoch = time.monotonic()
        self.boot_epoch = self.epoch
        self.requests = {}
        self.inbox = queue.Queue(maxsize=8)
        self.connected = False
        self.next_sync = self.next_telemetry = 0
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-{self.device_id}-{uuid4().hex[:8]}", clean_session=True)
        self.client.username_pw_set(credentials["username"], credentials["password"])
        if ca_file:
            self.client.tls_set(ca_certs=ca_file)
        self.client.max_inflight_messages_set(8)
        self.client.max_queued_messages_set(8)
        self.client.on_connect = self._connect
        self.client.on_pre_connect = self._pre_connect
        self.client.on_subscribe = self._subscribe
        self.client.on_disconnect = self._disconnect
        self.client.on_message = self._message
        self.client.will_set(self.prefix + "presence", json.dumps(self.envelope("PRESENCE") | {"status": "OFFLINE"}), qos=1, retain=True)
        self.host, self.port = host, port

    @property
    def prefix(self):
        return f"asd-ease/v1/SYNTHETIC/{self.device_id}/"

    def envelope(self, kind):
        return {"control_version": "1.0", "message_type": kind, "device_id": self.device_id,
                "data_origin": "SYNTHETIC", "boot_id": self.boot_id, "connection_id": self.connection_id}

    def _pre_connect(self, client, userdata):
        # Nonce và LWT phải được chọn trước CONNECT, kể cả reconnect tự động.
        self.connection_id = uuid4().hex
        self.requests.clear()
        self.accepted = False
        client.will_set(self.prefix + "presence", json.dumps(self.envelope("PRESENCE") | {"status": "OFFLINE"}), qos=1, retain=True)

    def _connect(self, client, userdata, flags, reason, properties):
        if reason.is_failure:
            return
        client.subscribe([(self.prefix + "command", 1), (self.prefix + "state/response", 1)])

    def _subscribe(self, client, userdata, mid, reasons, properties):
        self.connected = all(not reason.is_failure for reason in reasons)
        if self.connected:
            self.publish("presence", self.envelope("PRESENCE") | {"status": "ONLINE"}, retain=True)
            self.next_sync = 0

    def _disconnect(self, client, userdata, flags, reason, properties):
        self.connected, self.accepted = False, False

    def _message(self, client, userdata, message):
        if len(message.payload) > 4096 or message.retain:
            return
        try:
            self.inbox.put_nowait((message.topic, json.loads(message.payload)))
        except (queue.Full, ValueError):
            pass

    def publish(self, suffix, payload, *, retain=False, qos=1):
        return self.client.publish(self.prefix + suffix, json.dumps(payload, separators=(",", ":")), qos=qos, retain=retain)

    def timestamp(self):
        return int((time.monotonic() - (self.epoch if self.session_id else self.boot_epoch)) * 1000)

    def sync(self):
        request_id = uuid4().hex
        self.requests = {key: value for key, value in self.requests.items() if time.monotonic() - value < 30}
        self.requests[request_id] = time.monotonic()
        last_ack = copy.deepcopy(self.last_ack)
        if last_ack:
            last_ack.update(connection_id=self.connection_id, request_id=request_id)
        payload = self.envelope("STATE_REQUEST") | {"request_id": request_id, "actual_state": self.actual_state,
            "session_id": self.session_id, "last_command_id": self.last_ack["command_id"] if self.last_ack else None,
            "last_generation": self.generation, "timestamp_ms": self.timestamp(), "last_ack": last_ack}
        self.publish("state/request", payload)
        self.next_sync = time.monotonic() + (1 if self.last_ack and not self.accepted else 15)

    def command(self, command):
        if (command.get("device_id"), command.get("data_origin"), command.get("boot_id"), command.get("connection_id")) != (
            self.device_id, "SYNTHETIC", self.boot_id, self.connection_id
        ):
            return
        sent = self.requests.get(command.get("request_id"))
        if sent is None or time.monotonic() - sent >= command.get("expires_in_ms", 0) / 1000:
            return
        if command["generation"] < self.generation:
            return
        if self.last_ack and command["command_id"] == self.last_ack["command_id"]:
            if (command["session_id"], command["generation"], command["action"]) != (self.last_ack["session_id"], self.last_ack["generation"], self.last_ack["action"]):
                return
            ack = copy.deepcopy(self.last_ack)
        else:
            if command["generation"] == self.generation:
                return
            ack = self.envelope("ACK") | {"request_id": command["request_id"], "command_id": command["command_id"],
                "generation": command["generation"], "session_id": command["session_id"], "action": command["action"],
                "result": "REJECTED", "timestamp_ms": self.timestamp(), "reason": None, "final_summary": None}
            if command["action"] == "START":
                profile = command["acquisition_profile"]
                if profile != {"ppg_hz": 100, "imu_hz": 50, "gsr_hz": 20, "window_ms": 1000}:
                    ack["reason"] = "PROFILE_UNSUPPORTED"
                elif self.actual_state == "RECORDING":
                    ack["reason"] = "BUSY"
                else:
                    self.session_id, self.actual_state, self.epoch = command["session_id"], "RECORDING", time.monotonic()
                    ack.update(result="STARTED", timestamp_ms=0)
            else:
                self.session_id, self.actual_state = command["session_id"], "STOPPED"
                ack.update(result="STOPPED", timestamp_ms=0, final_summary={"cutoff_timestamp_ms": 0,
                    "final_batch_id": None, "total_generated_batches": 0, "dropped_batches": 0,
                    "slot_counts": {"ppg": 0, "imu": 0, "gsr": 0}, "missing_samples": {"ppg": 0, "imu": 0, "gsr": 0},
                    "dropped_batch_ranges": [], "loss_ranges_truncated": False, "raw_recording_enabled": False})
            self.generation, self.last_ack, self.accepted = command["generation"], copy.deepcopy(ack), False
        ack.update(connection_id=self.connection_id, request_id=command["request_id"])
        self.publish("ack", ack)
        self.next_sync = 0

    def telemetry(self):
        return {"schema_version": "1.0", "device_id": self.device_id,
            "session_id": self.session_id if self.actual_state == "RECORDING" else None,
            "timestamp_ms": self.timestamp() if self.actual_state == "RECORDING" else int((time.monotonic()-self.boot_epoch)*1000),
            "data_origin": "SYNTHETIC", "hr_bpm": 78.0, "gsr": {"raw": 1800, "delta": 0.04},
            "movement": {"score": 0.2}, "signal_quality": {"ppg": 0.9, "gsr": 0.85, "imu": 1.0},
            "prediction": {"probability": None, "state": "UNCERTAIN"},
            "firmware_version": "simulator-mqtt-0.1.0", "model_version": "none"}

    def step(self):
        while True:
            try:
                topic, payload = self.inbox.get_nowait()
            except queue.Empty:
                break
            if topic.endswith("state/response"):
                if (payload.get("boot_id"), payload.get("connection_id")) != (self.boot_id, self.connection_id) or payload.get("request_id") not in self.requests:
                    continue
                if self.last_ack:
                    self.accepted = payload.get("accepted_command_id") == self.last_ack["command_id"] and payload.get("state") in {"RECORDING", "STOPPING", "STOPPED", "ABORTED"}
                else:
                    self.accepted = payload.get("error_code") is None
                if payload.get("pending_command"):
                    self.command(payload["pending_command"])
            else:
                self.command(payload)
        if self.connected and time.monotonic() >= self.next_sync:
            self.sync()
        if self.connected and self.accepted and time.monotonic() >= self.next_telemetry:
            self.publish("telemetry", self.telemetry(), qos=0)
            self.next_telemetry = time.monotonic() + 1

    def start(self):
        self.client.connect_async(self.host, self.port, keepalive=15)
        self.client.loop_start()

    def stop(self):
        if self.connected:
            info = self.publish("presence", self.envelope("PRESENCE") | {"status": "OFFLINE"}, retain=True)
            try:
                info.wait_for_publish(timeout=2)
            except RuntimeError:
                pass
        self.client.disconnect()
        self.client.loop_stop()


def main():
    parser = argparse.ArgumentParser(description="Thiết bị SYNTHETIC MQTT, không phải dữ liệu thật")
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--ca-file")
    args = parser.parse_args()
    device = SyntheticDevice(json.loads(args.credentials.read_text()), host=args.host, port=args.port, ca_file=args.ca_file)
    print("SYNTHETIC TEST DATA — chỉ kiểm thử kết nối, không dữ liệu nghiên cứu")
    device.start()
    try:
        while True:
            device.step()
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        device.stop()


if __name__ == "__main__":
    main()
