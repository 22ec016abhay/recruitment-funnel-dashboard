"""Thin wrapper around the OpenAI-compatible Groq client used by AI #2 and AI #3.

The API key is read from .env by src.label_mapping.llm_mapper.get_client and is
never printed. Rate-limit errors (HTTP 429) are retried after the wait the
provider asks for, up to MAX_RETRIES attempts. Other errors are raised at once.
"""
import re
import time

from src.label_mapping.llm_mapper import get_client  # reuse the one provider implementation

MODEL = "openai/gpt-oss-20b"
MAX_RETRIES = 4
MAX_WAIT_S = 60.0
_WAIT_RE = re.compile(r"try again in\s*([0-9]+(?:\.[0-9]+)?)\s*(ms|s)\b", re.IGNORECASE)


def _is_rate_limit(err: Exception) -> bool:
    return getattr(err, "status_code", None) == 429 or type(err).__name__ == "RateLimitError"


def _wait_seconds(err: Exception, default: float = 10.0) -> float:
    """Read 'Please try again in 5.5s' (or ms) from the error text."""
    m = _WAIT_RE.search(str(err))
    if not m:
        return default
    value = float(m.group(1))
    return value / 1000.0 if m.group(2).lower() == "ms" else value


def chat(client, system: str, user: str, *, model: str = MODEL, max_tokens: int = 900,
         reasoning_effort: str = "low", sleep=time.sleep) -> tuple[str, dict]:
    """One chat call at temperature 0. Returns (text, meta)."""
    waited = 0.0
    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0,
                extra_body={"max_completion_tokens": max_tokens, "reasoning_effort": reasoning_effort},
            )
        except Exception as err:
            if _is_rate_limit(err) and attempt < MAX_RETRIES:
                wait = min(_wait_seconds(err) + 0.5, MAX_WAIT_S)
                waited += wait
                sleep(wait)
                continue
            raise
        ch = resp.choices[0]
        usage = getattr(resp, "usage", None)
        meta = {
            "latency_s": round(time.perf_counter() - t0, 3),
            "finish_reason": ch.finish_reason,
            "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "rate_limit_retries": attempt - 1,
            "rate_limit_wait_s": round(waited, 2),
        }
        return (ch.message.content or ""), meta
    raise RuntimeError("unreachable")