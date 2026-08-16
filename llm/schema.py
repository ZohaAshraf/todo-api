"""
The output schema for POST /enrich — the shape a model's answer must match
before it's ever returned to a caller. Every category-like field is a closed
enum, straight from JOB-CARD.md.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Category(str, Enum):
    fiction = "fiction"
    nonfiction = "nonfiction"
    poetry = "poetry"
    childrens = "childrens"
    other = "other"


class QualityFlag(str, Enum):
    missing_description = "missing_description"
    suspiciously_cheap = "suspiciously_cheap"
    suspiciously_expensive = "suspiciously_expensive"
    title_too_generic = "title_too_generic"


class EnrichRequest(BaseModel):
    """What the caller sends us — one book record to enrich."""

    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=3000)
    price_gbp: float = Field(..., gt=0)


class EnrichResponse(BaseModel):
    """What we always send back — nothing else, ever."""

    category: Category
    summary: str = Field(..., max_length=200)
    quality_flags: List[QualityFlag] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
