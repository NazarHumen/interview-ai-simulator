import json
from pathlib import Path

import streamlit as st

from services.gemini_client import evaluate_answer
from services.question_bank import advance_question, get_current_question, previous_question

# ── Data ──────────────────────────────────────────────────────────────────────
_data = json.loads((Path(__file__).parent / "data" / "topics.json").read_text())
TOPICS = _data["topics"]
TOPIC_LABELS = [t["label"] for t in TOPICS]
TOPIC_BY_LABEL = {t["label"]: t["key"] for t in TOPICS}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Interview Simulator", page_icon="🎯")
st.title("🎯 AI Interview Simulator")
st.caption("Practice technical interviews with AI-powered evaluation")

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in [("question", None), ("q_index", 0), ("q_total", 0),
                     ("evaluation", None), ("history", []), ("answer_key", 0),
                     ("cache", {})]:
    if key not in st.session_state:
        st.session_state[key] = default


def _cache_key(topic_key, idx):
    return f"{topic_key}::{idx}"


def _load_from_cache(topic_key, idx):
    """Restore saved answer text and evaluation for a (topic, idx) pair."""
    entry = st.session_state.cache.get(_cache_key(topic_key, idx))
    st.session_state.evaluation = entry["evaluation"] if entry else None
    st.session_state.answer_key += 1
    # Pre-populate the (new) answer widget value via session_state before it is created.
    st.session_state[f"answer_{st.session_state.answer_key}"] = (
        entry["answer"] if entry else ""
    )


def _save_answer_to_cache(topic_key, idx):
    """Persist the currently typed answer (keeping any existing evaluation) for a (topic, idx) pair."""
    current = st.session_state.get(f"answer_{st.session_state.answer_key}", "")
    entry = st.session_state.cache.get(_cache_key(topic_key, idx)) or {}
    st.session_state.cache[_cache_key(topic_key, idx)] = {
        "answer": current,
        "evaluation": entry.get("evaluation"),
    }

# ── Controls ──────────────────────────────────────────────────────────────────
topic_label = st.selectbox("Topic", TOPIC_LABELS)
topic = TOPIC_BY_LABEL[topic_label]

if st.button("▶️ Start / Continue", use_container_width=True):
    try:
        q, idx, total = get_current_question(topic)
        st.session_state.question = q
        st.session_state.q_index = idx
        st.session_state.q_total = total
        _load_from_cache(topic, idx)
    except Exception as e:
        st.error(f"Error: {e}")

# ── Question display ──────────────────────────────────────────────────────────
if st.session_state.question:
    q = st.session_state.question
    idx = st.session_state.q_index
    total = st.session_state.q_total

    st.caption(f"Question {idx + 1} of {total}")

    # Bilingual question card: Ukrainian bold+large, English smaller below
    st.markdown(
        f"""
        <div style="
            background: #1e2a3a;
            border-left: 4px solid #4a9eff;
            border-radius: 6px;
            padding: 16px 20px;
            margin-bottom: 8px;
        ">
            <div style="font-size: 1.15rem; font-weight: 700; color: #e8f0fe; margin-bottom: 6px;">
                {q['uk']}
            </div>
            <div style="font-size: 0.85rem; color: #8899aa; font-style: italic;">
                {q['en']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    answer_widget_key = f"answer_{st.session_state.answer_key}"
    st.text_area(
        "Your answer (Ukrainian or English)",
        height=200,
        placeholder="Type your answer here...",
        key=answer_widget_key,
    )

    col_prev, col_eval, col_refresh, col_next = st.columns(4)

    if col_prev.button("⬅️ Previous question", use_container_width=True):
        try:
            _save_answer_to_cache(topic, idx)
            q, new_idx, total = previous_question(topic)
            st.session_state.question = q
            st.session_state.q_index = new_idx
            st.session_state.q_total = total
            _load_from_cache(topic, new_idx)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    if col_eval.button("✅ Evaluate answer", use_container_width=True):
        if not st.session_state[answer_widget_key].strip():
            st.warning("Please enter your answer before evaluating.")
        else:
            with st.spinner("Evaluating..."):
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
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Evaluation error: {e}")

    if col_refresh.button("🔄 Clear answer", use_container_width=True,
                          help="Clear LLM evaluation and your answer for this question"):
        st.session_state.cache.pop(_cache_key(topic, idx), None)
        st.session_state.evaluation = None
        st.session_state.answer_key += 1
        st.session_state[f"answer_{st.session_state.answer_key}"] = ""
        st.rerun()

    if col_next.button("➡️ Next question", use_container_width=True):
        try:
            _save_answer_to_cache(topic, idx)
            q, new_idx, total = advance_question(topic)
            st.session_state.question = q
            st.session_state.q_index = new_idx
            st.session_state.q_total = total
            _load_from_cache(topic, new_idx)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# ── Evaluation results ────────────────────────────────────────────────────────
if st.session_state.evaluation:
    ev = st.session_state.evaluation
    st.divider()
    st.subheader("📊 Evaluation result")

    score = ev.get("score", "—")
    verdict = ev.get("verdict", "")

    color = "green" if score >= 7 else "orange" if score >= 4 else "red"
    st.markdown(f"### Score: :{color}[{score}/10]")
    st.markdown(f"**Verdict:** {verdict}")

    col_s, col_w = st.columns(2)
    with col_s:
        st.markdown("**✅ Strengths**")
        for item in ev.get("strengths", []):
            st.markdown(f"- {item}")
    with col_w:
        st.markdown("**⚠️ Weaknesses**")
        for item in ev.get("weaknesses", []):
            st.markdown(f"- {item}")

    if ev.get("missing_points"):
        st.markdown("**❌ Missing points**")
        for item in ev["missing_points"]:
            st.markdown(f"- {item}")

    with st.expander("💡 Ideal answer"):
        st.markdown(ev.get("ideal_answer", ""))

    if ev.get("follow_up_questions"):
        with st.expander("🔁 Follow-up questions"):
            for fq in ev["follow_up_questions"]:
                st.markdown(f"- {fq}")

# ── Session history ───────────────────────────────────────────────────────────
if len(st.session_state.history) > 1:
    st.divider()
    with st.expander(f"📜 Session history ({len(st.session_state.history)} entries)"):
        for i, entry in enumerate(reversed(st.session_state.history[:-1]), 1):
            ev = entry["evaluation"]
            score = ev.get("score", "—")
            st.markdown(
                f"**#{len(st.session_state.history) - i}** | "
                f"{entry['topic']} · Score: **{score}/10**"
            )
            st.markdown(f"> {entry['question']['en']}")
            st.caption(ev.get("verdict", ""))
            st.markdown("---")
