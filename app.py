import json
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from services.gemini_client import evaluate_answer
from services.question_bank import advance_question, get_current_question, \
    previous_question
from services.streak import evaluate_daily_streak_status, record_question_completion
from services.supabase_client import AuthError, \
    is_admin_user, \
    is_available as supabase_available, \
    last_error as supabase_error, sign_in, sign_up
from services.user_store import delete_answer, load_answers, load_progress, \
    load_user_stats, save_answer, save_user_stats

# ── Data ──────────────────────────────────────────────────────────────────────
_data = json.loads(
    (Path(__file__).parent / "data" / "topics.json").read_text(
        encoding="utf-8"))
TOPICS = _data["topics"]
TOPIC_LABELS = [t["label"] for t in TOPICS]
TOPIC_BY_LABEL = {t["label"]: t["key"] for t in TOPICS}

TOPIC_COLORS = {
    "Python": "#ffffff",
    "OOP": "#aaaaaa",
    "Computer Science": "#888888",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Interview Simulator",
                   page_icon=":material/terminal:", layout="wide")

# ── Custom CSS theme ──────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

:root, .stApp {
  --bg-start: #000000;
  --bg-end: #0d0d0d;
  --surface-dark: #080808;
  --surface-hover: #121212;
  --primary-color: #ffffff !important;
  --background-color: #000000 !important;
  --secondary-background-color: #080808 !important;
  --text-color: #ffffff !important;
  --glass: rgba(255, 255, 255, 0.03);
  --glass-hover: rgba(255, 255, 255, 0.08);
  --glass-border: rgba(255, 255, 255, 0.12);
  --glass-border-hover: rgba(255, 255, 255, 0.35);
  --text-primary: #ffffff;
  --text-secondary: #999999;
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
  background: linear-gradient(135deg, #ffffff, #888888, #ffffff, #888888);
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
  font-size: 1.1rem;
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
  transform: translateY(-3px);
  border-color: var(--glass-border-hover);
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
  margin-bottom: 1rem;
}
.badge {
  background: var(--glass);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  padding: 0.35rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}
.badge--earned {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.28);
  color: #ffffff;
}

/* Streak recovery alert */
.streak-recovery-alert {
  background: rgba(255, 82, 82, 0.08);
  border: 1px solid rgba(255, 82, 82, 0.35);
  border-radius: 14px;
  padding: 0.85rem 1.15rem;
  margin-top: 0.5rem;
  margin-bottom: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.streak-recovery-content {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}
.streak-recovery-icon {
  font-size: 1.8rem;
  line-height: 1;
}
.streak-recovery-title {
  color: #ff6b6b;
  font-weight: 700;
  font-size: 0.95rem;
  margin-bottom: 0.2rem;
}
.streak-recovery-desc {
  color: #d0d0d0;
  font-size: 0.85rem;
}
.streak-progress-pill {
  background: rgba(255, 82, 82, 0.18);
  border: 1px solid rgba(255, 82, 82, 0.4);
  color: #ff8585;
  padding: 0.35rem 0.85rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 700;
  white-space: nowrap;
}

/* Topic selector wrapper */
.topic-wrapper {
  max-width: 560px;
  margin: 0 auto 1.5rem;
}

/* ── Pure Black Selectbox (Topic Picker) ──────────────────────────────────── */
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
  background-color: var(--surface-dark) !important;
  border-radius: 14px !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background-color: var(--surface-dark) !important;
  background-image: none !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: 14px !important;
  min-height: 3.2rem !important;
  box-shadow: none !important;
  outline: none !important;
  transition: all 0.2s ease !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div > div,
div[data-testid="stSelectbox"] div[data-baseweb="select"] div[role="button"] {
  background-color: transparent !important;
  color: #ffffff !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover {
  background-color: var(--surface-hover) !important;
  border-color: var(--glass-border-hover) !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div[aria-expanded="true"] {
  background-color: #0c0c0c !important;
  border: 1px solid rgba(255, 255, 255, 0.55) !important;
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.08) !important;
  outline: none !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
  color: #ffffff !important;
  font-weight: 600 !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] svg {
  fill: #999999 !important;
  transition: transform 0.2s ease, fill 0.2s ease !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"]:hover svg {
  fill: #ffffff !important;
}

/* Dropdown menu list */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="menu"],
ul[data-testid="stSelectboxVirtualDropdown"],
ul[role="listbox"] {
  background-color: #080808 !important;
  border: 1px solid rgba(255, 255, 255, 0.16) !important;
  border-radius: 14px !important;
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.85) !important;
  padding: 0.35rem !important;
}
li[role="option"] {
  background-color: transparent !important;
  color: #999999 !important;
  border-radius: 8px !important;
  margin-bottom: 2px !important;
  font-weight: 500 !important;
  transition: background-color 0.15s ease, color 0.15s ease !important;
}
li[role="option"]:hover,
li[role="option"][aria-selected="true"] {
  background-color: rgba(255, 255, 255, 0.08) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

/* ── Pure Black TextArea (Answer Field) ────────────────────────────────────── */
div[data-testid="stTextArea"] label p {
  color: var(--text-secondary) !important;
  font-size: 0.85rem !important;
  font-weight: 600 !important;
}
div[data-testid="stTextArea"] div[data-baseweb="textarea"],
div[data-testid="stTextArea"] div[data-baseweb="base-input"],
div[data-testid="stTextArea"] textarea {
  background-color: var(--surface-dark) !important;
  color: var(--text-primary) !important;
  caret-color: #ffffff !important;
}
div[data-testid="stTextArea"] div[data-baseweb="textarea"] {
  border: 1px solid var(--glass-border) !important;
  border-radius: 16px !important;
  box-shadow: none !important;
  transition: border-color 0.2s ease, background-color 0.2s ease !important;
}
div[data-testid="stTextArea"] div[data-baseweb="textarea"]:hover {
  border-color: rgba(255, 255, 255, 0.25) !important;
}
div[data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within {
  border-color: rgba(255, 255, 255, 0.45) !important;
  background-color: #0c0c0c !important;
}
div[data-testid="stTextArea"] textarea::placeholder {
  color: #666666 !important;
  -webkit-text-fill-color: #666666 !important;
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
  transform: translateY(-2px);
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.5);
}
.question-card::before {
  content: "";
  position: absolute;
  top: 0; left: 0; width: 4px; height: 100%;
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

/* ── Unified Monochrome Buttons (All identical size & dark theme) ──────────── */
div[data-testid="stButton"] > button {
  background-color: var(--surface-dark) !important;
  background-image: none !important;
  border: 1px solid var(--glass-border) !important;
  color: var(--text-primary) !important;
  border-radius: 14px !important;
  height: 3.2rem !important;
  min-height: 3.2rem !important;
  max-height: 3.2rem !important;
  padding: 0 1.25rem !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  letter-spacing: 0.01em !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
  width: 100% !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 0.5rem !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35) !important;
  margin: 0 !important;
}

div[data-testid="stButton"] > button:hover {
  background-color: #141414 !important;
  border-color: var(--glass-border-hover) !important;
  color: #ffffff !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 10px 24px -6px rgba(0, 0, 0, 0.7), 0 0 12px rgba(255, 255, 255, 0.06) !important;
}

div[data-testid="stButton"] > button:active {
  transform: translateY(0px) scale(0.99) !important;
  background-color: #1c1c1c !important;
}

div[data-testid="stButton"] > button:focus:not(:active) {
  border-color: var(--glass-border-hover) !important;
  color: #ffffff !important;
  box-shadow: none !important;
}

div[data-testid="stButton"] > button span[data-testid="stIconMaterial"] {
  font-size: 1.15rem !important;
  color: inherit !important;
  opacity: 0.9;
}

/* ── Distinct Monochrome Style for "Очистити" (3rd column) ────────────────── */
div[data-testid="stHorizontalBlock"] > div:nth-child(3) div[data-testid="stButton"] > button {
  background-color: #030303 !important;
  border: 1px dashed rgba(255, 255, 255, 0.25) !important;
  color: #999999 !important;
}

div[data-testid="stHorizontalBlock"] > div:nth-child(3) div[data-testid="stButton"] > button:hover {
  background-color: #121212 !important;
  border: 1px solid rgba(255, 255, 255, 0.55) !important;
  color: #ffffff !important;
  box-shadow: 0 10px 24px -6px rgba(0, 0, 0, 0.8), 0 0 14px rgba(255, 255, 255, 0.1) !important;
}

/* Highlight "Оцінити відповідь" (2nd column) with a brighter monochrome border */
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stButton"] > button {
  background-color: #111111 !important;
  border: 1px solid rgba(255, 255, 255, 0.28) !important;
  color: #ffffff !important;
}

div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stButton"] > button:hover {
  background-color: #1c1c1c !important;
  border-color: #ffffff !important;
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
  background: rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--topic-color), #666666);
  border-radius: 6px;
  transition: width 0.6s ease;
}
.progress-text {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

/* ── Auth card ─────────────────────────────────────────────────────────────── */
.auth-wrapper {
  max-width: 420px;
  margin: 1rem auto 2rem;
}
.auth-card {
  background: var(--glass);
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  padding: 1.75rem 1.75rem 1.25rem;
  backdrop-filter: blur(16px);
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.6);
}
.auth-hero {
  text-align: center;
  margin-bottom: 1.25rem;
}
.auth-logo {
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #ffffff, #888888, #ffffff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 0.35rem 0;
  letter-spacing: -0.02em;
}
.auth-sub {
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin: 0;
}
/* Tabs inside auth card: compact and centered */
.auth-wrapper div[data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--glass-border) !important;
  gap: 0 !important;
  margin-bottom: 1rem !important;
}
.auth-wrapper button[data-baseweb="tab"] {
  flex: 1 !important;
  background: transparent !important;
  color: var(--text-secondary) !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  padding: 0.6rem 0 !important;
}
.auth-wrapper button[data-baseweb="tab"][aria-selected="true"] {
  color: #ffffff !important;
}
.auth-wrapper div[data-baseweb="tab-highlight"] {
  background: #ffffff !important;
  height: 2px !important;
}
/* Tighten inputs inside auth card */
.auth-wrapper div[data-testid="stTextInput"] input {
  background-color: var(--surface-dark) !important;
  color: #ffffff !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: 12px !important;
  height: 2.8rem !important;
  padding: 0 0.9rem !important;
}
.auth-wrapper div[data-testid="stTextInput"] input:focus {
  border-color: rgba(255, 255, 255, 0.45) !important;
  box-shadow: none !important;
  outline: none !important;
}
.auth-wrapper div[data-testid="stTextInput"] label p {
  color: var(--text-secondary) !important;
  font-size: 0.8rem !important;
  font-weight: 600 !important;
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
    ("badges", []), ("_cache_loaded", False),
    ("user", None), ("auth_mode", "login"),
    ("last_activity_date", None),
    ("frozen_streak", 0),
    ("recovery_progress", 0),
    ("show_streak_dialog", False),
    ("show_restored_dialog", False),
    ("_stats_loaded", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Auth screen ───────────────────────────────────────────────────────────────
def _render_auth_screen():
    # Центрована компактна картка: ліва/права колонки — порожні «поля»
    _l, _c, _r = st.columns([1, 1.2, 1])
    with _c:
        st.markdown(
            """
            <div class="auth-wrapper">
              <div class="auth-card">
                <div class="auth-hero">
                  <h1 class="auth-logo">◈ Interview AI</h1>
                  <p class="auth-sub">Увійдіть, щоб зберігати прогрес між пристроями</p>
                </div>
            """,
            unsafe_allow_html=True,
        )

        if not supabase_available():
            st.error(
                "Supabase не налаштовано. Додайте SUPABASE_URL та SUPABASE_KEY "
                "у `.env` або Streamlit Secrets. Деталі: "
                f"{supabase_error() or '—'}"
            )
            st.markdown("</div></div>", unsafe_allow_html=True)
            return

        st.markdown('<div class="auth-wrapper">', unsafe_allow_html=True)
        tab_login, tab_signup = st.tabs(["Вхід", "Реєстрація"])

        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", key="login_username",
                                         placeholder="your_username")
                password = st.text_input("Пароль", type="password",
                                         key="login_password",
                                         placeholder="••••••••")
                submitted = st.form_submit_button(
                    "Увійти", use_container_width=True,
                    icon=":material/login:",
                )
                if submitted:
                    try:
                        user = sign_in(username, password)
                        st.session_state.user = user
                        st.session_state._cache_loaded = False
                        st.session_state.question = None
                        st.rerun()
                    except AuthError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Помилка: {e}")

        with tab_signup:
            with st.form("signup_form", clear_on_submit=False):
                username = st.text_input("Username (мін. 3 символи)",
                                         key="signup_username",
                                         placeholder="your_username")
                password = st.text_input("Пароль (мін. 6 символів)",
                                         type="password",
                                         key="signup_password",
                                         placeholder="••••••••")
                submitted = st.form_submit_button(
                    "Створити акаунт", use_container_width=True,
                    icon=":material/person_add:",
                )
                if submitted:
                    try:
                        user = sign_up(username, password)
                        st.session_state.user = user
                        st.session_state._cache_loaded = False
                        st.session_state.question = None
                        st.success("Акаунт створено! Ви увійшли в систему.")
                        st.rerun()
                    except AuthError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Помилка: {e}")

        # Закриваємо .auth-wrapper (внутрішній) + .auth-card + .auth-wrapper (зовнішній)
        st.markdown("</div></div></div>", unsafe_allow_html=True)


if st.session_state.user is None:
    _render_auth_screen()
    st.stop()

_USER_ID = st.session_state.user["id"]
_USERNAME = st.session_state.user["username"]
_IS_ADMIN = is_admin_user(st.session_state.user)

# Restore persisted answers for this user once per server session
if not st.session_state._cache_loaded:
    st.session_state.cache = load_answers(_USER_ID)
    st.session_state._cache_loaded = True


def _persist_user_stats():
    save_user_stats(_USER_ID, {
        "streak": st.session_state.streak,
        "last_activity_date": st.session_state.last_activity_date,
        "frozen_streak": st.session_state.frozen_streak,
        "recovery_progress": st.session_state.recovery_progress,
        "xp": st.session_state.xp,
        "level": st.session_state.level,
        "badges": st.session_state.badges,
    })


# Restore persisted user stats & check daily streak
if not st.session_state._stats_loaded:
    user_stats = load_user_stats(_USER_ID)
    user_stats, burned = evaluate_daily_streak_status(user_stats)
    save_user_stats(_USER_ID, user_stats)

    st.session_state.xp = user_stats.get("xp", 0)
    st.session_state.level = user_stats.get("level", 1)
    st.session_state.streak = user_stats.get("streak", 0)
    st.session_state.last_activity_date = user_stats.get("last_activity_date")
    st.session_state.frozen_streak = user_stats.get("frozen_streak", 0)
    st.session_state.recovery_progress = user_stats.get("recovery_progress", 0)
    st.session_state.badges = user_stats.get("badges", [])
    st.session_state._stats_loaded = True

    if burned and st.session_state.frozen_streak > 0:
        st.session_state.show_streak_dialog = True
else:
    # Check if day elapsed during active session
    curr_stats = {
        "streak": st.session_state.streak,
        "last_activity_date": st.session_state.last_activity_date,
        "frozen_streak": st.session_state.frozen_streak,
        "recovery_progress": st.session_state.recovery_progress,
    }
    updated_stats, burned = evaluate_daily_streak_status(curr_stats)
    if burned and updated_stats["frozen_streak"] != st.session_state.frozen_streak:
        st.session_state.streak = updated_stats["streak"]
        st.session_state.frozen_streak = updated_stats["frozen_streak"]
        st.session_state.recovery_progress = updated_stats["recovery_progress"]
        _persist_user_stats()
        st.session_state.show_streak_dialog = True


# ── Dialogs ───────────────────────────────────────────────────────────────────
def _on_streak_dialog_dismiss():
    st.session_state.show_streak_dialog = False


@st.dialog("🔥 Ваша серія згоріла!", width="small", on_dismiss=_on_streak_dialog_dismiss)
def _show_streak_burned_dialog(frozen_streak: int, progress: int = 0):
    st.markdown(
        f"""
        <div style="text-align: center; padding: 0.25rem 0 0.5rem;">
          <div style="font-size: 3.2rem; line-height: 1; margin-bottom: 0.75rem;">🔥</div>
          <h2 style="font-size: 1.35rem; font-weight: 800; margin-bottom: 0.5rem; color: #ff5252;">
            Ваша щоденна серія згоріла!
          </h2>
          <p style="font-size: 0.95rem; color: #d0d0d0; line-height: 1.5; margin-bottom: 1.25rem;">
            Ви пропустили дні практики, і ваша серія зупинилася на <b>{frozen_streak} дн.</b>
          </p>
          <div style="background: rgba(255, 82, 82, 0.1); border: 1px solid rgba(255, 82, 82, 0.35); border-radius: 12px; padding: 1.1rem; margin-bottom: 1.25rem; text-align: left;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.6rem;">
              <span style="font-weight: 700; color: #ffffff; font-size: 0.95rem;">
                ⚡ Пройдіть 2 питання, щоб відновити серію!
              </span>
              <span style="color: #ff8585; font-weight: 800; font-size: 0.95rem;">
                {progress} / 2
              </span>
            </div>
            <div style="background: rgba(255, 255, 255, 0.1); border-radius: 6px; height: 9px; width: 100%; overflow: hidden;">
              <div style="background: linear-gradient(90deg, #ff5252, #ff7b7b); height: 100%; width: {min(progress * 50, 100)}%; transition: width 0.3s ease;"></div>
            </div>
            <div style="margin-top: 0.6rem; font-size: 0.8rem; color: #aaaaaa; line-height: 1.4;">
              Дайте відповіді та оцініть 2 запитання, щоб повернути серію на якій ви зупинилися.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Зрозуміло, пройти 2 питання", type="primary", use_container_width=True):
        st.session_state.show_streak_dialog = False
        st.rerun()


def _on_restored_dialog_dismiss():
    st.session_state.show_restored_dialog = False


@st.dialog("🎉 Серію відновлено!", width="small", on_dismiss=_on_restored_dialog_dismiss)
def _show_streak_restored_dialog(restored_streak: int):
    st.markdown(
        f"""
        <div style="text-align: center; padding: 0.25rem 0 0.5rem;">
          <div style="font-size: 3.2rem; line-height: 1; margin-bottom: 0.75rem;">⚡</div>
          <h2 style="font-size: 1.35rem; font-weight: 800; margin-bottom: 0.5rem; color: #4caf50;">
            Серію відновлено!
          </h2>
          <p style="font-size: 1rem; color: #d0d0d0; line-height: 1.5; margin-bottom: 1.25rem;">
            Ви успішно пройшли 2 запитання та повернули свою серію: <b>{restored_streak} дн.</b>!
          </p>
          <div style="background: rgba(76, 175, 80, 0.1); border: 1px solid rgba(76, 175, 80, 0.35); border-radius: 12px; padding: 0.9rem; margin-bottom: 1rem;">
            <span style="color: #81c784; font-weight: 600; font-size: 0.9rem;">
              Продовжуйте щоденні тренування, щоб примножувати свій прогрес!
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Чудово, продовжити!", type="primary", use_container_width=True):
        st.session_state.show_restored_dialog = False
        st.rerun()


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
    evaluation = entry.get("evaluation")
    st.session_state.cache[_cache_key(topic_key, idx)] = {
        "answer": current,
        "evaluation": evaluation,
    }
    save_answer(_USER_ID, topic_key, idx, current, evaluation)


def _add_badge(badge: str):
    if badge not in st.session_state.badges:
        st.session_state.badges.append(badge)
        _persist_user_stats()


def _award_xp(points: int, score: int | None = None):
    st.session_state.xp += points
    st.session_state.level = st.session_state.xp // 100 + 1
    if score is not None and score >= 10:
        _add_badge("✦ Ідеальний рахунок 10/10")
    elif score is not None and score >= 9:
        _add_badge("★ Відмінний рахунок 9+")
    if st.session_state.streak >= 5 and "⚡ Серія 5" not in st.session_state.badges:
        _add_badge("⚡ Серія 5")
    if st.session_state.streak >= 10 and "⟡ Серія 10" not in st.session_state.badges:
        _add_badge("⟡ Серія 10")
    if len(st.session_state.history) >= 1 and "◈ Перші кроки" not in st.session_state.badges:
        _add_badge("◈ Перші кроки")
    _persist_user_stats()


def _topic_color(topic: str) -> str:
    return TOPIC_COLORS.get(topic, "#ffffff")


def _load_progress_from_disk() -> dict:
    return load_progress(_USER_ID)


# ── Hero header ───────────────────────────────────────────────────────────────
admin_badge = (
    '<span style="font-size:0.7rem; background:rgba(255,255,255,0.12); '
    'border:1px solid rgba(255,255,255,0.25); border-radius:4px; padding:2px 6px; '
    'margin-left:8px; vertical-align:middle; font-weight:700; letter-spacing:0.05em;">ADMIN</span>'
    if _IS_ADMIN else ''
)

st.markdown(f"""
<div class="hero">
  <h1 class="hero-title">◈ AI Interview Simulator</h1>
  <p class="hero-subtitle" style="font-size:0.9rem;margin-top:0.25rem;">Вітаємо, <b>{_USERNAME}</b>{admin_badge}</p>
</div>
""", unsafe_allow_html=True)

_col_logout_l, _col_logout_r = st.columns([5, 1])
with _col_logout_r:
    if st.button("Вийти", icon=":material/logout:", use_container_width=True):
        for _k in ["user", "_cache_loaded", "cache", "question",
                   "evaluation", "history", "q_index", "q_total",
                   "_stats_loaded", "streak", "xp", "level", "badges",
                   "frozen_streak", "recovery_progress", "last_activity_date",
                   "show_streak_dialog", "show_restored_dialog"]:
            st.session_state.pop(_k, None)
        st.rerun()

# ── Stats bar ─────────────────────────────────────────────────────────────────
badges_html = ""
if st.session_state.badges:
    badges_html = "".join(
        f"<span class='badge badge--earned'>{b}</span>" for b in
        st.session_state.badges
    )
else:
    badges_html = "<span class='badge' style='opacity:0.4;'>—</span>"

if st.session_state.frozen_streak > 0:
    streak_val_html = f"<span style='color:#ff5252;'>0</span> <small style='font-size:0.55em;color:#ff8585;'>({st.session_state.frozen_streak} дн.)</small>"
    streak_label_html = f"Серія (відновлення {st.session_state.recovery_progress}/2)"
else:
    streak_val_html = f"{st.session_state.streak} <small style='font-size:0.55em;color:#888;'>дн.</small>"
    streak_label_html = "Серія"

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
    <span class="stat-value">{streak_val_html}</span>
    <span class="stat-label">{streak_label_html}</span>
  </div>
  <div class="stat-card">
    <span class="stat-value">{len(st.session_state.badges)}</span>
    <span class="stat-label">Бейджі</span>
  </div>
</div>
<div class="badges-row">{badges_html}</div>
""", unsafe_allow_html=True)

if st.session_state.frozen_streak > 0:
    col_alert_txt, col_alert_btn = st.columns([5, 1])
    with col_alert_txt:
        st.markdown(
            f"""
            <div class="streak-recovery-alert">
              <div class="streak-recovery-content">
                <span class="streak-recovery-icon">🔥</span>
                <div>
                  <div class="streak-recovery-title">Ваша серія згоріла!</div>
                  <div class="streak-recovery-desc">
                    Пройдіть <b>2 питання</b>, щоб відновити серію на якій зупинилися (<b>{st.session_state.frozen_streak} дн.</b>).
                  </div>
                </div>
              </div>
              <div class="streak-progress-pill">
                ⚡ Прогрес: {st.session_state.recovery_progress} / 2
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_alert_btn:
        if st.button("Поп-ап", icon=":material/visibility:", use_container_width=True, help="Відкрити вікно відновлення"):
            st.session_state.show_streak_dialog = True
            st.rerun()

# ── Trigger streak dialogs if requested ──────────────────────────────────────
if st.session_state.get("show_streak_dialog") and st.session_state.frozen_streak > 0:
    _show_streak_burned_dialog(st.session_state.frozen_streak, st.session_state.recovery_progress)

if st.session_state.get("show_restored_dialog"):
    _show_streak_restored_dialog(st.session_state.streak)

# ── Topic selector + progress sidebar ─────────────────────────────────────────
col_topic, col_progress = st.columns([3, 1])

with col_topic:
    topic_label = st.selectbox("Тема", TOPIC_LABELS,
                               label_visibility="collapsed")
    topic = TOPIC_BY_LABEL[topic_label]
    color = _topic_color(topic)

with col_progress:
    progress = _load_progress_from_disk()
    topic_progress = progress.get(topic, 0)
    questions_bank = json.loads(
        (Path(__file__).parent / "data" / "questions_bank.json").read_text(
            encoding="utf-8"))
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

# ── Auto-restore current question & evaluation after server restart ───────────
if st.session_state.question is None:
    try:
        _q, _idx, _total = get_current_question(topic, _USER_ID)
        st.session_state.question = _q
        st.session_state.q_index = _idx
        st.session_state.q_total = _total
        _load_from_cache(topic, _idx)
    except Exception:
        pass

# ── Start / Continue ──────────────────────────────────────────────────────────
if st.button("Розпочати / Продовжити", icon=":material/play_arrow:",
             use_container_width=True):
    try:
        q, idx, total = get_current_question(topic, _USER_ID)
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

    if col_prev.button("Попереднє", icon=":material/arrow_back:",
                       use_container_width=True):
        try:
            _save_answer_to_cache(topic, idx)
            q, new_idx, total = previous_question(topic, _USER_ID)
            st.session_state.question = q
            st.session_state.q_index = new_idx
            st.session_state.q_total = total
            _load_from_cache(topic, new_idx)
            st.rerun()
        except Exception as e:
            st.error(f"Помилка: {e}")

    if col_eval.button("Оцінити відповідь", icon=":material/task_alt:",
                       use_container_width=True):
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
                    save_answer(_USER_ID, topic, idx, answer_text, result)
                    st.session_state.history.append({
                        "topic": topic,
                        "question": q,
                        "answer": answer_text,
                        "evaluation": result,
                    })
                    # ── Daily streak & recovery tracking ─────────────────────
                    curr_stats = {
                        "streak": st.session_state.streak,
                        "last_activity_date": st.session_state.last_activity_date,
                        "frozen_streak": st.session_state.frozen_streak,
                        "recovery_progress": st.session_state.recovery_progress,
                    }
                    new_stats, events = record_question_completion(curr_stats)
                    st.session_state.streak = new_stats["streak"]
                    st.session_state.last_activity_date = new_stats["last_activity_date"]
                    st.session_state.frozen_streak = new_stats["frozen_streak"]
                    st.session_state.recovery_progress = new_stats["recovery_progress"]

                    # Gamification
                    score = result.get("score", 0)
                    points = 10
                    if score >= 7:
                        points += 25
                    if score >= 9:
                        points += 50
                    _award_xp(points, score)
                    _persist_user_stats()

                    # Trigger recovery toasts / dialogs
                    if events.get("recovered"):
                        st.session_state.show_restored_dialog = True
                    elif events.get("recovery_step"):
                        step = events["recovery_step"]
                        st.toast(f"⚡ Пройдено {step} з 2 питань для відновлення серії!", icon="🔥")
                    elif events.get("new_day_increment"):
                        st.toast(f"🔥 Щоденну серію продовжено: {st.session_state.streak} дн.!", icon="🔥")
                    elif events.get("first_day"):
                        st.toast("🔥 Початок нової щоденної серії: 1 день!", icon="🔥")

                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Помилка оцінки: {e}")

    if col_refresh.button("Очистити", icon=":material/delete_sweep:",
                          use_container_width=True):
        st.session_state.cache.pop(_cache_key(topic, idx), None)
        delete_answer(_USER_ID, topic, idx)
        st.session_state.evaluation = None
        st.session_state.answer_key += 1
        st.session_state[f"answer_{st.session_state.answer_key}"] = ""
        st.rerun()

    if col_next.button("Наступне", icon=":material/arrow_forward:",
                       use_container_width=True):
        try:
            _save_answer_to_cache(topic, idx)
            q, new_idx, total = advance_question(topic, _USER_ID)
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
    score_color = "#ffffff" if score >= 7 else "#cccccc" if score >= 4 else "#888888"

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
          colors: ['#ffffff', '#cccccc', '#aaaaaa', '#888888']
        });
        </script>
        """, height=0)

    col_s, col_w = st.columns(2)
    with col_s:
        st.markdown("""
        <div class="eval-section">
          <div class="eval-section-title">✦ Сильні сторони</div>
        """, unsafe_allow_html=True)
        for item in ev.get("strengths", []):
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col_w:
        st.markdown("""
        <div class="eval-section">
          <div class="eval-section-title">△ Слабкі сторони</div>
        """, unsafe_allow_html=True)
        for item in ev.get("weaknesses", []):
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    if ev.get("missing_points"):
        st.markdown("""
        <div class="eval-section">
          <div class="eval-section-title">✕ Пропущені пункти</div>
        """, unsafe_allow_html=True)
        for item in ev["missing_points"]:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Ідеальна відповідь", icon=":material/lightbulb:"):
        st.markdown(ev.get("ideal_answer", ""))

    if ev.get("follow_up_questions"):
        with st.expander("Питання для уточнення", icon=":material/forum:"):
            for fq in ev["follow_up_questions"]:
                st.markdown(f"- {fq}")

# ── Session history ───────────────────────────────────────────────────────────
if len(st.session_state.history) > 1:
    st.markdown("---")
    with st.expander(
            f"Сесійна історія ({len(st.session_state.history)} записів)",
            icon=":material/history:"):
        for i, entry in enumerate(reversed(st.session_state.history[:-1]), 1):
            ev = entry["evaluation"]
            score = ev.get("score", "—")
            color = "#ffffff" if score >= 7 else "#cccccc" if score >= 4 else "#888888"
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

# ── Admin Testing tools ──────────────────────────────────────────────────────
if _IS_ADMIN:
    with st.expander("🛠️ Адмін: Тестування щоденної серії", expanded=False):
        st.caption("Цей блок доступний лише під акаунтом адміністратора для перевірки згоряння та відновлення серії.")
        c_dev1, c_dev2, c_dev3 = st.columns(3)
        if c_dev1.button("Симулювати згоряння серії"):
            st.session_state.streak = 5
            st.session_state.frozen_streak = 0
            st.session_state.recovery_progress = 0
            st.session_state.last_activity_date = (date.today() - timedelta(days=3)).isoformat()
            curr = {
                "streak": 5,
                "last_activity_date": st.session_state.last_activity_date,
                "frozen_streak": 0,
                "recovery_progress": 0,
            }
            res, burned = evaluate_daily_streak_status(curr)
            st.session_state.streak = res["streak"]
            st.session_state.frozen_streak = res["frozen_streak"]
            st.session_state.recovery_progress = res["recovery_progress"]
            st.session_state.show_streak_dialog = True
            _persist_user_stats()
            st.rerun()
        if c_dev2.button("Скинути серію до 0"):
            st.session_state.streak = 0
            st.session_state.frozen_streak = 0
            st.session_state.recovery_progress = 0
            st.session_state.last_activity_date = None
            _persist_user_stats()
            st.rerun()
        if c_dev3.button("Встановити серію 5 дн. (сьогодні)"):
            st.session_state.streak = 5
            st.session_state.frozen_streak = 0
            st.session_state.recovery_progress = 0
            st.session_state.last_activity_date = date.today().isoformat()
            _persist_user_stats()
            st.rerun()
