from typing import List, Dict
from tron_ai.modules.tasks.models import AgentAssignedTask
from tron_ai.models.prompts import Prompt
from tron_ai.utils.LLMClient import LLMClient


class ReportGenerator:
    """Generates comprehensive reports from a list of completed tasks.

    This class takes the results of a task-based workflow and synthesizes them
    into a human-readable report. It combines a high-level execution summary
    with a detailed, LLM-generated analysis that connects the task outcomes
    back to the original user query.
    """

    def __init__(self, client: LLMClient):
        """Initializes the ReportGenerator.

        Args:
            client: An instance of LLMClient used to generate the detailed analysis.
        """
        self.client = client

    def generate_report(self, tasks: List[AgentAssignedTask], user_query: str) -> str:
        """Generates a detailed analysis report of the completed tasks.

        This is the main method of the class. It orchestrates the creation of
        task summaries, generates a detailed analysis via an LLM, and combines
        it with a structured execution summary.

        Args:
            tasks: A list of completed `AgentAssignedTask` objects, including their results.
            user_query: The original user query that initiated the workflow.

        Returns:
            A formatted string containing the full report.
        """
        # Create task summaries
        task_summaries = self._create_task_summaries(tasks)
        task_info = self._format_task_info(task_summaries)

        # Generate analysis using LLM
        detailed_report = self._generate_detailed_report(task_info, user_query)

        # Create execution summary
        summary = self._create_execution_summary(tasks)

        # Combine summary and detailed report
        if hasattr(detailed_report, "response"):
            return (
                "\n".join(summary)
                + "\n\n=== Detailed Analysis ===\n\n"
                + detailed_report.response
            )
        else:
            return (
                "\n".join(summary)
                + "\n\n=== Detailed Analysis ===\n\n"
                + detailed_report
            )

    def _create_task_summaries(self, tasks: List[AgentAssignedTask]) -> List[Dict]:
        """Creates a list of structured dictionaries, one for each task.

        This private method extracts key information from each task object to
        prepare it for formatting and analysis.

        Args:
            tasks: The list of `AgentAssignedTask` objects.

        Returns:
            A list of dictionaries, each summarizing a single task.
        """
        return [
            {
                "id": task.identifier,
                "description": task.description,
                "agent": task.agent.name,
                "dependencies": task.dependencies,
                "result": str(task.result),
            }
            for task in tasks
        ]

    def _format_task_info(self, task_summaries: List[Dict]) -> str:
        """Formats the task summaries into a single string for the LLM prompt.

        Args:
            task_summaries: A list of task summary dictionaries.

        Returns:
            A formatted string detailing the results of all tasks.
        """
        return "\n".join(
            [
                f"Task {t['id']}:"
                f"\nDescription: {t['description']}"
                f"\nAgent: {t['agent']}"
                f"\nDependencies: {', '.join(t['dependencies']) if t['dependencies'] else 'None'}"
                f"\nResult: {t['result']}\n"
                for t in task_summaries
            ]
        )

    def _generate_detailed_report(self, task_info: str, user_query: str) -> str:
        """Uses the LLM to generate an in-depth analysis of the task results.

        This method constructs a detailed prompt asking the LLM to analyze the
        task outcomes in the context of the user's original request and returns
        the model's response.

        Args:
            task_info: The formatted string containing all task results.
            user_query: The original user query.

        Returns:
            The LLM-generated analysis as a string.
        """
        prompt = f"""Analyze the following task execution results in the context of the original user request.

Original User Query:
"{user_query}"

Task Results:
{task_info}

Please provide a detailed analysis focusing on:
1. How well the tasks fulfilled the user's original request
2. How tasks worked together and dependencies were handled
3. Key findings or results from each task
4. Overall success of the workflow
5. Any notable patterns or insights
6. Whether the results fully address the user's needs

Provide your analysis in a clear, structured format that connects the results back to the original query."""

        response = self.client.call(
            user_query=prompt,
            system_prompt=Prompt(
                text="""You are an expert at analyzing task execution results. 
Your role is to:
1. Understand the user's original intent from their query
2. Analyze how well the executed tasks fulfilled that intent
3. Provide insights about the task execution process
4. Evaluate the completeness and quality of the results
5. Suggest any potential improvements or additional steps if needed

Then a concise summary of the report.

Provide a detailed, insightful analysis that helps users understand both what was accomplished and how it relates to their original request."""
            ),
        )

        return response

    def _create_execution_summary(self, tasks: List[AgentAssignedTask]) -> List[str]:
        """Creates a high-level summary of the task execution statistics.

        This method provides a quick overview of the workflow's outcome,
        including total, completed, and failed task counts, along with a
        brief result for each successful task.

        Args:
            tasks: The list of all executed `AgentAssignedTask` objects.

        Returns:
            A list of strings that form the execution summary.
        """
        completed_tasks = [t for t in tasks if t.done and not t.error]
        failed_tasks = [t for t in tasks if t.error]

        # Optimized: Build summary header with list, then extend with comprehension
        summary = [
            "=== Execution Summary ===\n",
            f"Total Tasks: {len(tasks)}\n",
            f"Completed: {len(completed_tasks)}\n",
            f"Failed: {len(failed_tasks)}\n",
            "\nTask Results:\n",
        ]

        # Optimized: Generate task summaries using list comprehension with conditional elements
        task_summaries = []
        for task in completed_tasks:
            task_summary = [
                f"\n[{task.identifier}] {task.description}",
                f"Agent: {task.agent.name}",
            ]
            if task.dependencies:
                task_summary.append(f"Dependencies: {', '.join(task.dependencies)}")
            task_summary.extend(["Result:\n\n", f"{task.result.response}", "---"])
            task_summaries.extend(task_summary)

        summary.extend(task_summaries)
        return summary
