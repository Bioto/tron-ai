# Tests for Tron AI

This directory contains tests for the Tron AI project.

## Test Structure

The test structure mirrors the package structure:

```
tests/
├── conftest.py          # Common test fixtures
├── executors/           # Tests for executor components
│   ├── test_base.py     # Tests for BaseExecutor
│   └── test_integration.py  # Integration tests for executors
└── ...
```

## Running Tests

You can run the tests using pytest:

```bash
pytest
```

To run a specific test file:

```bash
pytest tests/executors/test_base.py
```

For more verbose output:

```bash
pytest -v
```

With coverage information:

```bash
pytest --cov=tron-ai
```

## Writing Tests

When writing tests:

1. Follow the same structure as the main package
2. Use fixtures from `conftest.py` for common setup
3. Use mocks for external dependencies
4. Write docstrings for test classes and methods

## Test Types

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test how components work together
- **Functional Tests**: Test end-to-end functionality 