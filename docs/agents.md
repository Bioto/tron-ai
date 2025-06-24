# Tron AI Agents Documentation

## Table of Contents

1. [Agent System Overview](#agent-system-overview)
2. [Built-in Agents](#built-in-agents)
3. [Agent Architecture](#agent-architecture)
4. [Tool Integration](#tool-integration)
5. [Agent Orchestration](#agent-orchestration)
6. [Creating Custom Agents](#creating-custom-agents)
7. [Best Practices](#best-practices)

## Agent System Overview

The agent system in Tron AI provides specialized workers that handle specific types of tasks. Each agent has its own set of tools and expertise, allowing for efficient task decomposition and parallel execution.

### Agent Ecosystem

```mermaid
graph TB
    subgraph "Agent Types"
        CA[Code Agent]
        DA[Docker Agent]
        FA[File Agent]
        MA[MCP Agent]
        SA[Search Agent]
    end
    
    subgraph "Core Capabilities"
        CA --> CC[Code Analysis]
        CA --> CG[Code Generation]
        CA --> CT[Testing]
        
        DA --> DC[Container Mgmt]
        DA --> DI[Image Handling]
        DA --> DL[Log Analysis]
        
        FA --> FC[File CRUD]
        FA --> FD[Directory Ops]
        FA --> FS[Search]
        
        MA --> MC[MCP Servers]
        MA --> MT[Tool Discovery]
        MA --> ME[Dynamic Execution]
        
        SA --> SI[Internet Search]
        SA --> SR[Result Processing]
        SA --> SC[Content Extraction]
    end
```

## Built-in Agents

### 1. Code Agent

The Code Agent specializes in code analysis, generation, and manipulation.

#### Capabilities

```mermaid
mindmap
  root((Code Agent))
    Analysis
      Structure Analysis
      Dependency Mapping
      Complexity Metrics
      Security Scanning
    Generation
      Code Templates
      Test Generation
      Documentation
      Refactoring
    Quality
      Formatting
      Linting
      Best Practices
      Performance Tips
```

#### Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `analyze_code_structure` | Analyzes code organization | `code: str, language: str` |
| `check_code_quality` | Checks for issues and metrics | `code: str, language: str` |
| `format_code` | Formats code properly | `code: str, language: str` |
| `generate_tests` | Creates test cases | `code: str, language: str` |
| `analyze_dependencies` | Maps dependencies | `code: str, language: str` |
| `suggest_improvements` | Provides suggestions | `code: str, language: str` |

#### Example Usage

```python
# Via CLI
tron-ai agent "Analyze this Python module for security issues"

# Direct usage
from tron_intelligence.executors.agents.builtin import CodeAgent

agent = CodeAgent()
result = agent.analyze_code_structure(
    code=open("module.py").read(),
    language="python"
)
```

### 2. Docker Agent

Manages Docker containers and images with comprehensive container lifecycle management.

#### Architecture

```mermaid
stateDiagram-v2
    [*] --> Created: create_container
    Created --> Running: start_container
    Running --> Stopped: stop_container
    Stopped --> Running: start_container
    Stopped --> Removed: remove_container
    Running --> Removed: remove_container
    Removed --> [*]
    
    Running --> Inspecting: inspect_container
    Running --> Logs: get_logs
    Inspecting --> Running
    Logs --> Running
```

#### Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_containers` | Lists all containers | `all: bool = False` |
| `create_container` | Creates new container | `image: str, name: str, **kwargs` |
| `start_container` | Starts container | `container_id: str` |
| `stop_container` | Stops container | `container_id: str` |
| `remove_container` | Removes container | `container_id: str` |
| `get_logs` | Gets container logs | `container_id: str, tail: int` |
| `inspect_container` | Gets container details | `container_id: str` |

#### Container Management Flow

```mermaid
sequenceDiagram
    participant User
    participant DockerAgent
    participant DockerAPI
    participant Container
    
    User->>DockerAgent: Create web server
    DockerAgent->>DockerAPI: create_container(nginx)
    DockerAPI-->>DockerAgent: container_id
    
    DockerAgent->>DockerAPI: start_container(id)
    DockerAPI->>Container: Start
    Container-->>DockerAPI: Running
    
    DockerAgent->>DockerAPI: get_logs(id)
    DockerAPI-->>DockerAgent: Log output
    
    DockerAgent-->>User: Container running
```

### 3. File Agent

Handles all file system operations with safety checks and validation.

#### File Operations

```mermaid
graph LR
    subgraph "File Operations"
        CREATE[Create File]
        READ[Read File]
        UPDATE[Update File]
        DELETE[Delete File]
        LIST[List Directory]
    end
    
    subgraph "Safety Features"
        VALIDATE[Path Validation]
        BACKUP[Auto Backup]
        ROLLBACK[Rollback Support]
        PERMISSIONS[Permission Check]
    end
    
    CREATE --> VALIDATE
    UPDATE --> BACKUP
    DELETE --> BACKUP
    ALL[All Operations] --> PERMISSIONS
```

#### Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_file` | Creates new file | `path: str, content: str` |
| `read_file` | Reads file content | `path: str` |
| `update_file` | Updates file content | `path: str, content: str` |
| `delete_file` | Deletes file | `path: str` |
| `list_directory` | Lists directory contents | `path: str, recursive: bool` |

### 4. MCP Agent

Integrates with Model Context Protocol servers for dynamic tool loading. For multi-server management, use the MCP Agent Manager (see below).

#### MCP Integration Flow

```mermaid
sequenceDiagram
    participant MCPAgent
    participant MCPClient
    participant MCPServer
    participant Tools
    
    MCPAgent->>MCPClient: Initialize
    MCPClient->>MCPServer: Connect
    MCPServer-->>MCPClient: Server Info
    
    MCPClient->>MCPServer: List Tools
    MCPServer-->>MCPClient: Available Tools
    
    MCPClient->>Tools: Register Tools
    Tools-->>MCPAgent: Tools Ready
    
    Note over MCPAgent: Dynamic tool execution
    
    MCPAgent->>Tools: Execute Tool
    Tools->>MCPServer: Tool Request
    MCPServer-->>Tools: Tool Result
    Tools-->>MCPAgent: Formatted Result
```

#### Dynamic Tool Discovery

```mermaid
graph TD
    subgraph "MCP Tool Discovery"
        INIT[Initialize MCP Agent]
        SCAN[Scan MCP Servers]
        DISC[Discover Tools]
        REG[Register Tools]
        EXEC[Execute Tools]
    end
    
    INIT --> SCAN
    SCAN --> DISC
    DISC --> REG
    REG --> EXEC
    
    subgraph "Tool Types"
        FS[Filesystem Tools]
        DB[Database Tools]
        API[API Tools]
        CUSTOM[Custom Tools]
    end
    
    DISC --> FS
    DISC --> DB
    DISC --> API
    DISC --> CUSTOM
```

---

### 4a. MCP Agent Manager

The MCP Agent Manager (`MCPAgentManager`) is a singleton responsible for managing multiple MCP agents, each connected to a different MCP server. It provides a unified interface for initializing, adding, removing, and reloading MCP agents at runtime.

#### Key Features
- Singleton pattern for global access
- Manages a pool of named MCP agents
- Supports dynamic (re)loading from config files
- Async initialization and cleanup
- Default agent selection

#### Example Usage

```python
from tron_intelligence.executors.agents.builtin.mcp_agent_manager import MCPAgentManager

manager = MCPAgentManager()
await manager.initialize("mcp_servers.json")  # Load all agents from config

# Get default agent
agent = manager.get_default_agent()

# Get agent by name
agent = manager.get_agent("my-mcp-server")

# Add a new agent at runtime
await manager.add_agent("new-server", server_config)

# Remove an agent
await manager.remove_agent("old-server")

# Reload all agents from config
await manager.reload_agents("mcp_servers.json")

# Cleanup all agents
await manager.cleanup()
```

#### When to Use
- When you need to orchestrate multiple MCP servers
- For dynamic agent pool management in production
- To support hot-reloading of agent configs

---

### 5. Search Agent

Provides web search capabilities with result processing and content extraction.

#### Search Flow

```mermaid
flowchart LR
    subgraph "Search Pipeline"
        QUERY[Search Query]
        ENGINE[Search Engine]
        RESULTS[Raw Results]
        FILTER[Filter & Rank]
        EXTRACT[Extract Content]
        FORMAT[Format Output]
    end
    
    QUERY --> ENGINE
    ENGINE --> RESULTS
    RESULTS --> FILTER
    FILTER --> EXTRACT
    EXTRACT --> FORMAT
    
    subgraph "Processing"
        FILTER --> RELEVANCE[Relevance Check]
        FILTER --> QUALITY[Quality Score]
        EXTRACT --> SUMMARY[Summarize]
        EXTRACT --> FACTS[Extract Facts]
    end
```

## Agent Architecture

### Base Agent Structure

```mermaid
classDiagram
    class Agent {
        +name: str
        +description: str
        +prompt: Prompt
        +tools: ToolManager
        +supports_multiple_operations: bool
        +execute(query: str) Result
        +validate_input(input: Any) bool
        +format_output(output: Any) str
    }
    
    class ToolManager {
        +tools: List[Tool]
        +register_tool(tool: Tool)
        +get_tool(name: str) Tool
        +execute_tool(name: str, params: dict)
    }
    
    class Prompt {
        +template: str
        +variables: List[str]
        +build(**kwargs) str
    }
    
    Agent --> ToolManager
    Agent --> Prompt
```

### Agent Communication

```mermaid
sequenceDiagram
    participant Orchestrator
    participant Agent1
    participant Agent2
    participant SharedContext
    
    Orchestrator->>Agent1: Task Assignment
    Agent1->>SharedContext: Store Results
    
    Orchestrator->>Agent2: Related Task
    Agent2->>SharedContext: Query Context
    SharedContext-->>Agent2: Previous Results
    
    Agent2->>Agent2: Process with Context
    Agent2->>SharedContext: Store Results
    
    Orchestrator->>SharedContext: Collect All Results
    SharedContext-->>Orchestrator: Combined Output
```

## Tool Integration

### Tool Registration Process

```mermaid
flowchart TD
    subgraph "Tool Registration"
        DEFINE[Define Tool Function]
        DECORATE[Add Decorators]
        PARSE[Parse Metadata]
        VALIDATE[Validate Schema]
        REGISTER[Register in Manager]
        READY[Tool Ready]
    end
    
    DEFINE --> DECORATE
    DECORATE --> PARSE
    PARSE --> VALIDATE
    VALIDATE --> REGISTER
    REGISTER --> READY
    
    subgraph "Metadata"
        NAME[Tool Name]
        DESC[Description]
        PARAMS[Parameters]
        RETURNS[Return Type]
    end
    
    PARSE --> NAME
    PARSE --> DESC
    PARSE --> PARAMS
    PARSE --> RETURNS
```

### Tool Execution Pipeline

```mermaid
graph LR
    subgraph "Execution Pipeline"
        REQUEST[Tool Request]
        VALIDATE[Validate Params]
        EXECUTE[Execute Tool]
        HANDLE[Handle Errors]
        FORMAT[Format Result]
        RETURN[Return Output]
    end
    
    REQUEST --> VALIDATE
    VALIDATE -->|Valid| EXECUTE
    VALIDATE -->|Invalid| HANDLE
    EXECUTE -->|Success| FORMAT
    EXECUTE -->|Error| HANDLE
    HANDLE --> RETURN
    FORMAT --> RETURN
```

## Agent Orchestration

### Parallel Execution Strategy

```mermaid
graph TB
    subgraph "Parallel Orchestration"
        TASK[Complex Task]
        ANALYZE[Task Analysis]
        DECOMPOSE[Decompose]
        
        subgraph "Parallel Execution"
            AGENT1[Agent 1]
            AGENT2[Agent 2]
            AGENT3[Agent 3]
        end
        
        COMBINE[Combine Results]
        REPORT[Final Report]
    end
    
    TASK --> ANALYZE
    ANALYZE --> DECOMPOSE
    DECOMPOSE --> AGENT1
    DECOMPOSE --> AGENT2
    DECOMPOSE --> AGENT3
    
    AGENT1 --> COMBINE
    AGENT2 --> COMBINE
    AGENT3 --> COMBINE
    
    COMBINE --> REPORT
```

### Sequential Execution Strategy

```mermaid
flowchart TD
    subgraph "Sequential Orchestration"
        TASK[Complex Task]
        PLAN[Execution Plan]
        
        STEP1[Agent 1: Prepare]
        STEP2[Agent 2: Process]
        STEP3[Agent 3: Finalize]
        
        RESULT[Combined Result]
    end
    
    TASK --> PLAN
    PLAN --> STEP1
    STEP1 --> STEP2
    STEP2 --> STEP3
    STEP3 --> RESULT
    
    STEP1 -.-> |Context| STEP2
    STEP2 -.-> |Context| STEP3
```

## Creating Custom Agents

### Custom Agent Template

```python
from tron_intelligence.executors.agents.models.agent import Agent
from tron_intelligence.prompts.models import Prompt
from tron_intelligence.tools import ToolManager

class CustomAgent(Agent):
    """Custom agent for specific tasks."""
    
    def __init__(self):
        super().__init__(
            name="Custom Agent",
            description="Handles custom operations",
            prompt=Prompt(
                prompt="""You are a specialized agent that...
                
                Instructions:
                1. Analyze the request
                2. Use appropriate tools
                3. Provide detailed results
                
                User Query: {user_query}
                """,
                required_kwargs=["user_query"]
            ),
            supports_multiple_operations=True
        )
        
    @property
    def tools(self) -> ToolManager:
        """Define agent tools."""
        return ToolManager(tools=[
            self.custom_tool_1,
            self.custom_tool_2,
        ])
    
    def custom_tool_1(self, param1: str, param2: int) -> str:
        """First custom tool.
        
        Args:
            param1: Description
            param2: Description
            
        Returns:
            Tool result
        """
        # Implementation
        return f"Processed {param1} with {param2}"
```

### Agent Development Workflow

```mermaid
graph TD
    subgraph "Development Process"
        IDENTIFY[Identify Need]
        DESIGN[Design Agent]
        IMPLEMENT[Implement Logic]
        TOOLS[Create Tools]
        TEST[Test Agent]
        INTEGRATE[Integrate]
        DEPLOY[Deploy]
    end
    
    IDENTIFY --> DESIGN
    DESIGN --> IMPLEMENT
    IMPLEMENT --> TOOLS
    TOOLS --> TEST
    TEST --> INTEGRATE
    INTEGRATE --> DEPLOY
    
    TEST -->|Issues| IMPLEMENT
```

## Best Practices

### 1. Agent Selection

```mermaid
flowchart TD
    TASK[User Task]
    ANALYZE{Analyze Task Type}
    
    ANALYZE -->|Code Related| CODE[Use Code Agent]
    ANALYZE -->|File Operations| FILE[Use File Agent]
    ANALYZE -->|Container Mgmt| DOCKER[Use Docker Agent]
    ANALYZE -->|Web Search| SEARCH[Use Search Agent]
    ANALYZE -->|Multiple Types| MULTI[Use Multiple Agents]
    
    CODE --> EXEC[Execute]
    FILE --> EXEC
    DOCKER --> EXEC
    SEARCH --> EXEC
    MULTI --> ORCHESTRATE[Orchestrate Agents]
    ORCHESTRATE --> EXEC
```

### 2. Error Handling

```python
# Agent error handling pattern
try:
    result = agent.execute(task)
except AgentError as e:
    # Handle agent-specific errors
    logger.error(f"Agent {e.agent_name} failed: {e.message}")
    # Fallback strategy
    result = fallback_agent.execute(task)
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
    raise
```

### 3. Performance Optimization

- **Use appropriate agents**: Don't use complex agents for simple tasks
- **Leverage parallelization**: Execute independent agents concurrently
- **Cache results**: Store and reuse results for similar queries
- **Limit scope**: Provide specific instructions to agents

### 4. Testing Agents

```mermaid
graph LR
    subgraph "Testing Strategy"
        UNIT[Unit Tests]
        INTEGRATION[Integration Tests]
        E2E[End-to-End Tests]
        PERF[Performance Tests]
    end
    
    UNIT --> |Test Tools| TOOLS[Tool Tests]
    UNIT --> |Test Logic| LOGIC[Logic Tests]
    INTEGRATION --> |Test with LLM| LLM[LLM Integration]
    E2E --> |Test Workflows| WORKFLOW[Workflow Tests]
    PERF --> |Test Speed| SPEED[Speed Tests]
    PERF --> |Test Scale| SCALE[Scale Tests]
```

This documentation provides a comprehensive overview of the Tron AI agent system, including detailed information about each built-in agent, architecture patterns, and best practices for development and usage. 