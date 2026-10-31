"""Đọc JSON có giới hạn; không chấp nhận khoá lặp hoặc số giả."""
import json
from fastapi import HTTPException, Request


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Khoá JSON lặp")
        result[key] = value
    return result


def decode_json(data: bytes, limit: int = 4096):
    if len(data) > limit:
        raise ValueError("PAYLOAD_TOO_LARGE")
    def reject_constant(value):
        raise ValueError("Số JSON không hữu hạn")
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=reject_constant)
    def depth(item, level=0):
        if level > 8:
            raise ValueError("JSON quá sâu")
        if isinstance(item, dict):
            for child in item.values():
                depth(child, level + 1)
        elif isinstance(item, list):
            for child in item:
                depth(child, level + 1)
    depth(value)
    if not isinstance(value, dict):
        raise ValueError("JSON phải là object")
    return value


async def read_json(request: Request, limit=4096):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json" or request.headers.get("content-encoding", "identity") != "identity":
        raise HTTPException(415, "UNSUPPORTED_MEDIA_TYPE")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            raise HTTPException(413, "PAYLOAD_TOO_LARGE")
        body.extend(chunk)
    try:
        return decode_json(bytes(body), limit)
    except (ValueError, UnicodeError, RecursionError):
        raise HTTPException(400, "MALFORMED_JSON") from None


def validate(model, data):
    from pydantic import ValidationError
    try:
        return model.model_validate(data)
    except ValidationError:
        raise HTTPException(422, "SCHEMA_INVALID") from None
