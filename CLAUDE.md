# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Commands
- **Install dependencies**: `uv sync`
- **Run tests**: `make test` or `uv run pytest`
- **Test with coverage**: `make test-coverage` (minimum 80% coverage required)
- **Format code**: `make ruff-format` 
- **Lint code**: `make ruff` or `make ruff-fix` (auto-fix issues)
- **Run all quality checks**: `make check` (combines linting and test coverage)

### Testing Commands
- **Run specific test suites**:
  - CLI tests: `make test-cli`
  - Agent tests: `make test-agents` 
  - Executor tests: `make test-executors`
  - Tool tests: `make test-tools`
  - Utils tests: `make test-utils`
- **Test categories**: `make test-unit` (excludes integration), `make test-integration`
- **Failed tests only**: `make test-failed`
- **Quick test run**: `make quick` (no coverage, ignore warnings)

### Development Setup
- Uses `uv` as package manager and Python runner
- Python 3.12+ required
- Environment variables in `.env` file (OPENAI_API_KEY required)

## Architecture Overview

Tron AI is a modular AI orchestration framework with a layered executor pattern:

### Core Components
1. **Executors**: Different task execution strategies
   - `CompletionExecutor`: Simple LLM completions
   - `ChainExecutor`: Multi-step reasoning chains  
   - `AgentExecutor`: Complex tasks using specialized agents

2. **Agent System**: Specialized agents for different domains
   - `CodeAgent`: Code analysis, formatting, test generation
   - `DockerAgent`: Container lifecycle management
   - `FileAgent`: File system operations
   - `MCPAgent`: Model Context Protocol integration
   - `SearchAgent`: Web search capabilities

3. **Memory Management**: ChromaDB-based vector storage for context retention
4. **Tool System**: Dynamic tool loading with AdalFlow ToolManager
5. **MCP Integration**: Model Context Protocol servers for extended functionality

### Project Structure
```
tron_intelligence/           # Main package
├── cli.py                  # CLI entry point with asyncclick
├── executors/              # Execution strategies
│   ├── base.py            # Base executor interface
│   ├── completion.py      # Simple completions
│   ├── chain.py           # Multi-step chains
│   └── agents/            # Agent-based execution
├── modules/               # Core modules
│   ├── mcp/              # MCP client/server management
│   ├── a2a/              # Agent-to-agent communication
│   └── tasks/            # Task management
├── utils/                # Utilities (LLMClient, file management)
└── prompts/              # Prompt templates and loading
```

## Code Standards

### Technology Stack
- **Framework**: AdalFlow for LLM orchestration
- **CLI**: asyncclick with Rich for interactive interfaces
- **LLM Integration**: OpenAI API client
- **Vector Database**: ChromaDB for memory/embeddings
- **HTTP**: aiohttp for async requests
- **JSON**: orjson for performance-critical operations
- **Testing**: pytest with async support, 80% coverage minimum
- **Formatting**: ruff for linting and formatting
- **Packaging**: uv with hatchling build backend

### Development Guidelines
- Follow Clean Code principles and SOLID design patterns
- Use domain-driven design with ubiquitous language
- Async/await patterns for I/O operations
- Type hints with Pydantic models for validation
- Single responsibility principle for classes/functions
- Comprehensive error handling with specific exception types

### Performance Considerations
- Use `orjson` over standard `json` for 10-50x performance
- Leverage `aiohttp` for concurrent HTTP requests
- Implement ChromaDB batch operations for vector storage
- Cache expensive computations appropriately
- Consider async patterns for I/O-bound operations

## CLI Interface

Main commands available via `tron-ai`:
- `ask`: Simple one-off questions
- `assistant`: Interactive chat with memory persistence  
- `chain`: Multi-step reasoning tasks
- `agent`: Complex tasks using specialized agents

## Configuration

- **MCP Servers**: Configured in `mcp_servers.json`
- **Environment**: Uses `.env` for API keys and logging levels
- **Logging**: Configurable via `TRON_LOG_LEVEL_*` environment variables
- **Memory**: ChromaDB collection management for conversation context

## Testing

- Comprehensive test suite with 80% minimum coverage requirement
- Async test support with pytest-asyncio
- Mocking capabilities with pytest-mock
- Rich output formatting with pytest-rich
- Integration tests marked separately from unit tests