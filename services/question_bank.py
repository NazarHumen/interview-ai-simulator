import json
from pathlib import Path
from typing import Optional

from services.user_store import load_progress, save_progress

_DATA_DIR = Path(__file__).parent.parent / "data"
_BANK_FILE = _DATA_DIR / "questions_bank.json"


def _load_bank() -> dict:
    return json.loads(_BANK_FILE.read_text(encoding="utf-8"))


def get_current_question(
    topic: str, user_id: Optional[str] = None
) -> tuple[dict, int, int]:
    """Return (question_dict, current_index, total). Resumes from saved progress."""
    questions = _load_bank().get(topic, [])
    if not questions:
        raise ValueError(f"No questions found for {topic}")
    idx = load_progress(user_id).get(topic, 0) % len(questions)
    return questions[idx], idx, len(questions)


def advance_question(
    topic: str, user_id: Optional[str] = None
) -> tuple[dict, int, int]:
    """Save next index and return (question_dict, new_index, total)."""
    questions = _load_bank().get(topic, [])
    if not questions:
        raise ValueError(f"No questions found for {topic}")
    current = load_progress(user_id).get(topic, 0)
    next_idx = (current + 1) % len(questions)
    save_progress(user_id, topic, next_idx)
    return questions[next_idx], next_idx, len(questions)


def previous_question(
    topic: str, user_id: Optional[str] = None
) -> tuple[dict, int, int]:
    """Save previous index and return (question_dict, new_index, total)."""
    questions = _load_bank().get(topic, [])
    if not questions:
        raise ValueError(f"No questions found for {topic}")
    current = load_progress(user_id).get(topic, 0)
    prev_idx = (current - 1) % len(questions)
    save_progress(user_id, topic, prev_idx)
    return questions[prev_idx], prev_idx, len(questions)
