"""Persistent user session management.

Provides cryptographically signed (HMAC-SHA256) session tokens that persist
across browser restarts and page refreshes via:
1. HTTP / WebSocket cookies (read natively via st.context.cookies).
2. Browser localStorage and query parameters (cross-tab and reload fallback).
3. Configurable session lifetime (defaults to 15 days).
4. Secure server-side token revocation on explicit logout.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Optional

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore

from services.supabase_client import (
    _get_secret,
    get_user_by_id,
    is_admin_user,
)

COOKIE_NAME = "interview_session_token"
DEFAULT_EXPIRY_DAYS = 15

_DATA_DIR = Path(__file__).parent.parent / "data"
_SECRET_FILE = _DATA_DIR / ".session_secret"
_REVOKED_FILE = _DATA_DIR / "revoked_tokens.json"


# ── Secret handling ───────────────────────────────────────────────────────────
def _get_session_secret() -> bytes:
    """Return persistent HMAC signing secret."""
    secret = _get_secret("SESSION_SECRET")
    if secret:
        return secret.encode("utf-8")

    supabase_key = _get_secret("SUPABASE_KEY")
    if supabase_key:
        return supabase_key.encode("utf-8")

    # Local fallback file in data/
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        if _SECRET_FILE.exists():
            content = _SECRET_FILE.read_text(encoding="utf-8").strip()
            if content:
                return content.encode("utf-8")
        # Generate new random secret
        new_secret = secrets.token_hex(32)
        _SECRET_FILE.write_text(new_secret, encoding="utf-8")
        return new_secret.encode("utf-8")
    except OSError:
        return b"interview_ai_fallback_session_secret_key_32b"


# ── Base64 helpers ────────────────────────────────────────────────────────────
def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(s: str) -> bytes:
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


# ── Revocation store ──────────────────────────────────────────────────────────
_REVOKED_IN_MEMORY: dict[str, int] = {}


def _load_revoked_tokens() -> dict[str, int]:
    """Return dict of {token_sig: exp_timestamp} combining disk and memory."""
    combined = dict(_REVOKED_IN_MEMORY)
    now = int(time.time())
    if _REVOKED_FILE.exists():
        try:
            data = json.loads(_REVOKED_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for sig, exp in data.items():
                    if isinstance(exp, (int, float)) and exp > now:
                        combined[sig] = int(exp)
        except (json.JSONDecodeError, OSError):
            pass
    # Clean up expired tokens in memory
    expired = [k for k, v in combined.items() if v <= now]
    for k in expired:
        combined.pop(k, None)
        _REVOKED_IN_MEMORY.pop(k, None)
    return combined


def _save_revoked_tokens(revoked: dict[str, int]) -> None:
    _REVOKED_IN_MEMORY.update(revoked)
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _REVOKED_FILE.write_text(
            json.dumps(revoked, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def is_token_revoked(token: str) -> bool:
    if not token or "." not in token:
        return True
    _, sig_b64 = token.strip().split(".", 1)
    revoked = _load_revoked_tokens()
    return sig_b64 in revoked


def revoke_session_token(token: Optional[str]) -> None:
    """Invalidate a session token permanently on logout."""
    if not token or "." not in token:
        return
    try:
        parts = token.strip().split(".", 1)
        if len(parts) != 2:
            return
        payload_b64, sig_b64 = parts
        payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
        exp = int(payload.get("exp", time.time() + 86400))

        revoked = _load_revoked_tokens()
        revoked[sig_b64] = exp
        _save_revoked_tokens(revoked)
    except Exception:
        pass


# ── Token lifecycle ───────────────────────────────────────────────────────────
def create_session_token(user: dict,
                         expiry_days: int = DEFAULT_EXPIRY_DAYS) -> str:
    """Generate a signed HMAC session token valid for `expiry_days`."""
    now = int(time.time())
    exp = now + int(max(1, expiry_days) * 86400)
    payload = {
        "uid": str(user["id"]),
        "usr": str(user["username"]),
        "iat": now,
        "exp": exp,
        "rnd": secrets.token_hex(8),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64encode(payload_bytes)
    sig = hmac.new(_get_session_secret(), payload_b64.encode("ascii"),
                   hashlib.sha256).digest()
    sig_b64 = _b64encode(sig)
    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: Optional[str]) -> Optional[dict]:
    """Verify session token. Returns user dict {'id', 'username', 'is_admin'} or None."""
    if not token or not isinstance(token, str) or "." not in token:
        return None

    parts = token.strip().split(".", 1)
    if len(parts) != 2:
        return None

    payload_b64, sig_b64 = parts
    try:
        # Check HMAC signature
        expected_sig = hmac.new(
            _get_session_secret(),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        provided_sig = _b64decode(sig_b64)
        if not hmac.compare_digest(provided_sig, expected_sig):
            return None

        # Check revocation
        if is_token_revoked(token):
            return None

        # Check payload and expiration
        payload_bytes = _b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            return None

        exp = payload.get("exp", 0)
        if exp < time.time():
            return None

        uid = payload.get("uid")
        usr = payload.get("usr")
        if not uid or not usr:
            return None

        # Check user in DB if reachable
        try:
            db_user = get_user_by_id(uid)
            if db_user is not None:
                return db_user
        except Exception:
            pass

        # Fallback to verified payload if DB is temporarily offline
        return {
            "id": str(uid),
            "username": str(usr),
            "is_admin": is_admin_user({"username": usr}),
        }
    except Exception:
        return None


# ── Streamlit integration helpers ─────────────────────────────────────────────
def get_browser_session_token() -> Optional[str]:
    """Read session token from Streamlit request cookies or query parameters."""
    if st is None:
        return None

    # 1. Native st.context.cookies (sent in HTTP/WebSocket headers)
    try:
        if hasattr(st, "context") and hasattr(st.context, "cookies"):
            raw = st.context.cookies.get(COOKIE_NAME)
            if raw:
                return str(raw).strip()
    except Exception:
        pass

    # 2. st.query_params (?session=...)
    try:
        if hasattr(st, "query_params"):
            raw = st.query_params.get("session")
            if raw:
                return str(raw).strip()
    except Exception:
        pass

    return None


def render_session_sync(
        token_to_set: Optional[str] = None,
        clear: bool = False,
        restore_if_empty: bool = False,
        expiry_days: int = DEFAULT_EXPIRY_DAYS,
) -> None:
    """Render client-side JavaScript to sync cookies, localStorage and query params."""
    if st is None:
        return

    max_age = int(max(1, expiry_days) * 86400)
    js_body = ""

    if clear:
        js_body = f"""
        try {{
            const cookieStr = "{COOKIE_NAME}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
            if (window.parent && window.parent.document) {{
                window.parent.document.cookie = cookieStr;
                window.parent.localStorage.removeItem("{COOKIE_NAME}");
            }}
            document.cookie = cookieStr;
            localStorage.removeItem("{COOKIE_NAME}");
        }} catch (e) {{}}
        """
    elif token_to_set:
        token_escaped = json.dumps(token_to_set)
        js_body = f"""
        try {{
            const token = {token_escaped};
            const cookieStr = "{COOKIE_NAME}=" + encodeURIComponent(token) + "; path=/; max-age={max_age}; SameSite=Lax";
            if (window.parent && window.parent.document) {{
                window.parent.document.cookie = cookieStr;
                window.parent.localStorage.setItem("{COOKIE_NAME}", token);
            }}
            document.cookie = cookieStr;
            localStorage.setItem("{COOKIE_NAME}", token);
        }} catch (e) {{}}
        """
    elif restore_if_empty:
        js_body = f"""
        try {{
            let token = null;
            if (window.parent && window.parent.localStorage) {{
                token = window.parent.localStorage.getItem("{COOKIE_NAME}");
            }}
            if (!token) {{
                token = localStorage.getItem("{COOKIE_NAME}");
            }}
            if (token) {{
                const cookieStr = "{COOKIE_NAME}=" + encodeURIComponent(token) + "; path=/; max-age={max_age}; SameSite=Lax";
                if (window.parent && window.parent.document) {{
                    window.parent.document.cookie = cookieStr;
                    const parentUrl = new URL(window.parent.location.href);
                    if (parentUrl.searchParams.get("session") !== token) {{
                        parentUrl.searchParams.set("session", token);
                        window.parent.location.replace(parentUrl.toString());
                    }}
                }}
                document.cookie = cookieStr;
            }}
        }} catch (e) {{}}
        """

    if js_body:
        try:
            import streamlit.components.v1 as components
            html_snippet = f"""
            <script>
            (function() {{
                {js_body}
            }})();
            </script>
            """
            components.html(html_snippet, height=0, width=0)
        except Exception:
            pass
