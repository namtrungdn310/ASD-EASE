"""Paho chỉ làm transport test; JSON/epoch/StartStop đều do core C++ firmware."""
import json
import queue
import time
from uuid import uuid4
import paho.mqtt.client as mqtt
from firmware_native import NativeFirmware


class NativeDevice:
    def __init__(self, credentials, *, host="127.0.0.1", port=1883):
        if credentials["data_origin"] != "SYNTHETIC":
            raise ValueError("Harness qua broker chỉ dùng fixture SYNTHETIC")
        self.native = NativeFirmware()
        self.boot_epoch = time.monotonic()
        self.device_id = credentials["device_id"]
        self.latest = self.native.call("init", device_id=self.device_id, data_origin="SYNTHETIC", boot_id=uuid4().hex,
            profile={"ppg_hz":100,"imu_hz":50,"gsr_hz":20,"window_ms":1000})
        self.prefix = f"asd-ease/v1/SYNTHETIC/{self.device_id}/"
        self.inbox = queue.Queue(maxsize=8)
        self.connected = False
        self.next_telemetry = 0
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="native-"+uuid4().hex[:12], clean_session=True)
        self.client.username_pw_set(credentials["username"], credentials["password"])
        self.client.max_queued_messages_set(8)
        self.client.max_inflight_messages_set(8)
        self.client.on_pre_connect = self._prepare
        self.client.on_connect = self._connect
        self.client.on_subscribe = self._subscribed
        self.client.on_disconnect = self._disconnect
        self.client.on_message = self._message
        self.host, self.port = host, port

    def now(self):
        return int((time.monotonic() - self.boot_epoch) * 1000)

    def _prepare(self, client, userdata):
        self.latest = self.native.call("connect", self.now(), connection_id=uuid4().hex)
        client.will_set(self.prefix+"presence", json.dumps(self.latest["will"]), qos=1, retain=True)

    def _connect(self, client, userdata, flags, reason, properties):
        if not reason.is_failure:
            client.subscribe([(self.prefix+"command",1),(self.prefix+"state/response",1)])

    def _subscribed(self, client, userdata, mid, reasons, properties):
        self.connected = all(not reason.is_failure for reason in reasons)

    def _disconnect(self, client, userdata, flags, reason, properties):
        self.connected = False
        self.latest = self.native.call("disconnect", self.now())

    def _message(self, client, userdata, message):
        if len(message.payload) > 4096:
            return
        try:
            self.inbox.put_nowait((message.topic[len(self.prefix):], message.payload.decode(), message.retain))
        except (queue.Full, UnicodeError):
            pass

    def flush(self, result):
        for packet in result["out"]:
            self.client.publish(self.prefix+packet["suffix"], json.dumps(packet["payload"], separators=(",", ":")),
                qos=packet["qos"], retain=packet["retain"])

    @property
    def epoch(self):
        return self.latest["epoch"]

    @property
    def generation(self):
        return self.latest["generation"]

    @property
    def next_sync(self):
        return 0

    @next_sync.setter
    def next_sync(self, value):
        self.latest = self.native.call("resync", self.now())

    def timestamp(self):
        return self.now()-self.epoch if self.latest["state"] == "RECORDING" else self.now()

    def step(self):
        if not self.connected:
            return
        while True:
            try:
                suffix, wire, retain = self.inbox.get_nowait()
            except queue.Empty:
                break
            self.latest = self.native.call("receive", self.now(), suffix=suffix, wire=wire, retain=retain)
            self.flush(self.latest)
        self.latest = self.native.call("tick", self.now())
        self.flush(self.latest)
        if self.now() >= self.next_telemetry:
            self.latest = self.native.call("telemetry", self.now(), snapshot={"hr":78.0,"hr_valid":True,"hr_age":0,"ppg_age":0,
                "gsr_adc":1800,"gsr_readable":True,"gsr_valid":True,"gsr_age":0,"imu_age":0,"gsr_percent":4,"gsr_baseline":2})
            if "telemetry" in self.latest:
                self.client.publish(self.prefix+"telemetry", json.dumps(self.latest["telemetry"]), qos=0, retain=False)
            self.next_telemetry = self.now()+1000

    def start(self):
        self.client.connect_async(self.host, self.port, keepalive=15)
        self.client.loop_start()

    def stop(self):
        self.client.disconnect()
        self.client.loop_stop()
        self.native.close()
