"""
Stage 4: structured cost logging. One JSON line per model call, written to
stdout — following twelve-factor logging (write to stdout, let the
environment route it) rather than inventing a log file.
"""

import json
from datetime import datetime, timezone


def log_call(prompt_version: str, model: str, usage_info: dict, was_repair: bool) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prompt_version": prompt_version,
        "model": model,
        "input_tokens": usage_info.get("input_tokens"),
        "output_tokens": usage_info.get("output_tokens"),
        "duration_ms": usage_info.get("duration_ms"),
        "was_repair": was_repair,
    }
    print(json.dumps({"cost_log": entry}))
