import logging
import requests
from bs4 import BeautifulSoup
import json

logger = logging.getLogger(__name__)

class SalesTools:
    @staticmethod
    def research_prospect(query: str, max_results: int = 20) -> dict:
        """
        Research a sales prospect or topic using Perplexity AI for accurate, real-time information.

        Args:
            query (str): The search query for prospect research.
            max_results (int): Maximum number of results to process (though Perplexity returns a single response).

        Returns:
            str: Summarized research findings from Perplexity.
        """
        import os
        api_key = os.getenv('PERPLEXITY_API_KEY')
        if not api_key:
            return 'Error: PERPLEXITY_API_KEY not set in environment.'
        url = 'https://api.perplexity.ai/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        data = {
            'model': 'sonar-pro',
            'messages': [
                {'role': 'user', 'content': f"Provide an in-depth, professional analysis for consultative sales on the following: {query}. Focus on prospect's technical stack, challenges, industry context, pain points, and tailored solution recommendations."}   
            ],
            "reasoning_effort": "low",
            "max_tokens": 1024
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            citations = result.get('citations', [])
            search_results = result.get('search_results', [])
            content = result['choices'][0]['message']['content']
            
            return {
                "content": content,
            }
        except Exception as e:
            logger.error(f"Error in research_prospect with Perplexity: {str(e)}")
            return f"Error occurred: {str(e)}" 