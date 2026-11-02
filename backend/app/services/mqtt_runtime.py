"""Một consumer MQTT; callback chỉ xếp hàng, DB/WS chạy trên event loop ASGI."""
import asyncio
from collections import Counter
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import queue
import threading
import time
from fastapi import HTTPException
import paho.mqtt.client as mqtt
from pydantic import ValidationError
from app.core.wire import decode_json
from app.schemas.control import Ack, Presence, StateRequest
from app.schemas.ingestion import InboundTelemetry
from app.services.control_service import apply_ack, lease_command, synchronize
from app.services.session_service import expire_sessions

logger = logging.getLogger(__name__)


class ReceiverLock:
    def __init__(self, path):
        self.path, self.file = Path(path), None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        self.file.seek(0)
        self.file.write(b"0")
        self.file.flush()
        self.file.seek(0)
        try:
            if __import__("os").name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            self.file = None
            raise RuntimeError("Đã có MQTT receiver; dùng một worker, không --reload") from None

    def release(self):
        if self.file:
            if __import__("os").name == "nt":
                import msvcrt
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            self.file.close()
            self.file = None


@dataclass
class LiveConnection:
    boot_id: str
    connection_id: str
    request_id: str
    synced_at: float
    seen_requests: set = field(default_factory=set)
    last_dispatch: float = 0


class MQTTRuntime:
    def __init__(self, settings, registry, session_factory):
        self.settings, self.registry, self.session_factory = settings, registry, session_factory
        self.inbox = queue.Queue(maxsize=settings.mqtt_queue_messages)
        self.queue_bytes = 0
        self.mutex = threading.Lock()
        self.counters = Counter()
        self.live = {}
        self.connected = False
        self.connection_epoch = 0
        self.observed_epoch = 0
        self.client = None
        self.task = None
        self.lock = ReceiverLock(settings.mqtt_lock_file)
        self.stopping = False

    def _connected(self, client, userdata, flags, reason, properties):
        self.connection_epoch += 1
        if reason.is_failure:
            self.connected = False
            self.counters["connect_failed"] += 1
            return
        topics = []
        for identity in self.registry.entries:
            if identity.transport == "mqtt":
                prefix = self.prefix(identity)
                topics.extend([(prefix + "telemetry", 0), (prefix + "ack", 1),
                               (prefix + "state/request", 1), (prefix + "presence", 1)])
        if topics:
            client.subscribe(topics)

    def _subscribed(self, client, userdata, mid, reasons, properties):
        self.connected = bool(reasons) and all(not reason.is_failure for reason in reasons)
        if not self.connected:
            self.counters["subscription_failed"] += 1

    def _disconnected(self, client, userdata, flags, reason, properties):
        self.connected = False
        self.connection_epoch += 1

    def _message(self, client, userdata, message):
        self.enqueue(message.topic, bytes(message.payload), message.retain)

    def enqueue(self, topic, payload, retained=False):
        size = len(payload)
        with self.mutex:
            if size > 4096 or len(topic.encode("utf-8")) > 256:
                self.counters["oversize"] += 1
                return False
            if self.inbox.full() or self.queue_bytes + size > self.settings.mqtt_queue_bytes:
                self.counters["overload"] += 1
                return False
            self.inbox.put_nowait((topic, payload, retained, self.connection_epoch))
            self.queue_bytes += size
        return True

    @staticmethod
    def prefix(identity):
        return f"asd-ease/v1/{identity.data_origin}/{identity.device_id}/"

    def status(self):
        return {"enabled": self.settings.mqtt_enabled, "connected": self.connected,
                "synchronized_devices": sum(self.is_live(key) is not None for key in self.live), "queue_messages": self.inbox.qsize(),
                "queue_bytes": self.queue_bytes, "counters": dict(self.counters)}

    async def start(self):
        if self.settings.mqtt_enabled:
            self.lock.acquire()
            try:
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.settings.mqtt_client_id,
                                          clean_session=True, protocol=mqtt.MQTTv311)
                self.client.username_pw_set(self.settings.mqtt_username, self.settings.mqtt_password.get_secret_value())
                if self.settings.mqtt_ca_file:
                    self.client.tls_set(ca_certs=self.settings.mqtt_ca_file)
                self.client.max_inflight_messages_set(8)
                self.client.max_queued_messages_set(8)
                self.client.reconnect_delay_set(1, 5)
                self.client.on_connect = self._connected
                self.client.on_subscribe = self._subscribed
                self.client.on_disconnect = self._disconnected
                self.client.on_message = self._message
                self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=15)
                self.client.loop_start()
            except BaseException:
                self.lock.release()
                raise
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        self.stopping = True
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        if self.client:
            self.client.disconnect()
            await asyncio.to_thread(self.client.loop_stop)
        self.lock.release()
        self.live.clear()

    def publish(self, identity, suffix, payload):
        encoded = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
        if len(encoded) > 4096:
            self.counters["outgoing_oversize"] += 1
            return False
        if not self.connected or not self.client:
            return False
        info = self.client.publish(self.prefix(identity) + suffix, encoded, qos=1, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            self.counters["publish_failed"] += 1
            return False
        # PUBACK không thay ACK nghiệp vụ; DB command vẫn PENDING.
        return True

    def is_live(self, device_id):
        live = self.live.get(device_id)
        if live and time.monotonic() - live.synced_at < 30:
            return live
        return None

    def sync(self, identity, request):
        previous = self.live.get(identity.device_id)
        if previous and (previous.boot_id, previous.connection_id) == (request.boot_id, request.connection_id):
            if request.request_id in previous.seen_requests and request.request_id != previous.request_id:
                raise HTTPException(409, "STALE_COMMAND")
        with self.session_factory() as db:
            response = synchronize(db, identity, request)
        if previous and (previous.boot_id, previous.connection_id) == (request.boot_id, request.connection_id) and request.request_id == previous.request_id:
            live = previous
        else:
            seen = set(previous.seen_requests) if previous and previous.connection_id == request.connection_id else set()
            # Lịch sử nonce đầy đủ ở DB; bộ nhớ chỉ giữ cửa sổ gần nhất.
            if len(seen) >= 64:
                seen = {previous.request_id}
            seen.add(request.request_id)
            live = LiveConnection(request.boot_id, request.connection_id, request.request_id, time.monotonic(), seen)
            self.live[identity.device_id] = live
        if response.error_code is None or response.state == "STOPPING":
            with self.session_factory() as db:
                response.pending_command = lease_command(db, identity, live.boot_id, live.connection_id, live.request_id)
        return response

    def ack(self, identity, ack):
        live = self.is_live(identity.device_id)
        if not live or (live.boot_id, live.connection_id) != (ack.boot_id, ack.connection_id):
            raise HTTPException(409, "CONNECTION_MISMATCH")
        with self.session_factory() as db:
            apply_ack(db, identity, ack)

    async def dispatch(self):
        if not self.connected:
            return
        for identity in self.registry.entries:
            live = self.is_live(identity.device_id)
            if identity.transport != "mqtt" or not live or time.monotonic() - live.last_dispatch < 1:
                continue
            with self.session_factory() as db:
                command = lease_command(db, identity, live.boot_id, live.connection_id, live.request_id)
            if command:
                self.publish(identity, "command", command.model_dump(mode="json"))
            live.last_dispatch = time.monotonic()

    async def process(self, topic, payload, retained):
        from app.services.telemetry_service import receive_telemetry
        parts = topic.split("/")
        if len(parts) < 5 or parts[:2] != ["asd-ease", "v1"]:
            raise HTTPException(403, "IDENTITY_MISMATCH")
        identity = self.registry.identity(parts[3], parts[2])
        if identity.transport != "mqtt":
            raise HTTPException(403, "TRANSPORT_MISMATCH")
        suffix = "/".join(parts[4:])
        if retained and suffix != "presence":
            raise HTTPException(409, "RETAINED_CONTROL_REJECTED")
        data = decode_json(payload)
        if (data.get("device_id"), data.get("data_origin")) != (identity.device_id, identity.data_origin):
            raise HTTPException(403, "IDENTITY_MISMATCH")
        if suffix == "state/request":
            response = self.sync(identity, StateRequest.model_validate(data))
            self.publish(identity, "state/response", response.model_dump(mode="json"))
        elif suffix == "ack":
            self.ack(identity, Ack.model_validate(data))
        elif suffix == "telemetry":
            telemetry = InboundTelemetry.model_validate(data)
            with self.session_factory() as db:
                await receive_telemetry(db, telemetry, identity, self)
        elif suffix == "presence":
            presence = Presence.model_validate(data)
            live = self.live.get(identity.device_id)
            if not retained and presence.status == "OFFLINE" and live and (live.boot_id, live.connection_id) == (presence.boot_id, presence.connection_id):
                self.live.pop(identity.device_id, None)
            self.counters["presence_hint"] += 1
        else:
            raise HTTPException(403, "TOPIC_NOT_ALLOWED")

    async def _run(self):
        last_tick = 0
        while True:
            try:
                if self.observed_epoch != self.connection_epoch:
                    self.live = {key: value for key, value in self.live.items() if self.registry.by_id[key].transport == "http"}
                    self.observed_epoch = self.connection_epoch
                for _ in range(32):
                    try:
                        topic, payload, retained, epoch = self.inbox.get_nowait()
                    except queue.Empty:
                        break
                    with self.mutex:
                        self.queue_bytes -= len(payload)
                    try:
                        if epoch == self.connection_epoch:
                            await self.process(topic, payload, retained)
                        else:
                            self.counters["old_broker_connection"] += 1
                    except (HTTPException, ValidationError, ValueError, UnicodeError, RecursionError) as error:
                        code = error.detail if isinstance(error, HTTPException) else "SCHEMA_INVALID"
                        self.counters[str(code)] += 1
                    finally:
                        self.inbox.task_done()
                if time.monotonic() - last_tick >= 0.25:
                    with self.session_factory() as db:
                        expire_sessions(db)
                    await self.dispatch()
                    last_tick = time.monotonic()
                await asyncio.sleep(0.02)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.counters["processing_failure"] += 1
                logger.exception("Lỗi MQTT consumer; không xác nhận thành công")
                await asyncio.sleep(0.5)
