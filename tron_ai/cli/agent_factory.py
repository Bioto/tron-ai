"""
Agent factory for centralized agent creation and management.

This module provides a clean interface for creating agents and eliminates
repetitive try-except blocks throughout the CLI code.
"""

import logging
from typing import Dict, List, Optional, Type, Union

from rich.console import Console

from tron_ai.models.agent import Agent
from tron_ai.exceptions import TronAIError


logger = logging.getLogger(__name__)


class AgentNotFoundError(TronAIError):
    """Raised when a requested agent is not available."""
    pass


class AgentLoadError(TronAIError):
    """Raised when an agent fails to load."""
    pass


class AgentFactory:
    """
    Factory for creating and managing AI agents.
    
    Follows the Factory pattern to centralize agent creation logic
    and improve error handling consistency.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._agent_registry: Dict[str, Type[Agent]] = {}
        self._agent_cache: Dict[str, Agent] = {}
        
    def _register_core_agents(self) -> None:
        """Register core Tron agents."""
        try:
            from tron_ai.agents.tron.agent import TronAgent
            self._agent_registry["tron"] = TronAgent
        except ImportError as e:
            logger.warning(f"Failed to register Tron agent: {e}")
    
    def _register_productivity_agents(self) -> None:
        """Register productivity agents with proper error handling."""
        productivity_agents = {
            "google": ("tron_ai.agents.productivity.google.agent", "GoogleAgent"),
            "android": ("tron_ai.agents.productivity.android.agent", "AndroidAgent"),
            "todoist": ("tron_ai.agents.productivity.todoist.agent", "TodoistAgent"),
            "notion": ("tron_ai.agents.productivity.notion.agent", "NotionAgent"),
            "wordpress": ("tron_ai.agents.productivity.wordpress.agent", "WordPressAgent"),
        }
        
        for agent_name, (module_path, class_name) in productivity_agents.items():
            try:
                module = __import__(module_path, fromlist=[class_name])
                agent_class = getattr(module, class_name)
                self._agent_registry[agent_name] = agent_class
            except (ImportError, AttributeError) as e:
                logger.debug(f"Productivity agent '{agent_name}' not available: {e}")
    
    def _register_devops_agents(self) -> None:
        """Register DevOps agents with proper error handling."""
        devops_agents = {
            "ssh": ("tron_ai.agents.devops.ssh.agent", "SSHAgent"),
            "code_scanner": ("tron_ai.agents.devops.code_scanner.agent", "CodeScannerAgent"),
            "editor": ("tron_ai.agents.devops.editor.agent", "EditorAgent"),
            "repo_scanner": ("tron_ai.agents.devops.repo_scanner.agent", "RepoScannerAgent"),
        }
        
        for agent_name, (module_path, class_name) in devops_agents.items():
            try:
                module = __import__(module_path, fromlist=[class_name])
                agent_class = getattr(module, class_name)
                self._agent_registry[agent_name] = agent_class
            except (ImportError, AttributeError) as e:
                logger.debug(f"DevOps agent '{agent_name}' not available: {e}")
    
    def _register_business_agents(self) -> None:
        """Register business agents with proper error handling."""
        business_agents = {
            "marketing_strategy": ("tron_ai.agents.business.marketing_strategy.agent", "MarketingStrategyAgent"),
            "sales": ("tron_ai.agents.business.sales.agent", "SalesAgent"),
            "customer_success": ("tron_ai.agents.business.customer_success.agent", "CustomerSuccessAgent"),
            "product_management": ("tron_ai.agents.business.product_management.agent", "ProductManagementAgent"),
            "financial_planning": ("tron_ai.agents.business.financial_planning.agent", "FinancialPlanningAgent"),
            "ai_ethics": ("tron_ai.agents.business.ai_ethics.agent", "AIEthicsAgent"),
            "content_creation": ("tron_ai.agents.business.content_creation.agent", "ContentCreationAgent"),
            "community_relations": ("tron_ai.agents.business.community_relations.agent", "CommunityRelationsAgent"),
        }
        
        for agent_name, (module_path, class_name) in business_agents.items():
            try:
                module = __import__(module_path, fromlist=[class_name])
                agent_class = getattr(module, class_name)
                self._agent_registry[agent_name] = agent_class
            except (ImportError, AttributeError) as e:
                logger.debug(f"Business agent '{agent_name}' not available: {e}")
    
    def _register_mcp_agents(self) -> List[Agent]:
        """Register MCP agents with proper error handling."""
        mcp_agents = []
        try:
            from tron_ai.modules.mcp.manager import MCPAgentManager
            # Note: This would need to be called in an async context
            # For now, we'll return empty list and handle MCP separately
            logger.debug("MCP agent registration requires async context")
        except ImportError as e:
            logger.debug(f"MCP agents not available: {e}")
        
        return mcp_agents
    
    def initialize(self) -> None:
        """Initialize the agent factory by registering all available agents."""
        self._register_core_agents()
        self._register_productivity_agents()
        self._register_devops_agents()
        self._register_business_agents()
        
        logger.info(f"Agent factory initialized with {len(self._agent_registry)} agent types")
    
    def create_agent(self, agent_name: str, **kwargs) -> Agent:
        """
        Create an agent instance by name.
        
        Args:
            agent_name: Name of the agent to create
            **kwargs: Additional arguments to pass to agent constructor
            
        Returns:
            Agent instance
            
        Raises:
            AgentNotFoundError: If agent is not registered
            AgentLoadError: If agent fails to instantiate
        """
        if agent_name in self._agent_cache:
            return self._agent_cache[agent_name]
        
        if agent_name not in self._agent_registry:
            available_agents = list(self._agent_registry.keys())
            raise AgentNotFoundError(
                f"Agent '{agent_name}' not found. Available agents: {', '.join(available_agents)}"
            )
        
        try:
            agent_class = self._agent_registry[agent_name]
            agent_instance = agent_class(**kwargs)
            self._agent_cache[agent_name] = agent_instance
            
            self.console.print(f"[green]✓[/green] Created {agent_instance.name}")
            return agent_instance
            
        except Exception as e:
            error_msg = f"Failed to create agent '{agent_name}': {e}"
            logger.error(error_msg)
            raise AgentLoadError(error_msg) from e
    
    def create_agents_safely(self, agent_names: List[str]) -> List[Agent]:
        """
        Create multiple agents with graceful error handling.
        
        Args:
            agent_names: List of agent names to create
            
        Returns:
            List of successfully created agents
        """
        agents = []
        
        for agent_name in agent_names:
            try:
                agent = self.create_agent(agent_name)
                agents.append(agent)
            except (AgentNotFoundError, AgentLoadError) as e:
                self.console.print(f"[yellow]⚠[/yellow] {agent_name} Agent unavailable: {e}")
                logger.debug(f"Agent creation failed: {e}")
        
        return agents
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent names."""
        return list(self._agent_registry.keys())
    
    def get_agent_choices(self) -> List[str]:
        """Get agent choices for CLI options (includes generic)."""
        choices = ["generic"] + self.get_available_agents()
        return sorted(choices)
    
    async def create_mcp_agents(self) -> List[Agent]:
        """
        Create MCP agents asynchronously.
        
        Returns:
            List of MCP agent instances
        """
        mcp_agents = []
        try:
            from tron_ai.modules.mcp.manager import MCPAgentManager
            manager = MCPAgentManager()
            await manager.initialize()
            
            for server_name, agent in manager.agents.items():
                mcp_agents.append(agent)
                self.console.print(f"[green]✓[/green] Added MCP Agent: {agent.name}")
                
        except Exception as e:
            self.console.print(f"[red]✗[/red] Failed to load MCP agents: {e}")
            logger.error(f"MCP agent creation failed: {e}")
        
        return mcp_agents


# Global factory instance
_agent_factory: Optional[AgentFactory] = None


def get_agent_factory(console: Optional[Console] = None) -> AgentFactory:
    """Get the global agent factory instance."""
    global _agent_factory
    if _agent_factory is None:
        _agent_factory = AgentFactory(console)
        _agent_factory.initialize()
    return _agent_factory


def create_agent(agent_name: str, console: Optional[Console] = None, **kwargs) -> Agent:
    """Convenience function to create a single agent."""
    factory = get_agent_factory(console)
    return factory.create_agent(agent_name, **kwargs)


def create_agents_safely(agent_names: List[str], console: Optional[Console] = None) -> List[Agent]:
    """Convenience function to create multiple agents safely."""
    factory = get_agent_factory(console)
    return factory.create_agents_safely(agent_names)
