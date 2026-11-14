"""Daily streak logic and streak recovery management."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional, Tuple


def get_days_diff(last_date_str: Optional[str], current_date: Optional[date] = None) -> Optional[int]:
    """Return number of calendar days between last_date and current_date.
    
    Returns None if last_date_str is None or invalid.
    """
    if not last_date_str:
        return None
    if current_date is None:
        current_date = date.today()
    try:
        last_date = date.fromisoformat(str(last_date_str))
        return (current_date - last_date).days
    except (ValueError, TypeError):
        return None


def evaluate_daily_streak_status(
    stats: Dict[str, Any],
    current_date: Optional[date] = None,
) -> Tuple[Dict[str, Any], bool]:
    """Check if the user's daily streak has burned.
    
    A streak burns if more than 1 day has elapsed since last_activity_date
    (diff >= 2 days).
    
    Returns:
        (updated_stats, streak_just_burned)
    """
    if current_date is None:
        current_date = date.today()

    last_activity = stats.get("last_activity_date")
    streak = int(stats.get("streak") or 0)
    frozen = int(stats.get("frozen_streak") or 0)
    progress = int(stats.get("recovery_progress") or 0)

    diff = get_days_diff(last_activity, current_date)
    streak_burned = False

    if diff is not None and diff >= 2:
        if streak > 0:
            # Streak burned right now!
            frozen = streak
            streak = 0
            progress = 0
            streak_burned = True
        elif frozen > 0:
            # Already burned previously and waiting for recovery
            streak_burned = True

    stats["streak"] = streak
    stats["frozen_streak"] = frozen
    stats["recovery_progress"] = progress
    return stats, streak_burned


def record_question_completion(
    stats: Dict[str, Any],
    current_date: Optional[date] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Record an evaluated question for the daily streak.
    
    Returns:
        (updated_stats, event_dict)
        event_dict contains:
            - 'recovered': bool (if streak was restored on this question)
            - 'restored_streak': int (value of restored streak)
            - 'recovery_step': int (current progress, e.g. 1 of 2)
            - 'new_day_increment': bool (if streak incremented by +1 day)
            - 'already_active_today': bool (if already practiced today)
            - 'first_day': bool (if started a new streak of 1 day)
    """
    if current_date is None:
        current_date = date.today()
    today_str = current_date.isoformat()

    last_activity = stats.get("last_activity_date")
    streak = int(stats.get("streak") or 0)
    frozen = int(stats.get("frozen_streak") or 0)
    progress = int(stats.get("recovery_progress") or 0)

    events: Dict[str, Any] = {
        "recovered": False,
        "restored_streak": 0,
        "recovery_step": 0,
        "new_day_increment": False,
        "already_active_today": False,
        "first_day": False,
    }

    # If user has a burned streak waiting to be recovered
    if frozen > 0:
        progress += 1
        stats["recovery_progress"] = progress
        stats["last_activity_date"] = today_str

        if progress >= 2:
            # Successfully restored streak!
            streak = frozen
            stats["streak"] = streak
            stats["frozen_streak"] = 0
            stats["recovery_progress"] = 0
            events["recovered"] = True
            events["restored_streak"] = streak
        else:
            events["recovery_step"] = progress

        return stats, events

    # Normal daily streak logic
    diff = get_days_diff(last_activity, current_date)

    if diff is None:
        # First time user practices
        stats["streak"] = 1
        stats["last_activity_date"] = today_str
        events["first_day"] = True
    elif diff == 0:
        # Already completed for today
        events["already_active_today"] = True
    elif diff == 1:
        # Yesterday was completed, today completed -> +1 day!
        stats["streak"] = streak + 1
        stats["last_activity_date"] = today_str
        events["new_day_increment"] = True
    else:
        # diff >= 2 but frozen was 0 (streak was already 0)
        stats["streak"] = 1
        stats["last_activity_date"] = today_str
        events["first_day"] = True

    return stats, events
