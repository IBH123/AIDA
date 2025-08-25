.PHONY: install install-dev format lint typecheck test clean run-api

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

format:
	black aida tests
	ruff --fix aida tests

lint:
	ruff aida tests

typecheck:
	mypy aida

test:
	pytest tests/

clean:
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

run-api:
	uvicorn aida.api:app --reload --host 0.0.0.0 --port 8000

dev-setup: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'aida --help' to see CLI options"