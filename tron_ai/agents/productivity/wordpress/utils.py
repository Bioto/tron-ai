# tron_ai/agents/productivity/wordpress/utils.py
import os
import requests
from requests.auth import HTTPBasicAuth
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class WordPressClient:
    """WordPress REST API client for content management."""
    
    def __init__(self, site_url: str = None, username: str = None, app_password: str = None):
        """Initialize WordPress client.
        
        Args:
            site_url: WordPress site URL (e.g., 'https://yoursite.com')
            username: WordPress username
            app_password: WordPress application password
        """
        self.site_url = site_url or os.getenv("WORDPRESS_SITE_URL")
        self.username = username or os.getenv("WORDPRESS_USERNAME")
        self.app_password = app_password or os.getenv("WORDPRESS_APP_PASSWORD")
        
        if not self.site_url:
            from tron_ai.models.agent import MissingEnvironmentVariable
            raise MissingEnvironmentVariable("WORDPRESS_SITE_URL")
        if not self.username:
            from tron_ai.models.agent import MissingEnvironmentVariable
            raise MissingEnvironmentVariable("WORDPRESS_USERNAME")
        if not self.app_password:
            from tron_ai.models.agent import MissingEnvironmentVariable
            raise MissingEnvironmentVariable("WORDPRESS_APP_PASSWORD")
        
        # Ensure site URL has proper format
        if not self.site_url.startswith(('http://', 'https://')):
            self.site_url = f"https://{self.site_url}"
        
        self.site_url = self.site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(self.username, self.app_password)
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test the WordPress API connection."""
        try:
            response = requests.get(f"{self.api_base}/users/me", auth=self.auth, timeout=10)
            response.raise_for_status()
            logger.info("WordPress API connection successful")
        except requests.exceptions.RequestException as e:
            logger.error(f"WordPress API connection failed: {e}")
            raise ConnectionError(f"Failed to connect to WordPress API: {e}")
    
    def make_request(self, method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
        """Make a request to the WordPress REST API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without /wp-json/wp/v2 prefix)
            data: Request data for POST/PUT requests
            params: Query parameters
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                auth=self.auth,
                json=data,
                params=params,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"WordPress API request failed: {method} {url} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    raise Exception(f"WordPress API error: {error_data.get('message', str(e))}")
                except ValueError:
                    raise Exception(f"WordPress API error: {e}")
            raise Exception(f"WordPress API request failed: {e}")

def get_wordpress_client() -> WordPressClient:
    """Get an authenticated WordPress client instance.
    
    Returns:
        WordPress client instance
        
    Raises:
        MissingEnvironmentVariable: If required environment variables are not set
        ConnectionError: If connection to WordPress fails
    """
    return WordPressClient()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    client = get_wordpress_client()
    print(client.make_request("GET", "categories"))
    print(client.make_request("GET", "posts"))
    print(client.make_request("GET", "posts/1"))