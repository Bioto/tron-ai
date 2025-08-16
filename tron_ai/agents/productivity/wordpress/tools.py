# tron_ai/agents/productivity/wordpress/tools.py
from typing import List, Dict, Any, Optional
from tron_ai.agents.productivity.wordpress.utils import get_wordpress_client
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WordPressTools:
    """Tools for interacting with the WordPress REST API for content management."""
    
    @staticmethod
    def get_posts(per_page: int = 10, page: int = 1, search: str = None, 
                  status: str = "publish", author: int = None, categories: List[int] = None,
                  tags: List[int] = None, order: str = "desc", orderby: str = "date",
                  session_id: str = None) -> Dict[str, Any]:
        """Get WordPress posts with filtering and pagination.
        
        Args:
            per_page: Number of posts per page (max 100)
            page: Page number for pagination
            search: Search query for posts
            status: Post status (publish, draft, private, future, etc.)
            author: Author ID to filter by
            categories: List of category IDs to filter by
            tags: List of tag IDs to filter by
            order: Sort order (asc, desc)
            orderby: Sort by field (date, title, slug, etc.)
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing list of post dictionaries with success status
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] get_posts called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "get_posts called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            params = {
                "per_page": min(per_page, 100),
                "page": page,
                "status": status,
                "order": order,
                "orderby": orderby
            }
            
            if search:
                params["search"] = search
            if author:
                params["author"] = author
            if categories:
                params["categories"] = ",".join(map(str, categories))
            if tags:
                params["tags"] = ",".join(map(str, tags))
                
            posts = client.make_request("GET", "posts", params=params)
            
            return {
                "success": True,
                "posts": posts,
                "count": len(posts) if isinstance(posts, list) else 1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "posts": []
            }
    
    @staticmethod
    def get_post(post_id: int, session_id: str = None) -> Dict[str, Any]:
        """Get a specific WordPress post by ID.
        
        Args:
            post_id: WordPress post ID
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing post data with success status
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] get_post called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "get_post called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            post = client.make_request("GET", f"posts/{post_id}")
            
            return {
                "success": True,
                "post": post
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "post": None
            }
    
    @staticmethod
    def create_post(title: str, content: str = "", excerpt: str = "", status: str = "draft",
                   categories: List[int] = None, tags: List[int] = None, 
                   featured_media: int = None, meta_description: str = "",
                   session_id: str = None) -> Dict[str, Any]:
        """Create a new WordPress post.
        
        Args:
            title: Post title
            content: Post content (HTML allowed)
            excerpt: Post excerpt
            status: Post status (draft, publish, private, future)
            categories: List of category IDs
            tags: List of tag IDs
            featured_media: Featured image media ID
            meta_description: SEO meta description
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing created post data with success status
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] create_post called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "create_post called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            post_data = {
                "title": title,
                "content": content,
                "excerpt": excerpt,
                "status": status
            }
            
            if categories:
                post_data["categories"] = categories
            if tags:
                post_data["tags"] = tags
            if featured_media:
                post_data["featured_media"] = featured_media
            if meta_description:
                post_data["meta"] = {"_yoast_wpseo_metadesc": meta_description}
                
            post = client.make_request("POST", "posts", data=post_data)
            
            return {
                "success": True,
                "post": post,
                "post_id": post.get("id"),
                "url": post.get("link")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "post": None
            }
    
    @staticmethod
    def create_post_with_tag_names(title: str, content: str = "", excerpt: str = "", status: str = "draft",
                                  categories: List[int] = None, tag_names: List[str] = None, 
                                  featured_media: int = None, meta_description: str = "",
                                  session_id: str = None) -> Dict[str, Any]:
        """Create a new WordPress post with tag names (auto-creates missing tags).
        
        Args:
            title: Post title
            content: Post content (HTML allowed)
            excerpt: Post excerpt
            status: Post status (draft, publish, private, future)
            categories: List of category IDs
            tag_names: List of tag names (will be created if they don't exist)
            featured_media: Featured image media ID
            meta_description: SEO meta description
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing created post data with tag creation details
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] create_post_with_tag_names called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "create_post_with_tag_names called without session_id. Session tracking will break."
        try:
            tag_ids = []
            tag_creation_info = {
                "found_tags": [],
                "created_tags": [],
                "errors": []
            }
            
            # Convert tag names to IDs, creating tags as needed
            if tag_names:
                tag_result = WordPressTools.find_or_create_tags(tag_names=tag_names, session_id=session_id)
                if tag_result["success"]:
                    tag_ids = tag_result["tag_ids"]
                    tag_creation_info = {
                        "found_tags": tag_result["found_tags"],
                        "created_tags": tag_result["created_tags"],
                        "errors": tag_result["errors"]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to process tags: {tag_result['error']}",
                        "post": None,
                        "tag_creation_info": tag_creation_info
                    }
            
            # Create the post with the resolved tag IDs
            post_result = WordPressTools.create_post(
                title=title,
                content=content,
                excerpt=excerpt,
                status=status,
                categories=categories,
                tags=tag_ids,
                featured_media=featured_media,
                meta_description=meta_description,
                session_id=session_id
            )
            
            if post_result["success"]:
                return {
                    "success": True,
                    "post": post_result["post"],
                    "post_id": post_result["post_id"],
                    "url": post_result["url"],
                    "tag_creation_info": tag_creation_info
                }
            else:
                return {
                    "success": False,
                    "error": post_result["error"],
                    "post": None,
                    "tag_creation_info": tag_creation_info
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "post": None,
                "tag_creation_info": tag_creation_info
            }
    
    @staticmethod
    def update_post(post_id: int, title: str = None, content: str = None, 
                   excerpt: str = None, status: str = None, categories: List[int] = None,
                   tags: List[int] = None, featured_media: int = None, 
                   meta_description: str = None, session_id: str = None) -> Dict[str, Any]:
        """Update an existing WordPress post.
        
        Args:
            post_id: WordPress post ID to update
            title: New post title
            content: New post content
            excerpt: New post excerpt
            status: New post status
            categories: New list of category IDs
            tags: New list of tag IDs
            featured_media: New featured image media ID
            meta_description: New SEO meta description
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing updated post data with success status
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] update_post called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "update_post called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            post_data = {}
            if title is not None:
                post_data["title"] = title
            if content is not None:
                post_data["content"] = content
            if excerpt is not None:
                post_data["excerpt"] = excerpt
            if status is not None:
                post_data["status"] = status
            if categories is not None:
                post_data["categories"] = categories
            if tags is not None:
                post_data["tags"] = tags
            if featured_media is not None:
                post_data["featured_media"] = featured_media
            if meta_description is not None:
                post_data["meta"] = {"_yoast_wpseo_metadesc": meta_description}
                
            post = client.make_request("PUT", f"posts/{post_id}", data=post_data)
            
            return {
                "success": True,
                "post": post,
                "post_id": post.get("id"),
                "url": post.get("link")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "post": None
            }
    
    @staticmethod
    def update_post_with_tag_names(post_id: int, title: str = None, content: str = None, 
                                  excerpt: str = None, status: str = None, categories: List[int] = None,
                                  tag_names: List[str] = None, featured_media: int = None, 
                                  meta_description: str = None, session_id: str = None) -> Dict[str, Any]:
        """Update an existing WordPress post with tag names (auto-creates missing tags).
        
        Args:
            post_id: WordPress post ID to update
            title: New post title
            content: New post content
            excerpt: New post excerpt
            status: New post status
            categories: New list of category IDs
            tag_names: New list of tag names (will be created if they don't exist)
            featured_media: New featured image media ID
            meta_description: New SEO meta description
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing updated post data with tag creation details
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] update_post_with_tag_names called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "update_post_with_tag_names called without session_id. Session tracking will break."
        try:
            tag_ids = None
            tag_creation_info = {
                "found_tags": [],
                "created_tags": [],
                "errors": []
            }
            
            # Convert tag names to IDs, creating tags as needed
            if tag_names is not None:
                tag_result = WordPressTools.find_or_create_tags(tag_names=tag_names, session_id=session_id)
                if tag_result["success"]:
                    tag_ids = tag_result["tag_ids"]
                    tag_creation_info = {
                        "found_tags": tag_result["found_tags"],
                        "created_tags": tag_result["created_tags"],
                        "errors": tag_result["errors"]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to process tags: {tag_result['error']}",
                        "post": None,
                        "tag_creation_info": tag_creation_info
                    }
            
            # Update the post with the resolved tag IDs
            post_result = WordPressTools.update_post(
                post_id=post_id,
                title=title,
                content=content,
                excerpt=excerpt,
                status=status,
                categories=categories,
                tags=tag_ids,
                featured_media=featured_media,
                meta_description=meta_description,
                session_id=session_id
            )
            
            if post_result["success"]:
                return {
                    "success": True,
                    "post": post_result["post"],
                    "post_id": post_result["post_id"],
                    "url": post_result["url"],
                    "tag_creation_info": tag_creation_info
                }
            else:
                return {
                    "success": False,
                    "error": post_result["error"],
                    "post": None,
                    "tag_creation_info": tag_creation_info
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "post": None,
                "tag_creation_info": tag_creation_info
            }
    
    @staticmethod
    def delete_post(post_id: int, force: bool = False, session_id: str = None) -> Dict[str, Any]:
        """Delete a WordPress post.
        
        Args:
            post_id: WordPress post ID to delete
            force: Whether to permanently delete (true) or move to trash (false)
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing deletion status
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] delete_post called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "delete_post called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            params = {"force": force} if force else {}
            result = client.make_request("DELETE", f"posts/{post_id}", params=params)
            
            return {
                "success": True,
                "deleted": result.get("deleted", False),
                "previous": result.get("previous")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "deleted": False
            }
    
    @staticmethod
    def get_categories(per_page: int = 50, search: str = None, 
                      session_id: str = None) -> Dict[str, Any]:
        """Get WordPress categories.
        
        Args:
            per_page: Number of categories per page (max 100)
            search: Search query for categories
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing list of category dictionaries
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] get_categories called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "get_categories called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            params = {"per_page": min(per_page, 100)}
            if search:
                params["search"] = search
                
            categories = client.make_request("GET", "categories", params=params)
            
            return {
                "success": True,
                "categories": categories,
                "count": len(categories) if isinstance(categories, list) else 1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "categories": []
            }
    
    @staticmethod
    def create_category(name: str, description: str = "", parent: int = None,
                       session_id: str = None) -> Dict[str, Any]:
        """Create a new WordPress category.
        
        Args:
            name: Category name
            description: Category description
            parent: Parent category ID (for hierarchical categories)
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing created category data
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] create_category called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "create_category called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            category_data = {
                "name": name,
                "description": description
            }
            if parent:
                category_data["parent"] = parent
                
            category = client.make_request("POST", "categories", data=category_data)
            
            return {
                "success": True,
                "category": category,
                "category_id": category.get("id")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "category": None
            }
    
    @staticmethod
    def get_tags(per_page: int = 50, search: str = None, 
                session_id: str = None) -> Dict[str, Any]:
        """Get WordPress tags.
        
        Args:
            per_page: Number of tags per page (max 100)
            search: Search query for tags
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing list of tag dictionaries
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] get_tags called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "get_tags called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            params = {"per_page": min(per_page, 100)}
            if search:
                params["search"] = search
                
            tags = client.make_request("GET", "tags", params=params)
            
            return {
                "success": True,
                "tags": tags,
                "count": len(tags) if isinstance(tags, list) else 1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tags": []
            }
    
    @staticmethod
    def create_tag(name: str, description: str = "", session_id: str = None) -> Dict[str, Any]:
        """Create a new WordPress tag.
        
        Args:
            name: Tag name
            description: Tag description
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing created tag data
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] create_tag called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "create_tag called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            tag_data = {
                "name": name,
                "description": description
            }
                
            tag = client.make_request("POST", "tags", data=tag_data)
            
            return {
                "success": True,
                "tag": tag,
                "tag_id": tag.get("id")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tag": None
            }
    
    @staticmethod
    def get_tag(tag_id: int, session_id: str = None) -> Dict[str, Any]:
        """Get a specific WordPress tag by ID.
        
        Args:
            tag_id: WordPress tag ID
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing tag data with success status
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] get_tag called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "get_tag called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            tag = client.make_request("GET", f"tags/{tag_id}")
            
            return {
                "success": True,
                "tag": tag
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tag": None
            }
    
    @staticmethod
    def delete_tag(tag_id: int, force: bool = False, session_id: str = None) -> Dict[str, Any]:
        """Delete a WordPress tag.
        
        kwargs:
            tag_id: WordPress tag ID to delete
            force: Whether to permanently delete (true) or move to trash (false)
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing deletion status
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] delete_tag called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "delete_tag called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            params = {"force": force} if force else {}
            result = client.make_request("DELETE", f"tags/{tag_id}", params=params)
            
            return {
                "success": True,
                "deleted": result.get("deleted", False),
                "previous": result.get("previous")
            }
        except Exception as e:
            error_msg = str(e)
            
            # Check for specific WordPress REST API limitations
            if "501" in error_msg and "Not Implemented" in error_msg:
                return {
                    "success": False,
                    "error": "Tag deletion is not supported by this WordPress site via REST API. You may need to delete tags manually through the WordPress admin interface.",
                    "deleted": False,
                    "api_limitation": True
                }
            elif "403" in error_msg or "Forbidden" in error_msg:
                return {
                    "success": False,
                    "error": "You don't have permission to delete tags on this WordPress site. Check your user role and permissions.",
                    "deleted": False,
                    "permission_error": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to delete tag: {error_msg}",
                    "deleted": False
                }
    
    @staticmethod
    def check_api_capabilities(session_id: str = None) -> Dict[str, Any]:
        """Check what WordPress REST API capabilities are available.
        
        Args:
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing available API capabilities and endpoints
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] check_api_capabilities called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "check_api_capabilities called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            # Test basic endpoints
            capabilities = {
                "posts": {"read": False, "create": False, "update": False, "delete": False},
                "pages": {"read": False, "create": False, "update": False, "delete": False},
                "categories": {"read": False, "create": False, "update": False, "delete": False},
                "tags": {"read": False, "create": False, "update": False, "delete": False},
                "media": {"read": False, "create": False, "update": False, "delete": False}
            }
            
            # Test each endpoint
            for endpoint in capabilities.keys():
                try:
                    # Test read
                    client.make_request("GET", endpoint, params={"per_page": 1})
                    capabilities[endpoint]["read"] = True
                except:
                    pass
                
                # For other operations, we can check the OPTIONS method
                # or infer from the site's general REST API setup
                # Most sites support CRUD for posts/pages/categories/tags/media
                # but tag deletion is often disabled
                if endpoint in ["posts", "pages", "categories", "media"]:
                    capabilities[endpoint]["create"] = True
                    capabilities[endpoint]["update"] = True
                    capabilities[endpoint]["delete"] = True
                elif endpoint == "tags":
                    capabilities[endpoint]["create"] = True
                    capabilities[endpoint]["update"] = True
                    # Tag deletion is commonly disabled, so we'll be conservative
                    capabilities[endpoint]["delete"] = False
            
            return {
                "success": True,
                "capabilities": capabilities,
                "notes": {
                    "tag_deletion": "Tag deletion is often disabled in WordPress REST API. Use the admin interface if needed.",
                    "permissions": "Some operations may require specific user permissions."
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "capabilities": {}
            }
    
    @staticmethod
    def find_or_create_tags(tag_names: List[str], session_id: str = None) -> Dict[str, Any]:
        """Find existing tags by name or create new ones. Returns list of tag IDs.
        
        Args:
            tag_names: List of tag names to find or create
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing list of tag IDs and creation details
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] find_or_create_tags called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "find_or_create_tags called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            tag_ids = []
            created_tags = []
            found_tags = []
            errors = []
            
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if not tag_name:
                    continue
                
                # First, try to find existing tag by name
                try:
                    existing_tags = client.make_request("GET", "tags", params={"search": tag_name})
                    
                    # Look for exact match (case-insensitive)
                    exact_match = None
                    if isinstance(existing_tags, list):
                        for tag in existing_tags:
                            if tag.get("name", "").lower() == tag_name.lower():
                                exact_match = tag
                                break
                    
                    if exact_match:
                        tag_ids.append(exact_match["id"])
                        found_tags.append({
                            "name": exact_match["name"],
                            "id": exact_match["id"]
                        })
                    else:
                        # Tag doesn't exist, create it
                        new_tag_result = WordPressTools.create_tag(name=tag_name, session_id=session_id)
                        if new_tag_result["success"]:
                            tag_id = new_tag_result["tag_id"]
                            tag_ids.append(tag_id)
                            created_tags.append({
                                "name": tag_name,
                                "id": tag_id
                            })
                        else:
                            errors.append(f"Failed to create tag '{tag_name}': {new_tag_result['error']}")
                            
                except Exception as e:
                    errors.append(f"Error processing tag '{tag_name}': {str(e)}")
            
            return {
                "success": len(errors) == 0,
                "tag_ids": tag_ids,
                "found_tags": found_tags,
                "created_tags": created_tags,
                "errors": errors,
                "total_tags": len(tag_ids)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tag_ids": [],
                "found_tags": [],
                "created_tags": [],
                "errors": [str(e)]
            }
    
    @staticmethod
    def get_media(per_page: int = 10, search: str = None, media_type: str = None,
                 session_id: str = None) -> Dict[str, Any]:
        """Get WordPress media items.
        
        Args:
            per_page: Number of media items per page (max 100)
            search: Search query for media
            media_type: Filter by media type (image, video, audio, etc.)
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing list of media dictionaries
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] get_media called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "get_media called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            params = {"per_page": min(per_page, 100)}
            if search:
                params["search"] = search
            if media_type:
                params["media_type"] = media_type
                
            media = client.make_request("GET", "media", params=params)
            
            return {
                "success": True,
                "media": media,
                "count": len(media) if isinstance(media, list) else 1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "media": []
            }
    
    @staticmethod
    def upload_media(file_path: str, title: str = "", description: str = "",
                    alt_text: str = "", session_id: str = None) -> Dict[str, Any]:
        """Upload a media file to WordPress.
        
        Args:
            file_path: Path to the file to upload
            title: Media title
            description: Media description
            alt_text: Alt text for images
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing uploaded media data
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] upload_media called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "upload_media called without session_id. Session tracking will break."
        try:
            import os
            import mimetypes
            
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "media": None
                }
            
            client = get_wordpress_client()
            
            # Prepare file for upload
            filename = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, mime_type)
                }
                
                headers = {
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
                
                if title:
                    headers['Content-Title'] = title
                if description:
                    headers['Content-Description'] = description
                if alt_text:
                    headers['Content-Alt-Text'] = alt_text
                
                import requests
                response = requests.post(
                    f"{client.api_base}/media",
                    files=files,
                    headers=headers,
                    auth=client.auth,
                    timeout=60
                )
                response.raise_for_status()
                media = response.json()
            
            return {
                "success": True,
                "media": media,
                "media_id": media.get("id"),
                "url": media.get("source_url")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "media": None
            }
    
    @staticmethod
    def get_pages(per_page: int = 10, search: str = None, status: str = "publish",
                 order: str = "desc", orderby: str = "date", session_id: str = None) -> Dict[str, Any]:
        """Get WordPress pages.
        
        Args:
            per_page: Number of pages per page (max 100)
            search: Search query for pages
            status: Page status (publish, draft, private, etc.)
            order: Sort order (asc, desc)
            orderby: Sort by field (date, title, slug, etc.)
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing list of page dictionaries
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] get_pages called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "get_pages called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            params = {
                "per_page": min(per_page, 100),
                "status": status,
                "order": order,
                "orderby": orderby
            }
            
            if search:
                params["search"] = search
                
            pages = client.make_request("GET", "pages", params=params)
            
            return {
                "success": True,
                "pages": pages,
                "count": len(pages) if isinstance(pages, list) else 1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "pages": []
            }
    
    @staticmethod
    def create_page(title: str, content: str = "", status: str = "draft",
                   parent: int = None, template: str = "", session_id: str = None) -> Dict[str, Any]:
        """Create a new WordPress page.
        
        Args:
            title: Page title
            content: Page content (HTML allowed)
            status: Page status (draft, publish, private)
            parent: Parent page ID (for hierarchical pages)
            template: Page template to use
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing created page data
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] create_page called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "create_page called without session_id. Session tracking will break."
        try:
            client = get_wordpress_client()
            
            page_data = {
                "title": title,
                "content": content,
                "status": status
            }
            
            if parent:
                page_data["parent"] = parent
            if template:
                page_data["template"] = template
                
            page = client.make_request("POST", "pages", data=page_data)
            
            return {
                "success": True,
                "page": page,
                "page_id": page.get("id"),
                "url": page.get("link")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "page": None
            }
