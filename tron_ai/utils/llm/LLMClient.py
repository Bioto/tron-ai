# Standard library imports
from typing import Optional, Any, TYPE_CHECKING, List
import logging
import pprint
from datetime import datetime, timedelta

# Third-party imports
from adalflow import Component, Generator, ModelClient
from adalflow.core.tool_manager import ToolManager
from adalflow.core.types import Function, FunctionOutput
import pydantic
from pydantic_core import from_json
from polyfactory.factories.pydantic_factory import ModelFactory
import orjson

# Local imports
from tron_ai.models.config import LLMClientConfig
from tron_ai.models.prompts import Prompt, PromptDefaultResponse
from tron_ai.constants import (
    LLM_MAX_RETRIES,
    LLM_DEFAULT_TEMPERATURE,
    RETRY_BACKOFF_FACTOR,
    RETRY_MAX_BACKOFF,
)
from tron_ai.utils.io import json as json
from tron_ai.exceptions import (
    LLMResponseError,
    RetryExhaustedError,
    ToolExecutionError,
)

# Set up module logger
logger = logging.getLogger(__name__)

# Using TYPE_CHECKING to avoid circular imports in runtime
if TYPE_CHECKING:
    pass

BASE_PROMPT = """
<SYS>
    {# Main template #}
    {{_template}}

    {# Tools #}
    {% if tools %}
        You have these tools available:
        <TOOLS>
            {% for tool in tools %}
                {{ loop.index }}.
                {{tool}}
                ------------------------
            {% endfor %}
        </TOOLS>
        
        <TOOL_USAGE_RULES>
            - Only call tools if you need information that is not already available in the conversation
            - If you already have tool results that answer the user's question, use those results to provide your final response
            - Do not repeat tool calls that have already been executed successfully
            - If tool results are provided in the user query, analyze them first before deciding if additional tools are needed
            - When calling tools, use kwargs for named parameters (e.g., {"name": "tool_name", "kwargs": {"param1": "value1"}})
            - If a tool call fails with a parameter error, review the error message and retry with corrected parameters
            - Pay attention to the exact parameter names and types expected by each tool
        </TOOL_USAGE_RULES>
    {% endif %}

    {# Output format specification, custom output format #}
    {% if _output_format_str %}
    <OUTPUT_FORMAT>
        {{_output_format_str}}
    </OUTPUT_FORMAT>
    <OUTPUT_FORMAT_RULES>
        - Always return a List using `[]` of the above JSON objects, even if its just one item.
        - If generating a list of tool calls, make sure to include the `name` and `args` and `kwargs` for each tool call.
        - If you have sufficient information to provide a final response, include only the `response` field and omit `tool_calls`
        - When retrying failed tool calls, ensure you use the correct parameter format with kwargs
    </OUTPUT_FORMAT_RULES>
    {% endif %}

    {# Chain steps configuration #}
    {% if chain_steps %}
    <CHAIN>
        <CHAIN_STEPS>true</CHAIN_STEPS>
        <CHAIN_STEPS_PROMPT>
            If you are provided with input from a previous step, use it to complete the current step.
        </CHAIN_STEPS_PROMPT>
    </CHAIN>
    {% endif %}
</SYS>

User: {{_user_query}}
You:
"""


class LLMClient(Component):
    def __init__(self, client: ModelClient, config: LLMClientConfig, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._client = client
        self._config = config

        # Caching settings
        self._response_cache = {}
        self._cache_ttl = timedelta(minutes=10)

        # Memory management settings
        self._max_accumulated_results = 50
        self._result_cleanup_threshold = 100

    def _log(self, message: str) -> None:
        """Internal logging method that checks config before logging."""
        if self._config.logging:
            logger.info(f"[LLMClient] {message}")

    @property
    def api_client(self) -> ModelClient:
        return self._client

    @property
    def model(self) -> str:
        return self._config.model_name

    def _build_generator(
        self,
        prompt: str = BASE_PROMPT,
        output_processors=None,
        override_json_format: bool = None,
    ) -> Generator:
        json_output = (
            override_json_format
            if override_json_format is not None
            else self._config.json_output
        )

        model_kwargs = {
            "model": self._config.model_name,
            "temperature": LLM_DEFAULT_TEMPERATURE,
        }
        self._log(f"Building generator with model: {self._config.model_name}")

        if json_output:
            model_kwargs["response_format"] = {"type": "json_object"}
            self._log("JSON output format enabled")

        return Generator(
            template=prompt,
            model_client=self._client,
            model_kwargs=model_kwargs,
            prompt_kwargs={"_json_output": json_output},
            output_processors=output_processors,
        )

    def call(
        self, user_query: str, system_prompt: Prompt, prompt_kwargs: dict = {}
    ) -> pydantic.BaseModel:
        self._log(f"Making API call with query: {user_query[:100]}...")
        generator = self._build_generator()

        class GenericFactory(ModelFactory[system_prompt.output_format]):
            pass

        format_str = GenericFactory().build().model_dump_json()
        
        results = generator(
            prompt_kwargs={
                "_template": system_prompt.build(**prompt_kwargs), 
                "_user_query": user_query,
                "_output_format_str": format_str,
            } | prompt_kwargs
        )

        # try:
        response = system_prompt.output_format(**from_json(results.raw_response))
        self._log("Successfully parsed response")
        return response
        # except Exception as e:
        #     self._log(f"Error parsing response: {str(e)}")
        #     raise LLMResponseError(
        #         "Failed to parse LLM response",
        #         raw_response=results.raw_response,
        #         expected_format=str(system_prompt.output_format.model_json_schema())
        #     )

    def fcall(
        self,
        user_query: str,
        system_prompt: Prompt,
        tool_manager: Optional[ToolManager] = None,
        prompt_kwargs: dict = {},
    ) -> Any:
        """Execute function call with optional tool management.

        Args:
            user_query: The user's query
            system_prompt: The system prompt to use
            tool_manager: Optional tool manager for function execution
            prompt_kwargs: Additional prompt keyword arguments

        Returns:
            The response from the LLM, processed according to the output format
        """
        generator = self._build_generator()

        if tool_manager is None:
            return self._execute_direct_call(
                generator, system_prompt, user_query, []
            )
        try:    
            # Execute with tool management
            return self._execute_with_tools(
                generator,
                system_prompt,
                user_query,
                tool_manager,
                prompt_kwargs
            )
        except Exception as e:
            logger.error(f"Error in fcall: {str(e)}")
            raise e

    def _prepare_tool_prompt_kwargs(
        self, tool_manager: ToolManager, output_data_class: type
    ) -> dict:
        """Prepare prompt kwargs for tool-enabled calls.

        Args:
            tool_manager: The tool manager instance
            output_data_class: The output data class for formatting

        Returns:
            Dictionary of prompt kwargs
        """
        logger.info(f"Tool manager provided with {len(tool_manager.tools)} tools")
 
        class GenericFactory(ModelFactory[output_data_class]):
            pass

        format_str = GenericFactory().build().model_dump_json()

        return {"tools": tool_manager.yaml_definitions, "_output_format_str": format_str}

    def _format_query_with_results(self, query: str, tool_results: list) -> str:
        """Format query with tool call results.

        Args:
            query: The original query
            tool_results: List of tool execution results

        Returns:
            Formatted query string
        """
        if not tool_results:
            return query

        print("tool_results1", tool_results)
        logger.debug(f"Formatting query with {len(tool_results)} tool results")
        
        formatted_query = query + "\n\n<PREVIOUS_TOOL_RESULTS>\n"
        
        # Separate successful and failed results
        successful_results = [r for r in tool_results if not hasattr(r, 'error') or r.error is None]
        failed_results = [r for r in tool_results if hasattr(r, 'error') and r.error is not None]
        
        if successful_results:
            formatted_query += "The following tool calls have already been executed successfully. "
            formatted_query += "Use these results to provide your final response. Do not repeat these tool calls.\n\n"
            
            # Note: Tool results are truncated at 10000 chars to prevent context window overflow
            # while still allowing reasonably sized responses (e.g., lists of 20+ items)
            for i, result in enumerate(successful_results):
                output_str = str(result.output)
                print("output_str", output_str)
                print(f"Tool result {i+1}: {result.name}, output length: {len(output_str)}")
                if len(output_str) > 10000:
                    output_str = f"Output truncated: {output_str[:10000]}..."
                    logger.warning(f"Tool result {i+1} was truncated from {len(str(result.output))} to 10000 chars")
                formatted_query += f"Tool: {result.name}\n"
                formatted_query += f"Result: {output_str}\n"
                formatted_query += "---\n"
        
        if failed_results:
            formatted_query += "\n<TOOL_ERRORS>\n"
            formatted_query += "The following tool calls failed with errors. Please review the errors and retry with corrected parameters:\n\n"
            
            for i, result in enumerate(failed_results):
                formatted_query += f"Tool: {result.name}\n"
                formatted_query += f"Error: {result.error}\n"
                if hasattr(result, 'input') and result.input:
                    formatted_query += f"Original call: {result.input}\n"
                formatted_query += "---\n"
            
            formatted_query += "\nIMPORTANT: When retrying these failed tool calls, make sure to:\n"
            formatted_query += "1. Use kwargs for named parameters (e.g., {'query': 'value'} instead of positional arguments)\n"
            formatted_query += "2. Check the tool definition for required parameters\n"
            formatted_query += "3. Ensure parameter names match exactly what the tool expects\n"
            formatted_query += "</TOOL_ERRORS>\n"

        formatted_query += "</PREVIOUS_TOOL_RESULTS>\n\n"
        
        if successful_results and not failed_results:
            formatted_query += "Based on the above tool results, provide your final response."
        elif failed_results:
            formatted_query += "Please retry the failed tool calls with corrected parameters, then provide your final response."

        logger.debug(f"Final formatted query length: {len(formatted_query)} characters")
        return formatted_query

    def _execute_tool_calls(self, tool_calls: list, tool_manager: ToolManager) -> list:
        """Execute tool calls and return results.

        Args:
            tool_calls: List of tool call dictionaries
            tool_manager: Tool manager instance

        Returns:
            List of tool execution results
        """
        if not tool_calls:
            return []
        
        logger.debug(f"Processing {len(tool_calls)} tool calls")
        logger.info(f"[TOOL_EXECUTION] Processing {len(tool_calls)} tool calls")
        results = []

        for i, tool_call in enumerate(tool_calls):
            try:
                # Use from_dict to create Function object
                print("NICK===")
                print("tool_call", tool_call)
                
                # Normalize tool_call to ensure kwargs are properly separated
                normalized_tool_call = tool_call.copy()
                
                # If args contains a dict, move it to kwargs
                if 'args' in normalized_tool_call and isinstance(normalized_tool_call['args'], dict):
                    normalized_tool_call['kwargs'] = normalized_tool_call['args']
                    normalized_tool_call['args'] = ()
                
                tool = Function.from_dict(normalized_tool_call)
                logger.debug(f"Tool: {tool!r}")
                logger.info(f"[TOOL_EXECUTION] Tool {i+1}/{len(tool_calls)}: {tool.name} with args={tool.args}, kwargs={tool.kwargs}")
                
                # Execute tool using the manager
                tool_result = tool_manager.execute_func(tool)
                logger.info(f"[TOOL_EXECUTION] Tool {tool.name} completed successfully")
                
                # Log the actual result content
                if hasattr(tool_result, 'output'):
                    output_str = str(tool_result.output)
                    logger.info(f"[TOOL_EXECUTION] Tool {tool.name} output length: {len(output_str)} characters")
                    logger.debug(f"[TOOL_EXECUTION] Tool {tool.name} output preview: {output_str[:500]}...")
                    
                    # If it's a list, log the count
                    if isinstance(tool_result.output, list):
                        logger.info(f"[TOOL_EXECUTION] Tool {tool.name} returned a list with {len(tool_result.output)} items")
                        for idx, item in enumerate(tool_result.output[:5]):  # Log first 5 items
                            logger.debug(f"[TOOL_EXECUTION]   Item {idx+1}: {str(item)[:100]}...")

                results.append(tool_result)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error executing tool {tool_call.get('name', 'unknown')}: {error_msg}")
                
                # Check if it's a parameter error (signature mismatch, missing required params, etc)
                is_param_error = any(keyword in error_msg.lower() for keyword in [
                    'parameter', 'argument', 'signature', 'kwargs', 'missing', 
                    'required', 'unexpected', 'positional', 'keyword-only'
                ])
                
                # Create FunctionOutput with error information
                error_output = FunctionOutput(
                    name=tool_call.get('name', 'unknown'),
                    input=tool_call,
                    output=None,
                    error=error_msg
                )
                results.append(error_output)
                
                # If it's not a parameter error, we might want to raise it
                if not is_param_error:
                    logger.warning(f"Non-parameter error occurred: {error_msg}")
                    # Optionally raise for non-parameter errors
                    # raise ToolExecutionError(
                    #     "Failed to execute tool",
                    #     tool_name=tool_call.get('name', 'unknown'),
                    #     error=e
                    # )
        return results

    def _add_unique_results(self, all_results: list, new_results: list) -> list:
        """Add new unique results to the list of all results."""
        if not new_results:
            return all_results

        # Create a set of existing result identifiers for quick lookup
        existing_identifiers = {(r.name, str(r.output)) for r in all_results}

        for result in new_results:
            result_identifier = (result.name, str(result.output))
            if result_identifier not in existing_identifiers:
                all_results.append(result)
                existing_identifiers.add(result_identifier)

        return all_results

    def _should_continue_iteration(
        self, dataset: dict, response: Any, retry_count: int, max_retries: int
    ) -> bool:
        """Determine if another iteration is needed.

        Args:
            dataset: The dataset from the LLM response
            response: The processed response object
            retry_count: The current retry count
            max_retries: The maximum number of retries

        Returns:
            True if another iteration should be performed, False otherwise
        """
        # Check if we've reached the max retry limit
        if retry_count >= max_retries - 1:
            return False

        has_tool_calls = bool(dataset.get("tool_calls"))
        
        return has_tool_calls

    def _cleanup_accumulated_results(self, results: list) -> list:
        """Clean up accumulated results to prevent memory growth."""
        if len(results) > self._result_cleanup_threshold:
            self._log(
                f"Cleaning up results: {len(results)} -> {self._max_accumulated_results}"
            )
            # Keep only the most recent results
            return results[-self._max_accumulated_results :]
        return results



    def _execute_with_tools(
        self,
        generator: Generator,
        system_prompt: Prompt,
        user_query: str,
        tool_manager: ToolManager,
        prompt_kwargs: dict = {}
    ) -> Any:
        """Execute query with tool management support.

        Optimized version with:
        - Exponential backoff for retries
        - Memory management for accumulated results
        - Early exit on successful responses

        Args:
            generator: The generator instance
            system_prompt: System prompt
            user_query: User query
            tool_manager: Tool manager instance
            prompt_kwargs: Additional prompt kwargs
            output_data_class: Output data class

        Returns:
            Processed response
        """
        # Check cache first
        cache_key = f"{user_query}:{orjson.dumps(prompt_kwargs)}"
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response

        # Prepare tool-specific prompt kwargs
        tool_prompt_kwargs = self._prepare_tool_prompt_kwargs(
            tool_manager, system_prompt.output_format
        )

        # Initialize iteration state
        max_retries = LLM_MAX_RETRIES
        retry_count = 0
        all_tool_call_results = []
        current_query = user_query
        last_error = None

        # Track whether we've made progress to avoid redundant retries
        last_successful_tool_count = 0
        previous_tool_calls = []

        while retry_count < max_retries:
            self._log(f"Iteration {retry_count + 1} of {max_retries}")
            logger.info(f"[LLM_RETRY] Starting iteration {retry_count + 1} of {max_retries}")

            # Apply exponential backoff for retries
            if retry_count > 0:
                import time

                backoff_delay = RETRY_BACKOFF_FACTOR**retry_count
                actual_delay = min(backoff_delay, RETRY_MAX_BACKOFF)
                self._log(f"Applying backoff delay: {actual_delay}s")
                time.sleep(actual_delay)

            # Clean up accumulated results if needed
            all_tool_call_results = self._cleanup_accumulated_results(
                all_tool_call_results
            )
            
            # Format query with previous results
            formatted_query = self._format_query_with_results(
                current_query, all_tool_call_results
            )
            
            # Make LLM call
            try:
                logger.info(f"[LLM_RETRY] Making LLM call with {len(all_tool_call_results)} previous tool results")
                results = generator(
                    prompt_kwargs={
                        "_template": system_prompt.build(),
                        "_user_query": formatted_query,
                    }
                    | tool_prompt_kwargs | prompt_kwargs
                )
                dataset = orjson.loads(results.data)
                logger.debug(f"[LLM_RETRY] LLM response: {dataset}")

            except Exception as e:
                logger.error(f"Error making LLM call: {str(e)}")
                retry_count += 1
                continue


            # Process tool calls
            try:
                current_tool_calls = dataset.get("tool_calls", [])
                
                # Check if we're repeating the same tool calls
                if current_tool_calls == previous_tool_calls and retry_count > 0:
                    self._log("LLM is repeating the same tool calls. Breaking loop.")
                    logger.info(f"[LLM_RETRY] Duplicate tool calls detected: {current_tool_calls}")
                    logger.info(f"[LLM_RETRY] Dataset keys: {list(dataset.keys())}")
                    logger.info(f"[LLM_RETRY] Has response field: {'response' in dataset}")
                    
                    # Check if the LLM provided a final response
                    if "response" in dataset:
                        self._log("LLM provided final response with duplicates. Returning response.")
                        logger.info(f"[LLM_RETRY] Returning final response: {dataset.get('response', 'N/A')}")
                        final_response = system_prompt.output_format(**dataset)
                        self._cache_response(cache_key, final_response)
                        return final_response
                    # Otherwise, break to make final direct call
                    self._log("No response in duplicate detection. Breaking to make final direct call.")
                    logger.info(f"[LLM_RETRY] Breaking loop - no response field in dataset")
                    break
                
                # Check if LLM provided a final response without tool calls (early termination)
                if "response" in dataset and not current_tool_calls:
                    self._log("LLM provided final response without tool calls. Returning response.")
                    final_response = system_prompt.output_format(**dataset)
                    self._cache_response(cache_key, final_response)
                    return final_response
                
                previous_tool_calls = current_tool_calls
                new_results = self._execute_tool_calls(current_tool_calls, tool_manager)
                
                # Check if any of the new results are errors
                has_errors = any(hasattr(r, 'error') and r.error is not None for r in new_results)
                if has_errors:
                    logger.info(f"[LLM_RETRY] Tool execution resulted in errors, will retry")
                    # Add error results to accumulated results so LLM can see them
                    all_tool_call_results = self._add_unique_results(all_tool_call_results, new_results)
                    retry_count += 1
                    continue  # Continue the retry loop
                    
            except ToolExecutionError:
                raise  # Re-raise tool execution errors immediately

            # If there are no new tool calls to execute, we are done.
            if not new_results and not current_tool_calls:
                self._log("No new tool calls to execute. Finalizing.")
                # We can return the 'response' field from the last LLM call
                final_response = system_prompt.output_format(**dataset)
                self._cache_response(cache_key, final_response)
                return final_response

            # Check if we're making progress (only count successful results)
            successful_new_results = [r for r in new_results if not hasattr(r, 'error') or r.error is None]
            current_tool_count = len([r for r in all_tool_call_results if not hasattr(r, 'error') or r.error is None]) + len(successful_new_results)
            
            if current_tool_count == last_successful_tool_count and retry_count > 0:
                self._log("No progress made in tool execution, considering early exit")
                logger.info(f"[LLM_RETRY] No progress made - tool count remains at {current_tool_count}")
                # If we're not making progress and have tried at least once,
                # check if the LLM provided a final response
                if "response" in dataset:
                    self._log("LLM provided final response despite tool calls. Returning response.")
                    final_response = system_prompt.output_format(**dataset)
                    self._cache_response(cache_key, final_response)
                    return final_response
                # Otherwise, force a final direct call
                break
                    
            last_successful_tool_count = current_tool_count
            all_tool_call_results = self._add_unique_results(all_tool_call_results, new_results)
            
            retry_count += 1

        # Otherwise, make a final direct call
        self._log(f"Exhausted retries ({retry_count}), making final direct call")
        
        final_response = self._execute_direct_call(
            generator, system_prompt, user_query, all_tool_call_results
        )
        self._cache_response(cache_key, final_response)
        return final_response

    def _execute_direct_call(
        self,
        generator: Generator,
        system_prompt: Prompt,
        user_query: str,
        tool_results: List[FunctionOutput],
    ) -> Any:
        """Execute a direct call without tool iteration.

        Args:
            generator: The generator instance
            system_prompt: System prompt
            user_query: User query
            tool_results: Any tool results to include

        Returns:
            Processed response
        """
        logger.info("Making direct call without tool manager")

        formatted_query = f"""User query:
{user_query}"""

        # Separate successful and failed results
        successful_results = [r for r in tool_results if not hasattr(r, 'error') or r.error is None]
        failed_results = [r for r in tool_results if hasattr(r, 'error') and r.error is not None]
        
        if successful_results:
            tool_results_json = [
                {
                    "name": x.name,
                    "output": x.output
                }
                for x in successful_results
            ]
            
            formatted_query += f"""
                
Successful tool calls:
{json.dumps(tool_results_json)}"""
        
        if failed_results:
            error_results_json = [
                {
                    "name": x.name,
                    "error": x.error,
                    "input": x.input if hasattr(x, 'input') else None
                }
                for x in failed_results
            ]
            
            formatted_query += f"""

Failed tool calls (with errors):
{json.dumps(error_results_json)}

Note: Some tool calls failed due to parameter errors. Please provide the best response you can based on the successful results, or explain what went wrong if all tools failed."""
        
        class GenericFactory(ModelFactory[system_prompt.output_format]):
            pass

        format_str = GenericFactory().build().model_dump_json()

        results = generator(
            prompt_kwargs={
                "_template": system_prompt.build(),
                "_user_query": formatted_query,
                "_output_format_str": format_str,
            }
        )

        # try:
        response = system_prompt.output_format(**json.loads(results.data))
        self._log("Successfully processed response")
        return response
        # except Exception as e:
        #     self._log(f"Error processing response: {str(e)}")
        #     raise LLMResponseError(
        #         "Failed to parse direct call response",
        #         raw_response=results.data,
        #         expected_format=str(system_prompt.output_format.model_json_schema())
        #     )

    def _get_cached_response(self, key: str) -> Optional[Any]:
        """Get response from cache if not expired."""
        if key in self._response_cache:
            response, timestamp = self._response_cache[key]
            if datetime.now() - timestamp < self._cache_ttl:
                self._log(f"Cache hit for key: {key}")
                return response
            else:
                self._log(f"Cache expired for key: {key}")
                del self._response_cache[key]
        return None

    def _cache_response(self, key: str, response: Any) -> None:
        """Cache a response with a timestamp."""
        self._log(f"Caching response for key: {key}")
        self._response_cache[key] = (response, datetime.now())
