from .tools import DelegateTools
from .models import DelegateState
from tron_ai.utils.graph import StateGraph
from tron_ai.executors.base import Executor
from tron_ai.exceptions import ExecutionError

def build_delegate_graph(tools: DelegateTools) -> StateGraph:
    """Constructs the state graph for the task delegation workflow.

    This function defines the control flow for the multi-agent delegation process.
    It creates a state graph with nodes representing the key stages:
    - generate_tasks: Creates a task list from the user's query.
    - assign_agents_to_tasks: Assigns each task to the most appropriate agent.
    - execute_assigned_tasks: Executes the tasks.
    - handle_execution_results: Compiles the final report.

    The graph includes conditional edges to handle cases where no tasks are generated.

    Args:
        tools: An instance of `DelegateTools` containing the functions for each node.

    Returns:
        A compiled `StateGraph` instance ready for execution.
    """
    graph = StateGraph()
    
    graph.add_node(
        name="generate_tasks",
        func=tools.process_tasks
    )
    graph.add_node(
        name="assign_agents_to_tasks",
        func=tools.assign_agents
    )
    graph.add_node(
        name="execute_assigned_tasks",
        func=tools.execute_tasks
    )
    graph.add_node(
        name="handle_execution_results",
        func=tools.handle_results
    )

    
    graph.add_edge("generate_tasks", "assign_agents_to_tasks", condition=lambda state: bool(state.tasks))
    graph.add_edge("generate_tasks", "handle_execution_results", condition=lambda state: not bool(state.tasks))
    graph.add_edge("assign_agents_to_tasks", "execute_assigned_tasks")
    graph.add_edge("execute_assigned_tasks", "handle_execution_results")
    
    graph.set_entrypoint("generate_tasks")
    graph.set_exit("handle_execution_results")
    
    return graph
        

class TaskerExecutor(Executor):
    """An agent executor that orchestrates a team of specialized agents.

    This executor manages the entire lifecycle of a user request by delegating
    work to a collection of other agents. It uses a state graph (`StateGraph`)
    to break down the query, assign tasks, execute them, and synthesize the
    results into a single response.

    Attributes:
        state: The Pydantic model used to manage state across the graph execution.
        tools: An instance of `DelegateTools` that provides the concrete
            implementation for each step in the delegation process.
    """

    def __init__(self, state: DelegateState, *args, **kwargs):
        """Initializes the DelegateExecutor.

        Args:
            agents: A list of `Agent` instances available for task delegation.
            state: The initial state model for the workflow.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments passed to the base executor.
        """
        super().__init__(*args, **kwargs)
        self.state: DelegateState = state
        self.tools: DelegateTools = DelegateTools(client=self.client)

    async def execute(self, user_query: str) -> DelegateState:
        """Execute the delegation workflow for the given user query.
        
        Args:
            user_query: The user's input query to process
            
        Returns:
            str: The final execution report
            
        Raises:
            ExecutionError: If any step in the execution fails
        """
        self.logger.info(f"Starting execution for query: {user_query}")
        try:
            graph = build_delegate_graph(self.tools)
            state = self.state.model_copy(update={
                "user_query": user_query,
                "agents": self.state.agents
            })
            result = await graph.run(initial_state=state)
            return result
            
        except ExecutionError as e:
            self.logger.error(f"Execution failed: {str(e)}")
            raise