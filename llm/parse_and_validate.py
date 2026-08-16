"""
Stage 3: everything that turns raw model text into either a trusted
EnrichResponse or a clean, logged failure. The model is an external,
untrusted source — its answer gets parsed, validated, repaired once if
needed, and quarantined if it still fails. It never reaches the caller
unvalidated.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from llm.schema import EnrichResponse

QUARANTINE_PATH = Path(__file__).resolve().parent.parent / "logs" / "quarantine.jsonl"


def extract_json_object(text: str) -> dict:
    """
    Models like to wrap JSON in a code fence or add "Sure! Here's the
    JSON:" before it. Strip that noise and find the actual object.
    Raises ValueError if no JSON object can be found or parsed.
    """
    # Strip a ```json ... ``` or ``` ... ``` fence if present.
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    candidate = fence_match.group(1) if fence_match else text

    # If there's still leading/trailing prose, grab the first {...} block.
    brace_match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if not brace_match:
        raise ValueError("no JSON object found in model output")

    return json.loads(brace_match.group(0))


def write_quarantine_entry(input_data: dict, prompt_version: str, error: str, raw_output: str) -> None:
    QUARANTINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input": input_data,
        "prompt_version": prompt_version,
        "error": error,
        "raw_output": raw_output,
    }
    with QUARANTINE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def parse_and_validate(raw_text: str) -> tuple[EnrichResponse | None, str | None]:
    """
    Try to turn raw model text into a validated EnrichResponse.
    Returns (response, None) on success, or (None, error_message) on
    failure — never raises, so the caller can decide whether to repair.
    """
    try:
        obj = extract_json_object(raw_text)
        validated = EnrichResponse(**obj)
        return validated, None
    except ValidationError as e:
        # Must come before the ValueError branch — pydantic's ValidationError
        # is itself a subclass of ValueError, so catching ValueError first
        # would mis-label every schema failure as a parsing failure.
        return None, f"schema validation failed: {e}"
    except (ValueError, json.JSONDecodeError) as e:
        return None, f"could not parse JSON: {e}"
