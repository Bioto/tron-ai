# tron_ai/agents/notion/utils.py
import os
from notion_client import Client
import logging

logger = logging.getLogger(__name__)

def get_notion_client():
    """Get an authenticated Notion client instance.
    
    Returns:
        Notion client instance
        
    Raises:
        MissingEnvironmentVariable: If NOTION_API_TOKEN is not set
    """
    api_token = os.getenv("NOTION_API_TOKEN")
    if not api_token:
        from tron_ai.models.agent import MissingEnvironmentVariable
        raise MissingEnvironmentVariable("NOTION_API_TOKEN")
    
    return Client(auth=api_token)