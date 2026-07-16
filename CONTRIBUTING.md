# Contributing

Thanks for your interest in contributing! This is an educational portfolio
project, but contributions and improvements are welcome.

## Ways to contribute

- Report bugs via GitHub Issues.
- Suggest features via GitHub Issues.
- Open pull requests with fixes or documentation improvements.

## Development setup

```powershell
python -m pip install -e ".[dev]"
```

## Before opening a pull request

Run all checks locally and ensure they pass:

```powershell
ruff check .
black --check .
mypy src tools local_emulator
python -m pytest
python -m pytest --cov=src/incident_response --cov=src/lambda_forwarder --cov=tools --cov=local_emulator --cov-report=term-missing --cov-fail-under=85
cd terraform
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
cd ..
```

## Commit message style

Use conventional commits, e.g. `feat:`, `fix:`, `docs:`, `test:`, `ci:`,
`chore:`.

## Security

- **Never commit real secrets, credentials, account IDs, or PII.**
- Use sanitized sample events (account `111122223333`, documentation IP ranges).
- Do not add real Tines webhook URLs or Jira API tokens to the repository.

## Code style

- Python 3.11+, typed, stdlib-only unless a dependency is clearly justified.
- Keep code modular and tested (target >= 85% coverage).
- Terraform must pass `fmt` and `validate`.

## Pull request process

1. Fork and branch from `main`.
2. Run all checks above.
3. Open a PR against `main` and describe the change.
4. Ensure CI is green before requesting review.
