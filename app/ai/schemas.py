# app/ai/schemas.py
from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Injection-resistant validators ────────────────────────────────────────────

_INJECTION_RE = re.compile(
    r"(ignore\s+previous|system\s+prompt|jailbreak|<\|.*?\|>|\[INST\]"
    r"|forget\s+instructions|new\s+instructions|disregard)",
    re.IGNORECASE,
)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def _sanitise(value: str) -> str:
    value = _CONTROL_RE.sub("", value)
    if _INJECTION_RE.search(value):
        raise ValueError("Disallowed content pattern detected")
    return value


# ── Request (user → API) ──────────────────────────────────────────────────────

class RecipeRequest(BaseModel):
    dietary_preferences: list[
        Literal["vegetarian", "vegan", "gluten-free", "dairy-free", "halal", "kosher"]
    ] = Field(default_factory=list, max_length=5)
    cuisine_preference: str | None = Field(default=None, max_length=50)
    max_cook_time_minutes: int | None = Field(default=None, ge=5, le=480)

    @field_validator("cuisine_preference", mode="before")
    @classmethod
    def clean_cuisine(cls, v: str | None) -> str | None:
        return _sanitise(v) if v else None


# ── LLM output schema (strict) ────────────────────────────────────────────────

class RecipeStep(BaseModel):
    step_number: int = Field(ge=1, le=50)
    instruction: str = Field(min_length=5, max_length=600)
    duration_minutes: int | None = Field(default=None, ge=0, le=480)

    @field_validator("instruction", mode="before")
    @classmethod
    def clean(cls, v: str) -> str:
        return _sanitise(str(v))


class GeneratedRecipe(BaseModel):
    """
    Strict schema enforced on every LLM response.
    Any field out of range causes the entire response to be rejected.
    The AI layer never returns raw LLM text to the user.
    """
    title:              str = Field(min_length=3,  max_length=100)
    description:        str = Field(min_length=10, max_length=600)
    servings:           int = Field(ge=1, le=20)
    prep_time_minutes:  int = Field(ge=0, le=480)
    cook_time_minutes:  int = Field(ge=0, le=480)
    difficulty:         Literal["easy", "medium", "hard"]
    cuisine_type:       str = Field(max_length=60)
    ingredients_used:   list[str] = Field(min_length=1, max_length=50)
    steps:              list[RecipeStep] = Field(min_length=1, max_length=50)
    tags:               list[str] = Field(default_factory=list, max_length=10)

    @field_validator("title", "description", "cuisine_type", mode="before")
    @classmethod
    def clean_text(cls, v: str) -> str:
        return _sanitise(str(v))

    @field_validator("ingredients_used", "tags", mode="before")
    @classmethod
    def clean_list(cls, v: list) -> list:
        return [_sanitise(str(item)) for item in v]

    @model_validator(mode="after")
    def total_time_sanity(self) -> GeneratedRecipe:
        total = self.prep_time_minutes + self.cook_time_minutes
        if total > 600:
            raise ValueError("Total recipe time exceeds 10 hours — likely invalid")
        return self


# ── API response (API → user) ─────────────────────────────────────────────────

class RecipeResponse(BaseModel):
    recipe:     GeneratedRecipe
    cache_hit:  bool
    cost_usd:   float
    tokens:     int


# ── Internal usage record ──────────────────────────────────────────────────────

class UsageStats(BaseModel):
    model:             str
    prompt_tokens:     int
    completion_tokens: int
    total_tokens:      int
    cost_usd:          float
    latency_ms:        int
    cache_hit:         bool = False