import base64
import hashlib
import hmac
import json
import time

from fastapi import Header, HTTPException

from app.config import settings


def _auth_secret() -> str:
    return settings.auth_secret or settings.telegram_webhook_secret


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(telegram_user_id: int, chat_id: int, expires_in_seconds: int = 60 * 60 * 24 * 30) -> str:
    now = int(time.time())
    payload = {
        "telegram_user_id": telegram_user_id,
        "chat_id": chat_id,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(_auth_secret().encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return f"{_encode(payload_bytes)}.{_encode(signature)}"


def verify_access_token(token: str) -> dict:
    try:
        payload_part, signature_part = token.split(".", 1)
        payload_bytes = _decode(payload_part)
        signature = _decode(signature_part)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc

    expected_signature = hmac.new(_auth_secret().encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid access token")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=401, detail="Access token expired")

    return payload


def require_user_context(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing access token")

    token = authorization.removeprefix("Bearer ").strip()
    payload = verify_access_token(token)
    return payload


def require_user_id(authorization: str | None = Header(default=None)) -> int:
    payload = require_user_context(authorization)
    return int(payload["telegram_user_id"])