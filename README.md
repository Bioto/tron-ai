# Tron AI

AI agent framework with specialized agents for business, devops, and productivity tasks, featuring multi-agent orchestration via swarm executor.

## 📚 Documentation

- [Full Documentation](docs/index.md)
- [Architecture](docs/architecture.md)
- [CLI Guide](docs/cli-guide.md)
- [Agents](docs/agents.md)
- [API Reference](docs/api.md)
- [Development Guide](docs/development.md)

## Table of Contents

- [Tron AI](#tron-ai)
  - [📚 Documentation](#-documentation)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Quick Start](#quick-start)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Environment Setup](#environment-setup)
  - [Basic Usage](#basic-usage)
  - [CLI Commands](#cli-commands)
  - [Agent Categories](#agent-categories)
  - [Development](#development)
    - [Quick Setup](#quick-setup)
    - [Project Structure](#project-structure)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)

## Features

- 🤖 **Multi-Agent Orchestration**: Swarm executor for task delegation
- 🔧 **Specialized Agents**: Business, DevOps, Productivity domains
- 🧠 **Database Integration**: Conversation history persistence
- 🛠️ **MCP Support**: Dynamic tool discovery
- 📊 **CLI Interface**: Interactive chats and repo scanning
- 🔒 **Task Management**: Dependency-aware execution

## Quick Start

### Prerequisites

- Python 3.12+
- OpenAI API key
- Additional keys for specific agents (Groq, Todoist, Notion, Google)

### Installation

```bash
git clone https://github.com/yourusername/tron-ai.git
cd tron-ai
python -m venv .venv
source .venv/bin/activate
uv sync  # or pip install -e .
```

### Environment Setup

Copy the example environment file and configure your API keys:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual API keys
```

Required environment variables:
- `OPENAI_API_KEY` - OpenAI API key (required for most agents)
- `GROQ_API_KEY` - Groq API key (required for chat command)

Optional environment variables:
- `TODOIST_API_TOKEN` - For Todoist agent
- `NOTION_API_TOKEN` - For Notion agent  
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google credentials
- `PERPLEXITY_API_KEY` - For product management agent

The application automatically loads these from the `.env` file.

## Basic Usage

```bash
# Simple query
tron-ai ask "Explain AI" --agent generic

# Interactive chat
tron-ai chat "Plan my day" --agent tron

# Scan repository
tron-ai scan_repo .
```

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `ask` | Single query | `tron-ai ask "Query" --agent tron` |
| `chat` | Interactive session | `tron-ai chat "Initial query" --agent google` |
| `scan_repo` | Scan repository | `tron-ai scan_repo /path --output json` |
| `scan_repo_watch` | Watch for changes | `tron-ai scan_repo_watch /path` |
| `db` | Database management | `tron-ai db stats` |

See [CLI Guide](docs/cli-guide.md) for details.

## Agent Categories

- **Business**: Marketing, Sales, etc.
- **DevOps**: Code Scanner, SSH, etc.
- **Productivity**: Google, Todoist, Notion
- **Core**: Tron orchestrator

See [Agents Documentation](docs/agents.md).

## Development

### Quick Setup

```bash
pip install -e ".[dev,test]"
make test
make ruff-format
make ruff
```

### Project Structure

```
tron-ai/
  - alembic.ini
  - docs/
  - LICENSE.md
  - Makefile
  - mcp_servers.json
  - pyproject.toml
  - pytest.ini
  - README.md
  - tron_ai/
    - agents/
    - cli.py
    - config.py
    - constants.py
    - database/
    - exceptions.py
    - executors/
    - models/
    - modules/
    - processors/
    - test_gmail.py
    - utils/
    - vendor/
  - uv.lock
```

See [Development Guide](docs/development.md).

## Contributing

See [Development Guide](docs/development.md).

## License

MIT License - see LICENSE.

## Acknowledgments

- Powered by OpenAI/Groq
- Integrates Todoist/Notion/Google

---

For more, see [documentation](docs/index.md).
