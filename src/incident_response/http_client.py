"""HTTP client with retries, exponential backoff and secret-safe errors.

Uses only the Python standard library (``urllib``). The opener and sleep
functions are injectable so tests can run without real network access or real
delays.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .config import HttpRetryConfig
from .exceptions import (
    HttpClientError,
    HttpPermanentError,
    HttpTimeoutError,
    HttpTransientError,
)
from .logging_config import get_logger
from .masking import mask_url

Opener = Callable[[urllib.request.Request], Any]
Sleeper = Callable[[float], None]

_logger = get_logger("http_client")


class HttpClient:
    """Minimal JSON POST client with retry/backoff and secret-safe logging."""

    def __init__(
        self,
        config: HttpRetryConfig | None = None,
        opener: Opener | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        self.config = config or HttpRetryConfig()
        self._opener = opener or urllib.request.urlopen
        self._sleep = sleeper or time.sleep

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """POST ``payload`` as JSON to ``url`` and return the parsed response.

        Retries on timeouts, HTTP 408, 429 (honouring Retry-After) and 5xx.
        Permanent 4xx errors raise immediately. Raises ``HttpTransientError``
        on retry exhaustion.
        """
        effective_timeout = timeout if timeout is not None else self.config.timeout_seconds
        body = json.dumps(payload).encode("utf-8")
        base_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if headers:
            base_headers.update(headers)

        last_error: HttpClientError | None = None
        attempt = 0
        while attempt <= self.config.max_retries:
            attempt += 1
            req = urllib.request.Request(url, data=body, headers=base_headers, method="POST")
            try:
                _logger.info(
                    "http_request",
                    extra={
                        "method": "POST",
                        "url": mask_url(url),
                        "attempt": attempt,
                        "timeout": effective_timeout,
                    },
                )
                with self._opener(req) as resp:  # type: ignore[union-attr]
                    status = getattr(resp, "status", 200) or 200
                    raw = resp.read()
                return _parse_response(status, raw)
            except urllib.error.HTTPError as exc:
                status = exc.code
                last_error = _classify_http_error(status, exc)
                if not self.config.is_retryable(status):
                    _logger.error(
                        "http_permanent_error", extra={"status": status, "url": mask_url(url)}
                    )
                    raise last_error from None
                retry_after = _retry_after(exc)
                backoff = retry_after if retry_after is not None else self._backoff(attempt)
                _logger.warning(
                    "http_retryable_error",
                    extra={"status": status, "attempt": attempt, "backoff": backoff},
                )
                self._sleep(backoff)
            except urllib.error.URLError as exc:
                # Timeout/socket errors are treated as transient.
                last_error = HttpTimeoutError(f"network error: {exc.reason}")
                backoff = self._backoff(attempt)
                _logger.warning(
                    "http_network_error",
                    extra={"attempt": attempt, "backoff": backoff, "error": str(exc.reason)},
                )
                self._sleep(backoff)
            except TimeoutError as exc:
                last_error = HttpTimeoutError(f"timeout: {exc}")
                backoff = self._backoff(attempt)
                _logger.warning("http_timeout", extra={"attempt": attempt, "backoff": backoff})
                self._sleep(backoff)

        assert last_error is not None  # for type checkers
        _logger.error("http_retry_exhausted", extra={"url": mask_url(url)})
        raise HttpTransientError(
            f"retry exhaustion after {attempt} attempts: {last_error}",
            status_code=last_error.status_code,
        )

    def _backoff(self, attempt: int) -> float:
        delay = self.config.initial_backoff_seconds * (2 ** (attempt - 1))
        return min(delay, self.config.max_backoff_seconds)


def _retry_after(exc: urllib.error.HTTPError) -> float | None:
    """Parse a Retry-After header (seconds only) from an HTTPError."""
    value = exc.headers.get("Retry-After") if exc.headers else None
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _classify_http_error(status: int, exc: urllib.error.HTTPError) -> HttpClientError:
    if status in (408, 429) or status >= 500:
        return HttpTransientError(f"HTTP {status}", status_code=status)
    return HttpPermanentError(f"HTTP {status}", status_code=status)


def _parse_response(status: int, raw: bytes) -> dict[str, Any]:
    if 200 <= status < 300:
        if not raw:
            return {"status_code": status}
        try:
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict):
                parsed.setdefault("status_code", status)
                return parsed
            return {"status_code": status, "body": parsed}
        except (ValueError, UnicodeDecodeError):
            return {"status_code": status, "body": raw.decode("utf-8", errors="replace")}
    # Non-2xx that somehow slipped through (shouldn't happen with HTTPError).
    raise HttpPermanentError(f"HTTP {status}", status_code=status)
