.PHONY: install format lint typecheck test coverage terraform-fmt terraform-init terraform-validate validate demo clean

install:
	python -m pip install -e ".[dev]"

format:
	black .
	ruff check . --fix

lint:
	ruff check .

typecheck:
	mypy src tools local_emulator

test:
	python -m pytest

coverage:
	python -m pytest --cov=src/incident_response --cov=src/lambda_forwarder --cov=tools --cov=local_emulator --cov-report=term-missing --cov-fail-under=85

terraform-fmt:
	cd terraform && terraform fmt -recursive

terraform-init:
	cd terraform && terraform init -backend=false

terraform-validate:
	cd terraform && terraform validate

validate: lint
	black --check .
	mypy src tools local_emulator
	python -m pytest -q
	$(MAKE) terraform-fmt
	cd terraform && terraform fmt -check -recursive
	$(MAKE) terraform-init
	$(MAKE) terraform-validate

demo:
	python -m tools.simulate_finding --input examples/guardduty-high-severity.json --dry-run

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .mypy_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info src/*.egg-info .coverage htmlcov
	rm -rf terraform/.terraform terraform/builds
