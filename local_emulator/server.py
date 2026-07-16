"""Lightweight local emulator webhook server (standard library only).

Endpoints:

* ``GET /health``  -> ``{"status": "ok"}``
* ``POST /webhook`` -> validates, normalizes and produces a mock Jira issue

No real Jira API call is made unless ``real_jira`` is explicitly enabled and
credentials are provided. By default it runs in mock mode.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from incident_response.config import JiraConfig
from incident_response.exceptions import ValidationError
from incident_response.logging_config import configure_logging, get_logger
from incident_response.masking import mask_secrets, mask_url
from incident_response.normalizer import normalize_event

from .jira_mock import MockJira

configure_logging()
_log = get_logger("emulator")

DEFAULT_MAX_BODY_BYTES = 256 * 1024


@dataclass
class EmulatorConfig:
    """Runtime configuration for the local emulator."""

    host: str = "127.0.0.1"
    port: int = 8080
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    jira_config: JiraConfig = field(default_factory=JiraConfig)
    environment: str = "dev"
    real_jira: bool = False
    jira_base_url: str | None = None
    jira_user_email: str | None = None
    jira_api_token: str | None = None


class EmulatorHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the local emulator."""

    server: EmulatorServer  # type: ignore[assignment]

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003 - stdlib signature
        # Use structured logging instead of stderr noise.
        _log.info(
            "http_access", extra={"method": self.command, "path": self.path, "detail": fmt % args}
        )

    def do_GET(self) -> None:  # noqa: N802 - stdlib signature
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "not_found", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802 - stdlib signature
        if self.path != "/webhook":
            self._send_json(404, {"error": "not_found", "path": self.path})
            return

        length = self._content_length()
        if length is None:
            self._send_json(400, {"error": "missing_content_length"})
            return
        if length > self.server.emulator_config.max_body_bytes:
            self._send_json(
                413,
                {
                    "error": "payload_too_large",
                    "max_bytes": self.server.emulator_config.max_body_bytes,
                },
            )
            return

        raw = self.rfile.read(length)
        try:
            event = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            _log.warning("malformed_json", extra={"error": str(exc)})
            self._send_json(400, {"error": "malformed_json", "detail": str(exc)})
            return

        if not isinstance(event, dict):
            self._send_json(400, {"error": "invalid_event", "detail": "expected a JSON object"})
            return

        try:
            finding = normalize_event(event)
        except ValidationError as exc:
            _log.warning("validation_failed", extra={"error": str(exc)})
            self._send_json(422, {"error": "validation_failed", "detail": str(exc)})
            return

        cfg = self.server.emulator_config
        if cfg.real_jira:
            _log.info(
                "real_jira_enabled_but_unimplemented", extra={"url": mask_url(cfg.jira_base_url)}
            )
            self._send_json(
                501,
                {
                    "error": "real_jira_not_implemented",
                    "detail": "configure Jira credentials and a real client to enable.",
                },
            )
            return

        response = self.server.mock_jira.create_or_update(
            finding, cfg.jira_config, environment=cfg.environment
        )
        _log.info(
            "issue_mocked",
            extra={
                "finding_id": finding.finding_id,
                "key": response.get("key"),
                "event": mask_secrets(event),
            },
        )
        self._send_json(200, response)

    def do_PUT(self) -> None:  # noqa: N802 - stdlib signature
        self._send_json(405, {"error": "method_not_allowed", "method": "PUT"})

    def do_DELETE(self) -> None:  # noqa: N802 - stdlib signature
        self._send_json(405, {"error": "method_not_allowed", "method": "DELETE"})

    def _content_length(self) -> int | None:
        value = self.headers.get("Content-Length")
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class EmulatorServer(ThreadingHTTPServer):
    """HTTP server carrying emulator configuration and a mock Jira store."""

    def __init__(self, config: EmulatorConfig, mock_jira: MockJira | None = None) -> None:
        self.emulator_config = config
        self.mock_jira = mock_jira or MockJira()
        super().__init__((config.host, config.port), EmulatorHandler)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    jira_config: JiraConfig | None = None,
    environment: str = "dev",
    real_jira: bool = False,
    jira_base_url: str | None = None,
    jira_user_email: str | None = None,
    jira_api_token: str | None = None,
) -> EmulatorServer:
    """Create an :class:`EmulatorServer` without starting it."""
    cfg = EmulatorConfig(
        host=host,
        port=port,
        max_body_bytes=max_body_bytes,
        jira_config=jira_config or JiraConfig(),
        environment=environment,
        real_jira=real_jira,
        jira_base_url=jira_base_url,
        jira_user_email=jira_user_email,
        jira_api_token=jira_api_token,
    )
    return EmulatorServer(cfg)


def run_server(config: EmulatorConfig | None = None) -> None:
    """Start the emulator server (blocking)."""
    cfg = config or EmulatorConfig()
    server = EmulatorServer(cfg)
    _log.info("starting_emulator", extra={"host": cfg.host, "port": cfg.port})
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log.info("stopping_emulator")
    finally:
        server.server_close()
