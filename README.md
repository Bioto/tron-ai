# Tron AI

An advanced AI-powered agent orchestration framework built on top of AdalFlow and OpenAI. Tron AI provides a flexible architecture for coordinating multiple specialized agents to complete complex tasks through an intuitive CLI interface.

## 📚 Documentation

For comprehensive documentation, please visit:

- **[📖 Full Documentation](docs/index.md)** - Complete documentation hub
- **[🏗️ Architecture Overview](docs/architecture.md)** - System design and components
- **[💻 CLI Guide](docs/cli-guide.md)** - Detailed command usage
- **[🤖 Agents Documentation](docs/agents.md)** - Agent system guide
- **[🔧 API Reference](docs/api.md)** - Complete API documentation
- **[👩‍💻 Development Guide](docs/development.md)** - Setup and contribution guide

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🤖 **Multi-Agent Orchestration**: Coordinate multiple specialized agents (Code, Docker, File, MCP, Search) to solve complex tasks
- 🔧 **Flexible Executor Pattern**: Clean abstraction for different execution strategies (Completion, Chain, Agent-based)
- 🧠 **Memory Management**: Built-in vector database for context retention across conversations
- 🛠️ **Tool Management**: Dynamic tool loading and execution with proper error handling
- 📊 **Rich CLI Interface**: Interactive chat sessions with memory persistence
- 🔒 **Type Safety**: Extensive use of Pydantic models for data validation
- 📝 **Comprehensive Logging**: Configurable logging with environment variable overrides

## Quick Start

### Prerequisites

- Python 3.12 or higher
- OpenAI API key
- Perplexity API key (optional, for search functionality)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tron-ai.git
cd tron-ai

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Environment Setup

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=your-openai-api-key

# Optional
PERPLEXITY_API_KEY=your-perplexity-api-key

# Logging (optional)
TRON_LOG_LEVEL_ROOT=WARNING
TRON_LOG_LEVEL_tron-ai=INFO
```

## Basic Usage

```bash
# Simple question
tron-ai ask "What is the capital of France?"

# Interactive assistant
tron-ai assistant

# Complex task with agents
tron-ai agent "Analyze the security vulnerabilities in my Python code"
```

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `ask` | Simple one-off questions | `tron-ai ask "What is Python?"` |
| `assistant` | Interactive chat with memory | `tron-ai assistant` |
| `chain` | Multi-step reasoning | `tron-ai chain` |
| `agent` | Complex tasks with agents | `tron-ai agent "Create a web scraper"` |

For detailed command usage, see the [CLI Guide](docs/cli-guide.md).

## Built-in Agents

- 🔍 **Code Agent**: Code analysis, formatting, test generation
- 🐳 **Docker Agent**: Container lifecycle management
- 📁 **File Agent**: File system operations
- 🔌 **MCP Agent**: Model Context Protocol integration
- 🌐 **Search Agent**: Web search capabilities

Learn more in the [Agents Documentation](docs/agents.md).

## Development

### Quick Setup

```bash
# Install development dependencies
pip install -e ".[dev,test]"

# Run tests
make test

# Format code
make ruff-format

# Run linter
make ruff
```

### Project Structure

```
tron-ai/
├── tron-ai/            # Main package
├── tests/              # Test suite
├── docs/               # Documentation
└── pyproject.toml      # Project configuration
```

For detailed development instructions, see the [Development Guide](docs/development.md).

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific tests
pytest tests/executors/test_completion.py -v

# See all make commands
make help
```

## Contributing

We welcome contributions! Please see our [Development Guide](docs/development.md) for:

- Development setup
- Code standards
- Testing requirements
- Pull request process

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Run tests and linting (`make test && make ruff`)
5. Commit changes (`git commit -m 'feat: add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built on [AdalFlow](https://github.com/SylphAI-Inc/AdalFlow) framework
- Powered by OpenAI's GPT models
- Search capabilities via Perplexity API

---

For more information, visit our [complete documentation](docs/index.md).
