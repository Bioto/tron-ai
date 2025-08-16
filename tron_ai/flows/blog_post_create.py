import asyncio
from typing import Any, Dict, List
from pydantic import BaseModel, Field
import os
import requests
import json
from datetime import datetime
from pathlib import Path
from tron_ai.utils.graph.graph import StateGraph
from tron_ai.utils.llm.LLMClient import get_llm_client
from tron_ai.executors.completion import CompletionExecutor
from tron_ai.models.executors import ExecutorConfig
from tron_ai.models.prompts import Prompt, PromptDefaultResponse
from tron_ai.agents.devops.editor.agent import CodeEditorAgent
from tron_ai.flows._base import BaseFlow


class BlogState(BaseModel):
    prompt: str
    concept: str = ""
    research: str = ""
    article_json: Dict = Field(default_factory=dict)
    corrected_json: Dict = Field(default_factory=dict)
    images: List[Dict] = Field(default_factory=list)
    selected_image: Dict = Field(default_factory=dict)


async def generate_concept(state: BlogState) -> BlogState:
    llm_client = get_llm_client(model_name="gpt-4o", json_output=False)
    prompt = Prompt(
        text="You are a helpful assistant that generates blog post concepts. Generate a compelling and specific blog post concept based on the user's request.",
        output_format=PromptDefaultResponse
    )
    executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt))
    response = await executor.execute(f"Based on the user prompt: {state.prompt}, come up with a new blog post concept.")
    state.concept = response.response.strip()
    return state


async def get_research(state: BlogState) -> BlogState:
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        print("PERPLEXITY_API_KEY not set")
        state.research = "Error: PERPLEXITY_API_KEY not set."
        return state
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    data = {
        'model': 'sonar-pro',
        'messages': [
            {'role': 'user', 'content': f"Research about the blog post concept: {state.concept}. Provide in-depth information, sources, and key points."}
        ],
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    print(result)
    state.research = result['choices'][0]['message']['content']
    return state


async def generate_article(state: BlogState) -> BlogState:
    from tron_ai.models.prompts import BasePromptResponse
    
    class ArticleResponse(BasePromptResponse):
        title: str
        content: str
        seo_keywords: List[str]

    llm_client = get_llm_client(model_name="gpt-4o", json_output=True)
    prompt = Prompt(
        text="You are a helpful assistant that generates WordPress blog posts in JSON format with fields: title (string), content (string), seo_keywords (list of strings). Create a comprehensive, well-structured blog post.",
        output_format=ArticleResponse
    )
    executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt))
    response = await executor.execute(f"Generate a blog post based on concept: {state.concept} and research: {state.research}")

    state.article_json = {
        "title": response.title,
        "content": response.content,
        "seo_keywords": response.seo_keywords
    }
    return state


async def review_article(state: BlogState) -> BlogState:
    llm_client = get_llm_client(model_name="gpt-4o", json_output=True)
    prompt = Prompt(
        text="You are a professional editor reviewing blog posts. Provide corrections and improvements while maintaining the original intent. Return a JSON object with fields: title (string), content (string, with edits applied), seo_keywords (list of strings, updated if needed).",
        output_format=PromptDefaultResponse
    )
    executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt))
    article_str = json.dumps(state.article_json)
    query = f"""Review this blog post content and provide corrections and improvements:
    {article_str}"""
    response = await executor.execute(query)
    try:
        state.corrected_json = json.loads(response.response)
    except json.JSONDecodeError:
        state.corrected_json = state.article_json  # fallback
    return state


async def fetch_images(state: BlogState) -> BlogState:
    """Fetch relevant images from Pexels API based on SEO keywords."""
    api_key = os.getenv('PEXELS_API_KEY')
    if not api_key:
        state.images = [{"error": "PEXELS_API_KEY not set"}]
        return state
    
    # Get keywords from the corrected article
    keywords = state.corrected_json.get('seo_keywords', [])
    if not keywords:
        state.images = [{"error": "No SEO keywords found for image search"}]
        return state
    
    # Use the first few keywords as search query
    search_query = ' '.join(keywords[:3])  # Limit to first 3 keywords
    
    url = 'https://api.pexels.com/v1/search'
    headers = {
        'Authorization': api_key,
    }
    params = {
        'query': search_query,
        'per_page': 5,  # Get 5 relevant images
        'orientation': 'landscape'  # Good for blog headers
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        result = response.json()
        
        # Extract relevant image information
        images = []
        for photo in result.get('photos', []):
            images.append({
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
                'alt': photo['alt']
            })
        
        state.images = images
        
    except Exception as e:
        state.images = [{"error": f"Failed to fetch images: {str(e)}"}]
    
    return state


async def select_best_image(state: BlogState) -> BlogState:
    """Use a judge LLM to select the best image for the article based on alt text and article content."""
    
    # Check if we have images to select from
    if not state.images or any('error' in img for img in state.images):
        state.selected_image = {"error": "No valid images available for selection"}
        return state
    
    # Prepare image options with alt text for the judge
    image_options = []
    for i, img in enumerate(state.images):
        if 'alt' in img and img['alt']:
            image_options.append({
                "index": i,
                "alt_text": img['alt'],
                "photographer": img.get('photographer', 'Unknown')
            })
    
    if not image_options:
        state.selected_image = {"error": "No images with alt text available"}
        return state
    
    # Create the judge prompt with article context
    from tron_ai.models.prompts import BasePromptResponse
    
    class ImageSelectionResponse(BasePromptResponse):
        selected_index: int
        reasoning: str
    
    llm_client = get_llm_client(model_name="gpt-4o", json_output=True)
    prompt = Prompt(
        text="""You are an expert image curator for blog posts. Your task is to select the most appropriate image for the given article based on the image alt descriptions and article content.

Consider:
1. Relevance to the article topic and content
2. How well the image complements the title and keywords
3. Visual appeal and professionalism for a blog post
4. Appropriateness for the target audience

Return the index of the best image and provide clear reasoning for your choice.""",
        output_format=ImageSelectionResponse
    )
    
    # Prepare the selection query
    article_info = f"""
Article Title: {state.corrected_json.get('title', 'N/A')}
SEO Keywords: {', '.join(state.corrected_json.get('seo_keywords', []))}
Article Content Preview: {state.corrected_json.get('content', '')[:500]}...

Available Images:
"""
    
    for option in image_options:
        article_info += f"Index {option['index']}: {option['alt_text']} (by {option['photographer']})\n"
    
    article_info += "\nSelect the index of the most appropriate image for this blog post."
    
    try:
        executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt))
        response = await executor.execute(article_info)
        
        selected_index = response.selected_index
        
        # Validate the selected index
        if 0 <= selected_index < len(state.images):
            state.selected_image = state.images[selected_index].copy()
            state.selected_image['selection_reasoning'] = response.reasoning
            print(f"✅ Selected image {selected_index}: {state.images[selected_index].get('alt', 'No alt text')}")
            print(f"💭 Reasoning: {response.reasoning}")
        else:
            # Fallback to first image if invalid index
            state.selected_image = state.images[0].copy()
            state.selected_image['selection_reasoning'] = "Fallback selection due to invalid index"
            print(f"⚠️ Invalid index selected, using first image as fallback")
            
    except Exception as e:
        # Fallback to first image on error
        state.selected_image = state.images[0].copy() if state.images else {}
        state.selected_image['selection_reasoning'] = f"Error in selection process: {str(e)}"
        print(f"❌ Error in image selection: {str(e)}, using first image as fallback")
    
    return state


async def update_content_with_image(state: BlogState) -> BlogState:
    """Update the article content to include the selected image as an HTML tag."""
    
    # Check if we have a selected image
    if not state.selected_image or 'error' in state.selected_image:
        print("⚠️ No selected image available, skipping content update")
        return state
    
    # Get the image URL (prefer large, fallback to original)
    image_url = None
    if 'src' in state.selected_image:
        src = state.selected_image['src']
        image_url = src.get('large') or src.get('original')
    
    if not image_url:
        print("⚠️ No suitable image URL found, skipping content update")
        return state
    
    # Get image details
    alt_text = state.selected_image.get('alt', 'Blog post image')
    photographer = state.selected_image.get('photographer', 'Unknown')
    photographer_url = state.selected_image.get('photographer_url', '#')
    
    # Create HTML image tag with attribution
    image_html = f'''<div style="text-align: center; margin: 20px 0;">
    <img src="{image_url}" alt="{alt_text}" style="width: 100%; max-width: 800px; height: auto; border-radius: 8px;" />
    <p style="font-size: 12px; color: #666; margin-top: 8px;">
        Photo by <a href="{photographer_url}" target="_blank" rel="noopener">{photographer}</a> on Pexels
    </p>
</div>'''
    
    # Update the corrected_json content with the image
    if 'content' in state.corrected_json:
        content = state.corrected_json['content']
        
        # Find a good place to insert the image (after first paragraph or at the beginning)
        # Look for the first </p> tag or insert at the beginning
        if '</p>' in content:
            # Insert after the first paragraph
            first_paragraph_end = content.find('</p>') + 4
            updated_content = (content[:first_paragraph_end] + '\n\n' + 
                             image_html + '\n\n' + content[first_paragraph_end:])
        else:
            # If no paragraph tags, insert at the beginning
            updated_content = image_html + '\n\n' + content
        
        state.corrected_json['content'] = updated_content
        
        print(f"✅ Updated article content with selected image")
        print(f"🖼️ Image: {alt_text} by {photographer}")
    else:
        print("⚠️ No content found in article to update")
    
    return state


async def store_blog_post(state: BlogState) -> BlogState:
    """Store the complete blog post data in the storage directory."""
    try:
        # Create storage directory path
        storage_dir = Path(__file__).parent / "storage"
        storage_dir.mkdir(exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"blog_post_{timestamp}.json"
        file_path = storage_dir / filename
        
        # Prepare the complete data payload
        blog_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "original_prompt": state.prompt,
                "concept": state.concept,
                "filename": filename
            },
            "article": state.corrected_json,
            "research": state.research,
            "images": state.images,
            "selected_image": state.selected_image
        }
        
        # Write to JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(blog_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Blog post stored successfully at: {file_path}")
        
    except Exception as e:
        print(f"❌ Error storing blog post: {str(e)}")
    
    return state


class BlogPostCreateFlow(BaseFlow):
    def __init__(self):
        super().__init__("Blog Post Create", "Create a blog post")

    async def execute(self, query: str, *args, **kwargs) -> Any:
        graph = StateGraph[BlogState]()
        graph.add_node("generate_concept", generate_concept)
        graph.add_node("get_research", get_research)
        graph.add_node("generate_article", generate_article)
        graph.add_node("review_article", review_article)
        graph.add_node("fetch_images", fetch_images)
        graph.add_node("select_best_image", select_best_image)
        graph.add_node("update_content_with_image", update_content_with_image)
        graph.add_node("store_blog_post", store_blog_post)
        graph.set_entrypoint("generate_concept")
        graph.add_edge("generate_concept", "get_research")
        graph.add_edge("get_research", "generate_article")
        graph.add_edge("generate_article", "review_article")
        graph.add_edge("review_article", "fetch_images")
        graph.add_edge("fetch_images", "select_best_image")
        graph.add_edge("select_best_image", "update_content_with_image")
        graph.add_edge("update_content_with_image", "store_blog_post")
        graph.add_edge("store_blog_post", "end")
        graph.set_exit("end")
        initial_state = BlogState(prompt=query)
        final_state = await graph.run(initial_state)
        
        # Print the complete result including images
        result = {
            "article": final_state.corrected_json,
            "images": final_state.images,
            "selected_image": final_state.selected_image
        }
        print(json.dumps(result, indent=2))
        return result
    
if __name__ == "__main__":
    flow = BlogPostCreateFlow()
    asyncio.run(flow.execute("Write a blog post about the benefits of using AI in marketing."))