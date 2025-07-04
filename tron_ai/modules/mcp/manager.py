import logging
from typing import Dict, Optional
from tron_ai.modules.mcp.agent import Agent
from tron_ai.modules.mcp.client import load_mcp_server_configs

logger = logging.getLogger("mcp_agent_manager")

class MCPAgentManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.default_agent_name: Optional[str] = None
        self._initialized = False

    async def initialize(self, config_path: str = "mcp_servers.json"):
        if self._initialized:
            return
        logger.info(f"Loading MCP server configs from {config_path}")
        server_configs = load_mcp_server_configs(config_path)
        logger.info(f"Found {len(server_configs)} server configurations")
        
        for server_name, server_config in server_configs.items():
            logger.info(f"Creating agent for server: {server_name}")
            agent = Agent(server_name, server_config)
            await agent.initialize()
            self.agents[server_name] = agent
            
            # Log the tools for this agent
            if agent.tool_manager:
                tool_names = [tool.fn.__name__ for tool in agent.tool_manager.tools]
                logger.info(f"Agent '{server_name}' initialized with {len(tool_names)} tools: {tool_names[:5]}{'...' if len(tool_names) > 5 else ''}")
            else:
                logger.warning(f"Agent '{server_name}' has no tool_manager!")
                
        if self.agents:
            self.default_agent_name = next(iter(self.agents))
        self._initialized = True
        logger.info(f"Initialized {len(self.agents)} MCP agents")
        
        # Log summary of all agents and their tools
        logger.info("=== Agent Tool Summary ===")
        for name, agent in self.agents.items():
            if agent.tool_manager:
                logger.info(f"  {name}: {len(agent.tool_manager.tools)} tools")
            else:
                logger.info(f"  {name}: No tools")
        logger.info("========================")

    def get_default_agent(self) -> Optional[Agent]:
        if self.default_agent_name:
            return self.agents.get(self.default_agent_name)
        return None

    def get_agent(self, server_name: str) -> Optional[Agent]:
        return self.agents.get(server_name)

    async def add_agent(self, server_name: str, server_config: dict):
        if server_name in self.agents:
            logger.warning(f"Agent for server {server_name} already exists")
            return
        agent = Agent(server_name, server_config)
        await agent.initialize()
        self.agents[server_name] = agent
        if not self.default_agent_name:
            self.default_agent_name = server_name
        logger.info(f"Added MCP agent for server {server_name}")

    async def remove_agent(self, server_name: str):
        agent = self.agents.pop(server_name, None)
        if agent:
            await agent.cleanup()
            logger.info(f"Removed MCP agent for server {server_name}")
        if self.default_agent_name == server_name:
            self.default_agent_name = next(iter(self.agents), None)

    async def reload_agents(self, config_path: str = "mcp_servers.json"):
        logger.info("Reloading MCP agents from config")
        await self.cleanup()
        self._initialized = False
        await self.initialize(config_path)

    async def cleanup(self):
        logger.info("Cleaning up all MCP agents")
        for agent in self.agents.values():
            await agent.cleanup()
        self.agents.clear()
        self.default_agent_name = None
        self._initialized = False 