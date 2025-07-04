import asyncio
from typing import Dict, List
from tron_ai.executors.agents.base_executors import BaseAgentExecutor, R
from tron_ai.executors.agents.models.agent import AgentExecutorResults, AgentExecutorResponse, Agent
from tron_ai.exceptions import ExecutionError

class AgentExecutor(BaseAgentExecutor[AgentExecutorResponse]):
    """Agent executor that coordinates multiple agents to process user queries.
    
    This executor manages the parallel execution of multiple agents, each with their own
    specialized capabilities and tools. It handles agent preparation, execution coordination,
    and result aggregation.
    """
    
    async def execute(self, user_query: str) -> R:
        """Execute the user query by coordinating multiple agents and tasks.

        Args:
            user_query: The user's original request

        Returns:
            AgentExecutorResults containing responses from all agents

        Raises:
            ExecutionError: If execution fails or encounters an error
        """
        self.logger.info("Starting multi-agent execution")
        
        try:
            self._prepare_agents()
            agents_dict = {agent.name: agent for agent in self.agents}
            results = await self.execute_agents(user_query, agents_dict)
            
            final_results = [
                AgentExecutorResponse(
                    agent_name=result.agent_name if hasattr(result, 'agent_name') else None,
                    diagnostics=result.diagnostics,
                    response=result.response or "",
                ) for result in results
            ]
            return AgentExecutorResults(results=final_results)
            
        except ExecutionError:
            raise
        except Exception as e:
            self.logger.exception(f"Error during execution: {str(e)}")
            raise ExecutionError(f"Error during execution: {str(e)}")
            
    async def execute_agents(self, user_query: str, agents: Dict[str, Agent]) -> List[AgentExecutorResponse]:
        """Execute multiple agents in parallel for a given query.
        
        Args:
            user_query: The query to process
            agents: Dictionary mapping agent names to Agent instances
            
        Returns:
            List of AgentExecutorResponse objects containing results from each agent
        """
        self.logger.info(f"Executing {len(agents)} agents for query: {user_query[:50]}...")
        
        # Log agent capabilities
        for agent_name, agent in agents.items():
            if hasattr(agent, 'tool_manager') and agent.tool_manager:
                tool_count = len(agent.tool_manager.tools)
                tool_names = [tool.fn.__name__ for tool in agent.tool_manager.tools[:3]]
                self.logger.info(f"Agent '{agent_name}' has {tool_count} tools. First 3: {tool_names}")
            else:
                self.logger.info(f"Agent '{agent_name}' has no tool_manager")

        # Create parallel execution tasks
        tasks = [
            self.client.fcall(
                user_query=user_query,
                system_prompt=agent.prompt,
                tool_manager=agent.tool_manager,
                prompt_kwargs={},
                output_data_class=agent.prompt.output_format,
            ) for agent in agents.values()
        ]
        
        self.logger.info(f"Created {len(tasks)} tasks for parallel execution")
        responses = await asyncio.gather(*tasks)
        self.logger.info(f"Received {len(responses)} responses")

        # Map responses to agent names and format results
        return [
            AgentExecutorResponse(
                agent_name=agent.name,
                diagnostics=result.diagnostics,
                response=result.response or "",
            ) for result, agent in zip(responses, agents.values())
        ]
