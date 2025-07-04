# Standard library imports
from typing import Type

# Third-party imports
import pydantic
from pydantic_core import from_json

# Local imports
from tron_ai.executors.base import Executor
from tron_ai.models.prompts import Prompt, PromptDefaultResponse


class Step(pydantic.BaseModel):
    prompt: Prompt
    output_format: Type[pydantic.BaseModel] = PromptDefaultResponse


class ChainExecutor(Executor):
    def execute(self, user_query: str, steps: list[Step]) -> pydantic.BaseModel:
        step_results = []

        chain_query = user_query
        step_result = None

        result = None

        for index, step in enumerate(steps):
            chain_query = f"""
                # Current step: {index} / {len(steps)}
                # Original user query: {user_query}
                # Previous steps results: {step_results}
                # Previous step result: {step_result}
                # Follow your instructions to complete the current step.
                # Never use data from the output format example.
            """

            result = self.client.call(
                user_query=chain_query, system_prompt=step.prompt
            ).model_dump_json()

            step_results.append(result)
            step_result = result

        return steps[-1].output_format(**from_json(result))
