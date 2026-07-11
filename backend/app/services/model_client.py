import logging
import time
from contextlib import contextmanager
from typing import Any

import requests

from app.core.config import (
    LLM_CONCURRENCY_LIMIT,
    LLM_CONCURRENCY_TTL_SECONDS,
    MODEL_REQUEST_BACKOFF_SECONDS,
    MODEL_REQUEST_RETRIES,
)
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)


class ModelCallError(RuntimeError):
    pass


class ModelCallTimeout(ModelCallError):
    pass


class ModelConcurrencyLimitError(ModelCallError):
    pass


RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
LLM_CONCURRENCY_REQUESTS = {
    "ollama_generation",
    "ollama_vision",
    "ollama_vision_summary",
}


@contextmanager
def llm_concurrency_slot(request_name: str):
    if LLM_CONCURRENCY_LIMIT <= 0 or request_name not in LLM_CONCURRENCY_REQUESTS:
        yield
        return

    key = "llm_concurrency:active"
    current_count = redis_client.incr(key)
    redis_client.expire(key, LLM_CONCURRENCY_TTL_SECONDS)

    if current_count > LLM_CONCURRENCY_LIMIT:
        redis_client.decr(key)
        raise ModelConcurrencyLimitError(
            f"Too many concurrent LLM requests. Limit is {LLM_CONCURRENCY_LIMIT}."
        )

    try:
        yield
    finally:
        remaining = redis_client.decr(key)
        if remaining <= 0:
            redis_client.delete(key)


def post_json_with_retry(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: int,
    request_name: str,
) -> dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(1, int(MODEL_REQUEST_RETRIES) + 2):
        try:
            with llm_concurrency_slot(request_name):
                response = requests.post(url, json=payload, timeout=timeout)

            if response.status_code in RETRYABLE_STATUS_CODES:
                response.raise_for_status()

            response.raise_for_status()

            try:
                return response.json()
            except ValueError as exc:
                raise ModelCallError(f"{request_name} returned invalid JSON") from exc

        except requests.exceptions.Timeout as exc:
            last_error = exc
            logger.warning(
                "%s timed out",
                request_name,
                extra={"attempt": attempt, "timeout_seconds": timeout},
            )

        except requests.exceptions.RequestException as exc:
            last_error = exc
            status_code = getattr(getattr(exc, "response", None), "status_code", None)

            if status_code is not None and status_code not in RETRYABLE_STATUS_CODES:
                raise ModelCallError(f"{request_name} failed with status {status_code}") from exc

            logger.warning(
                "%s failed with retryable error",
                request_name,
                extra={"attempt": attempt, "status_code": status_code},
            )

        if attempt <= MODEL_REQUEST_RETRIES:
            time.sleep(MODEL_REQUEST_BACKOFF_SECONDS * attempt)

    if isinstance(last_error, requests.exceptions.Timeout):
        raise ModelCallTimeout(f"{request_name} timed out after retries") from last_error

    raise ModelCallError(f"{request_name} failed after retries") from last_error
