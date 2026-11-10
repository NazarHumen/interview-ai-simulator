"""Per-user storage for answers and progress.

Primary backend: Supabase (tables `user_answers`, `user_progress`).
Fallback: local JSON files (kept for offline/dev or when Supabase is down).
Fallback files are per-user: `data/users/<user_id>/answers_cache.json`
and `data/users/<user_id>/progress.json`.

If no user_id is provided (anonymous/dev), the legacy shared files
`data/answers_cache.json` and `data/progress.json` are used — matching the
previous behavior so nothing breaks.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from services.supabase_client import get_client

_DATA_DIR = Path(__file__).parent.parent / "data"
_LEGACY_ANSWERS = _DATA_DIR / "answers_cache.json"
_LEGACY_PROGRESS = _DATA_DIR / "progress.json"


# ── Local fallback paths ──────────────────────────────────────────────────────
def _local_paths(user_id: Optional[str]) -> tuple[Path, Path]:
    if not user_id:
        return _LEGACY_ANSWERS, _LEGACY_PROGRESS
    base = _DATA_DIR / "users" / str(user_id)
    base.mkdir(parents=True, exist_ok=True)
    return base / "answers_cache.json", base / "progress.json"


def _read_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def _cache_key(topic: str, idx: int) -> str:
    return f"{topic}::{idx}"


# ── Answers cache ─────────────────────────────────────────────────────────────
def load_answers(user_id: Optional[str]) -> dict:
    """Return dict of {"<topic>::<idx>": {"answer": str, "evaluation": dict|None}}."""
    client = get_client() if user_id else None
    if client is not None:
        try:
            res = (
                client.table("user_answers")
                .select("topic, q_index, answer, evaluation")
                .eq("user_id", user_id)
                .execute()
            )
            return {
                _cache_key(r["topic"], r["q_index"]): {
                    "answer": r.get("answer") or "",
                    "evaluation": r.get("evaluation"),
                }
                for r in (res.data or [])
            }
        except Exception:
            pass  # fall back to local
    answers_path, _ = _local_paths(user_id)
    return _read_json(answers_path)


def save_answer(
    user_id: Optional[str],
    topic: str,
    idx: int,
    answer: str,
    evaluation: Optional[dict],
) -> None:
    client = get_client() if user_id else None
    if client is not None:
        try:
            client.table("user_answers").upsert(
                {
                    "user_id": user_id,
                    "topic": topic,
                    "q_index": idx,
                    "answer": answer,
                    "evaluation": evaluation,
                },
                on_conflict="user_id,topic,q_index",
            ).execute()
            return
        except Exception:
            pass
    answers_path, _ = _local_paths(user_id)
    cache = _read_json(answers_path)
    cache[_cache_key(topic, idx)] = {"answer": answer, "evaluation": evaluation}
    _write_json(answers_path, cache)


def delete_answer(user_id: Optional[str], topic: str, idx: int) -> None:
    client = get_client() if user_id else None
    if client is not None:
        try:
            (
                client.table("user_answers")
                .delete()
                .eq("user_id", user_id)
                .eq("topic", topic)
                .eq("q_index", idx)
                .execute()
            )
            return
        except Exception:
            pass
    answers_path, _ = _local_paths(user_id)
    cache = _read_json(answers_path)
    cache.pop(_cache_key(topic, idx), None)
    _write_json(answers_path, cache)


# ── Progress (current question index per topic) ───────────────────────────────
def load_progress(user_id: Optional[str]) -> dict:
    """Return dict of {"<topic>": current_idx}."""
    client = get_client() if user_id else None
    if client is not None:
        try:
            res = (
                client.table("user_progress")
                .select("topic, current_idx")
                .eq("user_id", user_id)
                .execute()
            )
            return {r["topic"]: int(r["current_idx"]) for r in (res.data or [])}
        except Exception:
            pass
    _, progress_path = _local_paths(user_id)
    return _read_json(progress_path)


def save_progress(user_id: Optional[str], topic: str, current_idx: int) -> None:
    client = get_client() if user_id else None
    if client is not None:
        try:
            client.table("user_progress").upsert(
                {
                    "user_id": user_id,
                    "topic": topic,
                    "current_idx": current_idx,
                },
                on_conflict="user_id,topic",
            ).execute()
            return
        except Exception:
            pass
    _, progress_path = _local_paths(user_id)
    progress = _read_json(progress_path)
    progress[topic] = current_idx
    _write_json(progress_path, progress)
