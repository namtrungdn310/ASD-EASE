"""Registry ràng buộc nguồn/thiết bị; cookie người vận hành không chứa token."""
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from typing import Literal
from fastapi import HTTPException, Request, WebSocket
from pydantic import Field, SecretStr, TypeAdapter, ValidationError
from app.schemas.control import AcquisitionProfile, Identifier, WireModel

COOKIE_NAME = "asd_operator"


def secret_matches(value: str, expected: str) -> bool:
    try:
        return secrets.compare_digest(value.encode("utf-8"), expected.encode("utf-8"))
    except UnicodeError:
        return False


class DeviceIdentity(WireModel):
    device_id: Identifier
    data_origin: Literal["DEVICE", "SYNTHETIC"]
    http_token: SecretStr
    mqtt_username: Identifier
    transport: Literal["http", "mqtt"] = "mqtt"
    acquisition_profile: AcquisitionProfile = Field(default_factory=AcquisitionProfile)


class Registry:
    def __init__(self, path: Path):
        try:
            self.entries = TypeAdapter(list[DeviceIdentity]).validate_python(json.loads(path.read_text(encoding="utf-8")))
        except (ValidationError, ValueError):
            raise ValueError("Registry không đúng cấu trúc; không ghi nội dung credential vào log") from None
        for field in ("device_id", "mqtt_username"):
            values = [getattr(item, field) for item in self.entries]
            if len(values) != len(set(values)):
                raise ValueError(f"Registry có {field} lặp")
        tokens = [entry.http_token.get_secret_value() for entry in self.entries]
        if len(tokens) != len(set(tokens)) or any(len(token) < 32 for token in tokens):
            raise ValueError("Mỗi thiết bị cần HTTP token riêng, ít nhất32 ký tự")
        self.by_id = {entry.device_id: entry for entry in self.entries}

    def identity(self, device_id, origin=None):
        entry = self.by_id.get(device_id)
        if entry is None or (origin is not None and origin != entry.data_origin):
            raise HTTPException(403, "IDENTITY_MISMATCH")
        return entry


def bearer(connection):
    header = connection.headers.get("authorization", "")
    return header[7:] if header.startswith("Bearer ") else ""


def device_auth(request: Request):
    token = bearer(request)
    if not token:
        raise HTTPException(401, "DEVICE_AUTH_REQUIRED")
    for entry in request.app.state.registry.entries:
        if secret_matches(token, entry.http_token.get_secret_value()):
            return entry
    raise HTTPException(401, "DEVICE_AUTH_INVALID")


def issue_cookie(settings):
    body = f"{int(time.time()) + 3600}.{secrets.token_hex(16)}"
    signature = hmac.new(settings.cookie_secret.get_secret_value().encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def operator_allowed(connection):
    settings = connection.app.state.settings
    token = bearer(connection)
    if token and secret_matches(token, settings.operator_token.get_secret_value()):
        return True
    try:
        expiry, nonce, signature = connection.cookies.get(COOKIE_NAME, "").split(".")
        expected = hmac.new(settings.cookie_secret.get_secret_value().encode(), f"{expiry}.{nonce}".encode(), hashlib.sha256).hexdigest()
        if not secret_matches(signature, expected) or int(expiry) <= time.time():
            return False
    except (ValueError, TypeError):
        return False
    origin = connection.headers.get("origin")
    if isinstance(connection, WebSocket) or connection.method not in ("GET", "HEAD"):
        if origin not in settings.cors_origin_list:
            return False
    return origin is None or origin in settings.cors_origin_list


def operator_auth(request: Request):
    if not operator_allowed(request):
        raise HTTPException(401, "OPERATOR_AUTH_REQUIRED")


def assert_identity(identity, device_id, origin):
    if identity.device_id != device_id or identity.data_origin != origin:
        raise HTTPException(403, "IDENTITY_MISMATCH")
