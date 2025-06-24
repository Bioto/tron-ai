# Tron AI Architecture Overview

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [Execution Flow](#execution-flow)
4. [Agent System](#agent-system)
5. [Memory Management](#memory-management)
6. [Tool System](#tool-system)
7. [Error Handling](#error-handling)

## System Overview

Tron AI is a modular AI orchestration framework that coordinates multiple specialized agents to solve complex tasks. The system is built on a layered architecture with clear separation of concerns.

```mermaid
graph TB
    subgraph "User Interface Layer"
        CLI[CLI Interface]
        API[API Endpoints]
    end
    
    subgraph "Orchestration Layer"
        EM[Executor Manager]
        CE[Completion Executor]
        CHE[Chain Executor]
        AE[Agent Executor]
    end
    
    subgraph "Agent Layer"
        CA[Code Agent]
        DA[Docker Agent]
        FA[File Agent]
        MA[MCP Agent]
        SA[Search Agent]
    end
    
    subgraph "Core Services"
        LLM[LLM Client]
        TM[Tool Manager]
        MM[Memory Manager]
        CM[Connection Manager]
    end
    
    subgraph "Infrastructure"
        OAI[OpenAI API]
        CDB[ChromaDB]
        FS[File System]
        MCP[MCP Servers]
        PP[Perplexity API]
    end
    
    CLI --> EM
    API --> EM
    EM --> CE
    EM --> CHE
    EM --> AE
    
    CE --> LLM
    CHE --> LLM
    AE --> CA
    AE --> DA
    AE --> FA
    AE --> MA
    AE --> SA
    
    CA --> TM
    DA --> TM
    FA --> TM
    MA --> TM
    SA --> TM
    
    LLM --> OAI
    MM --> CDB
    CM --> CDB
    FA --> FS
    MA --> MCP
    SA --> PP
```

## Core Components

### 1. Executors

The executor pattern provides different strategies for task execution:

```mermaid
classDiagram
    class BaseExecutor {
        <<abstract>>
        +config: ExecutorConfig
        +execute()* BaseModel
    }
    
    class CompletionExecutor {
        +execute() BaseModel
        -_simple_completion()
    }
    
    class ChainExecutor {
        +execute() List[BaseModel]
        -_execute_step()
    }
    
    class AgentExecutor {
        +agents: List[Agent]
        +execute() AgentExecutorResponse
        -_orchestrate_agents()
        -_execute_parallel()
        -_execute_sequential()
    }
    
    BaseExecutor <|-- CompletionExecutor
    BaseExecutor <|-- ChainExecutor
    BaseExecutor <|-- AgentExecutor
```

### 2. LLM Client Architecture

The LLM Client provides a unified interface for language model interactions:

```mermaid
classDiagram
    class LLMClient {
        +client: OpenAIClient
        +config: LLMClientConfig
        +call() BaseModel
        +fcall() BaseModel
        -_build_generator()
        -_handle_retries()
    }
    
    class LLMClientConfig {
        +model_name: str
        +json_output: bool
        +logging: bool
    }
    
    class ToolManager {
        +tools: List[Tool]
        +register_tool()
        +get_tool()
        +execute_tool()
    }
    
    LLMClient --> LLMClientConfig
    LLMClient --> ToolManager
```

## Execution Flow

### Standard Request Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Executor
    participant LLMClient
    participant Agent
    participant Tool
    participant LLM
    
    User->>CLI: Command
    CLI->>Executor: Create & Execute
    Executor->>Agent: Select Agent(s)
    Agent->>LLMClient: Prepare Request
    LLMClient->>LLM: API Call
    LLM-->>LLMClient: Response
    
    alt Tool Required
        LLMClient->>Tool: Execute Tool
        Tool-->>LLMClient: Tool Result
        LLMClient->>LLM: Follow-up Call
        LLM-->>LLMClient: Final Response
    end
    
    LLMClient-->>Agent: Processed Response
    Agent-->>Executor: Agent Result
    Executor-->>CLI: Execution Result
    CLI-->>User: Display Output
```

### Parallel Agent Execution

```mermaid
graph LR
    subgraph "Parallel Execution"
        AE[Agent Executor]
        AE -->|async| CA[Code Agent]
        AE -->|async| FA[File Agent]
        AE -->|async| SA[Search Agent]
        
        CA -->|Result| AR1[Agent Result 1]
        FA -->|Result| AR2[Agent Result 2]
        SA -->|Result| AR3[Agent Result 3]
        
        AR1 --> CM[Combine Results]
        AR2 --> CM
        AR3 --> CM
        
        CM --> FR[Final Report]
    end
```

## Agent System

### Agent Hierarchy

```mermaid
graph TD
    subgraph "Agent Base"
        A[Agent]
        A --> N[name: str]
        A --> D[description: str]
        A --> P[prompt: Prompt]
        A --> T[tools: ToolManager]
    end
    
    subgraph "Specialized Agents"
        CA[CodeAgent]
        DA[DockerAgent]
        FA[FileAgent]
        MA[MCPAgent]
        SA[SearchAgent]
    end
    
    A --> CA
    A --> DA
    A --> FA
    A --> MA
    A --> SA
    
    %% Add MCPAgentManager as the orchestrator for MCP agents
    MA -.->|managed by| MAM[MCPAgentManager]
    
    subgraph "Code Agent Tools"
        CA --> ACT[analyze_code_structure]
        CA --> CCQ[check_code_quality]
        CA --> FC[format_code]
        CA --> GT[generate_tests]
    end
    
    subgraph "Docker Agent Tools"
        DA --> LC[list_containers]
        DA --> CC[create_container]
        DA --> SC[start_container]
        DA --> STC[stop_container]
    end
    
    subgraph "File Agent Tools"
        FA --> CF[create_file]
        FA --> RF[read_file]
        FA --> UF[update_file]
        FA --> DF[delete_file]
    end
```

### Agent Selection Process

```mermaid
flowchart TD
    Start([User Query]) --> Parse[Parse Query Intent]
    Parse --> Analyze{Analyze Requirements}
    
    Analyze -->|Code Related| SelectCode[Select Code Agent]
    Analyze -->|File Operations| SelectFile[Select File Agent]
    Analyze -->|Docker Tasks| SelectDocker[Select Docker Agent]
    Analyze -->|Web Search| SelectSearch[Select Search Agent]
    Analyze -->|MCP Operations| SelectMCP[Select MCP Agent]
    Analyze -->|Multiple Needs| SelectMultiple[Select Multiple Agents]
    
    SelectCode --> Execute[Execute Agent(s)]
    SelectFile --> Execute
    SelectDocker --> Execute
    SelectSearch --> Execute
    SelectMCP --> Execute
    SelectMultiple --> ParallelExec{Parallel Execution?}
    
    ParallelExec -->|Yes| AsyncExec[Async Execution]
    ParallelExec -->|No| SeqExec[Sequential Execution]
    
    AsyncExec --> Execute
    SeqExec --> Execute
    
    Execute --> Results[Combine Results]
    Results --> End([Return Response])
```

## Memory Management

### Memory System Architecture

```mermaid
graph TB
    subgraph "Memory Components"
        MM[Memory Manager]
        MC[Memory Collection]
        VI[Vector Index]
        MS[Memory Store]
    end
    
    subgraph "Memory Operations"
        ST[Store Memory]
        QM[Query Memory]
        UM[Update Memory]
        DM[Delete Memory]
    end
    
    subgraph "ChromaDB Backend"
        CDB[(ChromaDB)]
        EMB[Embeddings]
        META[Metadata]
    end
    
    MM --> MC
    MC --> VI
    VI --> MS
    
    ST --> MM
    QM --> MM
    UM --> MM
    DM --> MM
    
    MS --> CDB
    CDB --> EMB
    CDB --> META
```

### Memory Query Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant MemoryTool
    participant ChromaDB
    participant Embeddings
    
    User->>CLI: Query with context
    CLI->>MemoryTool: Check for memories
    MemoryTool->>Embeddings: Generate query embedding
    Embeddings-->>MemoryTool: Query vector
    MemoryTool->>ChromaDB: Vector similarity search
    
    alt Memories Found
        ChromaDB-->>MemoryTool: Related memories
        MemoryTool-->>CLI: Context + memories
        CLI->>CLI: Augment prompt
    else No Memories
        ChromaDB-->>MemoryTool: Empty result
        MemoryTool-->>CLI: Original context
    end
    
    CLI->>CLI: Continue execution
```

## Tool System

### Tool Manager Architecture

```mermaid
classDiagram
    class ToolManager {
        +tools: List[ToolCall]
        +func_tools: Dict[str, FunctionTool]
        +register_tool()
        +get_tool()
        +execute_tool()
        +batch_execute()
    }
    
    class ToolCall {
        +name: str
        +description: str
        +parameters: Dict
        +execute()
    }
    
    class FunctionTool {
        +fn: Callable
        +docstring: str
        +parse_docstring()
    }
    
    class FileManagerTool {
        +create_file()
        +read_file()
        +update_file()
        +delete_file()
        +list_directory()
    }
    
    class MemoryTool {
        +store_memory()
        +query_memory()
        +update_memory()
    }
    
    ToolManager --> ToolCall
    ToolManager --> FunctionTool
    ToolCall <|-- FileManagerTool
    ToolCall <|-- MemoryTool
```

### Tool Execution Pipeline

```mermaid
flowchart LR
    subgraph "Tool Execution"
        TR[Tool Request] --> TV{Validate}
        TV -->|Valid| TE[Execute Tool]
        TV -->|Invalid| ER[Error Response]
        
        TE --> TRY{Try Execute}
        TRY -->|Success| RES[Tool Result]
        TRY -->|Error| EH[Error Handler]
        
        EH --> RT{Retry?}
        RT -->|Yes| TE
        RT -->|No| ER
        
        RES --> FMT[Format Result]
        FMT --> RET[Return to LLM]
    end
```

## Error Handling

### Exception Hierarchy

```mermaid
classDiagram
    class TronAIError {
        <<Exception>>
        +message: str
    }
    
    class ExecutionError {
        <<Exception>>
        +executor: str
        +operation: str
    }
    
    class AgentError {
        <<Exception>>
        +agent_name: str
        +operation: str
    }
    
    class TaskError {
        <<Exception>>
        +task_id: str
        +reason: str
    }
    
    class ConfigError {
        <<Exception>>
        +config_key: str
        +reason: str
    }
    
    TronAIError <|-- ExecutionError
    TronAIError <|-- AgentError
    TronAIError <|-- TaskError
    TronAIError <|-- ConfigError
```

### Error Handling Flow

```mermaid
flowchart TD
    subgraph "Error Handling Strategy"
        OP[Operation] --> TRY{Try Block}
        TRY -->|Success| SUC[Return Result]
        TRY -->|Exception| CAT{Catch Type}
        
        CAT -->|TronAIError| HAI[Handle AI Error]
        CAT -->|APIError| HAPI[Handle API Error]
        CAT -->|Timeout| HTO[Handle Timeout]
        CAT -->|Other| HGE[Handle Generic]
        
        HAI --> LOG1[Log Error]
        HAPI --> RET{Retry?}
        HTO --> CAN[Cancel Operation]
        HGE --> LOG2[Log & Wrap]
        
        RET -->|Yes| OP
        RET -->|No| FAIL[Return Error]
        
        LOG1 --> FAIL
        CAN --> FAIL
        LOG2 --> FAIL
    end
```

## Configuration Management

### Configuration Flow

```mermaid
graph TD
    subgraph "Configuration Sources"
        ENV[Environment Variables]
        CONST[Constants Module]
        CONF[Config Files]
    end
    
    subgraph "Configuration Loader"
        CL[Config Loader]
        VAL[Validator]
        MERGE[Merger]
    end
    
    subgraph "Runtime Config"
        RC[Runtime Config]
        LOG[Logging Config]
        LLM[LLM Config]
        MEM[Memory Config]
        TO[Timeout Config]
    end
    
    ENV --> CL
    CONST --> CL
    CONF --> CL
    
    CL --> VAL
    VAL --> MERGE
    MERGE --> RC
    
    RC --> LOG
    RC --> LLM
    RC --> MEM
    RC --> TO
```

## Deployment Architecture

### Container Architecture

```mermaid
graph TB
    subgraph "Docker Deployment"
        MAIN[Main Container]
        CDB[ChromaDB Container]
        MCP[MCP Server Container]
    end
    
    subgraph "Volumes"
        DATA[Data Volume]
        CONFIG[Config Volume]
        LOGS[Logs Volume]
    end
    
    subgraph "Network"
        NET[Docker Network]
    end
    
    MAIN --> NET
    CDB --> NET
    MCP --> NET
    
    MAIN --> DATA
    MAIN --> CONFIG
    MAIN --> LOGS
    CDB --> DATA
```

This architecture documentation provides a comprehensive overview of the Tron AI system, showing how components interact and data flows through the system. 