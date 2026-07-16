"""Normalization of GuardDuty findings into the ``Finding`` model.

Normalization never raises on missing *optional* fields. Required fields are
assumed to have been validated upstream (see ``validation.py``). When optional
fields are absent they are represented as `
one`` or empty containers.
"""

from __future__ import annotations

import json
from typing import Any

from .exceptions import NormalizationError
from .models import AffectedResource, Finding, RemoteActor
from .severity import Severity
from .validation import validate_finding_detail


def _first_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _country(remote: dict[str, Any]) -> str | None:
    country = remote.get("country")
    if isinstance(country, dict):
        return _first_str(country.get("countryName"))
    return None


def _organization(remote: dict[str, Any]) -> str | None:
    org = remote.get("organization")
    if isinstance(org, dict):
        return _first_str(org.get("asnOrg")) or _first_str(org.get("org"))
    return _first_str(org)


def _extract_resources(detail: dict[str, Any]) -> list[AffectedResource]:
    resources = detail.get("resource")
    if not isinstance(resources, dict):
        return []
    instances = resources.get("instanceDetails")
    s3_buckets = resources.get("s3BucketDetails")
    eks = resources.get("eksClusterDetails")
    k8s = resources.get("kubernetesDetails")
    access_keys = resources.get("accessKeyDetails")
    container = resources.get("containerDetails")
    malware = resources.get("malwareScanDetails")
    other = resources.get("resourceDetails")

    extracted: list[AffectedResource] = []

    def add(
        type_name: str, ident: str | None, raw: dict[str, Any], region: str | None = None
    ) -> None:
        extracted.append(AffectedResource(type=type_name, id=ident, region=region, raw=raw or {}))

    if isinstance(instances, list):
        for inst in instances:
            if isinstance(inst, dict):
                add(
                    "EC2 Instance",
                    _first_str(inst.get("instanceId")),
                    inst,
                    _first_str(inst.get("region")),
                )
    elif isinstance(instances, dict):
        add(
            "EC2 Instance",
            _first_str(instances.get("instanceId")),
            instances,
            _first_str(instances.get("region")),
        )

    if isinstance(s3_buckets, list):
        for bucket in s3_buckets:
            if isinstance(bucket, dict):
                add("S3 Bucket", _first_str(bucket.get("name")), bucket)

    if isinstance(access_keys, dict):
        add("IAM Access Key", _first_str(access_keys.get("accessKeyId")), access_keys)

    if isinstance(eks, dict):
        add("EKS Cluster", _first_str(eks.get("name")), eks)

    if isinstance(k8s, dict):
        add("Kubernetes", _first_str(k8s.get("clusterName")), k8s)

    if isinstance(container, dict) and container:
        add("Container", _first_str(container.get("containerName")), container)

    if isinstance(malware, dict) and malware:
        add("Malware Scan", _first_str(malware.get("scanId")), malware)

    if isinstance(other, dict) and other:
        add("Resource", _first_str(other.get("resourceId")), other)

    return extracted


def _actor_from_remote(
    remote: dict[str, Any], port: int | None = None, protocol: str | None = None
) -> RemoteActor:
    return RemoteActor(
        ip_address=_first_str(remote.get("ipAddressV4")),
        country=_country(remote),
        organization=_organization(remote),
        port=port,
        protocol=protocol,
        raw=remote,
    )


def _extract_remote_actors(detail: dict[str, Any]) -> list[RemoteActor]:
    actors: list[RemoteActor] = []
    service = detail.get("service")
    if not isinstance(service, dict):
        return actors
    action = service.get("action")
    if not isinstance(action, dict):
        return actors

    net = action.get("networkConnectionAction")
    if isinstance(net, dict):
        remote = net.get("remoteIpDetails")
        remote_port = None
        remote_port_details = net.get("remotePortDetails")
        if isinstance(remote_port_details, dict):
            port = remote_port_details.get("port")
            if isinstance(port, int):
                remote_port = port
        protocol = _first_str(net.get("protocol"))
        if isinstance(remote, dict):
            actors.append(_actor_from_remote(remote, port=remote_port, protocol=protocol))

    api = action.get("awsApiCallAction")
    if isinstance(api, dict):
        remote = api.get("remoteIpDetails")
        if isinstance(remote, dict):
            actors.append(_actor_from_remote(remote))

    for key in ("portProbeAction", "dnsRequestsAction"):
        sub = action.get(key)
        if isinstance(sub, dict):
            remote = sub.get("remoteIpDetails")
            if isinstance(remote, dict):
                actors.append(_actor_from_remote(remote))

    return actors


def _extract_occurrence_count(detail: dict[str, Any]) -> int | None:
    service = detail.get("service")
    if not isinstance(service, dict):
        return None
    additional = service.get("additionalInfo")
    if isinstance(additional, dict):
        raw_count = additional.get("occurrenceCount") or additional.get("eventCount")
        if isinstance(raw_count, int):
            return raw_count
        if isinstance(raw_count, str) and raw_count.isdigit():
            return int(raw_count)
    elif isinstance(additional, str) and additional:
        try:
            parsed = json.loads(additional)
        except ValueError:
            return None
        if isinstance(parsed, dict):
            raw_count = parsed.get("occurrenceCount") or parsed.get("eventCount")
            if isinstance(raw_count, int):
                return raw_count
            if isinstance(raw_count, str) and raw_count.isdigit():
                return int(raw_count)
    count = service.get("eventCount")
    if isinstance(count, int):
        return count
    return None


def normalize_finding_detail(detail: dict[str, Any]) -> Finding:
    """Normalize a validated GuardDuty ``detail`` object into a ``Finding``."""
    try:
        validate_finding_detail(detail)
    except Exception as exc:  # pragma: no cover - re-raised as NormalizationError
        raise NormalizationError(str(exc)) from exc

    severity_score = detail.get("severity")
    try:
        severity_score_float = float(severity_score) if severity_score is not None else None
    except (TypeError, ValueError):
        severity_score_float = None

    severity = Severity.from_score(severity_score_float)

    raw_service = detail.get("service")
    service: dict[str, Any] = raw_service if isinstance(raw_service, dict) else {}
    service_action = service.get("action") if isinstance(service.get("action"), dict) else {}
    service_action_type = None
    if isinstance(service_action, dict) and service_action:
        keys = [k for k in service_action if k.endswith("Action")]
        service_action_type = keys[0] if keys else None

    first_seen = None
    last_seen = None
    if isinstance(service, dict):
        first_seen = _first_str(service.get("eventFirstSeen"))
        last_seen = _first_str(service.get("eventLastSeen"))

    return Finding(
        finding_id=detail["id"],
        finding_type=_first_str(detail.get("type")),
        title=_first_str(detail.get("title")),
        description=_first_str(detail.get("description")),
        severity_score=severity_score_float,
        severity=severity,
        aws_account_id=_first_str(detail.get("accountId")),
        aws_region=_first_str(detail.get("region")),
        first_seen=first_seen,
        last_seen=last_seen,
        created_at=_first_str(detail.get("createdAt")),
        updated_at=_first_str(detail.get("updatedAt")),
        occurrence_count=_extract_occurrence_count(detail),
        resources=_extract_resources(detail),
        service_name=_first_str(service.get("serviceName")) if isinstance(service, dict) else None,
        service_action=service_action if isinstance(service_action, dict) else {},
        service_action_type=service_action_type,
        remote_actors=_extract_remote_actors(detail),
        raw=detail,
    )


def normalize_event(event: dict[str, Any]) -> Finding:
    """Validate and normalize a full EventBridge GuardDuty finding event."""
    from .validation import validate_event

    detail = validate_event(event)
    return normalize_finding_detail(detail)
