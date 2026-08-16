"""
The LLM client — one function that turns a book record into raw model text.
Stage 3 will add parsing, validation, and repair on top of this.
"""

import json
import os
from pathlib import Path

from openai import OpenAI

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "enrich-v1.md"


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def get_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )


def call_model_for_enrichment(title: str, description: str | None, price_gbp: float) -> str:
    """
    Send one book record to the model and return the raw text it replies
    with. Temperature is kept low because this is a classification task —
    we want the same answer for the same input, not creative variation.
    """
    client = get_client()
    system_prompt = load_system_prompt()

    # Real JSON, not Python repr — and json.dumps safely escapes anything
    # in title/description that could otherwise break out of the object
    # (including an attempted prompt injection embedded in the text).
    user_content = json.dumps({
        "title": title,
        "description": description,
        "price_gbp": price_gbp,
    })

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )

    return response.choices[0].message.content
