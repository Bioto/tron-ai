# Makefile for Tron AI project

# Default shell
SHELL := /bin/bash

# Python interpreter
PYTHON := uv run python
PYTEST := uv run pytest
RUFF := uv run ruff

# Test directories and options
TEST_DIR := tests
MIN_COVERAGE := 80

# Default target
.DEFAULT_GOAL := test

# Help command
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make test          - Run all tests"
	@echo "  make test-verbose  - Run tests with verbose output"
	@echo "  make test-quiet    - Run tests without warnings"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo "  make test-watch    - Run tests in watch mode (requires pytest-watch)"
	@echo "  make test-failed   - Run only previously failed tests"
	@echo "  make test-cli      - Run only CLI tests"
	@echo "  make clean         - Clean up cache and temporary files"
	@echo "  make install       - Install dependencies"
	@echo "  make format        - Format code (if black is installed)"
	@echo "  make lint          - Run linters (if installed)"
	@echo "  make ruff          - Run ruff linter"
	@echo "  make ruff-fix      - Run ruff and auto-fix issues"
	@echo "  make ruff-format   - Format code with ruff"
	@echo "  make db-upgrade    - Run database migrations"
	@echo "  make db-init       - Initialize database"
	@echo "  make db-current    - Show current migration"
	@echo "  make db-reset      - Reset database (WARNING: deletes data)"
	@echo "  make compose-up    - Start tron-compose services"

# Run all tests
.PHONY: test
test:
	$(PYTEST)

# Run tests with verbose output
.PHONY: test-verbose
test-verbose:
	$(PYTEST) -v

# Run tests without deprecation warnings
.PHONY: test-quiet
test-quiet:
	$(PYTEST) -W ignore::DeprecationWarning

# Run tests with coverage
.PHONY: test-coverage
test-coverage:
	$(PYTEST) --cov=tron-ai --cov-report=term-missing --cov-report=html --cov-fail-under=$(MIN_COVERAGE)
	@echo "Coverage report generated in htmlcov/index.html"

# Run tests in watch mode (requires pytest-watch)
.PHONY: test-watch
test-watch:
	$(PYTHON) -m pytest_watch

# Run only previously failed tests
.PHONY: test-failed
test-failed:
	$(PYTEST) --lf

# Run specific test suites
.PHONY: test-cli
test-cli:
	$(PYTEST) tests/test_cli.py -v

.PHONY: test-agents
test-agents:
	$(PYTEST) tests/executors/agents/ -v

.PHONY: test-executors
test-executors:
	$(PYTEST) tests/executors/ -v

.PHONY: test-tools
test-tools:
	$(PYTEST) tests/tools/ -v

.PHONY: test-utils
test-utils:
	$(PYTEST) tests/utils/ -v

# Run tests with specific markers (if you add pytest markers in the future)
.PHONY: test-unit
test-unit:
	$(PYTEST) -m "not integration"

.PHONY: test-integration
test-integration:
	$(PYTEST) -m integration

# Ruff commands
.PHONY: ruff
ruff:
	$(RUFF) check tron-ai tests

.PHONY: ruff-fix
ruff-fix:
	$(RUFF) check --fix tron-ai tests

.PHONY: ruff-format
ruff-format:
	$(RUFF) format tron-ai tests

.PHONY: ruff-all
ruff-all: ruff-fix ruff-format
	@echo "Ruff linting and formatting complete!"

# Clean up
.PHONY: clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

# Install dependencies
.PHONY: install
install:
	uv sync

# Format code (optional - if black is in your dependencies)
.PHONY: format
format:
	$(PYTHON) -m black tron-ai tests || echo "Black not installed"
	$(PYTHON) -m isort tron-ai tests || echo "isort not installed"

# Lint code (optional - if linters are in your dependencies)
.PHONY: lint
lint:
	$(PYTHON) -m flake8 tron-ai tests || echo "flake8 not installed"
	$(PYTHON) -m mypy tron-ai || echo "mypy not installed"

# Run all quality checks
.PHONY: check
check: ruff test-coverage

# Development setup
.PHONY: dev
dev: install
	@echo "Development environment ready!"

# Database migration commands
.PHONY: db-upgrade
db-upgrade:
	$(PYTHON) -m alembic upgrade head
	@echo "Database upgraded to latest migration"

.PHONY: db-downgrade
db-downgrade:
	$(PYTHON) -m alembic downgrade -1
	@echo "Database downgraded by one migration"

.PHONY: db-current
db-current:
	$(PYTHON) -m alembic current
	@echo "Current database revision shown above"

.PHONY: db-history
db-history:
	$(PYTHON) -m alembic history
	@echo "Migration history shown above"

.PHONY: db-create-migration
db-create-migration:
	@read -p "Enter migration message: " message; \
	$(PYTHON) -m alembic revision --autogenerate -m "$$message"
	@echo "New migration created"

.PHONY: db-create-a2a-migration
db-create-a2a-migration:
	$(PYTHON) -m alembic revision --autogenerate -m "add_a2a_session_continuity_tables"
	@echo "A2A session continuity migration created"

.PHONY: db-reset
db-reset:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		rm -f data/conversations.db* || true; \
		$(PYTHON) -m alembic upgrade head; \
		echo "Database reset complete"; \
	else \
		echo "Database reset cancelled"; \
	fi

.PHONY: db-init
db-init:
	$(PYTHON) -c "from tron_ai.database.manager import DatabaseManager; from tron_ai.database.config import DatabaseConfig; import asyncio; asyncio.run(DatabaseManager(DatabaseConfig()).initialize())"
	@echo "Database initialized"

# CI/CD oriented targets
.PHONY: ci
ci: clean ruff test-coverage

# Quick test run (no coverage, ignore warnings)
.PHONY: quick
quick:
	$(PYTEST) -x -W ignore::DeprecationWarning 

# Start tron-compose services
.PHONY: compose-up
compose-up:
	docker compose -f .docker/tron-compose.yml up -d 

# Stop tron-compose services
compose-down-tron:
	docker compose -f .docker/tron-compose.yml down

# Start mcp-compose services
compose-up-mcp:
	docker compose -f .docker/mcp/docker-compose.yml up -d 

# Stop mcp-compose services
compose-down-mcp:
	docker compose -f .docker/mcp/docker-compose.yml down