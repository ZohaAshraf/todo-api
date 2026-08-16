"""
The LLM client — turns a book record into raw model text, with a real
timeout and an explicit, deliberate retry policy instead of the SDK's
silent defaults (10-minute timeout, 2 automatic retries).
"""

import json
import os
import random
import time
from pathlib import Path

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "enrich-v1.md"

# An HTTP endpoint should never wait as long as the SDK defaults to
# (openai-python waits up to 10 minutes by default). 20 seconds is a
# generous ceiling for a small classification call.
REQUEST_TIMEOUT_SECONDS = 20.0

# We disable the SDK's own silent retries (max_retries=0) and do our own
# instead, so the policy is explicit and visible rather than hidden inside
# a library default.
MAX_RETRIES = 2  # one original attempt + up to 2 retries on transient errors
BASE_BACKOFF_SECONDS = 1.0


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def get_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=0,  # we handle retries ourselves, deliberately
    )


def _call_with_retry(client: OpenAI, **kwargs):
    """
    Retries on timeouts, rate limits (429), and 5xx server errors —
    problems worth a second try. Never retries on 400/401/403: a bad
    request or a bad key will still be bad in a few seconds, and retrying
    those just burns quota for nothing. Uses exponential backoff with a
    little random jitter so repeated failures don't all retry in lockstep.
    """
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except (APITimeoutError, RateLimitError, APIConnectionError) as error:
            last_error = error
            if attempt < MAX_RETRIES:
                backoff = BASE_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(backoff)
                continue
            raise
        # Explicitly NOT catching AuthenticationError (401) or
        # PermissionDeniedError (403) or BadRequestError (400) — those
        # propagate immediately, on purpose, without a retry.
    raise last_error


def call_model_for_enrichment(title: str, description: str | None, price_gbp: float) -> tuple[str, dict]:
    """
    Send one book record to the model. Returns (raw_text, usage_info) where
    usage_info carries the numbers needed for cost logging: input tokens,
    output tokens, and duration in milliseconds.
    """
    client = get_client()
    system_prompt = load_system_prompt()

    user_content = json.dumps({
        "title": title,
        "description": description,
        "price_gbp": price_gbp,
    })

    start = time.monotonic()
    response = _call_with_retry(
        client,
        model=os.environ["LLM_MODEL"],
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    duration_ms = round((time.monotonic() - start) * 1000, 1)

    usage_info = {
        "input_tokens": getattr(response.usage, "prompt_tokens", None),
        "output_tokens": getattr(response.usage, "completion_tokens", None),
        "duration_ms": duration_ms,
    }

    return response.choices[0].message.content, usage_info


def call_model_for_repair(title: str, description: str | None, price_gbp: float,
                           broken_output: str, validation_error: str) -> tuple[str, dict]:
    """Same contract as call_model_for_enrichment, for the repair retry."""
    client = get_client()
    system_prompt = load_system_prompt()

    user_content = json.dumps({
        "title": title,
        "description": description,
        "price_gbp": price_gbp,
    })

    repair_instruction = (
        f"Your previous answer was rejected for this reason: {validation_error}\n\n"
        f"Your previous answer was:\n{broken_output}\n\n"
        "Return only corrected JSON matching the schema described in your instructions. "
        "No explanation, no markdown code fences — the JSON object only."
    )

    start = time.monotonic()
    response = _call_with_retry(
        client,
        model=os.environ["LLM_MODEL"],
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": broken_output},
            {"role": "user", "content": repair_instruction},
        ],
    )
    duration_ms = round((time.monotonic() - start) * 1000, 1)

    usage_info = {
        "input_tokens": getattr(response.usage, "prompt_tokens", None),
        "output_tokens": getattr(response.usage, "completion_tokens", None),
        "duration_ms": duration_ms,
    }

    return response.choices[0].message.content, usage_info