"""Tests for the local emulator webhook server."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Any

import pytest
from local_emulator.server import create_server

from incident_response.config import JiraConfig


@pytest.fixture
def running_server():
    server = create_server(host="127.0.0.1", port=0, jira_config=JiraConfig(project_key="SEC"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    yield base, server
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _request(base: str, method: str, path: str, body: bytes | None = None) -> tuple[int, Any]:
    url = base + path
    req = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.add_header("Content-Length", str(len(body)))
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
            status = getattr(resp, "status", 200)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except ValueError:
        parsed = raw.decode("utf-8", errors="replace")
    return status, parsed


def test_health_endpoint(running_server):
    base, _ = running_server
    status, body = _request(base, "GET", "/health")
    assert status == 200
    assert body["status"] == "ok"


def test_valid_webhook(running_server, high_severity_event):
    base, _ = running_server
    data = json.dumps(high_severity_event).encode("utf-8")
    status, body = _request(base, "POST", "/webhook", data)
    assert status == 200
    assert body["mock"] is True
    assert body["key"].startswith("SEC-")
    assert body["duplicate"] is False


def test_malformed_json(running_server):
    base, _ = running_server
    status, body = _request(base, "POST", "/webhook", b"{not json")
    assert status == 400
    assert body["error"] == "malformed_json"


def test_invalid_finding(running_server, malformed_event):
    base, _ = running_server
    data = json.dumps(malformed_event).encode("utf-8")
    status, body = _request(base, "POST", "/webhook", data)
    assert status == 422
    assert body["error"] == "validation_failed"


def test_unsupported_method(running_server):
    base, _ = running_server
    status, body = _request(base, "PUT", "/webhook")
    assert status == 405
    assert body["error"] == "method_not_allowed"


def test_request_body_size_limit():
    server = create_server(host="127.0.0.1", port=0, jira_config=JiraConfig(), max_body_bytes=16)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    try:
        big = b"x" * 100
        status, body = _request(base, "POST", "/webhook", big)
        assert status == 413
        assert body["error"] == "payload_too_large"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_mock_jira_dedup(running_server, high_severity_event):
    base, _ = running_server
    data = json.dumps(high_severity_event).encode("utf-8")
    s1, b1 = _request(base, "POST", "/webhook", data)
    s2, b2 = _request(base, "POST", "/webhook", data)
    assert b1["duplicate"] is False
    assert b2["duplicate"] is True
    assert b2["occurrence_count"] == 2


def test_unknown_path_get(running_server):
    base, _ = running_server
    status, body = _request(base, "GET", "/nope")
    assert status == 404
