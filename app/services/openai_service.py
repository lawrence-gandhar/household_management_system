# app/services/openai_service.py
from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, TypeVar, Type

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.ai.schemas import UsageStats
from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ── Cost table (USD per 1M tokens, update as OpenAI changes pricing) ──────────
_COST_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4.1":     {"input": 2.00,  "output": 8.00},
    "gpt-4o":      {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini": {"input": 0.15,  "output": 0.60},
}


# ── Circuit breaker ───────────────────────────────────────────────────────────

class _CBState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Thread-safe circuit breaker for the OpenAI API.

    State machine:
      CLOSED ──(failures ≥ threshold)──► OPEN
      OPEN   ──(recovery_timeout elapsed)──► HALF_OPEN
      HALF_OPEN ──(success)──► CLOSED
      HALF_OPEN ──(failure)──► OPEN
    """

    def __init__(self, failure_threshold: int, recovery_timeout_s: int) -> None:
        self._threshold = failure_threshold
        self._recovery  = recovery_timeout_s
        self._failures  = 0
        self._opened_at: float | None = None
        self._state     = _CBState.CLOSED

    @property
    def state(self) -> _CBState:
        if (
            self._state == _CBState.OPEN
            and self._opened_at is not None
            and time.monotonic() - self._opened_at >= self._recovery
        ):
            self._state = _CBState.HALF_OPEN
        return self._state

    def allow(self) -> bool:
        return self.state in (_CBState.CLOSED, _CBState.HALF_OPEN)

    def success(self) -> None:
        self._failures = 0
        self._state    = _CBState.CLOSED
        self._opened_at = None

    def failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._state     = _CBState.OPEN
            self._opened_at = time.monotonic()


_breaker = CircuitBreaker(
    failure_threshold  = settings.CB_FAILURE_THRESHOLD,
    recovery_timeout_s = settings.CB_RECOVERY_TIMEOUT_S,
)


# ── Service ───────────────────────────────────────────────────────────────────

class OpenAIService:
    """
    Singleton wrapper around the AsyncOpenAI client.

    Responsibilities:
    - Structured output via OpenAI's beta.parse endpoint
    - Exponential back-off retries on transient errors
    - Circuit breaker to prevent cascade failures
    - Cost and token tracking on every call
    - Never returns raw LLM text — only validated Pydantic objects

    What it does NOT do:
    - Fetch data from the database
    - Construct prompts (callers do this)
    - Log to the database (callers do this)
    """

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key    = settings.OPENAI_API_KEY,
            timeout    = settings.OPENAI_TIMEOUT_SECONDS,
            max_retries = 0,   # we manage retries ourselves
        )

    async def structured_completion(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        temperature: float = 0.3,
    ) -> tuple[T, UsageStats]:
        """
        Call OpenAI with enforced structured output.

        Returns (validated_object, usage_stats).
        Raises OpenAIUnavailableError when circuit is OPEN.
        Raises OutputValidationError when schema enforcement fails.
        """
        if not _breaker.allow():
            raise OpenAIUnavailableError("Circuit breaker OPEN — OpenAI unavailable")

        start = time.monotonic()

        for attempt in range(settings.OPENAI_MAX_RETRIES):
            try:
                response = await self._client.beta.chat.completions.parse(
                    model           = model,
                    messages        = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    response_format = schema,
                    temperature     = temperature,
                    max_tokens      = 2048,
                )
            except openai.APITimeoutError:
                _breaker.failure()
                raise AITimeoutError(f"OpenAI timed out after {settings.OPENAI_TIMEOUT_SECONDS}s")
            except openai.RateLimitError:
                wait = 2 ** attempt
                logger.warning("OpenAI rate-limited; retry %d in %ds", attempt + 1, wait)
                await asyncio.sleep(wait)
                continue
            except openai.APIConnectionError as exc:
                _breaker.failure()
                if attempt < settings.OPENAI_MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise OpenAIUnavailableError("Connection failed") from exc
            except openai.BadRequestError as exc:
                # Don't retry — malformed request
                raise OutputValidationError(f"Bad request: {exc}") from exc

            # ── Happy path ────────────────────────────────────────
            parsed = response.choices[0].message.parsed
            if parsed is None:
                _breaker.failure()
                raise OutputValidationError("OpenAI returned null parsed content")

            _breaker.success()

            usage    = response.usage
            cost_usd = self._cost(model, usage.prompt_tokens, usage.completion_tokens)
            latency  = int((time.monotonic() - start) * 1000)

            return parsed, UsageStats(
                model             = model,
                prompt_tokens     = usage.prompt_tokens,
                completion_tokens = usage.completion_tokens,
                total_tokens      = usage.total_tokens,
                cost_usd          = cost_usd,
                latency_ms        = latency,
            )

        _breaker.failure()
        raise OpenAIUnavailableError("Exhausted retries")

    @staticmethod
    def _cost(model: str, prompt: int, completion: int) -> float:
        rates = _COST_PER_1M.get(model, {"input": 0.0, "output": 0.0})
        return round(
            (prompt * rates["input"] + completion * rates["output"]) / 1_000_000, 6
        )


# ── Exceptions ────────────────────────────────────────────────────────────────

class OpenAIServiceError(Exception):    
    pass

class OpenAIUnavailableError(OpenAIServiceError): 
    pass

class AITimeoutError(OpenAIServiceError):         
    pass

class OutputValidationError(OpenAIServiceError):  
    pass