.PHONY: help install install-dev dev lint format type-check test test-integration test-all docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  make install           - Install production dependencies"
	@echo "  make install-dev       - Install development dependencies"
	@echo "  make dev               - Run development server with auto-reload"
	@echo "  make lint              - Run ruff linter"
	@echo "  make format            - Format code with ruff and black"
	@echo "  make type-check        - Run mypy type checker"
	@echo "  make test              - Run unit tests"
	@echo "  make test-integration  - Run integration test (~2 minutes)"
	@echo "  make test-all          - Run all tests"
	@echo "  make docker-up         - Build and start Docker services (idempotent)"
	@echo "  make docker-down       - Stop Docker services"
	@echo "  make clean             - Remove build artifacts"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

dev:
	uvicorn main:app --reload --reload-exclude '.history/*'

lint:
	ruff check .

format:
	ruff check --fix .
	ruff format .
	black .

type-check:
	mypy . --ignore-missing-imports

test:
	pytest test_webhook_unit.py -v

test-integration:
	python test_integration.py

test-all: test test-integration

docker-up:
	docker compose up --build

docker-up-d:
	docker compose up -d --build

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
