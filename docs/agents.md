# Tron AI Agents Documentation

## Table of Contents

1. [Agent System Overview](#agent-system-overview)
2. [Agent Categories](#agent-categories)
3. [Core Agents](#core-agents)
4. [Agent Architecture](#agent-architecture)
5. [Tool Integration](#tool-integration)
6. [Agent Orchestration](#agent-orchestration)
7. [Creating Custom Agents](#creating-custom-agents)
8. [Best Practices](#best-practices)

## Agent System Overview

Tron AI's agent system is organized into categories for different domains: business, devops, productivity, and the core tron agent. Each agent is specialized for specific tasks and integrates with various tools and services.

### Agent Ecosystem

```mermaid
graph TB
    subgraph "Agent Categories"
        BUS[Business]
        DEV[DevOps]
        PROD[Productivity]
        TRON[Tron]
    end
    
    subgraph "Business Agents"
        BUS --> MS[Marketing Strategy]
        BUS --> SA[Sales]
        BUS --> CS[Customer Success]
        BUS --> PM[Product Management]
        BUS --> FP[Financial Planning]
        BUS --> AE[AI Ethics]
        BUS --> CC[Content Creation]
        BUS --> CR[Community Relations]
    end
    
    subgraph "DevOps Agents"
        DEV --> CSA[Code Scanner]
        DEV --> CEA[Code Editor]
        DEV --> RSA[Repo Scanner]
        DEV --> SSHA[SSH]
    end
    
    subgraph "Productivity Agents"
        PROD --> GA[Google]
        PROD --> NA[Notion]
        PROD --> TA[Todoist]
    end
    
    subgraph "Core"
        TRON --> TA[Tron Agent]
    end
```

## Agent Categories

### Business Agents

Specialized for business operations and strategy:

- **Marketing Strategy Agent**: Develops marketing plans and content.
- **Sales Agent**: Handles sales processes and customer interactions.
- **Customer Success Agent**: Manages customer relationships and support.
- **Product Management Agent**: Oversees product development and roadmaps.
- **Financial Planning Agent**: Assists with budgeting and financial analysis.
- **AI Ethics Agent**: Ensures ethical AI practices.
- **Content Creation Agent**: Generates marketing and educational content.
- **Community Relations Agent**: Manages community engagement.

### DevOps Agents

Focused on development and operations:

- **Code Scanner Agent**: Analyzes code repositories.
- **Code Editor Agent**: Edits and modifies code.
- **Repo Scanner Agent**: Scans and maps repositories.
- **SSH Agent**: Manages remote server access.

### Productivity Agents

For personal and team productivity:

- **Google Agent**: Manages email and calendar.
- **Notion Agent**: Handles Notion workspace operations.
- **Todoist Agent**: Manages tasks and projects in Todoist.

### Tron Agent

The core orchestrator that can delegate to other agents via swarm execution.

## Core Agents

### Tron Agent

Main orchestrator using swarm for task delegation.

#### Tools
- execute_on_swarm
- query_memory

### Google Agent

Manages email and calendar.

#### Tools
- Various Google API tools (search_messages, get_message, etc.)

### Todoist Agent

Task management.

#### Tools
- Todoist API tools (get_tasks, create_task, etc.)

### Notion Agent

Knowledge management.

#### Tools
- Notion API tools (create_page, update_page, etc.)

<!-- Add similar sections for other agents with their tools from search results -->

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

Tron Agent uses swarm executor for orchestration.

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
from tron_ai.executors.agents.models.agent import Agent
from tron_ai.prompts.models import Prompt
from tron_ai.tools import ToolManager

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