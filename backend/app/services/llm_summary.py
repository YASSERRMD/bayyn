"""Optional LLM summary service — wraps OpenAI chat completions via httpx."""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
_SUMMARY_MODEL = "gpt-4o-mini"
_SYSTEM_PROMPT = (
    "You are a precise summarizer. "
    "Summarize the following transcript in 3-5 concise sentences. "
    "Focus on the key topics discussed. Do not include personal opinions."
)
_MAX_TOKENS = 300
_TEMPERATURE = 0.3
_MAX_INPUT_CHARS = 12_000


class LLMSummaryError(Exception):
    pass


class LLMDisabledError(LLMSummaryError):
    pass


async def generate_summary(transcript_text: str) -> str:
    if not settings.enable_llm_summary:
        raise LLMDisabledError("AI summary feature is not enabled on this server.")
    if not settings.openai_api_key:
        raise LLMSummaryError("OpenAI API key is not configured.")
    if not transcript_text or not transcript_text.strip():
        raise LLMSummaryError("Cannot summarize an empty transcript.")

    truncated = len(transcript_text) > _MAX_INPUT_CHARS
    text = transcript_text[:_MAX_INPUT_CHARS]
    if truncated:
        text += "\n[Transcript truncated for summary]"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _OPENAI_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _SUMMARY_MODEL,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": _MAX_TOKENS,
                    "temperature": _TEMPERATURE,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        logger.error("OpenAI API error status=%d", status_code)
        if status_code == 401:
            raise LLMSummaryError("Invalid OpenAI API key.")
        if status_code == 429:
            raise LLMSummaryError("OpenAI rate limit exceeded. Try again later.")
        raise LLMSummaryError("Failed to generate summary. Please try again later.")

    except httpx.RequestError as exc:
        logger.error("OpenAI request error exc_type=%s", type(exc).__name__)
        raise LLMSummaryError("Failed to connect to AI service. Please try again later.")


def is_enabled() -> bool:
    return settings.enable_llm_summary and bool(settings.openai_api_key)
