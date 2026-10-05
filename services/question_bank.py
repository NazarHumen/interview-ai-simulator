import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"
_BANK_FILE = _DATA_DIR / "questions_bank.json"
_PROGRESS_FILE = _DATA_DIR / "progress.json"


def _load_bank() -> dict:
    return json.loads(_BANK_FILE.read_text(encoding="utf-8"))


def _load_progress() -> dict:
    if _PROGRESS_FILE.exists():
        return json.loads(_PROGRESS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_progress(progress: dict) -> None:
    _PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def get_current_question(topic: str) -> tuple[dict, int, int]:
    """Return (question_dict, current_index, total). Resumes from saved progress."""
    questions = _load_bank().get(topic, [])
    if not questions:
        raise ValueError(f"No questions found for {topic}")
    idx = _load_progress().get(topic, 0) % len(questions)
    return questions[idx], idx, len(questions)


def advance_question(topic: str) -> tuple[dict, int, int]:
    """Save next index to disk and return (question_dict, new_index, total)."""
    questions = _load_bank().get(topic, [])
    if not questions:
        raise ValueError(f"No questions found for {topic}")
    progress = _load_progress()
    next_idx = (progress.get(topic, 0) + 1) % len(questions)
    progress[topic] = next_idx
    _save_progress(progress)
    return questions[next_idx], next_idx, len(questions)
