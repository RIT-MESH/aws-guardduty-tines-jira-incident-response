"""Runtime configuration for the Lambda forwarder.

Configuration is read from environment variables at construction time rather
than at module import time, so tests and the Lambda runtime can inject values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from incident_response.config import HttpRetryConfig


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    return value if value is not None else default


@dataclass
class LambdaConfig:
    """Configuration built from Lambda environment variables."""

    tines_webhook_url: str = ""
    tines_shared_secret: str = ""
    tines_shared_secret_header: str = "X-Tines-Shared-Secret"
    min_severity_score: float = 0.0
    timeout_seconds: float = 10.0
    max_retries: int = 3
    environment: str = "prod"
    project_name: str = "guardduty-incident-response"
    http: HttpRetryConfig = field(default_factory=HttpRetryConfig)

    @classmethod
    def from_env(cls) -> LambdaConfig:
        """Build a config from the current process environment."""
        timeout = _to_float(_env("TINES_TIMEOUT_SECONDS"), 10.0)
        retries = _to_int(_env("TINES_MAX_RETRIES"), 3)
        min_sev = _to_float(_env("GUARDDUTY_MIN_SEVERITY"), 0.0)
        http = HttpRetryConfig(
            max_retries=retries,
            timeout_seconds=timeout,
        )
        return cls(
            tines_webhook_url=_env("TINES_WEBHOOK_URL"),
            tines_shared_secret=_env("TINES_SHARED_SECRET"),
            tines_shared_secret_header=_env("TINES_SHARED_SECRET_HEADER", "X-Tines-Shared-Secret"),
            min_severity_score=min_sev,
            timeout_seconds=timeout,
            max_retries=retries,
            environment=_env("ENVIRONMENT", "prod"),
            project_name=_env("PROJECT_NAME", "guardduty-incident-response"),
            http=http,
        )


def _to_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
