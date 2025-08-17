import asyncio
from typing import Any, Dict, List
from pydantic import BaseModel, Field
import os
import requests
import json
from datetime import datetime
from pathlib import Path
from tron_ai.utils.graph.graph import StateGraph
from tron_ai.utils.llm.LLMClient import get_llm_client, get_llm_client_from_config
from tron_ai.executors.completion import CompletionExecutor
from tron_ai.models.executors import ExecutorConfig
from tron_ai.models.prompts import Prompt, PromptDefaultResponse
from tron_ai.flows._base import BaseFlow
from tron_ai.models.config import ChatGPT5HighConfig, ChatGPT5LowConfig, ChatGPT5MediumConfig, LLMClientConfig


class BlogState(BaseModel):
    prompt: str
    concept: str = ""
    research: str = ""
    article_json: Dict = Field(default_factory=dict)
    corrected_json: Dict = Field(default_factory=dict)
    images: List[Dict] = Field(default_factory=list)
    selected_image: Dict = Field(default_factory=dict)


async def generate_concept(state: BlogState) -> BlogState:
    print("💡 Starting concept generation...")
    print(f"📝 User prompt: {state.prompt}")
    
    print("🔑 Getting LLM client...")
    llm_client = get_llm_client_from_config(ChatGPT5LowConfig())
    print(f"✅ LLM client obtained: {type(llm_client).__name__}")
    
    print("📝 Creating prompt...")
    prompt = Prompt(
        text="You are a helpful assistant that generates blog post concepts. Generate a compelling and specific blog post concept based on the user's request. Do not provide a title, only reply with the concept.",
        output_format=PromptDefaultResponse
    )
    print(f"✅ Prompt created: {prompt}")
    
    print("⚙️ Creating executor...")
    executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt))
    print(f"✅ Executor created: {type(executor).__name__}")
    
    print(f"🤖 Executing concept generation for prompt: {state.prompt[:100]}...")
    try:
        response = await executor.execute(f"Based on the user prompt: {state.prompt}, come up with a new blog post concept.")
        print(f"📤 Raw response received: {response}")
        print(f"📤 Response type: {type(response)}")
        print(f"📤 Response attributes: {dir(response)}")
        
        state.concept = response.response.strip()
        print(f"✅ Concept generated and stored: {state.concept}")
        print(f"🔍 Concept length: {len(state.concept)} characters")
        
    except Exception as e:
        print(f"❌ Error during concept generation: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        state.concept = f"Error generating concept: {str(e)}"
    return state


async def get_research(state: BlogState) -> BlogState:
    print("🔍 Starting research phase...")
    print(f"📋 Research concept: {state.concept}")
    
    print("🔑 Checking environment variables...")
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        print("❌ PERPLEXITY_API_KEY not set")
        print("🔍 Available env vars: {list(os.environ.keys()) if len(os.environ) < 20 else 'Too many to list'}")
        state.research = "Error: PERPLEXITY_API_KEY not set."
        return state
    
    print(f"✅ Perplexity API key found: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else 'short'}")
    
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
    
    print(f"🌐 Making API request to Perplexity...")
    print(f"   URL: {url}")
    print(f"   Headers: {headers}")
    print(f"   Data: {data}")
    print(f"   Concept length: {len(state.concept)} characters")
    
    try:
        print("📡 Sending HTTP request...")
        response = requests.post(url, headers=headers, json=data)
        print(f"📡 HTTP response status: {response.status_code}")
        print(f"📡 HTTP response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        print("✅ HTTP request successful")
        
        result = response.json()
        print(f"📊 Perplexity API response received: {len(str(result))} characters")
        print(f"📊 Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if 'choices' in result and result['choices']:
            choice = result['choices'][0]
            print(f"📊 Choice keys: {list(choice.keys()) if isinstance(choice, dict) else 'Not a dict'}")
            
            if 'message' in choice and choice['message']:
                message = choice['message']
                print(f"📊 Message keys: {list(message.keys()) if isinstance(message, dict) else 'Not a dict'}")
                
                if 'content' in message:
                    state.research = message['content']
                    print(f"✅ Research completed: {len(state.research)} characters")
                    print(f"🔍 Research preview: {state.research[:200]}...")
                else:
                    print(f"❌ No 'content' in message: {message}")
                    state.research = f"Error: No content in API response - {message}"
            else:
                print(f"❌ No 'message' in choice: {choice}")
                state.research = f"Error: No message in API response - {choice}"
        else:
            print(f"❌ No 'choices' in response: {result}")
            state.research = f"Error: No choices in API response - {result}"
        
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP request error: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        state.research = f"Error: HTTP request failed - {str(e)}"
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {str(e)}")
        print(f"❌ Response text: {response.text[:500]}...")
        state.research = f"Error: Invalid JSON response - {str(e)}"
    except Exception as e:
        print(f"❌ Unexpected error during research: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        state.research = f"Error: Unexpected error - {str(e)}"

    return state


async def generate_title(state: BlogState) -> BlogState:
    """Generate a compelling blog post title."""
    print("🏷️ Starting title generation...")
    llm_client = get_llm_client_from_config(
        LLMClientConfig.build(model_name="gpt-4-turbo", json_output=True)
    )
    prompt = Prompt(
        text="""You are a professional copywriter specializing in blog post titles. 
Generate a compelling, SEO-friendly title that accurately represents the blog post content. 
The title should be engaging, clear, and optimized for search engines.

CRITICAL INSTRUCTION: Return ONLY the title text without any formatting, quotes, or JSON structure.
Do NOT include quotation marks, do NOT wrap in JSON, do NOT add any prefixes or suffixes.
Just return the plain title text exactly as it should appear on the blog post.

Example of correct response: How to Master Digital Marketing in 2024
Example of WRONG response: "How to Master Digital Marketing in 2024" or {"title": "How to Master Digital Marketing in 2024"}""",
        output_format=PromptDefaultResponse
    )
    executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt))
    print(f"📝 Generating title for concept: {state.concept}...")
    response = await executor.execute(f"Generate a compelling blog post title for this concept: {state.concept}")
    
    # Initialize article_json if it doesn't exist
    if not hasattr(state, 'article_json') or not state.article_json:
        state.article_json = {}
        
    state.article_json["title"] = response.response.strip()
    print(f"✅ Title generated: {state.article_json['title']}")
    return state


async def generate_content(state: BlogState) -> BlogState:
    """Generate the main blog post content."""
    print("📖 Starting content generation...")
    llm_client = get_llm_client_from_config(LLMClientConfig.build(model_name="gpt-4o", json_output=True))
    prompt = Prompt(
        text="""You are a professional content writer specializing in online blog posts. 
Generate comprehensive, well-structured blog post content using proper HTML formatting. 
The content should be engaging, informative, and properly formatted with HTML elements.

IMPORTANT: Return ONLY HTML content, NOT markdown. Use these HTML tags appropriately:
- <p> for paragraphs
- <h2>, <h3>, <h4> for section headings (do NOT use <h1>)
- <ul> and <li> for unordered lists
- <ol> and <li> for ordered lists
- <strong> for bold text
- <em> for emphasized text
- <blockquote> for quotes
- <a href=""> for links (when relevant)

Structure the content with clear sections and subsections. Make it scannable with appropriate headings.
Do not include the title in the content as it will be handled separately.
Format your response as pure HTML - do not use markdown syntax like #, *, or ```.
Return only the HTML content, nothing else.""",
        output_format=PromptDefaultResponse
    )
    executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt))
    print(f"📝 Generating content for title: {state.article_json.get('title', 'No title yet')}")
    response = await executor.execute(f"Generate blog post content based on concept: {state.concept} and research: {state.research}. Focus on creating valuable, engaging content that matches the title: {state.article_json.get('title', '')}")
    
    # Initialize article_json if it doesn't exist
    if not hasattr(state, 'article_json') or not state.article_json:
        state.article_json = {}
        
    state.article_json["content"] = response.response.strip()
    print(f"✅ Content generated: {len(state.article_json['content'])} characters")
    return state


async def generate_seo_tags(state: BlogState) -> BlogState:
    """Generate SEO tags for the blog post."""
    print("🔍 Starting SEO tags generation...")

    llm_client = get_llm_client_from_config(LLMClientConfig.build(model_name="gpt-4o", json_output=True))
    prompt = Prompt(
        text="""You are an expert SEO specialist with deep knowledge of search engine optimization and keyword research. 

Analyze the provided blog post and generate 5-8 highly relevant, strategically selected SEO tags that will maximize search visibility and organic traffic.

REQUIREMENTS:
- Focus on long-tail keywords (3-5 words) with high search intent and lower competition
- Include a mix of primary keywords, semantic variations, and related terms
- Consider both informational and commercial search intent
- Ensure tags are specific to the content topic and target audience
- Prioritize keywords that real users would actually search for

ANALYSIS CRITERIA:
- Search volume potential (favor moderate volume with lower competition)
- Content relevance and alignment
- User search behavior and intent
- Topic authority and expertise demonstration
- Geographic and demographic targeting where applicable

OUTPUT FORMAT:
Return exactly 5-8 comma-separated tags as a plain string. Do not use JSON formatting, quotation marks around individual tags, or any additional text.

EXAMPLE OUTPUT:
digital marketing automation tools, small business email campaigns, customer retention strategies, automated lead nurturing, marketing workflow optimization""",
        output_format=PromptDefaultResponse
    )
    executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt))
    print(f"📝 Generating SEO tags for title: {state.article_json.get('title', 'No title yet')}")
    response = await executor.execute(f"Generate SEO tags for this blog post. Title: {state.article_json.get('title', '')}, Content preview: {state.article_json.get('content', '')}...")

    # Initialize article_json if it doesn't exist
    if not hasattr(state, 'article_json') or not state.article_json:
        state.article_json = {}
        
    state.article_json["seo_tags"] = response.response
    print(f"✅ SEO tags generated: {state.article_json['seo_tags']}")
    return state


async def generate_article(state: BlogState) -> BlogState:
    """Generate article components in parallel."""    
    print("🏗️ Starting article generation workflow...")
    print(f"📊 Current article_json state: {state.article_json}")
    
    # Run title generation first, then content and SEO tags in parallel
    print("📝 Generating title first...")
    try:
        state = await generate_title(state)
        print(f"✅ Title generation completed")
        print(f"📊 Title: {state.article_json.get('title', 'No title')}")
    except Exception as e:
        print(f"❌ Error in title generation: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
    
    # Run content and SEO tags generation in parallel
    # Content needs the title, but SEO tags can use the concept and title
    print("🔄 Starting parallel generation of content and SEO tags...")
    
    print("📖 Generating content...")
    try:
        state = await generate_content(state)
        print(f"✅ Content generation completed")
        print(f"📊 Content length: {len(state.article_json.get('content', ''))} characters")
    except Exception as e:
        print(f"❌ Error in content generation: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
    
    print("🔍 Generating SEO tags...")
    try:
        state = await generate_seo_tags(state)
        print(f"✅ SEO tags generation completed")
        print(f"📊 SEO tags: {state.article_json.get('seo_tags', 'No tags')}")
    except Exception as e:
        print(f"❌ Error in SEO tags generation: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
    
    print("✅ Both content and SEO tags generation completed")
    
    print(f"📊 Final article state:")
    print(f"   - Title: {len(state.article_json.get('title', ''))} chars")
    print(f"   - Content: {len(state.article_json.get('content', ''))} chars")
    print(f"   - SEO tags: {state.article_json.get('seo_tags', [])}")
    print(f"   - Article JSON keys: {list(state.article_json.keys())}")

    return state


async def review_article(state: BlogState) -> BlogState:
    print("📝 Starting article review...")
    print(f"📊 Article JSON to review: {state.article_json}")
    
    print("🔑 Getting LLM client for review...")
    try:
        llm_client = get_llm_client_from_config(LLMClientConfig.build(model_name="gpt-4o", json_output=True))
        print(f"✅ LLM client obtained: {type(llm_client).__name__}")
    except Exception as e:
        print(f"❌ Error getting LLM client: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return state
    
    print("📝 Creating review prompt...")
    prompt = Prompt(
        text="""You are a professional editor reviewing blog posts. 
        Provide corrections and improvements while maintaining the original intent. 
        Return a JSON object with fields: title (string), content (string in basic HTML format with edits applied), 
        seo_tags (list of strings, updated if needed). 
        Do NOT return the title in the content. 
        dont wrap it in a json object""",
        output_format=PromptDefaultResponse
    )
    print(f"✅ Review prompt created: {prompt}")
    
    print("⚙️ Creating review executor...")
    try:
        executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt, ))
        print(f"✅ Review executor created: {type(executor).__name__}")
    except Exception as e:
        print(f"❌ Error creating executor: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return state
    
    print("📋 Preparing article for review...")
    article_str = json.dumps(state.article_json)
    print(f"📋 Article JSON string length: {len(article_str)} characters")
    print(f"📋 Article JSON preview: {article_str[:200]}...")
    
    query = f"""Review this blog post content and provide corrections and improvements:
    {article_str}"""
    print(f"📝 Review query length: {len(query)} characters")
    
    print("🤖 Executing article review...")
    try:
        response = await executor.execute(query)
        print(f"📤 Review response received: {response}")
        print(f"📤 Response type: {type(response)}")
        print(f"📤 Response attributes: {dir(response)}")
        
        if hasattr(response, 'response'):
            print(f"📤 Response content: {response.response}")
            print(f"📤 Response content type: {type(response.response)}")
            print(f"📤 Response content length: {len(str(response.response))} characters")
            
            try:
                print("🔍 Attempting to parse JSON response...")
                state.corrected_json = json.loads(response.response)
                print(f"✅ JSON parsing successful")
                print(f"📊 Corrected JSON keys: {list(state.corrected_json.keys())}")
                print(f"📊 Corrected title: {state.corrected_json.get('title', 'No title')}")
                print(f"📊 Corrected content length: {len(state.corrected_json.get('content', ''))} characters")
                print(f"📊 Corrected SEO tags: {state.corrected_json.get('seo_tags', [])}")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {str(e)}")
                print(f"❌ Raw response: {response.response}")
                print("🔄 Falling back to original article JSON")
                state.corrected_json = state.article_json.copy()
                
        else:
            print(f"❌ Response has no 'response' attribute")
            print(f"🔄 Falling back to original article JSON")
            state.corrected_json = state.article_json.copy()
            
    except Exception as e:
        print(f"❌ Error during article review: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        print("🔄 Falling back to original article JSON")
        state.corrected_json = state.article_json.copy()

    return state


async def fetch_images(state: BlogState) -> BlogState:
    """Fetch relevant images from Pexels API based on SEO tags."""
    print("🖼️ Starting image fetching...")
    print(f"📊 Corrected JSON state: {state.article_json}")
    
    print("🔑 Checking Pexels API key...")
    api_key = os.getenv('PEXELS_API_KEY')
    if not api_key:
        print("❌ PEXELS_API_KEY not set")
        print("🔍 Available env vars: {list(os.environ.keys()) if len(os.environ) < 20 else 'Too many to list'}")
        state.images = [{"error": "PEXELS_API_KEY not set"}]
        return state
    
    print(f"✅ Pexels API key found: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else 'short'}")
    
    # Get tags from the corrected article
    print("🏷️ Extracting SEO tags for image search...")
    tags = state.article_json.get('seo_tags', [])
    print(f"🏷️ Found tags: {tags}")
    
    if not tags:
        print("❌ No SEO tags found for image search")
        state.images = [{"error": "No SEO tags found for image search"}]
        return state
    
    # Use the first few tags as search query
    search_query = ' '.join(tags[:3])  # Limit to first 3 tags
    print(f"🔍 Search query: '{search_query}'")
    
    url = 'https://api.pexels.com/v1/search'
    headers = {
        'Authorization': api_key,
    }
    params = {
        'query': search_query,
        'per_page': 5,  # Get 5 relevant images
        'orientation': 'landscape'  # Good for blog headers
    }
    
    print(f"🌐 Making Pexels API request...")
    print(f"   URL: {url}")
    print(f"   Headers: {headers}")
    print(f"   Params: {params}")
    
    try:
        print("📡 Sending HTTP request to Pexels...")
        response = requests.get(url, headers=headers, params=params)
        print(f"📡 HTTP response status: {response.status_code}")
        print(f"📡 HTTP response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        print("✅ Pexels HTTP request successful")
        
        result = response.json()
        print(f"📊 Pexels API response received: {len(str(result))} characters")
        print(f"📊 Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if 'photos' in result:
            photos = result['photos']
            print(f"📸 Found {len(photos)} photos")
            
            # Extract relevant image information
            images = []
            for i, photo in enumerate(photos):
                print(f"📸 Processing photo {i+1}/{len(photos)}: ID {photo.get('id', 'No ID')}")
                
                try:
                    image_data = {
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
                    }
                    images.append(image_data)
                    print(f"✅ Photo {i+1} processed successfully")
                    
                except KeyError as e:
                    print(f"❌ Missing key in photo {i+1}: {e}")
                    print(f"❌ Photo data: {photo}")
                except Exception as e:
                    print(f"❌ Error processing photo {i+1}: {str(e)}")
            
            state.images = images
            print(f"✅ Successfully processed {len(images)} images")
            
        else:
            print(f"❌ No 'photos' in Pexels response: {result}")
            state.images = [{"error": "No photos in Pexels API response"}]
        
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP request error: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        state.images = [{"error": f"HTTP request failed - {str(e)}"}]
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {str(e)}")
        print(f"❌ Response text: {response.text[:500]}...")
        state.images = [{"error": f"Invalid JSON response - {str(e)}"}]
    except Exception as e:
        print(f"❌ Unexpected error during image fetching: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        state.images = [{"error": f"Unexpected error - {str(e)}"}]
    
    print(f"📊 Final images state: {len(state.images)} images")
    for i, img in enumerate(state.images):
        if 'error' in img:
            print(f"   Image {i}: Error - {img['error']}")
        else:
            print(f"   Image {i}: {img.get('alt', 'No alt')} by {img.get('photographer', 'Unknown')}")
    return state


async def select_best_image(state: BlogState) -> BlogState:
    """Use a judge LLM to select the best image for the article based on alt text and article content."""
    print("🎯 Starting image selection...")
    print(f"📊 Available images: {len(state.images)} images")
    
    # Check if we have images to select from
    if not state.images:
        print("❌ No images available for selection")
        state.selected_image = {"error": "No images available for selection"}
        return state
    
    print("Images:")
    print(state.images)
    
    # Check for errors in images
    error_images = [i for i, img in enumerate(state.images) if 'error' in img]
    if error_images:
        print(f"⚠️ Found {len(error_images)} images with errors: {error_images}")
        if len(error_images) == len(state.images):
            print("❌ All images have errors, cannot proceed with selection")
            state.selected_image = {"error": "All images have errors"}
            return state
    
    print("✅ Valid images found for selection")
    
    # Prepare image options with alt text for the judge
    print("📋 Preparing image options for LLM judge...")
    image_options = []
    for i, img in enumerate(state.images):
        if 'error' not in img:
            if 'alt' in img and img['alt']:
                image_options.append({
                    "index": i,
                    "alt_text": img['alt'],
                    "photographer": img.get('photographer', 'Unknown')
                })
                print(f"   Image {i}: {img['alt'][:50]}... by {img.get('photographer', 'Unknown')}")
            else:
                print(f"   Image {i}: No alt text available")
    
    if not image_options:
        print("❌ No images with alt text available for selection")
        state.selected_image = {"error": "No images with alt text available"}
        return state
    
    print(f"✅ Prepared {len(image_options)} image options for selection")
    
    # Create the judge prompt with article context
    print("📝 Creating image selection prompt...")
    from tron_ai.models.prompts import BasePromptResponse
    
    class ImageSelectionResponse(BasePromptResponse):
        selected_index: int
        reasoning: str
    
    print("🔑 Getting LLM client for image selection...")
    try:
        llm_client = get_llm_client_from_config(LLMClientConfig.build(model_name="gpt-4o", json_output=True))
        print(f"✅ LLM client obtained: {type(llm_client).__name__}")
    except Exception as e:
        print(f"❌ Error getting LLM client: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        # Fallback to first image
        state.selected_image = state.images[0].copy() if state.images else {}
        state.selected_image['selection_reasoning'] = f"Error getting LLM client: {str(e)}"
        return state
    
    print("📝 Creating selection prompt...")
    prompt = Prompt(
        text="""You are an expert image curator for blog posts. Your task is to select the most appropriate image for the given article based on the image alt descriptions and article content.

Consider:
1. Relevance to the article topic and content
2. How well the image complements the title and tags
3. Visual appeal and professionalism for a blog post
4. Appropriateness for the target audience

Return the index of the best image and provide clear reasoning for your choice.""",
        output_format=ImageSelectionResponse
    )
    print(f"✅ Selection prompt created: {prompt}")
    
    # Prepare the selection query
    print("📋 Preparing article context for image selection...")
    article_info = f"""
Article Title: {state.article_json.get('title', 'N/A')}
SEO tags: {state.article_json.get('seo_tags', '')}
Article Content Preview: {state.article_json.get('content', '')[:500]}...

Available Images:
"""
    
    for option in image_options:
        article_info += f"Index {option['index']}: {option['alt_text']} (by {option['photographer']})\n"
    
    article_info += "\nSelect the index of the most appropriate image for this blog post."
    
    print(f"📝 Selection query prepared: {len(article_info)} characters")
    print(f"📝 Query preview: {article_info[:200]}...")
    
    try:
        print("⚙️ Creating selection executor...")
        executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=prompt))
        print(f"✅ Selection executor created: {type(executor).__name__}")
        
        print("🤖 Executing image selection...")
        response = await executor.execute(article_info)
        print(f"📤 Selection response received: {response}")
        print(f"📤 Response type: {type(response)}")
        print(f"📤 Response attributes: {dir(response)}")
        
        if hasattr(response, 'selected_index') and hasattr(response, 'reasoning'):
            selected_index = response.selected_index
            reasoning = response.reasoning
            
            print(f"🎯 LLM selected index: {selected_index}")
            print(f"💭 LLM reasoning: {reasoning}")
            
            # Validate the selected index
            if 0 <= selected_index < len(state.images):
                state.selected_image = state.images[selected_index].copy()
                state.selected_image['selection_reasoning'] = reasoning
                print(f"✅ Successfully selected image {selected_index}")
                print(f"🖼️ Selected image: {state.images[selected_index].get('alt', 'No alt text')}")
                print(f"👤 Photographer: {state.images[selected_index].get('photographer', 'Unknown')}")
            else:
                print(f"⚠️ Invalid index {selected_index} selected (valid range: 0-{len(state.images)-1})")
                print("🔄 Falling back to first image")
                state.selected_image = state.images[0].copy()
                state.selected_image['selection_reasoning'] = f"Fallback selection due to invalid index {selected_index}"
        else:
            print(f"❌ Response missing required attributes")
            print(f"📤 Available attributes: {dir(response)}")
            print("🔄 Falling back to first image")
            state.selected_image = state.images[0].copy()
            state.selected_image['selection_reasoning'] = "Fallback selection due to missing response attributes"
            
    except Exception as e:
        print(f"❌ Error during image selection: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Fallback to first image on error
        print("🔄 Falling back to first image due to error")
        state.selected_image = state.images[0].copy() if state.images else {}
        state.selected_image['selection_reasoning'] = f"Error in selection process: {str(e)}"
    
    print(f"📊 Final selected image: {state.selected_image}")
    return state


async def update_content_with_image(state: BlogState) -> BlogState:
    """Update the article content to include the selected image as an HTML tag."""
    print("🖼️ Starting content update with image...")
    print(f"📊 Selected image: {state.selected_image}")
    
    # Check if we have a selected image
    if not state.selected_image:
        print("❌ No selected image available, skipping content update")
        return state
    
    if 'error' in state.selected_image:
        print(f"❌ Selected image has error: {state.selected_image['error']}")
        print("⚠️ Skipping content update due to image error")
        return state
    
    print("✅ Valid selected image found")
    
    # Get the image URL (prefer large, fallback to original)
    print("🔗 Extracting image URL...")
    image_url = None
    if 'src' in state.selected_image:
        src = state.selected_image['src']
        print(f"📊 Available src options: {list(src.keys()) if isinstance(src, dict) else 'Not a dict'}")
        
        image_url = src.get('large') or src.get('original')
        print(f"🔗 Selected image URL: {image_url}")
    else:
        print("❌ No 'src' in selected image")
        print(f"📊 Selected image keys: {list(state.selected_image.keys()) if isinstance(state.selected_image, dict) else 'Not a dict'}")
    
    if not image_url:
        print("❌ No suitable image URL found, skipping content update")
        return state
    
    # Get image details
    print("📋 Extracting image metadata...")
    alt_text = state.selected_image.get('alt', 'Blog post image')
    photographer = state.selected_image.get('photographer', 'Unknown')
    photographer_url = state.selected_image.get('photographer_url', '#')
    
    print(f"📋 Image details:")
    print(f"   - Alt text: {alt_text}")
    print(f"   - Photographer: {photographer}")
    print(f"   - Photographer URL: {photographer_url}")
    
    # Create HTML image tag with attribution
    print("🏗️ Creating HTML image tag...")
    image_html = f'''<div style="text-align: center; margin: 20px 0;">
    <img src="{image_url}" alt="{alt_text}" style="width: 100%; max-width: 800px; height: auto; border-radius: 8px;" />
    <p style="font-size: 12px; color: #666; margin-top: 8px;">
        Photo by <a href="{photographer_url}" target="_blank" rel="noopener">{photographer}</a> on Pexels
    </p>
</div>'''
    
    print(f"✅ HTML image tag created: {len(image_html)} characters")
    print(f"🔍 HTML preview: {image_html[:100]}...")
    
    # Update the corrected_json content with the image
    print("📝 Updating article content...")
    if 'content' in state.article_json:
        content = state.article_json['content']
        print(f"📊 Original content length: {len(content)} characters")
        print(f"📊 Content preview: {content[:100]}...")
        
        # Find a good place to insert the image (after first paragraph or at the beginning)
        # Look for the first </p> tag or insert at the beginning
        if '</p>' in content:
            print("📍 Found paragraph tags, inserting after first paragraph")
            first_paragraph_end = content.find('</p>') + 4
            print(f"📍 First paragraph ends at position: {first_paragraph_end}")
            
            updated_content = (content[:first_paragraph_end] + '\n\n' + 
                             image_html + '\n\n' + content[first_paragraph_end:])
            print(f"✅ Inserted image after first paragraph")
        else:
            print("📍 No paragraph tags found, inserting at beginning")
            updated_content = image_html + '\n\n' + content
            print(f"✅ Inserted image at beginning of content")
        
        state.corrected_json['content'] = updated_content
        print(f"✅ Article content updated successfully")
        print(f"📊 New content length: {len(updated_content)} characters")
        print(f"📊 Content change: +{len(updated_content) - len(content)} characters")
        print(f"🖼️ Image inserted: {alt_text} by {photographer}")
        
    else:
        print("❌ No content found in corrected_json to update")
        print(f"📊 Corrected JSON keys: {list(state.corrected_json.keys()) if isinstance(state.corrected_json, dict) else 'Not a dict'}")
    
    print(f"📊 State after content update: {state}")
    return state


async def store_blog_post(state: BlogState) -> BlogState:
    """Store the complete blog post data in the storage directory."""
    print("💾 Starting blog post storage...")
    
    try:
        # Create storage directory path
        print("📁 Creating storage directory...")
        storage_dir = Path(__file__).parent / "storage"
        print(f"📁 Storage directory path: {storage_dir}")
        print(f"📁 Storage directory exists: {storage_dir.exists()}")
        
        storage_dir.mkdir(exist_ok=True)
        print(f"✅ Storage directory ready: {storage_dir}")
        
        # Create filename with timestamp
        print("📝 Creating filename...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"blog_post_{timestamp}.json"
        file_path = storage_dir / filename
        print(f"📝 Filename: {filename}")
        print(f"📝 Full file path: {file_path}")
        
        # Prepare the complete data payload
        print("📋 Preparing blog data payload...")
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
        
        print(f"📊 Blog data structure:")
        print(f"   - Metadata keys: {list(blog_data['metadata'].keys())}")
        print(f"   - Article keys: {list(blog_data['article'].keys()) if isinstance(blog_data['article'], dict) else 'Not a dict'}")
        print(f"   - Research length: {len(blog_data['research'])} characters")
        print(f"   - Images count: {len(blog_data['images'])}")
        print(f"   - Selected image: {'Yes' if blog_data['selected_image'] and 'error' not in blog_data['selected_image'] else 'No'}")
        
        # Calculate total data size
        data_str = json.dumps(blog_data, ensure_ascii=False)
        data_size = len(data_str.encode('utf-8'))
        print(f"📊 Total data size: {data_size} bytes ({data_size/1024:.2f} KB)")
        
        # Write to JSON file
        print("✍️ Writing blog data to file...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(blog_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Blog post stored successfully at: {file_path}")
        print(f"📁 File size: {file_path.stat().st_size} bytes")
        print(f"📁 File permissions: {oct(file_path.stat().st_mode)}")
        
        # Verify the file was written correctly
        print("🔍 Verifying file contents...")
        with open(file_path, 'r', encoding='utf-8') as f:
            verification_data = json.load(f)
        
        print(f"✅ File verification successful")
        print(f"📊 Verified data keys: {list(verification_data.keys())}")
        
    except FileNotFoundError as e:
        print(f"❌ File not found error: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
    except PermissionError as e:
        print(f"❌ Permission error: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
    except json.JSONEncodeError as e:
        print(f"❌ JSON encode error: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        print(f"❌ Problem data: {blog_data}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
    except Exception as e:
        print(f"❌ Unexpected error storing blog post: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
    
    print(f"📊 State after storage: {state}")
    return state


class BlogPostCreateFlow(BaseFlow):
    def __init__(self):
        super().__init__("Blog Post Create", "Create a blog post")

    async def execute(self, query: str, *args, **kwargs) -> Any:
        print(f"🚀 Starting BlogPostCreateFlow execution...")
        print(f"📝 Query: {query}")
        print(f"🔧 Args: {args}")
        print(f"🔑 Kwargs: {kwargs}")
        
        print("🏗️ Building workflow graph...")
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
        graph.add_edge("generate_article", "fetch_images")
        # graph.add_edge("review_article", "fetch_images")
        graph.add_edge("fetch_images", "select_best_image")
        graph.add_edge("select_best_image", "update_content_with_image")
        graph.add_edge("update_content_with_image", "store_blog_post")
        graph.add_edge("store_blog_post", "end")
        graph.set_exit("end")
        print("✅ Workflow graph built successfully")
        
        print("🎯 Initializing workflow state...")
        initial_state = BlogState(prompt=query)
        print(f"📊 Initial state: {initial_state}")
        
        print("🔄 Executing workflow...")
        final_state = await graph.run(initial_state)
        print(f"✅ Workflow execution completed")
        print(f"📊 Final state summary:")
        print(f"   - Concept: {len(final_state.concept)} chars")
        print(f"   - Research: {len(final_state.research)} chars")
        print(f"   - Article JSON keys: {list(final_state.article_json.keys()) if final_state.article_json else 'None'}")
        print(f"   - Corrected JSON keys: {list(final_state.corrected_json.keys()) if final_state.corrected_json else 'None'}")
        print(f"   - Images found: {len(final_state.images)}")
        print(f"   - Selected image: {'Yes' if final_state.selected_image and 'error' not in final_state.selected_image else 'No'}")
        
        # Print the complete result including images
        result = {
            "article": final_state.article_json,
            "images": final_state.images,
            "selected_image": final_state.selected_image
        }
        print("📋 Final result:")
        print(json.dumps(result, indent=2))
        return result
    
if __name__ == "__main__":
    flow = BlogPostCreateFlow()
    asyncio.run(flow.execute("Write a blog post about the benefits of using AI in marketing."))