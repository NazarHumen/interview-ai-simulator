import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def _read_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")

def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Check your .env file.")
    return genai.Client(api_key=api_key)

_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemma-3-12b-it", "gemma-3-4b-it"]

def _generate(prompt: str, temperature: float = 1.0) -> str:
    client = _get_client()
    last_error = None
    for model in _MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature),
            )
            return response.text.strip()
        except Exception as e:
            last_error = e
            continue
    raise last_error

def generate_question(topic: str, difficulty: str) -> str:
    """Generate one interview question for the given topic and difficulty."""
    template = _read_prompt("question_prompt.txt")
    prompt = template.format(topic=topic, difficulty=difficulty)
    return _generate(prompt, temperature=1.5)

def evaluate_answer(question: str, answer: str) -> dict:
    """Send question + answer to Gemini and return parsed evaluation JSON."""
    template = _read_prompt("evaluation_prompt.txt")
    prompt = template.format(question=question, answer=answer)
    raw = _generate(prompt)

    # Strip markdown code fences if model wraps response anyway
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned malformed JSON: {e}\n\nRaw response:\n{raw}")
