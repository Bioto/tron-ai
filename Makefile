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
	$(PYTEST) --cov=tron_intelligence --cov-report=term-missing --cov-report=html --cov-fail-under=$(MIN_COVERAGE)
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
	$(RUFF) check tron_intelligence tests

.PHONY: ruff-fix
ruff-fix:
	$(RUFF) check --fix tron_intelligence tests

.PHONY: ruff-format
ruff-format:
	$(RUFF) format tron_intelligence tests

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
	$(PYTHON) -m black tron_intelligence tests || echo "Black not installed"
	$(PYTHON) -m isort tron_intelligence tests || echo "isort not installed"

# Lint code (optional - if linters are in your dependencies)
.PHONY: lint
lint:
	$(PYTHON) -m flake8 tron_intelligence tests || echo "flake8 not installed"
	$(PYTHON) -m mypy tron_intelligence || echo "mypy not installed"

# Run all quality checks
.PHONY: check
check: ruff test-coverage

# Development setup
.PHONY: dev
dev: install
	@echo "Development environment ready!"

# CI/CD oriented targets
.PHONY: ci
ci: clean ruff test-coverage

# Quick test run (no coverage, ignore warnings)
.PHONY: quick
quick:
	$(PYTEST) -x -W ignore::DeprecationWarning 