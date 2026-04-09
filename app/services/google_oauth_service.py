from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.auth import create_oauth_state_token, verify_oauth_state_token
from app.config import settings
from app.db import get_db


logger = logging.getLogger(__name__)

GOOGLE_OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
GOOGLE_PROFILE_SCOPES = "openid email profile"


def _ensure_configured() -> None:
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise ValueError("Google OAuth is not configured")


def _redirect_uri() -> str:
    return settings.public_base_url.rstrip("/") + "/google/calendar/callback"


def build_google_calendar_auth_url(telegram_user_id: int) -> str:
    _ensure_configured()
    state = create_oauth_state_token(telegram_user_id, purpose="google_calendar_oauth")
    params = httpx.QueryParams(
        {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": _redirect_uri(),
            "response_type": "code",
            "scope": f"{GOOGLE_CALENDAR_SCOPE} {GOOGLE_PROFILE_SCOPES}",
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
    )
    return f"{GOOGLE_OAUTH_AUTHORIZE_URL}?{params}"


def _exchange_code_for_tokens(code: str) -> dict:
    _ensure_configured()
    response = httpx.post(
        GOOGLE_OAUTH_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "redirect_uri": _redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def _store_connection(
    telegram_user_id: int,
    token_data: dict,
    email: str | None,
    refresh_token: str,
) -> dict:
    expires_in = int(token_data.get("expires_in") or 0)
    token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else None

    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO google_calendar_connections (
                telegram_user_id,
                email,
                access_token,
                refresh_token,
                token_expiry,
                scopes,
                connected_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (telegram_user_id) DO UPDATE SET
                email = EXCLUDED.email,
                access_token = EXCLUDED.access_token,
                refresh_token = COALESCE(EXCLUDED.refresh_token, google_calendar_connections.refresh_token),
                token_expiry = EXCLUDED.token_expiry,
                scopes = EXCLUDED.scopes,
                updated_at = NOW()
            RETURNING telegram_user_id, email, token_expiry, scopes, connected_at, updated_at;
            """,
            (
                telegram_user_id,
                email,
                token_data.get("access_token"),
                refresh_token,
                token_expiry,
                token_data.get("scope"),
            ),
        )
        row = cur.fetchone()
        conn.commit()

    return row


def complete_google_calendar_oauth(code: str, state: str) -> dict:
    payload = verify_oauth_state_token(state, purpose="google_calendar_oauth")
    token_data = _exchange_code_for_tokens(code)
    if not token_data.get("access_token"):
        raise ValueError("Google did not return an access token")

    with get_db() as (_, cur):
        cur.execute(
            """
            SELECT refresh_token
            FROM google_calendar_connections
            WHERE telegram_user_id = %s;
            """,
            (payload["telegram_user_id"],),
        )
        existing = cur.fetchone()

    refresh_token = token_data.get("refresh_token") or (existing["refresh_token"] if existing else None)
    if not refresh_token:
        raise ValueError("Google did not return a refresh token")

    return _store_connection(
        telegram_user_id=int(payload["telegram_user_id"]),
        token_data=token_data,
        email=None,
        refresh_token=refresh_token,
    )


def get_google_calendar_status(telegram_user_id: int) -> dict:
    with get_db() as (_, cur):
        cur.execute(
            """
            SELECT email, token_expiry, connected_at, updated_at
            FROM google_calendar_connections
            WHERE telegram_user_id = %s;
            """,
            (telegram_user_id,),
        )
        row = cur.fetchone()

    if not row:
        return {"connected": False}

    return {
        "connected": True,
        "email": row["email"],
        "token_expiry": row["token_expiry"],
        "connected_at": row["connected_at"],
        "updated_at": row["updated_at"],
    }


def disconnect_google_calendar(telegram_user_id: int) -> None:
    with get_db() as (conn, cur):
        cur.execute(
            """
            DELETE FROM google_calendar_connections
            WHERE telegram_user_id = %s;
            """,
            (telegram_user_id,),
        )
        conn.commit()


def _refresh_google_access_token(telegram_user_id: int) -> str | None:
    _ensure_configured()
    with get_db() as (_, cur):
        cur.execute(
            """
            SELECT refresh_token
            FROM google_calendar_connections
            WHERE telegram_user_id = %s;
            """,
            (telegram_user_id,),
        )
        row = cur.fetchone()

    if not row or not row["refresh_token"]:
        return None

    response = httpx.post(
        GOOGLE_OAUTH_TOKEN_URL,
        data={
            "refresh_token": row["refresh_token"],
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    response.raise_for_status()
    token_data = response.json()

    access_token = token_data.get("access_token")
    if not access_token:
        return None

    expires_in = int(token_data.get("expires_in") or 0)
    token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else None

    with get_db() as (conn, cur):
        cur.execute(
            """
            UPDATE google_calendar_connections
            SET access_token = %s,
                token_expiry = COALESCE(%s, token_expiry),
                updated_at = NOW()
            WHERE telegram_user_id = %s;
            """,
            (access_token, token_expiry, telegram_user_id),
        )
        conn.commit()

    return access_token


def get_valid_google_access_token(telegram_user_id: int) -> str | None:
    with get_db() as (_, cur):
        cur.execute(
            """
            SELECT access_token, token_expiry
            FROM google_calendar_connections
            WHERE telegram_user_id = %s;
            """,
            (telegram_user_id,),
        )
        row = cur.fetchone()

    if not row:
        return None

    access_token = row["access_token"]
    token_expiry = row["token_expiry"]
    if access_token and token_expiry and token_expiry > datetime.now(timezone.utc):
        return access_token

    return _refresh_google_access_token(telegram_user_id)