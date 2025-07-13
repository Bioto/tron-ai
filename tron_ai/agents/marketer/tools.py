import logging
import requests
from bs4 import BeautifulSoup
import json

logger = logging.getLogger(__name__)

class MarketerTools:
    @staticmethod
    def research_topic(query: str, max_results: int = 20) -> dict:
        """
        Research a marketing topic using Perplexity AI for accurate, real-time information.

        Args:
            query (str): The search query for marketing research.
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
                {'role': 'user', 'content': f"Provide an in-depth, professional marketing analysis of the following topic: {query}. Use advanced marketing terminology and frameworks. Focus on strategic implications, market positioning, audience segmentation, and actionable insights."}   
            ],
            "reasoning_effort": "low",
            "max_tokens": 1024
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            citations = result['citations']
            search_results = result['search_results']
            content = result['choices'][0]['message']['content']
            
            return {
                "content": content,
            }
        except Exception as e:
            logger.error(f"Error in research_topic with Perplexity: {str(e)}")
            return f"Error occurred: {str(e)}"

    @staticmethod
    def generate_content_idea(topic: str, target_audience: str) -> str:
        """
        Generate a marketing content idea based on topic and audience.

        Args:
            topic (str): The main topic.
            target_audience (str): The target audience (e.g., 'C-level executives').

        Returns:
            str: Generated content idea.
        """
        # Placeholder: In a full implementation, this could call an LLM
        return f"Idea for {target_audience} on {topic}: Create a webinar titled 'Unlocking {topic} for Business Growth' with case studies and Q&A." 