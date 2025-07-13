import logging
import requests
import json

logger = logging.getLogger(__name__)

class AIEthicsTools:
    @staticmethod
    def research_ethics_topic(query: str, max_results: int = 20) -> dict:
        """
        Research an AI ethics topic using Perplexity AI.

        Args:
            query (str): The search query.
            max_results (int): Max results.

        Returns:
            dict: Research findings.
        """
        import os
        api_key = os.getenv('PERPLEXITY_API_KEY')
        if not api_key:
            return 'Error: PERPLEXITY_API_KEY not set.'
        url = 'https://api.perplexity.ai/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        data = {
            'model': 'sonar-pro',
            'messages': [
                {'role': 'user', 'content': f"Provide in-depth analysis on AI ethics for: {query}. Cover bias detection, regulatory compliance, privacy concerns, and governance frameworks."}
            ],
            'max_tokens': 1024
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            return {"content": content}
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return f"Error: {str(e)}" 