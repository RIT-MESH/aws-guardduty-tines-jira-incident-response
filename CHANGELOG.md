# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-07-17

### Added
- Core Python package `incident_response` (validation, normalizer, severity,
  Jira ADF payload, dedup, HTTP client, secret masking, JSON logging).
- Optional AWS Lambda forwarder (`lambda_forwarder`).
- CLI simulator `tools/simulate_finding` (dry-run by default).
- Local emulator (`local_emulator`) with mock Jira and dedup.
- 12 sanitized GuardDuty example events.
- pytest suite (106 tests, 87.9% coverage).
- Terraform infrastructure (GuardDuty, EventBridge, API Destination, Lambda,
  IAM, SQS DLQ, CloudWatch, Secrets Manager, SSM).
- Importable Tines Story template (19 actions, credential placeholders).
- Documentation: README, architecture, setup guides, event schema, playbooks,
  threat model, monitoring, troubleshooting, demo guide, interview points.
- GitHub Actions CI/CD workflows and repository quality files.
