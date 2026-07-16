"""Recursive secret masking for logs and error messages."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

MASKED = "***REDACTED***"

SENSITIVE_KEY_PATTERNS: tuple[str, ...] = (
    "authorization",
    "api_token",
    "jira_api_token",
    "token",
    "password",
    "secret",
    "shared_secret",
    "webhook_url",
    "cookie",
    "x-api-key",
)

_KEY_RE = re.compile("|".join(re.escape(k) for k in SENSITIVE_KEY_PATTERNS), re.IGNORECASE)


def _is_sensitive_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    return bool(_KEY_RE.search(key))


def _mask(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if _is_sensitive_key(k):
                out[k] = MASKED
            else:
                out[k] = _mask(v)
        return out
    if isinstance(value, list):
        return [_mask(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask(item) for item in value)
    return value


def mask_value(value: Any) -> Any:
    """Deep-copy and mask sensitive fields in an arbitrary JSON-like value."""
    return _mask(value)


def mask_secrets(value: Any) -> Any:
    """Public alias for :func:`mask_value`."""
    return mask_value(value)


def mask_url(url: str | None) -> str:
    """Sanitize a URL so credentials or secret path components are hidden."""
    if not url or not isinstance(url, str):
        return "N/A"
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return "***REDACTED***"
    # Strip userinfo (credentials) from the network location.
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    if not host:
        return "***REDACTED***"
    return f"{parsed.scheme}://{host}/***"


def scrub_secrets_from_text(text: str, secrets: Iterable[str] | None = None) -> str:
    """Replace known secret literal values found in ``text`` with the placeholder."""
    if not text:
        return text
    result = text
    if secrets:
        for s in secrets:
            if s and isinstance(s, str) and s in result:
                result = result.replace(s, MASKED)
    return result
