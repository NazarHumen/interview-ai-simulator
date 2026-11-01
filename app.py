import json
from pathlib import Path

import streamlit as st

from services.gemini_client import evaluate_answer
from services.question_bank import advance_question, get_current_question, previous_question

# ── Data ──────────────────────────────────────────────────────────────────────
_data = json.loads(
    (Path(__file__).parent / "data" / "topics.json").read_text(encoding="utf-8"))
TOPICS = _data["topics"]
TOPIC_LABELS = [t["label"] for t in TOPICS]
TOPIC_BY_LABEL = {t["label"]: t["key"] for t in TOPICS}

TOPIC_COLORS = {
    "Python": "#6366f1",
    "OOP": "#ec4899",
    "Computer Science": "#10b981",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Interview Simulator", page_icon="🎯", layout="wide")

# ── Custom CSS theme ──────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

:root {
  --bg-start: #0f172a;
  --bg-end: #1e293b;
  --accent: #6366f1;
  --glass: rgba(255, 255, 255, 0.06);
  --glass-border: rgba(255, 255, 255, 0.12);
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --score-green: #22c55e;
  --score-orange: #f59e0b;
  --score-red: #ef4444;
}

.stApp {
  background: linear-gradient(135deg, var(--bg-start) 0%, var(--bg-end) 100%);
  background-attachment: fixed;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: var(--text-primary);
}

/* Hide Streamlit default chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}

/* Hero */
.hero {
  padding: 2.5rem 1rem 1rem;
  text-align: center;
  margin-bottom: 1rem;
}
.hero-title {
  font-size: 3rem;
  font-weight: 800;
  margin: 0;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #6366f1, #ec4899, #10b981, #6366f1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: gradientMove 6s ease infinite;
  background-size: 300% 300%;
}
@keyframes gradientMove {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
.hero-subtitle {
  color: var(--text-secondary);
  margin-top: 0.75rem;
  font-size: 1.15rem;
  font-weight: 400;
}

/* Stats bar */
.stats-bar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}
.stat-card {
  flex: 1;
  min-width: 130px;
  background: var(--glass);
  border: 1px solid var(--glass-border);
  border-radius: 14px;
  padding: 1rem 0.75rem;
  backdrop-filter: blur(12px);
  text-align: center;
  transition: transform 0.2s, border-color 0.2s;
}
.stat-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.3);
}
.stat-value {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--text-primary);
  display: block;
}
.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 0.25rem;
}

/* Badges row */
.badges-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
}
.badge {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  padding: 0.35rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}
.badge--earned {
  background: rgba(99, 102, 241, 0.2);
  border-color: rgba(99, 102, 241, 0.5);
  color: #a5b4fc;
}

/* Topic selector wrapper */
.topic-wrapper {
  max-width: 560px;
  margin: 0 auto 1.5rem;
}

/* Question card */
.question-card {
  background: var(--glass);
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  padding: 1.75rem 2rem;
  margin-bottom: 1.5rem;
  backdrop-filter: blur(16px);
  position: relative;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}
.question-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.4);
}
.question-card::before {
  content: "";
  position: absolute;
  top: 0; left: 0; width: 5px; height: 100%;
  background: var(--topic-color, var(--accent));
}
.question-num {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.75rem;
  display: block;
}
.question-uk {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
  line-height: 1.4;
}
.question-en {
  font-size: 0.95rem;
  color: var(--text-secondary);
  font-style: italic;
  line-height: 1.5;
}

/* Buttons — premium icon + text style */
.stButton > button {
  background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
  border: 1px solid var(--glass-border);
  color: var(--text-primary);
  border-radius: 14px;
  padding: 0.85rem 1rem;
  font-weight: 700;
  font-size: 0.9rem;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(12px);
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  position: relative;
  overflow: hidden;
}
.stButton > button::before {
  content: "";
  position: absolute;
  inset: 0;
  padding: 2px;
  background: linear-gradient(135deg, var(--accent), #4f46e5, var(--accent));
  border-radius: 14px;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: destination-out;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.25s;
  pointer-events: none;
}
.stButton > button:hover {
  border-color: rgba(255, 255, 255, 0.35);
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 16px 32px -12px rgba(0, 0, 0, 0.5);
}
.stButton > button:hover::before {
  opacity: 1;
}
.stButton > button:active {
  transform: translateY(-1px) scale(0.98);
}

/* Primary CTA button — full gradient */
.start-btn {
  background: linear-gradient(135deg, var(--accent), #4f46e5) !important;
  border: none !important;
  color: #ffffff !important;
  font-size: 1rem !important;
  padding: 1rem !important;
  box-shadow: 0 10px 24px -6px rgba(99, 102, 241, 0.45);
}
.start-btn:hover {
  background: linear-gradient(135deg, #4f46e5, var(--accent)) !important;
  transform: translateY(-3px) scale(1.02) !important;
  box-shadow: 0 16px 36px -10px rgba(99, 102, 241, 0.55) !important;
}
.start-btn::before {
  display: none !important;
}

/* Evaluate button — success gradient */
.eval-btn {
  background: linear-gradient(135deg, #22c55e, #16a34a) !important;
  border: none !important;
  color: #ffffff !important;
  font-size: 0.95rem !important;
  box-shadow: 0 10px 24px -6px rgba(34, 197, 94, 0.35);
}
.eval-btn:hover {
  background: linear-gradient(135deg, #16a34a, #22c55e) !important;
  transform: translateY(-3px) scale(1.02) !important;
  box-shadow: 0 16px 36px -10px rgba(34, 197, 94, 0.45) !important;
}
.eval-btn::before {
  display: none !important;
}

/* Secondary nav buttons — subtle glass */
.nav-btn {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid var(--glass-border) !important;
  color: var(--text-secondary) !important;
}
.nav-btn:hover {
  background: rgba(255,255,255,0.14) !important;
  border-color: rgba(255,255,255,0.3) !important;
  color: var(--text-primary) !important;
}
.nav-btn::before {
  opacity: 0 !important;
}

/* Clear button — danger tint */
.clear-btn {
  background: rgba(239, 68, 68, 0.1) !important;
  border: 1px solid rgba(239, 68, 68, 0.25) !important;
  color: #fca5a5 !important;
}
.clear-btn:hover {
  background: rgba(239, 68, 68, 0.2) !important;
  border-color: rgba(239, 68, 68, 0.45) !important;
  color: #ffffff !important;
  box-shadow: 0 12px 28px -8px rgba(239, 68, 68, 0.3) !important;
}
.clear-btn::before {
  opacity: 0 !important;
}

/* Apply button variants by column position in the action row */
/* Column 1: Previous question — nav-btn */
.stHorizontalBlock > div:nth-child(1) .stButton > button {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid var(--glass-border) !important;
  color: var(--text-secondary) !important;
}
.stHorizontalBlock > div:nth-child(1) .stButton > button:hover {
  background: rgba(255,255,255,0.14) !important;
  border-color: rgba(255,255,255,0.3) !important;
  color: var(--text-primary) !important;
  box-shadow: 0 12px 28px -8px rgba(0,0,0,0.3) !important;
}

/* Column 2: Evaluate answer — eval-btn (primary) */
.stHorizontalBlock > div:nth-child(2) .stButton > button {
  background: linear-gradient(135deg, #22c55e, #16a34a) !important;
  border: none !important;
  color: #ffffff !important;
  box-shadow: 0 10px 24px -6px rgba(34, 197, 94, 0.35);
}
.stHorizontalBlock > div:nth-child(2) .stButton > button:hover {
  background: linear-gradient(135deg, #16a34a, #22c55e) !important;
  box-shadow: 0 16px 36px -10px rgba(34, 197, 94, 0.45) !important;
}

/* Column 3: Clear answer — clear-btn (danger) */
.stHorizontalBlock > div:nth-child(3) .stButton > button {
  background: rgba(239, 68, 68, 0.1) !important;
  border: 1px solid rgba(239, 68, 68, 0.25) !important;
  color: #fca5a5 !important;
}
.stHorizontalBlock > div:nth-child(3) .stButton > button:hover {
  background: rgba(239, 68, 68, 0.2) !important;
  border-color: rgba(239, 68, 68, 0.45) !important;
  color: #ffffff !important;
  box-shadow: 0 12px 28px -8px rgba(239, 68, 68, 0.3) !important;
}

/* Column 4: Next question — nav-btn */
.stHorizontalBlock > div:nth-child(4) .stButton > button {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid var(--glass-border) !important;
  color: var(--text-secondary) !important;
}
.stHorizontalBlock > div:nth-child(4) .stButton > button:hover {
  background: rgba(255,255,255,0.14) !important;
  border-color: rgba(255,255,255,0.3) !important;
  color: var(--text-primary) !important;
  box-shadow: 0 12px 28px -8px rgba(0,0,0,0.3) !important;
}

/* Start/Continue standalone button — full gradient */
.stButton > button:has-text("▶️ Розпочати / Продовжити") {
  background: linear-gradient(135deg, var(--accent), #4f46e5) !important;
  border: none !important;
  color: #ffffff !important;
  font-size: 1rem !important;
  padding: 1rem !important;
  box-shadow: 0 10px 24px -6px rgba(99, 102, 241, 0.45);
}
.stButton > button:has-text("▶️ Розпочати / Продовжити"):hover {
  background: linear-gradient(135deg, #4f46e5, var(--accent)) !important;
  transform: translateY(-3px) scale(1.02) !important;
  box-shadow: 0 16px 36px -10px rgba(99, 102, 241, 0.55) !important;
}

/* Score circle */
.score-circle {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: var(--glass);
  border: 1px solid var(--glass-border);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin: 0 auto 1rem;
  backdrop-filter: blur(12px);
}
.score-ring {
  width: 130px;
  height: 130px;
  transform: rotate(-90deg);
}
.score-ring-bg {
  fill: none;
  stroke: rgba(255, 255, 255, 0.08);
  stroke-width: 10;
}
.score-ring-progress {
  fill: none;
  stroke-width: 10;
  stroke-linecap: round;
  transition: stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1);
}
.score-value {
  position: absolute;
  font-size: 1.9rem;
  font-weight: 800;
  color: var(--text-primary);
}

/* Evaluation card */
.eval-card {
  background: var(--glass);
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  padding: 1.75rem 2rem;
  margin-top: 1.5rem;
  backdrop-filter: blur(16px);
}
.eval-verdict {
  font-size: 1.35rem;
  font-weight: 700;
  text-align: center;
  margin-bottom: 1.25rem;
}
.eval-section {
  margin-top: 1rem;
}
.eval-section-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Progress sidebar */
.progress-card {
  background: var(--glass);
  border: 1px solid var(--glass-border);
  border-radius: 14px;
  padding: 1.25rem;
  margin-bottom: 1rem;
  backdrop-filter: blur(12px);
  text-align: center;
}
.progress-topic {
  font-weight: 700;
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
  display: block;
}
.progress-bar-wrap {
  height: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--topic-color), #818cf8);
  border-radius: 6px;
  transition: width 0.6s ease;
}
.progress-text {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

/* History */
.history-entry {
  background: var(--glass);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.75rem;
  transition: border-color 0.2s;
}
.history-entry:hover {
  border-color: rgba(255, 255, 255, 0.25);
}
.history-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
}
.history-num {
  font-weight: 700;
  color: var(--text-secondary);
}
.history-topic {
  font-size: 0.85rem;
  color: var(--text-secondary);
}
.history-score {
  font-weight: 700;
}
.history-q {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 0.35rem;
}
.history-verdict {
  font-size: 0.8rem;
  font-style: italic;
}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in [
    ("question", None), ("q_index", 0), ("q_total", 0),
    ("evaluation", None), ("history", []), ("answer_key", 0),
    ("cache", {}), ("xp", 0), ("level", 1), ("streak", 0),
    ("badges", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Helpers ───────────────────────────────────────────────────────────────────
def _cache_key(topic_key, idx):
    return f"{topic_key}::{idx}"


def _load_from_cache(topic_key, idx):
    """Restore saved answer text and evaluation for a (topic, idx) pair."""
    entry = st.session_state.cache.get(_cache_key(topic_key, idx))
    st.session_state.evaluation = entry["evaluation"] if entry else None
    st.session_state.answer_key += 1
    st.session_state[f"answer_{st.session_state.answer_key}"] = (
        entry["answer"] if entry else ""
    )


def _save_answer_to_cache(topic_key, idx):
    """Persist the currently typed answer (keeping any existing evaluation)."""
    current = st.session_state.get(f"answer_{st.session_state.answer_key}", "")
    entry = st.session_state.cache.get(_cache_key(topic_key, idx)) or {}
    st.session_state.cache[_cache_key(topic_key, idx)] = {
        "answer": current,
        "evaluation": entry.get("evaluation"),
    }


def _add_badge(badge: str):
    if badge not in st.session_state.badges:
        st.session_state.badges.append(badge)


def _award_xp(points: int, score: int | None = None):
    st.session_state.xp += points
    st.session_state.level = st.session_state.xp // 100 + 1
    if score is not None and score >= 10:
        _add_badge("💎 Ідеальний рахунок 10/10")
    elif score is not None and score >= 9:
        _add_badge("⭐ Відмінний рахунок 9+")
    if st.session_state.streak >= 5 and "🔥 Серія 5" not in st.session_state.badges:
        _add_badge("🔥 Серія 5")
    if st.session_state.streak >= 10 and "⚡ Серія 10" not in st.session_state.badges:
        _add_badge("⚡ Серія 10")
    if len(st.session_state.history) >= 1 and "👣 Перші кроки" not in st.session_state.badges:
        _add_badge("👣 Перші кроки")


def _topic_color(topic: str) -> str:
    return TOPIC_COLORS.get(topic, "#6366f1")


def _load_progress_from_disk() -> dict:
    _progress_file = Path(__file__).parent / "data" / "progress.json"
    if _progress_file.exists():
        return json.loads(_progress_file.read_text(encoding="utf-8"))
    return {}


# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1 class="hero-title">🎯 AI Interview Simulator</h1>
  <p class="hero-subtitle">Практикуйте технічні співбесіди з AI-оцінюванням · питання українською та англійською</p>
</div>
""", unsafe_allow_html=True)

# ── Stats bar ─────────────────────────────────────────────────────────────────
badges_html = ""
if st.session_state.badges:
    badges_html = "".join(
        f"<span class='badge badge--earned'>{b}</span>" for b in st.session_state.badges
    )
else:
    badges_html = "<span class='badge' style='opacity:0.4;'>—</span>"

st.markdown(f"""
<div class="stats-bar">
  <div class="stat-card">
    <span class="stat-value">{st.session_state.level}</span>
    <span class="stat-label">Рівень</span>
  </div>
  <div class="stat-card">
    <span class="stat-value">{st.session_state.xp}</span>
    <span class="stat-label">XP</span>
  </div>
  <div class="stat-card">
    <span class="stat-value">{st.session_state.streak}</span>
    <span class="stat-label">Серія</span>
  </div>
  <div class="stat-card">
    <span class="stat-value">{len(st.session_state.badges)}</span>
    <span class="stat-label">Бейджі</span>
  </div>
</div>
<div class="badges-row">{badges_html}</div>
""", unsafe_allow_html=True)

# ── Topic selector + progress sidebar ─────────────────────────────────────────
col_topic, col_progress = st.columns([3, 1])

with col_topic:
    st.markdown("<div class='topic-wrapper'>", unsafe_allow_html=True)
    topic_label = st.selectbox("Тема", TOPIC_LABELS, label_visibility="collapsed")
    topic = TOPIC_BY_LABEL[topic_label]
    color = _topic_color(topic)
    st.markdown("</div>", unsafe_allow_html=True)

with col_progress:
    progress = _load_progress_from_disk()
    topic_progress = progress.get(topic, 0)
    questions_bank = json.loads(
        (Path(__file__).parent / "data" / "questions_bank.json").read_text(encoding="utf-8"))
    total = len(questions_bank.get(topic, []))
    pct = int((topic_progress / total) * 100) if total else 0
    st.markdown(f"""
    <div class="progress-card">
      <span class="progress-topic" style="color:{color};">{topic}</span>
      <div class="progress-bar-wrap">
        <div class="progress-fill" style="width: {pct}%; --topic-color: {color};"></div>
      </div>
      <span class="progress-text">{topic_progress} з {total} питань</span>
    </div>
    """, unsafe_allow_html=True)

# ── Start / Continue ──────────────────────────────────────────────────────────
if st.button("▶️ Розпочати / Продовжити", use_container_width=True):
    try:
        q, idx, total = get_current_question(topic)
        st.session_state.question = q
        st.session_state.q_index = idx
        st.session_state.q_total = total
        _load_from_cache(topic, idx)
        st.rerun()
    except Exception as e:
        st.error(f"Помилка: {e}")

# ── Question display ──────────────────────────────────────────────────────────
if st.session_state.question:
    q = st.session_state.question
    idx = st.session_state.q_index
    total = st.session_state.q_total
    color = _topic_color(topic)

    st.markdown(f"""
    <div class="question-num">Питання {idx + 1} з {total}</div>
    <div class="question-card" style="--topic-color: {color};">
      <div class="question-uk">{q['uk']}</div>
      <div class="question-en">{q['en']}</div>
    </div>
    """, unsafe_allow_html=True)

    answer_widget_key = f"answer_{st.session_state.answer_key}"
    st.text_area(
        "Ваша відповідь (українською або англійською)",
        height=200,
        placeholder="Напишіть свою відповідь тут…",
        key=answer_widget_key,
    )

    col_prev, col_eval, col_refresh, col_next = st.columns(4)

    if col_prev.button("⬅️ Попереднє питання", use_container_width=True):
        try:
            _save_answer_to_cache(topic, idx)
            q, new_idx, total = previous_question(topic)
            st.session_state.question = q
            st.session_state.q_index = new_idx
            st.session_state.q_total = total
            _load_from_cache(topic, new_idx)
            st.rerun()
        except Exception as e:
            st.error(f"Помилка: {e}")

    if col_eval.button("✅ Оцінити відповідь", use_container_width=True):
        if not st.session_state[answer_widget_key].strip():
            st.warning("Будь ласка, введіть відповідь перед оцінкою.")
        else:
            with st.spinner("Оцінюємо вашу відповідь…"):
                try:
                    question_text = q["en"]
                    answer_text = st.session_state[answer_widget_key]
                    result = evaluate_answer(question_text, answer_text)
                    st.session_state.evaluation = result
                    st.session_state.cache[_cache_key(topic, idx)] = {
                        "answer": answer_text,
                        "evaluation": result,
                    }
                    st.session_state.history.append({
                        "topic": topic,
                        "question": q,
                        "answer": answer_text,
                        "evaluation": result,
                    })
                    # Gamification
                    st.session_state.streak += 1
                    score = result.get("score", 0)
                    points = 10
                    if score >= 7:
                        points += 25
                    if score >= 9:
                        points += 50
                    _award_xp(points, score)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Помилка оцінки: {e}")

    if col_refresh.button("🔄 Очистити", use_container_width=True,
                          help="Очистити відповідь та оцінку для цього питання"):
        st.session_state.cache.pop(_cache_key(topic, idx), None)
        st.session_state.evaluation = None
        st.session_state.streak = 0
        st.session_state.answer_key += 1
        st.session_state[f"answer_{st.session_state.answer_key}"] = ""
        st.rerun()

    if col_next.button("➡️ Наступне питання", use_container_width=True):
        try:
            _save_answer_to_cache(topic, idx)
            q, new_idx, total = advance_question(topic)
            st.session_state.question = q
            st.session_state.q_index = new_idx
            st.session_state.q_total = total
            _load_from_cache(topic, new_idx)
            st.rerun()
        except Exception as e:
            st.error(f"Помилка: {e}")

# ── Evaluation results ────────────────────────────────────────────────────────
if st.session_state.evaluation:
    ev = st.session_state.evaluation
    score = ev.get("score", "—")
    verdict = ev.get("verdict", "")
    score_color = "#22c55e" if score >= 7 else "#f59e0b" if score >= 4 else "#ef4444"

    # Animated score circle
    stroke_dasharray = 314  # 2 * PI * 50
    stroke_dashoffset = stroke_dasharray - (score / 10) * stroke_dasharray

    st.markdown(f"""
    <div class="eval-card">
      <div class="score-circle">
        <svg class="score-ring" viewBox="0 0 120 120">
          <circle class="score-ring-bg" cx="60" cy="60" r="50" />
          <circle class="score-ring-progress" cx="60" cy="60" r="50"
            stroke="{score_color}" stroke-dasharray="{stroke_dasharray}"
            stroke-dashoffset="{stroke_dashoffset}" />
        </svg>
        <div class="score-value" style="color:{score_color};">{score}/10</div>
      </div>
      <div class="eval-verdict" style="color:{score_color};">{verdict}</div>
    </div>
    """, unsafe_allow_html=True)

    # Confetti celebration for high scores
    if score >= 8:
        st.components.v1.html("""
        <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
        <script>
        confetti({
          particleCount: 160,
          spread: 80,
          origin: { y: 0.45 },
          colors: ['#6366f1', '#ec4899', '#10b981', '#f59e0b']
        });
        </script>
        """, height=0)

    col_s, col_w = st.columns(2)
    with col_s:
        st.markdown("""
        <div class="eval-section">
          <div class="eval-section-title">✅ Сильні сторони</div>
        """, unsafe_allow_html=True)
        for item in ev.get("strengths", []):
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col_w:
        st.markdown("""
        <div class="eval-section">
          <div class="eval-section-title">⚠️ Слабкі сторони</div>
        """, unsafe_allow_html=True)
        for item in ev.get("weaknesses", []):
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    if ev.get("missing_points"):
        st.markdown("""
        <div class="eval-section">
          <div class="eval-section-title">❌ Пропущені пункти</div>
        """, unsafe_allow_html=True)
        for item in ev["missing_points"]:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("💡 Ідеальна відповідь"):
        st.markdown(ev.get("ideal_answer", ""))

    if ev.get("follow_up_questions"):
        with st.expander("🔁 Питання для уточнення"):
            for fq in ev["follow_up_questions"]:
                st.markdown(f"- {fq}")

# ── Session history ───────────────────────────────────────────────────────────
if len(st.session_state.history) > 1:
    st.markdown("---")
    with st.expander(f"📜 Сесійна історія ({len(st.session_state.history)} записів)"):
        for i, entry in enumerate(reversed(st.session_state.history[:-1]), 1):
            ev = entry["evaluation"]
            score = ev.get("score", "—")
            color = "#22c55e" if score >= 7 else "#f59e0b" if score >= 4 else "#ef4444"
            topic_color = _topic_color(entry["topic"])
            st.markdown(f"""
            <div class="history-entry" style="border-left: 4px solid {topic_color};">
              <div class="history-row">
                <span class="history-num">#{len(st.session_state.history) - i}</span>
                <span class="history-topic">{entry['topic']}</span>
                <span class="history-score" style="color:{color};">Score: {score}/10</span>
              </div>
              <div class="history-q">{entry['question']['en']}</div>
              <div class="history-verdict" style="color:{color};">{ev.get('verdict', '')}</div>
            </div>
            """, unsafe_allow_html=True)
