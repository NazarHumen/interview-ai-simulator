# 🎯 AI Interview Simulator

Practice technical interviews with AI-powered evaluation using Google Gemini.
Questions are shown in both **Ukrainian** and **English**. Answers and feedback are in Ukrainian.

## Project Structure

```
interview-simulator/
├── app.py                        # Streamlit UI
├── services/
│   ├── gemini_client.py          # Gemini API wrapper with model fallback
│   └── question_bank.py          # Question bank logic and progress tracking
├── data/
│   ├── topics.json               # Topic list with bilingual labels
│   ├── questions_bank.json       # All questions (en + uk) per topic
│   └── progress.json             # Auto-generated, tracks your position per topic
├── prompts/
│   └── evaluation_prompt.txt     # System prompt for answer evaluation
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```
GEMINI_API_KEY=your_actual_api_key_here
```

Get a free API key at: https://aistudio.google.com/app/apikey

### 3. Run the app

```bash
streamlit run app.py
```

## How it works

1. Select a **topic** from the dropdown
2. Click **"Start / Continue"** — resumes from where you left off, even after restart
3. Each question is shown in **Ukrainian** (large, bold) and English (smaller, italic)
4. Type your answer (Ukrainian or English)
5. Click **"Evaluate answer"** to receive AI feedback:
   - Score (1–10)
   - Verdict summary
   - Strengths and weaknesses
   - Missing points
   - Ideal answer
   - Follow-up questions
6. Click **"Next question"** to advance — progress is saved immediately to `data/progress.json`
7. Questions cycle back to the beginning after the last one

## Model fallback

The app tries models in this order and automatically falls back if one is unavailable or over quota:

```
gemini-2.5-flash → gemini-2.0-flash → gemini-2.0-flash-lite → gemma-3-12b-it → gemma-3-4b-it
```

## Extending

- **Add topics:** add a new entry to `data/topics.json` and a matching key in `data/questions_bank.json`
- **Add questions:** edit `data/questions_bank.json` — each question needs `"en"` and `"uk"` fields
- **Tune evaluation:** edit `prompts/evaluation_prompt.txt`
- **Change models:** edit `_MODELS` list in `services/gemini_client.py`
