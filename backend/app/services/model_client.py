import logging
import time
from typing import Any

import requests

from app.core.config import MODEL_REQUEST_BACKOFF_SECONDS, MODEL_REQUEST_RETRIES

logger = logging.getLogger(__name__)


class ModelCallError(RuntimeError):
    pass


class ModelCallTimeout(ModelCallError):
    pass


RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def post_json_with_retry(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: int,
    request_name: str,
) -> dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(1, MODEL_REQUEST_RETRIES + 2):
        try:
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
