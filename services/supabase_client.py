"""Supabase client + simple username/password auth.

Credentials are read from (in order):
  1. Streamlit secrets: st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
  2. Environment variables: SUPABASE_URL, SUPABASE_KEY

The key should be the service_role key (backend-only, never exposed to the
browser directly — Streamlit runs server-side, so this is OK).

This module purposefully does NOT use Supabase Auth; we store users in our own
`users` table and hash passwords with bcrypt.
"""
from __future__ import annotations

import os
from typing import Optional

import bcrypt

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover
    Client = None  # type: ignore
    create_client = None  # type: ignore


# ── Credentials ───────────────────────────────────────────────────────────────
def _get_secret(name: str) -> Optional[str]:
    if st is not None:
        try:
            if name in st.secrets:
                return str(st.secrets[name])
        except Exception:
            pass
    return os.environ.get(name)


# ── Client singleton ──────────────────────────────────────────────────────────
_client: Optional["Client"] = None
_init_error: Optional[str] = None


def get_client() -> Optional["Client"]:
    """Return a cached Supabase client, or None if not configured/available."""
    global _client, _init_error
    if _client is not None:
        return _client
    if create_client is None:
        _init_error = "supabase package is not installed"
        return None
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_KEY")
    if not url or not key:
        _init_error = "SUPABASE_URL / SUPABASE_KEY not configured"
        return None
    try:
        _client = create_client(url, key)
        return _client
    except Exception as e:  # pragma: no cover
        _init_error = f"Supabase init failed: {e}"
        return None


def is_available() -> bool:
    return get_client() is not None


def last_error() -> Optional[str]:
    return _init_error


# ── Password hashing ──────────────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except Exception:
        return False


# ── Auth ──────────────────────────────────────────────────────────────────────
class AuthError(Exception):
    pass


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def sign_up(username: str, password: str) -> dict:
    """Create a new user. Returns {'id', 'username'}. Raises AuthError."""
    client = get_client()
    if client is None:
        raise AuthError("Supabase не налаштовано.")
    username = _normalize_username(username)
    if len(username) < 3:
        raise AuthError("Username має містити щонайменше 3 символи.")
    if len(password) < 6:
        raise AuthError("Пароль має містити щонайменше 6 символів.")

    # Check uniqueness
    existing = (
        client.table("users").select("id").eq("username", username).execute()
    )
    if existing.data:
        raise AuthError("Такий username уже зайнятий.")

    res = (
        client.table("users")
        .insert({"username": username, "password_hash": _hash_password(password)})
        .execute()
    )
    if not res.data:
        raise AuthError("Не вдалося створити користувача.")
    row = res.data[0]
    return {"id": row["id"], "username": row["username"]}


def sign_in(username: str, password: str) -> dict:
    """Verify credentials. Returns {'id', 'username'}. Raises AuthError."""
    client = get_client()
    if client is None:
        raise AuthError("Supabase не налаштовано.")
    username = _normalize_username(username)
    res = (
        client.table("users")
        .select("id, username, password_hash")
        .eq("username", username)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise AuthError("Невірний username або пароль.")
    row = res.data[0]
    if not _verify_password(password, row["password_hash"]):
        raise AuthError("Невірний username або пароль.")
    return {"id": row["id"], "username": row["username"]}
