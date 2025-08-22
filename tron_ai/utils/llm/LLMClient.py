# Standard library imports
from typing import Optional, Any, TYPE_CHECKING, List
import logging
import pprint
from datetime import datetime, timedelta
import ast

# Third-party imports
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

# Import Component at module level since it's needed for inheritance
from adalflow import Component

# Local imports (keep lightweight ones at module level)
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
    from adalflow import Generator, ModelClient, OpenAIClient
    from adalflow.core.tool_manager import ToolManager
    from adalflow.core.types import Function, FunctionOutput
    import pydantic
    from pydantic_core import from_json
    from polyfactory.factories.pydantic_factory import ModelFactory
    import orjson

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
        - Return your output as a single JSON object matching the format above.
        - If generating tool calls, include 'tool_calls' as a list of objects, each with 'name', 'args', and 'kwargs'.
        - If you have sufficient information to provide a final response, include only the 'response' field and omit 'tool_calls'
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
    def __init__(self, client: 'ModelClient', config: LLMClientConfig, *args, **kwargs):
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
    def api_client(self):
        return self._client

    @property
    def model(self) -> str:
        return self._config.model_name

    def _build_generator(
        self,
        prompt: str = BASE_PROMPT,
        output_processors=None,
        override_json_format: bool = None,
    ):
        # Lazy import Generator
        from adalflow import Generator
        
        if hasattr(self._config, 'json_output'):
            json_output = self._config.json_output
        else:
            json_output = False

        model_kwargs = self._config.build_model_kwargs()
        
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

    def _generate_format_string(self, output_format_class: type) -> str:
        """Generate format string for output formatting.
        
        Args:
            output_format_class: The output format class to generate format for
            
        Returns:
            JSON string representation of the format
        """
        # Lazy import
        from polyfactory.factories.pydantic_factory import ModelFactory
        
        class GenericFactory(ModelFactory[output_format_class]):
            pass

        return GenericFactory().build().model_dump_json()

    def _generate_example_format_string(self, output_format_class: type) -> str:
        """Generate example format string for output formatting.
        
        Args:
            output_format_class: The output format class to generate format for
            
        Returns:
            Example format string
        """
        return output_format_class().generated_example()

    def _process_llm_response(self, results, output_format_class: type) -> Any:
        """Process LLM response and convert to output format.
        
        Args:
            results: Raw results from generator
            output_format_class: Expected output format class
            
        Returns:
            Processed response in the expected format
        """
        # Lazy import
        from pydantic_core import from_json
        
        dataset = from_json(results.raw_response)
        
        # Handle list responses
        if isinstance(dataset, list):
            if len(dataset) == 1:
                dataset = dataset[0]
            else:
                logger.warning(f"LLM returned list of {len(dataset)} items; taking first")
                dataset = dataset[0]
        
        return output_format_class(**dataset)

    def _ensure_tool_calls_field(self, response: Any) -> Any:
        """Ensure tool_calls field is present if the model supports it.
        
        Args:
            response: The response object to check
            
        Returns:
            Response with tool_calls field ensured
        """
        if self._supports_tool_calls(response):
            if not hasattr(response, 'tool_calls') or response.tool_calls is None:
                response.tool_calls = []
        return response

    def _build_prompt_kwargs(
        self, 
        system_prompt: Prompt, 
        user_query: str, 
        format_str: str, 
        prompt_kwargs: dict = {}
    ) -> dict:
        """Build common prompt kwargs for LLM calls.
        
        Args:
            system_prompt: The system prompt to use
            user_query: The user query
            format_str: The output format string
            prompt_kwargs: Additional prompt kwargs
            
        Returns:
            Dictionary of prompt kwargs
        """
        return {
            "_template": system_prompt.build(**prompt_kwargs),
            "_user_query": user_query,
            "_output_format_str": format_str,
        } | prompt_kwargs

    def call(
        self, user_query: str, system_prompt: Prompt, prompt_kwargs: dict = {}
    ):
        """Make a simple LLM call without tool management.
        
        Args:
            user_query: The user's query
            system_prompt: The system prompt to use
            prompt_kwargs: Additional prompt keyword arguments
            
        Returns:
            The response from the LLM, processed according to the output format
        """
        self._log(f"Making API call with query: {user_query[:100]}...")
        
        generator = self._build_generator()
        format_str = self._generate_format_string(system_prompt.output_format)
        
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((Exception,)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        def _make_simple_llm_call():
            return generator(
                prompt_kwargs=self._build_prompt_kwargs(
                    system_prompt, user_query, format_str, prompt_kwargs
                )
            )
        
        try:
            results = _make_simple_llm_call()
        except Exception as e:
            logger.error(f"Simple LLM call failed after retries: {e}")
            raise

        response = self._process_llm_response(results, system_prompt.output_format)
        response = self._ensure_tool_calls_field(response)
        
        self._log("Successfully parsed response")
        return response

    def fcall(
        self,
        user_query: str,
        system_prompt: Prompt,
        tool_manager: Optional['ToolManager'] = None,
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
            result = self._execute_direct_call(
                generator, system_prompt, user_query, []
            )
            return self._ensure_tool_calls_field(result)
        
        # Execute with tool management
        return self._execute_with_tools(
            generator,
            system_prompt,
            user_query,
            tool_manager,
            prompt_kwargs
        )

    def _prepare_tool_prompt_kwargs(
        self, tool_manager: 'ToolManager', output_data_class: type
    ) -> dict:
        """Prepare prompt kwargs for tool-enabled calls.

        Args:
            tool_manager: The tool manager instance
            output_data_class: The output data class for formatting

        Returns:
            Dictionary of prompt kwargs
        """
        logger.info(f"Tool manager provided with {len(tool_manager.tools)} tools")
        format_str = self._generate_example_format_string(output_data_class)
        return {"tools": tool_manager.yaml_definitions, "_output_format_str": format_str}

    def _format_query_with_results(self, query: str, tool_results: list, previous_tool_calls: list = None) -> str:
        """Format query with tool call results and previous calls.

        Args:
            query: The original query
            tool_results: List of tool execution results
            previous_tool_calls: List of previous tool calls made

        Returns:
            Formatted query string
        """
        if not tool_results and not previous_tool_calls:
            return query

        logger.debug(f"Formatting query with {len(tool_results)} tool results and {len(previous_tool_calls) if previous_tool_calls else 0} previous calls")
        
        formatted_query = query + "\n\n<PREVIOUS_INTERACTION>\n"
        
        if previous_tool_calls:
            formatted_query += "You previously requested these tool calls:\n"
            formatted_query += json.dumps(previous_tool_calls, indent=2) + "\n\n"
        
        formatted_query += "<PREVIOUS_TOOL_RESULTS>\n"
        
        # Separate successful and failed results
        successful_results = [r for r in tool_results if not hasattr(r, 'error') or r.error is None]
        failed_results = [r for r in tool_results if hasattr(r, 'error') and r.error is not None]
        
        if successful_results:
            formatted_query += "The following tool calls have already been executed successfully. "
            formatted_query += "Use these results to provide your final response. Do not repeat these tool calls.\n\n"
            
            for i, result in enumerate(successful_results):
                output_str = str(result.output)
                
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

        formatted_query += "</PREVIOUS_TOOL_RESULTS>\n</PREVIOUS_INTERACTION>\n\n"
        
        if successful_results and not failed_results:
            formatted_query += "Based on the above tool results, provide your final response."
        elif failed_results:
            formatted_query += "Please retry the failed tool calls with corrected parameters if needed, or provide your final response based on available information."

        logger.debug(f"Final formatted query length: {len(formatted_query)} characters")
        return formatted_query

    def _execute_tool_calls(self, tool_calls: list, tool_manager: 'ToolManager') -> list:
        """Execute tool calls and return results.

        Args:
            tool_calls: List of tool call dictionaries
            tool_manager: Tool manager instance

        Returns:
            List of tool execution results
        """
        # Lazy imports
        from adalflow.core.types import Function, FunctionOutput
        
        if not tool_calls:
            return []
        
        logger.debug(f"Processing {len(tool_calls)} tool calls")
        logger.info(f"[TOOL_EXECUTION] Processing {len(tool_calls)} tool calls")
        results = []

        for i, tool_call in enumerate(tool_calls):
            # Normalize tool_call to ensure kwargs are properly separated
            if tool_call is None:
                continue
            if isinstance(tool_call, str):
                print('tool_call is str', tool_call)
                tool_call = json.loads(tool_call)
            normalized_tool_call = tool_call.copy()
            
            # If args contains a dict, move it to kwargs
            if 'args' in normalized_tool_call and isinstance(normalized_tool_call['args'], dict):
                normalized_tool_call['kwargs'] = normalized_tool_call['kwargs'] | normalized_tool_call['args']
                normalized_tool_call['args'] = []
                
            if not hasattr(normalized_tool_call, 'args'):
                normalized_tool_call['args'] = []
                
            tool = Function.from_dict(normalized_tool_call)
            logger.debug(f"Tool: {tool!r}")
            logger.info(f"[TOOL_EXECUTION] Tool {i+1}/{len(tool_calls)}: {tool.name} with args={tool.args}, kwargs={tool.kwargs}")
            
            # Execute tool using the manager
            try:
                tool_result = tool_manager.execute_func(tool)
            except Exception as e:
                tool_result = FunctionOutput(
                    name=tool.name,
                    input=tool,  # Store the original call
                    output=None,
                    error=str(e)
                )
                logger.error(f"Tool {tool.name} failed with exception: {str(e)}")

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

    def _supports_tool_calls(self, obj: Any) -> bool:
        """Check if a Pydantic model supports a 'tool_calls' field."""
        import pydantic
        return (
            isinstance(obj, pydantic.BaseModel) and
            'tool_calls' in obj.__class__.model_fields
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def _execute_with_tools(
        self,
        generator,
        system_prompt: Prompt,
        user_query: str,
        tool_manager: 'ToolManager',
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

        Returns:
            Processed response
        """
        # Lazy imports
        import orjson
        
        # Check cache first
        cache_key = f"{user_query}:{orjson.dumps(prompt_kwargs)}"
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return self._ensure_tool_calls_field(cached_response)

        # Prepare tool-specific prompt kwargs
        tool_prompt_kwargs = self._prepare_tool_prompt_kwargs(
            tool_manager, system_prompt.output_format
        )

        # Initialize iteration state
        max_iterations = 10  # Increased for better multi-turn support
        max_error_retries = LLM_MAX_RETRIES
        iteration = 0
        error_retries = 0
        all_tool_call_results = []
        previous_tool_calls = []
        last_successful_tool_count = 0

        while iteration < max_iterations:
            self._log(f"Iteration {iteration + 1} of {max_iterations}")
            logger.info(f"[LLM_ITERATION] Starting iteration {iteration + 1} of {max_iterations}")

            # Clean up accumulated results if needed
            all_tool_call_results = self._cleanup_accumulated_results(
                all_tool_call_results
            )
            
            # Format query with previous results and calls
            formatted_query = self._format_query_with_results(
                user_query, all_tool_call_results, previous_tool_calls
            )
            
            # Make LLM call with retry logic
            logger.info(f"[LLM_ITERATION] Making LLM call with {len(all_tool_call_results)} previous tool results")

            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type((Exception,)),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True
            )
            def _make_llm_call():
                return generator(
                    prompt_kwargs=self._build_prompt_kwargs(
                        system_prompt, formatted_query, tool_prompt_kwargs["_output_format_str"]
                    ) | tool_prompt_kwargs | prompt_kwargs
                )
            
            try:
                results = _make_llm_call()
            except Exception as e:
                logger.error(f"[LLM_ITERATION] LLM call failed after retries: {e}")
                raise
            print('results', results)
            if isinstance(results.data, str):
                try:
                    dataset = extract_json_from_string(results.data)
                except ValueError:
                    raise LLMResponseError(
                        "Failed to extract or parse JSON from LLM response",
                        raw_response=results.data,
                        expected_format="JSON object"
                    )
            else:
                dataset = results.data
                
            print('=== dataset ===')
            print('dataset', dataset    )
                
            if isinstance(dataset, list):
                if len(dataset) == 1:
                    dataset = dataset[0]
                else:
                    logger.warning(f"LLM returned list of {len(dataset)} items; taking first")
                    dataset = dataset[0]
            logger.debug(f"[LLM_ITERATION] LLM response: {dataset}")

            # Process tool calls
            current_tool_calls = dataset.get("tool_calls", [])
            
            # Check if we're repeating the same tool calls
            if current_tool_calls == previous_tool_calls and iteration > 0:
                self._log("LLM is repeating the same tool calls. Breaking loop.")
                logger.info(f"[LLM_ITERATION] Duplicate tool calls detected: {current_tool_calls}")
                logger.info(f"[LLM_ITERATION] Dataset keys: {list(dataset.keys())}")
                logger.info(f"[LLM_ITERATION] Has response field: {'response' in dataset}")
                
                # Check if the LLM provided a final response
                if "response" in dataset:
                    self._log("LLM provided final response with duplicates. Returning response.")
                    logger.info(f"[LLM_ITERATION] Returning final response: {dataset.get('response', 'N/A')}")
                    final_response = system_prompt.output_format(**dataset)
                    if self._supports_tool_calls(final_response):
                        final_response.tool_calls = self._build_tool_calls_list(all_tool_call_results)
                    self._cache_response(cache_key, final_response)
                    return final_response
                # Otherwise, break to make final direct call
                self._log("No response in duplicate detection. Breaking to make final direct call.")
                logger.info(f"[LLM_ITERATION] Breaking loop - no response field in dataset")
                break
            
            # Check if LLM provided a final response without tool calls (early termination)
            if "response" in dataset and not current_tool_calls:
                self._log("LLM provided final response without tool calls. Returning response.")
                final_response = system_prompt.output_format(**dataset)
                if self._supports_tool_calls(final_response):
                    final_response.tool_calls = self._build_tool_calls_list(all_tool_call_results)
                self._cache_response(cache_key, final_response)
                return final_response
            
            previous_tool_calls = current_tool_calls
            new_results = self._execute_tool_calls(current_tool_calls, tool_manager)
            
            # Check if any of the new results are errors
            has_errors = any(hasattr(r, 'error') and r.error is not None for r in new_results)
            if has_errors:
                logger.info("[LLM_ITERATION] Tool execution resulted in errors, will retry with backoff")
                # Apply backoff only on errors
                import time
                backoff_delay = RETRY_BACKOFF_FACTOR ** error_retries
                actual_delay = min(backoff_delay, RETRY_MAX_BACKOFF)
                self._log(f"Applying backoff delay for error retry: {actual_delay}s")
                time.sleep(actual_delay)
                
                # Add error results so LLM can see them
                all_tool_call_results = self._add_unique_results(all_tool_call_results, new_results)
                error_retries += 1
                if error_retries >= max_error_retries:
                    self._log(f"Exhausted error retries ({error_retries}), proceeding to final call")
                    break
                # Don't increment iteration for error retries
                continue

            # Reset error retries on successful execution
            error_retries = 0

            # If no tool calls were made, we're done
            if not current_tool_calls:
                self._log("No tool calls in response. Finalizing.")
                final_response = system_prompt.output_format(**dataset)
                if self._supports_tool_calls(final_response):
                    final_response.tool_calls = self._build_tool_calls_list(all_tool_call_results)
                self._cache_response(cache_key, final_response)
                return final_response

            # Check progress
            successful_new_results = [r for r in new_results if not hasattr(r, 'error') or r.error is None]
            current_tool_count = len([r for r in all_tool_call_results if not hasattr(r, 'error') or r.error is None]) + len(successful_new_results)
            
            if current_tool_count == last_successful_tool_count and iteration > 0:
                self._log("No progress made in tool execution, considering early exit")
                logger.info(f"[LLM_ITERATION] No progress made - tool count remains at {current_tool_count}")
                if "response" in dataset:
                    self._log("LLM provided final response despite tool calls. Returning response.")
                    final_response = system_prompt.output_format(**dataset)
                    if self._supports_tool_calls(final_response):
                        final_response.tool_calls = self._build_tool_calls_list(all_tool_call_results)
                    self._cache_response(cache_key, final_response)
                    return final_response
                break
                    
            last_successful_tool_count = current_tool_count
            all_tool_call_results = self._add_unique_results(all_tool_call_results, new_results)
            
            iteration += 1

        # If loop exited without returning, make final direct call
        self._log(f"Reached max iterations ({iteration}), making final direct call")
        
        final_response = self._execute_direct_call(
            generator, system_prompt, user_query, all_tool_call_results
        )
        if self._supports_tool_calls(final_response):
            final_response.tool_calls = self._build_tool_calls_list(all_tool_call_results)
        self._cache_response(cache_key, final_response)
        return final_response

    def _execute_direct_call(
        self,
        generator,
        system_prompt: Prompt,
        user_query: str,
        tool_results: List,
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

        format_str = self._generate_example_format_string(system_prompt.output_format)
        
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((Exception,)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        def _make_direct_llm_call():
            return generator(
                prompt_kwargs=self._build_prompt_kwargs(
                    system_prompt, formatted_query, format_str
                )
            )
        
        try:
            results = _make_direct_llm_call()
        except Exception as e:
            logger.error(f"Direct LLM call failed after retries: {e}")
            raise
        
        response = self._process_llm_response(results, system_prompt.output_format)
        self._log("Successfully processed response")
        
        if self._supports_tool_calls(response):
            response.tool_calls = self._build_tool_calls_list(tool_results)
        
        return response

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
        """Cache the response with a TTL."""
        self._response_cache[key] = (response, datetime.now())

    def _build_tool_calls_list(self, results: list) -> list:
        """Helper to build tool_calls list from results."""
        tool_calls = []
        for r in results:
            entry = {
                "name": getattr(r, 'name', None),
                "args": getattr(r, 'args', None),
                "kwargs": getattr(r, 'kwargs', None),
                "error": getattr(r, 'error', None)
            }
            if hasattr(r, 'tool_calls'):
                entry["tool_calls"] = getattr(r, 'tool_calls')
            else:
                entry["output"] = getattr(r, 'output', None)
            tool_calls.append(entry)
        return tool_calls


def get_llm_client(
    model_name: str = "gpt-5",
    model_kwargs: dict = {},
    json_output: bool = False,
    logging: bool = False,
    client: Optional['ModelClient'] = None,
) -> "LLMClient":
    """
    Factory function to get an LLMClient instance.

    Args:
        model_name (str, optional): The model name to use. Defaults to "gpt-4o".
        json_output (bool, optional): Whether to expect JSON output. Defaults to False.
        logging (bool, optional): Whether to enable logging. Defaults to False.
        client (Optional[ModelClient], optional): An existing ModelClient instance.
                                                   If None, a new OpenAIClient will be created.
                                                   Defaults to None.

    Returns:
        LLMClient: An instance of the LLM client.
    """
    # Lazy import OpenAIClient only when needed
    if client is None:
        from adalflow import OpenAIClient
        client = OpenAIClient()

    config = LLMClientConfig(
        model_name=model_name, json_output=json_output, logging=logging
    )

    return LLMClient(client=client, config=config)

def get_llm_client_from_config(config: LLMClientConfig, client: Optional['ModelClient'] = None, client_name: str = "openai") -> "LLMClient":
    # Lazy import OpenAIClient only when needed
    if client is None:
        from adalflow import OpenAIClient
        from adalflow import GroqAPIClient
        if client_name == "groq":
            client = GroqAPIClient()
        else:
            client = OpenAIClient()
        
    """Get an LLMClient instance from a config."""
    return LLMClient(client=client, config=config)

def extract_json_from_string(s: str) -> dict:
    pos = s.find('{')
    if pos == -1:
        raise ValueError("No JSON object found")
    level = 1
    for j in range(pos + 1, len(s)):
        if s[j] == '{':
            level += 1
        elif s[j] == '}':
            level -= 1
            if level == 0:
                return json.loads(s[pos:j+1])
    raise ValueError("No valid JSON object found")