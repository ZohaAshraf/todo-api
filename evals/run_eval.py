"""
Stage 5: run all 8 hand-labelled cases through the live /enrich endpoint
and report how many got the expected category right. Run this with the
server already running in another terminal (uvicorn main:app --port 8000).

Usage: python evals/run_eval.py
"""

import json
import time
from pathlib import Path

import requests

CASES_PATH = Path(__file__).parent / "cases.json"
ENDPOINT = "http://localhost:8000/enrich"

# Generous: our own client retries with backoff on transient errors, which
# can legitimately take longer than a single call would. A small delay
# between cases also keeps us well under OpenRouter's 20-requests-per-minute
# free-tier limit.
REQUEST_TIMEOUT_SECONDS = 90
DELAY_BETWEEN_CASES_SECONDS = 2


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    correct = 0
    failures = []

    for i, case in enumerate(cases):
        try:
            response = requests.post(ENDPOINT, json=case["input"], timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.exceptions.ReadTimeout:
            failures.append((case["id"], "request timed out after 90s -- check the server terminal for what happened"))
            continue

        if response.status_code != 200:
            failures.append((case["id"], f"HTTP {response.status_code}: {response.text[:100]}"))
            continue

        actual_category = response.json().get("category")
        expected_category = case["expected_category"]

        if actual_category == expected_category:
            correct += 1
        else:
            failures.append((
                case["id"],
                f"expected {expected_category!r}, got {actual_category!r} -- {case['note']}",
            ))

        if i < len(cases) - 1:
            time.sleep(DELAY_BETWEEN_CASES_SECONDS)

    total = len(cases)
    print(f"\nScore: {correct}/{total}\n")

    if failures:
        print("Failed cases:")
        for case_id, reason in failures:
            print(f"  #{case_id}: {reason}")
    else:
        print("All cases passed.")


if __name__ == "__main__":
    main()