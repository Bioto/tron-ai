"""State graph implementation for managing asynchronous execution flows.

This module provides a StateGraph class that implements a directed graph for managing
asynchronous execution flows. It supports conditional transitions between nodes and
maintains state throughout the execution.

Example:
    ```python
    graph = StateGraph()
    graph.add_node("start", start_node)
    graph.add_node("process", process_node)
    graph.set_entrypoint("start")
    graph.set_exit("end")
    graph.add_edge("start", "process")
    graph.add_edge("process", "end", lambda s: s.is_complete)
    final_state = await graph.run(initial_state)
    ```
"""

import asyncio
from typing import Callable, Dict, Optional, Awaitable, TypeVar, Generic
from pydantic import BaseModel
from tron_ai.config import setup_logging
import logging

# Setup logging for this module
setup_logging()
logger = logging.getLogger("tron_ai.graph")

T = TypeVar('T', bound=BaseModel)

class StateGraph(Generic[T]):
    """A directed graph for managing asynchronous execution flows.
    
    This class implements a state machine where nodes are async functions that process
    state and edges define transitions between nodes. Edges can have optional conditions
    that determine whether the transition should occur.
    
    Attributes:
        nodes: Dictionary mapping node names to their processing functions
        edges: Dictionary mapping source nodes to dictionaries of target nodes and conditions
        entrypoint: The name of the starting node
        exit_nodes: Set of node names that mark the end of execution
    """
    
    def __init__(self):
        """Initialize a new StateGraph instance."""
        self.logger = logging.getLogger("tron_ai.graph")
        self.nodes: Dict[str, Callable[[T], Awaitable[T]]] = {}
        self.edges: Dict[str, Dict[str, Optional[Callable[[T], bool]]]] = {}
        self.entrypoint: Optional[str] = None
        self.exit_nodes: set[str] = set()

    def add_node(self, name: str, func: Callable[[T], Awaitable[T]]) -> None:
        """Add a node to the graph.
        
        Args:
            name: Unique identifier for the node
            func: Async function that processes the state
        """
        self.nodes[name] = func

    def add_edge(
        self, 
        from_node: str, 
        to_node: str, 
        condition: Optional[Callable[[T], bool]] = None
    ) -> None:
        """Add an edge between two nodes.
        
        Args:
            from_node: Source node name
            to_node: Target node name
            condition: Optional function that determines if transition should occur
        """
        if from_node not in self.edges:
            self.edges[from_node] = {}
        self.edges[from_node][to_node] = condition

    def set_entrypoint(self, name: str) -> None:
        """Set the starting node for execution.
        
        Args:
            name: Name of the entry node
        """
        self.entrypoint = name

    def set_exit(self, name: str) -> None:
        """Add a node to the set of exit nodes.
        
        Args:
            name: Name of the exit node
        """
        self.exit_nodes.add(name)

    async def run(self, initial_state: T, timeout: float = 30.0, max_cycles: int = 100) -> T:
        """Execute the graph starting from the entrypoint.

        Args:
            initial_state: Initial state to process
            timeout: Timeout in seconds for each node execution
            max_cycles: Maximum number of node executions to prevent infinite loops

        Returns:
            Final state after execution completes

        Raises:
            ValueError: If entrypoint is not set
            RuntimeError: If no valid transition is found
            asyncio.TimeoutError: If a node execution times out
            RecursionError: If cycle detection limit is exceeded
        """
        if not self.entrypoint:
            raise ValueError("Entrypoint not set")

        current_node = self.entrypoint
        state = initial_state
        visited_nodes = set()
        execution_count = 0

        while current_node not in self.exit_nodes:
            # Cycle detection
            if current_node in visited_nodes:
                raise RecursionError(f"Cycle detected at node {current_node}. Visited nodes: {visited_nodes}")
            visited_nodes.add(current_node)

            # Execution limit check
            execution_count += 1
            if execution_count > max_cycles:
                raise RecursionError(f"Maximum execution cycles ({max_cycles}) exceeded. Possible infinite loop.")

            node_fn = self.nodes[current_node]
            self.logger.info(f"Executing node: {current_node} (cycle {execution_count})")

            # Execute with timeout
            try:
                state = await asyncio.wait_for(node_fn(state), timeout=timeout)
            except asyncio.TimeoutError as e:
                self.logger.error(f"Node {current_node} timed out after {timeout}s")
                raise asyncio.TimeoutError(f"Node execution timeout: {current_node}") from e

            # Determine next node
            outgoing = self.edges.get(current_node, {})
            if not outgoing:
                raise RuntimeError(f"No outgoing edges from node {current_node}")

            if len(outgoing) == 1:
                # Only one possible next node
                next_node = next(iter(outgoing))
                current_node = next_node
                continue

            # Multiple possible next nodes, check conditions
            found = False
            for next_node, condition in outgoing.items():
                if condition is None or condition(state):
                    current_node = next_node
                    found = True
                    break

            if not found:
                raise RuntimeError(f"No valid transition from {current_node} for state {state}")

        self.logger.info(f"Exiting at node: {current_node} after {execution_count} executions")

        # Execute exit node if it's a processing node
        if current_node in self.nodes:
            try:
                state = await asyncio.wait_for(self.nodes[current_node](state), timeout=timeout)
            except asyncio.TimeoutError as e:
                self.logger.error(f"Exit node {current_node} timed out after {timeout}s")
                raise asyncio.TimeoutError(f"Exit node execution timeout: {current_node}") from e

        return state

# Example usage
class MyState(BaseModel):
    """Example state model for demonstration."""
    value: int = 0

async def increment_node(state: MyState) -> MyState:
    """Example node that increments the state value."""
    state.value += 1
    return state

async def check_node(state: MyState) -> MyState:
    """Example node that checks the state value."""
    return state

async def main() -> None:
    """Example usage of StateGraph."""
    graph = StateGraph[MyState]()
    graph.add_node("increment", increment_node)
    graph.add_node("check", check_node)
    graph.set_entrypoint("increment")
    graph.set_exit("end")
    graph.add_edge("increment", "check")
    graph.add_edge("check", "increment", lambda s: s.value < 3)
    graph.add_edge("check", "end", lambda s: s.value >= 3)
    final_state = await graph.run(MyState(), timeout=10.0, max_cycles=5)
    
if __name__ == "__main__":
    asyncio.run(main())