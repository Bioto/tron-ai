import asyncio
import os
import requests
import json
import logging
from tron_ai.models.prompts import Prompt, PromptDefaultResponse
from tron_ai.utils.llm.LLMClient import get_llm_client_from_config, LLMClientConfig
from tron_ai.models.executors import ExecutorConfig
from tron_ai.utils.graph.graph import StateGraph
from tron_ai.flows._base import BaseFlow
from pydantic import BaseModel, Field
from typing import Any, Dict, List
from tron_ai.executors.completion import CompletionExecutor

logger = logging.getLogger(__name__)


class PostState(BaseModel):
    user_query: str = ""
    concept: str = ""
    
    title: str = ""
    content: str = ""
    meta_description: str = ""
    
    tags: List[str] = []
    keywords: List[str] = []
    banner_image: Dict = Field(default_factory=dict)
    
    finalized_content: str = ""
    research: str = ""
    
    

llm_client = None

def get_llm_client():
    global llm_client
    if llm_client is None:
        llm_client = get_llm_client_from_config(LLMClientConfig.build(model_name="gpt-4o", json_output=True))
    return llm_client


class WordpressGeneratePostTools:
    @staticmethod
    async def generate_concept(state: PostState) -> PostState:
        """Generate a concept for the blog post."""
        logger.info("🎯 Starting concept generation...")
        # Pull the user query from the state
        user_query = state.user_query
        logger.info(f"📝 User query: {user_query}")
        
        prompt = Prompt(
            text="""
            You are a professional content writer, specializing in taking a simple idea and generating a concept for a blog post. Return a single paragraph of text that captures the essence of the idea.
            """,
            output_format=PromptDefaultResponse
        )
        logger.info("🤖 Creating completion executor for concept generation...")
        executor = CompletionExecutor(config=ExecutorConfig(client=get_llm_client(), prompt=prompt))
        logger.info("📡 Executing concept generation prompt...")
        request = await executor.execute(
            f"""
            {user_query}
            """
        )
        
        state.concept = request.response
        logger.info(f"✅ Concept generated: {state.concept}")
    
        return state
    
    @staticmethod
    async def generate_title(state: PostState) -> PostState:
        """Generate a title for the blog post."""
        logger.info("📰 Starting title generation...")
        logger.info(f"💡 Using concept: {state.concept}")
        prompt = Prompt(
            text="""
            You are a professional content writer, specializing in taking a simple idea and generating a title for a blog post. Return only the title as a string without any quotes or formatting, nothing else.
            """,
            output_format=PromptDefaultResponse
        )
        logger.info("🤖 Creating completion executor for title generation...")
        executor = CompletionExecutor(config=ExecutorConfig(client=get_llm_client(), prompt=prompt))
        logger.info("📡 Executing title generation prompt...")
        request = await executor.execute(
            f"""
            {state.concept}
            """
        )
        
        state.title = request.response
        logger.info(f"✅ Title generated: {state.title}")
        
        # Return the state
        return state
    
    @staticmethod
    async def generate_keywords(state: PostState) -> PostState:
        """Generate SEO keywords for the blog post."""
        logger.info("🎯 Starting keywords generation...")
        logger.info(f"💡 Using concept: {state.concept}")
        logger.info(f"📰 Using title: {state.title}")
        logger.info(f"📄 Using content length: {len(state.content)} characters")
        
        prompt = Prompt(
            text="""
            You are an SEO specialist. Based on the concept, title, and content, generate 5-8 relevant SEO keywords that would help this blog post rank well in search engines. Return only the keywords as a comma-separated list, nothing else.
            """,
            output_format=PromptDefaultResponse
        )
        logger.info("🤖 Creating completion executor for keywords generation...")
        executor = CompletionExecutor(config=ExecutorConfig(client=get_llm_client(), prompt=prompt))
        logger.info("📡 Executing keywords generation prompt...")
        request = await executor.execute(
            f"""
            <concept>{state.concept}</concept>
            <title>{state.title}</title>
            <content>{state.content}</content>
            """
        )
        
        # Parse the comma-separated keywords into a list
        keywords_text = request.response.strip()
        logger.info(f"📝 Raw keywords response: {keywords_text}")
        state.keywords = [keyword.strip() for keyword in keywords_text.split(',') if keyword.strip()]
        logger.info(f"✅ Keywords generated: {state.keywords}")
        
        return state
    
    @staticmethod
    async def generate_tags(state: PostState) -> PostState:
        """Generate relevant tags for the blog post."""
        logger.info("🏷️ Starting tags generation...")
        logger.info(f"💡 Using concept: {state.concept}")
        logger.info(f"📰 Using title: {state.title}")
        logger.info(f"📄 Using content length: {len(state.content)} characters")
        logger.info(f"🎯 Using keywords: {state.keywords}")
        
        prompt = Prompt(
            text="""
            You are a content categorization expert. Based on the concept, title, content, and keywords, generate 3-5 relevant tags that would help categorize this blog post. Return only the tags as a comma-separated list, nothing else.
            """,
            output_format=PromptDefaultResponse
        )
        logger.info("🤖 Creating completion executor for tags generation...")
        executor = CompletionExecutor(config=ExecutorConfig(client=get_llm_client(), prompt=prompt))
        logger.info("📡 Executing tags generation prompt...")
        request = await executor.execute(
            f"""
            <concept>{state.concept}</concept>
            <title>{state.title}</title>
            <content>{state.content}</content>
            <keywords>{', '.join(state.keywords)}</keywords>
            """
        )
        
        # Parse the comma-separated tags into a list
        tags_text = request.response.strip()
        logger.info(f"📝 Raw tags response: {tags_text}")
        state.tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
        logger.info(f"✅ Tags generated: {state.tags}")
        
        return state
    
    @staticmethod
    async def generate_content(state: PostState) -> PostState:
        """Generate the content for the blog post."""
        logger.info("📄 Starting content generation...")
        logger.info(f"💡 Using concept: {state.concept}")
        logger.info(f"📰 Using title: {state.title}")
        logger.info(f"📝 Using user query: {state.user_query}")
        
        prompt = Prompt(
            text="""
            You are a professional content writer, specializing in taking a simple idea, a title, and a concept and generating a blog post. Return only the blog post content, nothing else. The content should be in HTML format. Do NOT include the title in the content - the title will be handled separately. Use the provided research as reference material.
            """,
            output_format=PromptDefaultResponse
        )
        logger.info("🤖 Creating completion executor for content generation...")
        executor = CompletionExecutor(config=ExecutorConfig(client=get_llm_client(), prompt=prompt))
        logger.info("📡 Executing content generation prompt...")
        request = await executor.execute(
            f"""
            Write a blog post about the following:
            <concept>{state.concept}</concept>
            <research>{state.research}</research>
            <title>{state.title}</title>
            <user_query>{state.user_query}</user_query>
            """
        )
        
        state.content = request.response
        logger.info(f"✅ Content generated: {len(state.content)} characters")
        return state
    
    @staticmethod
    async def generate_meta_description(state: PostState) -> PostState:
        """Generate a meta description for the blog post."""
        logger.info("📝 Starting meta description generation...")
        logger.info(f"💡 Using concept: {state.concept}")
        logger.info(f"📰 Using title: {state.title}")
        logger.info(f"📄 Using content length: {len(state.content)} characters")
        
        prompt = Prompt(
            text="""
            You are an SEO specialist. Based on the concept, title, and content, generate a compelling meta description (150-160 characters) that accurately summarizes the blog post and encourages clicks from search results. Return only the meta description, nothing else.
            """,
            output_format=PromptDefaultResponse
        )
        logger.info("🤖 Creating completion executor for meta description generation...")
        executor = CompletionExecutor(config=ExecutorConfig(client=get_llm_client(), prompt=prompt))
        logger.info("📡 Executing meta description generation prompt...")
        request = await executor.execute(
            f"""
            <concept>{state.concept}</concept>
            <title>{state.title}</title>
            <content>{state.content}</content>
            """
        )
        
        state.meta_description = request.response.strip()
        logger.info(f"✅ Meta description generated ({len(state.meta_description)} chars): {state.meta_description}")
        return state

    @staticmethod
    async def generate_banner_image(state: PostState) -> PostState:
        """Fetch a banner image from Pexels API based on the generated keywords."""
        logger.info("🖼️ Starting banner image generation...")
        
        # Check if we have keywords to search with
        if not state.keywords:
            logger.warning("❌ No keywords available for image search")
            state.banner_image = {"error": "No keywords available for image search"}
            return state
        
        logger.info("🔑 Checking Pexels API key...")
        api_key = os.getenv('PEXELS_API_KEY')
        if not api_key:
            logger.error("❌ PEXELS_API_KEY not set")
            state.banner_image = {"error": "PEXELS_API_KEY not set"}
            return state
        
        logger.info(f"✅ Pexels API key found: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else 'short'}")
        
        # Use the first few keywords as search query
        search_query = ' '.join(state.keywords[:3])  # Limit to first 3 keywords
        logger.info(f"🔍 Search query: '{search_query}'")
        
        url = 'https://api.pexels.com/v1/search'
        headers = {
            'Authorization': api_key,
        }
        params = {
            'query': search_query,
            'per_page': 5,  # Get 5 relevant images
            'orientation': 'landscape'  # Good for blog banners
        }
        
        logger.info(f"🌐 Making Pexels API request...")
        logger.debug(f"   URL: {url}")
        logger.debug(f"   Headers: {headers}")
        logger.debug(f"   Params: {params}")
        
        try:
            logger.info("📡 Sending HTTP request to Pexels...")
            response = requests.get(url, headers=headers, params=params)
            logger.info(f"📡 HTTP response status: {response.status_code}")
            
            response.raise_for_status()
            logger.info("✅ Pexels HTTP request successful")
            
            result = response.json()
            logger.info(f"📊 Pexels API response received: {len(str(result))} characters")
            
            if 'photos' in result and result['photos']:
                photos = result['photos']
                logger.info(f"📸 Found {len(photos)} photos")
                
                # Select the first image as the banner (most relevant)
                photo = photos[0]
                logger.info(f"🎯 Selected first photo: ID {photo.get('id', 'No ID')}")
                
                try:
                    banner_data = {
                        'id': photo['id'],
                        'photographer': photo['photographer'],
                        'photographer_url': photo['photographer_url'],
                        'url': photo['url'],
                        'src': {
                            'original': photo['src']['original'],
                            'large': photo['src']['large'],
                            'medium': photo['src']['medium'],
                            'small': photo['src']['small']
                        },
                        'alt': photo['alt'],
                        'search_query': search_query
                    }
                    state.banner_image = banner_data
                    logger.info(f"✅ Banner image selected successfully")
                    logger.info(f"🖼️ Image: {photo.get('alt', 'No alt')} by {photo.get('photographer', 'Unknown')}")
                    
                except KeyError as e:
                    logger.error(f"❌ Missing key in photo: {e}")
                    state.banner_image = {"error": f"Missing key in photo data: {e}"}
                except Exception as e:
                    logger.error(f"❌ Error processing photo: {str(e)}")
                    state.banner_image = {"error": f"Error processing photo: {str(e)}"}
            else:
                logger.warning(f"❌ No photos found in Pexels response")
                state.banner_image = {"error": "No photos found in Pexels API response"}
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HTTP request error: {str(e)}")
            state.banner_image = {"error": f"HTTP request failed - {str(e)}"}
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {str(e)}")
            state.banner_image = {"error": f"Invalid JSON response - {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Unexpected error during image fetching: {str(e)}")
            state.banner_image = {"error": f"Unexpected error - {str(e)}"}
        
        logger.debug(f"📊 Final banner image state: {state.banner_image}")
        return state

    @staticmethod
    async def generate_research(state: PostState) -> PostState:
        """Research the concept using Perplexity AI."""
        logger.info("🔍 Starting research phase...")
        logger.info(f"📋 Research concept: {state.concept}")
        
        api_key = os.getenv('PERPLEXITY_API_KEY')
        if not api_key:
            logger.error("❌ PERPLEXITY_API_KEY not set")
            state.research = "Error: PERPLEXITY_API_KEY not set."
            return state
        
        url = 'https://api.perplexity.ai/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        data = {
            'model': 'sonar-pro',
            'messages': [
                {'role': 'user', 'content': f"Research about the blog post concept: {state.concept}. Provide in-depth information, sources, and key points."}
            ],
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            state.research = result['choices'][0]['message']['content']
            logger.info(f"✅ Research completed: {len(state.research)} characters")
        except Exception as e:
            logger.error(f"❌ Error during research: {str(e)}")
            state.research = f"Error: {str(e)}"
        
        return state

    @staticmethod
    async def finalize_content(state: PostState) -> PostState:
        """Embed the banner image into the content and store in finalized_content."""
        logger.info("🎯 Starting content finalization...")
        
        # Check if we have content and banner image
        if not state.content:
            logger.warning("❌ No content available for finalization")
            state.finalized_content = ""
            return state
        
        if not state.banner_image or 'error' in state.banner_image:
            logger.warning("⚠️ No banner image available, using original content")
            state.finalized_content = state.content
            return state
        
        logger.info("✅ Content and banner image available for finalization")
        
        # Get the banner image URL (prefer large, fallback to original)
        image_url = None
        if 'src' in state.banner_image:
            src = state.banner_image['src']
            image_url = src.get('large') or src.get('original')
            logger.info(f"🔗 Selected image URL: {image_url}")
        
        if not image_url:
            logger.warning("⚠️ No suitable image URL found, using original content")
            state.finalized_content = state.content
            return state
        
        # Get image details
        alt_text = state.banner_image.get('alt', 'Blog post banner image')
        photographer = state.banner_image.get('photographer', 'Unknown')
        photographer_url = state.banner_image.get('photographer_url', '#')
        
        logger.info(f"📋 Image details:")
        logger.debug(f"   - Alt text: {alt_text}")
        logger.debug(f"   - Photographer: {photographer}")
        logger.debug(f"   - Photographer URL: {photographer_url}")
        
        # Create HTML image tag with attribution
        logger.info("🏗️ Creating HTML image tag...")
        image_html = f'''<div style="text-align: center; margin: 20px 0;">
    <img src="{image_url}" alt="{alt_text}" style="width: 100%; max-width: 100%; height: auto; border-radius: 8px;" />
    <p style="font-size: 12px; color: #666; margin-top: 8px;">
        Photo by <a href="{photographer_url}" target="_blank" rel="noopener">{photographer}</a> on Pexels
    </p>
</div>'''
        
        logger.info(f"✅ HTML image tag created: {len(image_html)} characters")
        
        # Combine banner image with content
        logger.info("📝 Combining banner image with content...")
        finalized_content = image_html + '\n\n' + state.content
        
        state.finalized_content = finalized_content
        
        logger.info(f"✅ Content finalized successfully")
        logger.debug(f"📊 Original content length: {len(state.content)} characters")
        logger.debug(f"📊 Finalized content length: {len(finalized_content)} characters")
        logger.debug(f"📊 Content change: +{len(finalized_content) - len(state.content)} characters")
        logger.info(f"🖼️ Banner image embedded: {alt_text} by {photographer}")
        
        return state

class WordpressGeneratePost(BaseFlow):
    def __init__(self):
        super().__init__(
            name = "WordpressGeneratePost",
            description = "Generate a blog post about the user's query"
        )
        
        self.graph = StateGraph[PostState]()
        self._add_nodes()
        self._add_edges()
        self.graph.set_entrypoint("generate_concept")
        self.graph.set_exit("finalize_content")
        
        self.state = PostState()
        
    def _add_nodes(self):
        self.graph.add_node("generate_concept", WordpressGeneratePostTools.generate_concept)
        self.graph.add_node("generate_title", WordpressGeneratePostTools.generate_title)
        self.graph.add_node("generate_content", WordpressGeneratePostTools.generate_content)
        self.graph.add_node("generate_meta_description", WordpressGeneratePostTools.generate_meta_description)
        self.graph.add_node("generate_keywords", WordpressGeneratePostTools.generate_keywords)
        self.graph.add_node("generate_tags", WordpressGeneratePostTools.generate_tags)
        self.graph.add_node("generate_banner_image", WordpressGeneratePostTools.generate_banner_image)
        self.graph.add_node("generate_research", WordpressGeneratePostTools.generate_research)
        self.graph.add_node("finalize_content", WordpressGeneratePostTools.finalize_content)
        
    def _add_edges(self):
        self.graph.add_edge("generate_concept", "generate_research")
        self.graph.add_edge("generate_research", "generate_title")
        self.graph.add_edge("generate_title", "generate_content")
        self.graph.add_edge("generate_content", "generate_meta_description")
        self.graph.add_edge("generate_meta_description", "generate_keywords")
        self.graph.add_edge("generate_keywords", "generate_tags")
        self.graph.add_edge("generate_tags", "generate_banner_image")
        self.graph.add_edge("generate_banner_image", "finalize_content")
        
        self.graph.set_entrypoint("generate_concept")
        self.graph.set_exit("finalize_content")
        
    async def execute(self, query: str, *args, **kwargs) -> Any:
        logger.info("🚀 Starting WordpressGeneratePost execution...")
        logger.info(f"\t📝 Query: {query}")
        logger.debug(f"\t🔧 Args: {args}")
        logger.debug(f"\t🔑 Kwargs: {kwargs}")
        
        self.state.user_query = query
        self.state = await self.graph.run(self.state)
        
        logger.debug("=== STATE ===")
        logger.debug(self.state)
        logger.debug("=== STATE ===")
        
        return {
            "title": self.state.title,
            "content": self.state.finalized_content,
            "meta_description": self.state.meta_description,
            "tags": self.state.tags,
            "keywords": self.state.keywords,
            "additional_instructions": '''
                When responding to the user, show them the title, meta description, tags, and keywords. If you do show them the content, make sure to show it in a code block, formatted in HTML.
            '''
        }
        
        
if __name__ == "__main__":
    import asyncio
    from tron_ai.config import setup_logging

    setup_logging()
    flow = WordpressGeneratePost()
    results = asyncio.run(flow.execute("generate a blog post about LLM's and prompting, aim for an article that will take ~3 minutes to read,"))
    print(results)