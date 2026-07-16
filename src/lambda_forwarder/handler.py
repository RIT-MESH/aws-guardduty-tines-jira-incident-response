"""Lambda handler that forwards normalized GuardDuty findings to Tines."""

from __future__ import annotations

from typing import Any

from incident_response.exceptions import (
    HttpPermanentError,
    HttpTransientError,
    ValidationError,
)
from incident_response.http_client import HttpClient
from incident_response.logging_config import configure_logging, get_logger
from incident_response.masking import mask_secrets
from incident_response.normalizer import normalize_event
from incident_response.severity import severity_label

from .config import LambdaConfig

_logger = configure_logging()


def _request_id(context: Any) -> str | None:
    if context is None:
        return None
    return getattr(context, "aws_request_id", None)


def _build_payload(finding: Any, config: LambdaConfig, request_id: str | None) -> dict[str, Any]:
    """Build the Tines webhook payload with automation metadata."""
    return {
        "source": "aws.guardduty",
        "automation": {
            "project": config.project_name,
            "environment": config.environment,
            "forwarder": "lambda-forwarder",
            "request_id": request_id,
        },
        "finding": {
            "id": finding.finding_id,
            "type": finding.finding_type,
            "title": finding.title,
            "severity": finding.severity.value,
            "severity_label": severity_label(finding.severity_score),
            "severity_score": finding.severity_score,
            "aws_account_id": finding.aws_account_id,
            "aws_region": finding.aws_region,
            "first_seen": finding.first_seen,
            "last_seen": finding.last_seen,
            "occurrence_count": finding.occurrence_count,
            "resources": [
                {"type": r.type, "id": r.id, "region": r.region} for r in finding.resources
            ],
            "remote_actors": [
                {"ip_address": a.ip_address, "country": a.country, "organization": a.organization}
                for a in finding.remote_actors
            ],
            "service_name": finding.service_name,
            "service_action_type": finding.service_action_type,
        },
    }


def _meets_severity_threshold(finding: Any, config: LambdaConfig) -> bool:
    score = finding.severity_score if finding.severity_score is not None else 0.0
    return score >= config.min_severity_score


def lambda_handler(
    event: dict[str, Any], context: Any = None, config: LambdaConfig | None = None
) -> dict[str, Any]:
    """Process a GuardDuty EventBridge event and forward it to Tines."""
    cfg = config or LambdaConfig.from_env()
    request_id = _request_id(context)
    log = get_logger("handler")

    try:
        log.info("received_event", extra={"request_id": request_id, "event": mask_secrets(event)})
        finding = normalize_event(event)
    except ValidationError as exc:
        log.error("validation_failed", extra={"request_id": request_id, "error": str(exc)})
        return {"status": "rejected", "reason": "validation_failed", "error": str(exc)}

    if not _meets_severity_threshold(finding, cfg):
        log.info(
            "below_severity_threshold",
            extra={
                "request_id": request_id,
                "score": finding.severity_score,
                "min": cfg.min_severity_score,
            },
        )
        return {
            "status": "filtered",
            "reason": "below_severity_threshold",
            "finding_id": finding.finding_id,
        }

    if not cfg.tines_webhook_url:
        log.error("missing_webhook_config", extra={"request_id": request_id})
        raise ValueError("TINES_WEBHOOK_URL is not configured")

    payload = _build_payload(finding, cfg, request_id)
    headers: dict[str, str] = {}
    if cfg.tines_shared_secret:
        headers[cfg.tines_shared_secret_header] = cfg.tines_shared_secret

    client = HttpClient(config=cfg.http)
    try:
        response = client.post_json(cfg.tines_webhook_url, payload, headers=headers)
    except (HttpTransientError, HttpPermanentError) as exc:
        log.error(
            "forwarding_failed",
            extra={"request_id": request_id, "status_code": exc.status_code, "error": str(exc)},
        )
        raise

    log.info("forwarded", extra={"request_id": request_id, "finding_id": finding.finding_id})
    return {
        "status": "forwarded",
        "finding_id": finding.finding_id,
        "severity": finding.severity.value,
        "response": response,
    }
