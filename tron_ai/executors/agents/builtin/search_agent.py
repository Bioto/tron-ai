# Third-party imports
from adalflow.core.func_tool import FunctionTool
from adalflow.core.tool_manager import ToolManager
import aiohttp
from typing import List
import asyncio

# Local imports
from tron_ai.executors.agents.models.agent import Agent
from tron_ai.prompts.models import Prompt
from tron_ai import config


def perplexity_config_exists() -> bool:
    return config.PERPLEXITY_API_KEY is not None and config.PERPLEXITY_MODEL is not None


# Search Tools
async def query_perplexity(
    query: str,
    api_key: str = config.PERPLEXITY_API_KEY,
    model: str = config.PERPLEXITY_MODEL,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 50,
) -> dict:
    """
    Queries the Perplexity API for search results.

    Args:
        query (str): Search query text
        api_key (str): Perplexity API key
        model (str): Model to use for the query
        max_tokens (int): Maximum tokens in response
        temperature (float): Response randomness (0-1)
        top_p (float): Nucleus sampling parameter
        top_k (int): Top k sampling parameter

    Returns:
        dict: Search results and metadata
    """
    if not perplexity_config_exists():
        return {"error": "Perplexity API key or model not configured"}

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": query}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "error": f"API request failed with status {response.status}",
                        "details": error_text,
                    }

                result = await response.json()
                return {
                    "success": True,
                    "response": result["choices"][0]["message"]["content"],
                    "model": result["model"],
                    "usage": result.get("usage", {}),
                    "metadata": {
                        "finish_reason": result["choices"][0].get("finish_reason"),
                        "created": result.get("created"),
                        "id": result.get("id"),
                    },
                }

    except Exception as e:
        return {"error": f"Failed to query Perplexity API: {str(e)}"}


async def search_with_context(
    query: str,
    context: str,
    api_key: str = config.PERPLEXITY_API_KEY,
    model: str = config.PERPLEXITY_MODEL,
) -> dict:
    """
    Performs a search query with additional context.

    Args:
        query (str): Search query text
        context (str): Additional context for the search
        api_key (str): Perplexity API key
        model (str): Model to use for the query

    Returns:
        dict: Search results with context
    """
    if not perplexity_config_exists():
        return {"error": "Perplexity API key or model not configured"}

    try:
        enhanced_query = f"Context: {context}\n\nQuery: {query}"
        return await query_perplexity(enhanced_query, api_key, model)
    except Exception as e:
        return {"error": f"Failed to perform contextual search: {str(e)}"}


async def batch_search(
    queries: List[str],
    api_key: str = config.PERPLEXITY_API_KEY,
    model: str = config.PERPLEXITY_MODEL,
    max_concurrent: int = 3,
) -> dict:
    """
    Performs multiple search queries in parallel.

    Kwargs:
        queries (List[str]): List of search queries

    Returns:
        dict: Combined search results
    """
    if not perplexity_config_exists():
        return {"error": "Perplexity API key or model not configured"}

    try:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_search(query: str) -> dict:
            async with semaphore:
                return await query_perplexity(query, api_key, model)

        tasks = [bounded_search(query) for query in queries]
        results = await asyncio.gather(*tasks)

        return {
            "success": True,
            "results": results,
            "summary": {
                "total_queries": len(queries),
                "successful_queries": sum(
                    1 for r in results if r.get("success", False)
                ),
                "failed_queries": sum(
                    1 for r in results if not r.get("success", False)
                ),
            },
        }
    except Exception as e:
        return {"error": f"Failed to perform batch search: {str(e)}"}


# Create tool manager with search tools
search_tools = ToolManager(
    tools=[
        FunctionTool(fn=query_perplexity),
        FunctionTool(fn=search_with_context),
        FunctionTool(fn=batch_search),
    ]
)


class SearchAgent(Agent):
    """Search operations agent using Perplexity API."""

    def __init__(self):
        super().__init__(
            name="Search Agent",
            description="Manages search operations using Perplexity API. Note: Can only effectively handle one search operation at a time - multiple concurrent operations will reduce accuracy of results.",
            prompt=Prompt(
                text="""You are a search operations expert.

Your responsibilities include:
1. Query Management
   - Process search queries
   - Handle API interactions
   - Manage response formatting
   - Optimize search results

2. Context Enhancement
   - Analyze search context
   - Enhance query relevance
   - Process additional information
   - Improve result accuracy

3. Batch Processing
   - Handle multiple queries
   - Manage concurrent searches
   - Optimize resource usage
   - Aggregate results

4. Error Handling
   - Handle API errors
   - Manage rate limits
   - Process timeout issues
   - Provide error reporting

5. Result Processing
   - Format search results
   - Extract key information
   - Organize responses
   - Generate summaries

6. Performance Optimization
   - Manage API usage
   - Handle request batching
   - Optimize response times
   - Monitor resource usage

Always follow these practices:
- Validate API credentials
- Handle rate limiting
- Implement error handling
- Optimize query performance
- Protect sensitive data
- Monitor API usage
- Maintain result quality"""
            ),
            tool_manager=search_tools,
            supports_multiple_operations=True,
        )
