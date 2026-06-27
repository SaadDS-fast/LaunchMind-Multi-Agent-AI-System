import os
import time

from google import genai
from openai import OpenAI

from logging_utils import log_skip


TERMINAL_ERROR_MARKERS = (
    "RESOURCE_EXHAUSTED",
    "PERMISSION_DENIED",
    "insufficient_quota",
    "invalid_api_key",
    "unauthorized",
    "forbidden",
    "429",
    "403",
    "401",
)


def _provider() -> str:
    configured = os.getenv("LLM_PROVIDER", "").strip().lower()
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if groq_key and groq_key.startswith("gsk_"):
        return "groq"
    if configured == "groq":
        return "groq"
    if configured in {"grok", "xai"}:
        return "grok"
    if configured in {"gemini", "google"}:
        return "gemini"
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"):
        return "grok"
    return "gemini"


def _model_for(provider: str, explicit_model: str | None = None) -> str:
    if provider == "grok":
        return (
            explicit_model
            or os.getenv("GROK_MODEL")
            or os.getenv("XAI_MODEL")
            or "grok-4.3"
        )
    if provider == "groq":
        return explicit_model or os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"
    return explicit_model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")


def _is_terminal_error(error: Exception) -> bool:
    error_text = str(error)
    return any(marker in error_text for marker in TERMINAL_ERROR_MARKERS)


def _call_grok(prompt: str, model: str) -> str:
    api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing XAI_API_KEY or GROK_API_KEY")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
    )
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "You are a precise startup-building assistant. Follow the requested output format exactly.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return (response.output_text or "").strip()


def _call_groq(prompt: str, model: str) -> str:
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a precise startup-building assistant. Follow the requested output format exactly.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _call_gemini(prompt: str, model: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else genai.Client()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return (response.text or "").strip()


def call_llm(prompt: str, agent_name: str, model: str | None = None, attempts: int = 3) -> str:
    """Call the configured LLM provider and return text, or an empty string for fallback."""
    provider = _provider()
    selected_model = _model_for(provider, model)
    last_error = None

    for attempt in range(attempts):
        try:
            if provider == "groq":
                return _call_groq(prompt, selected_model)
            if provider == "grok":
                return _call_grok(prompt, selected_model)
            return _call_gemini(prompt, selected_model)
        except Exception as e:
            last_error = e
            log_skip(agent_name, f"{provider.upper()} request failed on attempt {attempt + 1} ({e}).")
            if _is_terminal_error(e):
                break
            time.sleep(2**attempt)

    if last_error:
        log_skip(agent_name, f"{provider.upper()} unavailable; using fallback where available.")
    return ""
