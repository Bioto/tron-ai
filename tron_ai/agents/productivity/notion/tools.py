from typing import List, Dict, Any, Optional
from tron_ai.agents.productivity.notion.utils import get_notion_client
import json
import logging

logger = logging.getLogger(__name__)

class NotionTools:
    """Tools for interacting with the Notion API."""
    
    @staticmethod
    def search_pages(query: str = None, filter_type: str = None, 
                    sort_direction: str = "descending", page_size: int = 10,
                    start_cursor: str = None, session_id: str = None) -> Dict[str, Any]:
        """Search for pages in the Notion workspace.
        
        Args:
            query: Search query text
            filter_type: Filter by type ('page', 'database')
            sort_direction: Sort direction ('ascending', 'descending')
            page_size: Number of results to return (max 100)
            start_cursor: Cursor for pagination
            session_id: Session ID for session tracking
            
        Returns:
            Dict containing list of page dictionaries with success status
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                logger.warning("[SESSION] search_pages called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "search_pages called without session_id. Session tracking will break."
        try:
            client = get_notion_client()
            
            search_params = {
                "page_size": page_size,
                "sort": {
                    "direction": sort_direction,
                    "timestamp": "last_edited_time"
                }
            }
            
            if query:
                search_params["query"] = query
            if filter_type:
                search_params["filter"] = {"property": "object", "value": filter_type}
            if start_cursor:
                search_params["start_cursor"] = start_cursor
                
            results = client.search(**search_params)
            
            pages = []
            for result in results.get("results", []):
                page_info = {
                    "id": result["id"],
                    "type": result["object"],
                    "title": "",
                    "url": result.get("url", ""),
                    "last_edited_time": result.get("last_edited_time", "")
                }
                
                # Extract title from different page types
                if result["object"] == "page":
                    if "properties" in result and "title" in result["properties"]:
                        title_prop = result["properties"]["title"]
                        if title_prop["type"] == "title" and title_prop["title"]:
                            page_info["title"] = "".join([text["plain_text"] for text in title_prop["title"]])
                elif result["object"] == "database":
                    if "title" in result and result["title"]:
                        page_info["title"] = "".join([text["plain_text"] for text in result["title"]])
                
                pages.append(page_info)
            
            return {
                "success": True,
                "pages": pages,
                "count": len(pages),
                "has_more": results.get("has_more", False),
                "next_cursor": results.get("next_cursor")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "pages": []
            }
    
    @staticmethod
    def get_page(page_id: str) -> Dict[str, Any]:
        """Get a specific page by ID.
        
        Args:
            page_id: Page ID
            
        Returns:
            Dict containing page details with success status
        """
        try:
            client = get_notion_client()
            page = client.pages.retrieve(page_id)
            
            # Extract page title
            title = ""
            if "properties" in page and "title" in page["properties"]:
                title_prop = page["properties"]["title"]
                if title_prop["type"] == "title" and title_prop["title"]:
                    title = "".join([text["plain_text"] for text in title_prop["title"]])
            
            return {
                "success": True,
                "page": {
                    "id": page["id"],
                    "title": title,
                    "url": page.get("url", ""),
                    "properties": page.get("properties", {}),
                    "last_edited_time": page.get("last_edited_time", "")
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "page": None
            }
    
    @staticmethod
    def create_page(title: str, parent_id: str = None, parent_type: str = "page_id",
                   content: str = None, properties: Dict[str, Any] = None,
                   icon: Dict[str, Any] = None, cover: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new page.
        
        Args:
            title: Page title (required)
            parent_id: Parent page or database ID
            parent_type: Type of parent ('page_id', 'database_id')
            content: Initial page content
            properties: Page properties (for database pages)
            icon: Page icon
            cover: Page cover image
            
        Returns:
            Dict containing created page details with success status
        """
        try:
            client = get_notion_client()
            
            # Prepare page properties
            page_properties = {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
            
            # Add custom properties if provided
            if properties:
                page_properties.update(properties)
            
            # Prepare parent
            parent = {parent_type: parent_id} if parent_id else None
            
            # Create page
            page = client.pages.create(
                parent=parent,
                properties=page_properties,
                icon=icon,
                cover=cover
            )
            
            # Add content if provided
            if content:
                NotionTools.add_block_content(page["id"], content)
            
            return {
                "success": True,
                "page": {
                    "id": page["id"],
                    "title": title,
                    "url": page.get("url", ""),
                    "message": f"Page '{title}' created successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "page": None
            }
    
    @staticmethod
    def update_page(page_id: str, title: str = None, properties: Dict[str, Any] = None,
                   icon: Dict[str, Any] = None, cover: Dict[str, Any] = None) -> Dict[str, Any]:
        """Update an existing page.
        
        Args:
            page_id: Page ID to update (required)
            title: New page title
            properties: New page properties
            icon: New page icon
            cover: New page cover
            
        Returns:
            Dict containing updated page details with success status
        """
        try:
            client = get_notion_client()
            
            update_data = {}
            
            if title:
                update_data["properties"] = {
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                }
            
            if properties:
                if "properties" not in update_data:
                    update_data["properties"] = {}
                update_data["properties"].update(properties)
            
            if icon is not None:
                update_data["icon"] = icon
            
            if cover is not None:
                update_data["cover"] = cover
            
            page = client.pages.update(page_id, **update_data)
            
            return {
                "success": True,
                "page": {
                    "id": page["id"],
                    "title": title or "Updated",
                    "url": page.get("url", ""),
                    "message": "Page updated successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "page": None
            }
    
    @staticmethod
    def delete_page(page_id: str) -> Dict[str, Any]:
        """Delete a page (move to trash).
        
        Args:
            page_id: Page ID to delete
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            client.pages.update(page_id, archived=True)
            return {
                "success": True,
                "message": f"Page {page_id} moved to trash successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_database(database_id: str) -> Dict[str, Any]:
        """Get a specific database by ID.
        
        Args:
            database_id: Database ID
            
        Returns:
            Dict containing database details with success status
        """
        try:
            client = get_notion_client()
            database = client.databases.retrieve(database_id)
            
            title = ""
            if "title" in database and database["title"]:
                title = "".join([text["plain_text"] for text in database["title"]])
            
            return {
                "success": True,
                "database": {
                    "id": database["id"],
                    "title": title,
                    "url": database.get("url", ""),
                    "properties": database.get("properties", {}),
                    "description": database.get("description", [])
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "database": None
            }
    
    @staticmethod
    def create_database(title: str, parent_id: str, properties: Dict[str, Any],
                       description: str = None, icon: Dict[str, Any] = None,
                       cover: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new database.
        
        Args:
            title: Database title (required)
            parent_id: Parent page ID (required)
            properties: Database properties/schema (required)
            description: Database description
            icon: Database icon
            cover: Database cover image
            
        Returns:
            Dict containing created database details with success status
        """
        try:
            client = get_notion_client()
            
            database = client.databases.create(
                parent={"page_id": parent_id},
                title=[{"text": {"content": title}}],
                properties=properties,
                description=[{"text": {"content": description}}] if description else None,
                icon=icon,
                cover=cover
            )
            
            return {
                "success": True,
                "database": {
                    "id": database["id"],
                    "title": title,
                    "url": database.get("url", ""),
                    "message": f"Database '{title}' created successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "database": None
            }
    
    @staticmethod
    def query_database(database_id: str, filter_params: Dict[str, Any] = None,
                      sort_params: List[Dict[str, Any]] = None, page_size: int = 100,
                      start_cursor: str = None) -> Dict[str, Any]:
        """Query a database for entries.
        
        Args:
            database_id: Database ID to query
            filter_params: Filter parameters
            sort_params: Sort parameters
            page_size: Number of results to return
            start_cursor: Cursor for pagination
            
        Returns:
            Dict containing database entries with success status
        """
        try:
            client = get_notion_client()
            
            query_params = {
                "page_size": page_size
            }
            
            if filter_params:
                query_params["filter"] = filter_params
            if sort_params:
                query_params["sorts"] = sort_params
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            results = client.databases.query(database_id, **query_params)
            
            entries = []
            for result in results.get("results", []):
                entry = {
                    "id": result["id"],
                    "properties": result.get("properties", {}),
                    "url": result.get("url", ""),
                    "created_time": result.get("created_time", ""),
                    "last_edited_time": result.get("last_edited_time", "")
                }
                entries.append(entry)
            
            return {
                "success": True,
                "entries": entries,
                "count": len(entries),
                "has_more": results.get("has_more", False),
                "next_cursor": results.get("next_cursor")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "entries": []
            }
    
    @staticmethod
    def add_block_content(page_id: str, content: str, block_type: str = "paragraph") -> Dict[str, Any]:
        """Add content blocks to a page.
        
        Args:
            page_id: Page ID to add content to
            content: Content text
            block_type: Type of block ('paragraph', 'heading_1', 'heading_2', 'heading_3', 'bulleted_list_item', 'numbered_list_item')
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            block_data = {
                "object": "block",
                "type": block_type,
                block_type: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        }
                    ]
                }
            }
            
            block = client.blocks.children.append(page_id, children=[block_data])
            
            return {
                "success": True,
                "block": {
                    "id": block["results"][0]["id"] if block["results"] else None,
                    "type": block_type,
                    "message": f"Content block added successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_page_blocks(page_id: str, start_cursor: str = None, page_size: int = 100) -> Dict[str, Any]:
        """Get all blocks from a page.
        
        Args:
            page_id: Page ID
            start_cursor: Cursor for pagination
            page_size: Number of blocks to return
            
        Returns:
            Dict containing page blocks with success status
        """
        try:
            client = get_notion_client()
            
            params = {"page_size": page_size}
            if start_cursor:
                params["start_cursor"] = start_cursor
            
            results = client.blocks.children.list(page_id, **params)
            
            blocks = []
            for block in results.get("results", []):
                block_info = {
                    "id": block["id"],
                    "type": block["type"],
                    "has_children": block.get("has_children", False),
                    "created_time": block.get("created_time", ""),
                    "last_edited_time": block.get("last_edited_time", "")
                }
                
                # Extract content based on block type
                if block["type"] in block:
                    content = block[block["type"]]
                    if "rich_text" in content:
                        block_info["content"] = "".join([text["plain_text"] for text in content["rich_text"]])
                
                blocks.append(block_info)
            
            return {
                "success": True,
                "blocks": blocks,
                "count": len(blocks),
                "has_more": results.get("has_more", False),
                "next_cursor": results.get("next_cursor")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "blocks": []
            }
    
    @staticmethod
    def create_meeting_notes_template(title: str, parent_id: str, meeting_date: str = None,
                                    attendees: List[str] = None, agenda: List[str] = None) -> Dict[str, Any]:
        """Create a meeting notes template page.
        
        Args:
            title: Meeting title
            parent_id: Parent page ID
            meeting_date: Meeting date
            attendees: List of attendees
            agenda: List of agenda items
            
        Returns:
            Dict containing created page details with success status
        """
        try:
            # Create the page
            page_result = NotionTools.create_page(title, parent_id)
            if not page_result["success"]:
                return page_result
            
            page_id = page_result["page"]["id"]
            
            # Add meeting template content
            content_blocks = [
                ("heading_1", f"📅 {title}"),
                ("paragraph", f"Date: {meeting_date or 'TBD'}"),
                ("paragraph", f"Attendees: {', '.join(attendees) if attendees else 'TBD'}"),
                ("heading_2", "📋 Agenda"),
            ]
            
            # Add agenda items
            if agenda:
                for item in agenda:
                    content_blocks.append(("bulleted_list_item", f"• {item}"))
            else:
                content_blocks.append(("bulleted_list_item", "• [Add agenda items here]"))
            
            content_blocks.extend([
                ("heading_2", "📝 Notes"),
                ("paragraph", "[Add meeting notes here]"),
                ("heading_2", "✅ Action Items"),
                ("bulleted_list_item", "• [Add action items here]"),
                ("heading_2", "📅 Next Steps"),
                ("paragraph", "[Add next steps here]")
            ])
            
            # Add all content blocks
            for block_type, content in content_blocks:
                NotionTools.add_block_content(page_id, content, block_type)
            
            return {
                "success": True,
                "page": {
                    "id": page_id,
                    "title": title,
                    "url": page_result["page"]["url"],
                    "message": f"Meeting notes template '{title}' created successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "page": None
            }
    
    @staticmethod
    def create_project_database(title: str, parent_id: str) -> Dict[str, Any]:
        """Create a project management database.
        
        Args:
            title: Database title
            parent_id: Parent page ID
            
        Returns:
            Dict containing created database details with success status
        """
        try:
            properties = {
                "Name": {"title": {}},
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Not Started", "color": "gray"},
                            {"name": "In Progress", "color": "blue"},
                            {"name": "Review", "color": "yellow"},
                            {"name": "Done", "color": "green"}
                        ]
                    }
                },
                "Priority": {
                    "select": {
                        "options": [
                            {"name": "Low", "color": "gray"},
                            {"name": "Medium", "color": "yellow"},
                            {"name": "High", "color": "red"}
                        ]
                    }
                },
                "Due Date": {"date": {}},
                "Assignee": {"people": {}},
                "Tags": {"multi_select": {"options": []}},
                "Notes": {"rich_text": {}}
            }
            
            return NotionTools.create_database(title, parent_id, properties)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "database": None
            }

    @staticmethod
    def update_block_content(block_id: str, content: str) -> Dict[str, Any]:
        """Update content of an existing block.
        
        Args:
            block_id: Block ID to update
            content: New content text
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            # Get the current block to determine its type
            current_block = client.blocks.retrieve(block_id)
            block_type = current_block["type"]
            
            # Prepare update data based on block type
            update_data = {
                block_type: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        }
                    ]
                }
            }
            
            updated_block = client.blocks.update(block_id, **update_data)
            
            return {
                "success": True,
                "block": {
                    "id": updated_block["id"],
                    "type": updated_block["type"],
                    "message": f"Block content updated successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def delete_block(block_id: str) -> Dict[str, Any]:
        """Delete a specific block from a page.
        
        Args:
            block_id: Block ID to delete
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            client.blocks.delete(block_id)
            return {
                "success": True,
                "message": f"Block {block_id} deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def create_code_block(page_id: str, code: str, language: str = "python") -> Dict[str, Any]:
        """Create a code block with syntax highlighting.
        
        Args:
            page_id: Page ID to add code block to
            code: Code content
            language: Programming language for syntax highlighting
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            block_data = {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": code
                            }
                        }
                    ],
                    "language": language
                }
            }
            
            block = client.blocks.children.append(page_id, children=[block_data])
            
            return {
                "success": True,
                "block": {
                    "id": block["results"][0]["id"] if block["results"] else None,
                    "type": "code",
                    "language": language,
                    "message": f"Code block added successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def create_table(page_id: str, headers: List[str], rows: List[List[str]]) -> Dict[str, Any]:
        """Create a table with headers and data.
        
        Args:
            page_id: Page ID to add table to
            headers: List of column headers
            rows: List of rows, each containing list of cell values
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            # Create table structure
            table_children = []
            
            # Add header row
            header_cells = []
            for header in headers:
                header_cells.append({
                    "type": "text",
                    "text": {"content": header}
                })
            table_children.append({
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": [header_cells]
                }
            })
            
            # Add data rows
            for row in rows:
                row_cells = []
                for cell in row:
                    row_cells.append({
                        "type": "text",
                        "text": {"content": str(cell)}
                    })
                table_children.append({
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [row_cells]
                    }
                })
            
            # Create table block
            table_block = {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": len(headers),
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": table_children
                }
            }
            
            block = client.blocks.children.append(page_id, children=[table_block])
            
            return {
                "success": True,
                "block": {
                    "id": block["results"][0]["id"] if block["results"] else None,
                    "type": "table",
                    "columns": len(headers),
                    "rows": len(rows) + 1,  # +1 for header
                    "message": f"Table created successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def create_toggle_block(page_id: str, title: str, content: str = None) -> Dict[str, Any]:
        """Create a collapsible toggle block.
        
        Args:
            page_id: Page ID to add toggle block to
            title: Toggle title
            content: Optional content inside the toggle
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            toggle_data = {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
            
            # Add content if provided
            if content:
                toggle_data["toggle"]["children"] = [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": content
                                    }
                                }
                            ]
                        }
                    }
                ]
            
            block = client.blocks.children.append(page_id, children=[toggle_data])
            
            return {
                "success": True,
                "block": {
                    "id": block["results"][0]["id"] if block["results"] else None,
                    "type": "toggle",
                    "message": f"Toggle block created successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def create_callout_block(page_id: str, content: str, icon: str = "💡", color: str = "default") -> Dict[str, Any]:
        """Create a highlighted callout block.
        
        Args:
            page_id: Page ID to add callout block to
            content: Callout content
            icon: Emoji or icon for the callout
            color: Callout color ('default', 'gray', 'brown', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink', 'red')
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            callout_data = {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        }
                    ],
                    "icon": {
                        "type": "emoji",
                        "emoji": icon
                    },
                    "color": color
                }
            }
            
            block = client.blocks.children.append(page_id, children=[callout_data])
            
            return {
                "success": True,
                "block": {
                    "id": block["results"][0]["id"] if block["results"] else None,
                    "type": "callout",
                    "icon": icon,
                    "color": color,
                    "message": f"Callout block created successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def add_image_to_page(page_id: str, image_url: str, caption: str = None) -> Dict[str, Any]:
        """Add an image to a page from URL.
        
        Args:
            page_id: Page ID to add image to
            image_url: URL of the image
            caption: Optional image caption
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            image_data = {
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": image_url
                    }
                }
            }
            
            if caption:
                image_data["image"]["caption"] = [
                    {
                        "type": "text",
                        "text": {
                            "content": caption
                        }
                    }
                ]
            
            block = client.blocks.children.append(page_id, children=[image_data])
            
            return {
                "success": True,
                "block": {
                    "id": block["results"][0]["id"] if block["results"] else None,
                    "type": "image",
                    "url": image_url,
                    "caption": caption,
                    "message": f"Image added successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def add_external_link(page_id: str, url: str, text: str = None) -> Dict[str, Any]:
        """Add an external link to a page.
        
        Args:
            page_id: Page ID to add link to
            url: External URL
            text: Link text (defaults to URL if not provided)
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            link_text = text or url
            
            link_data = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": link_text,
                                "link": {
                                    "url": url
                                }
                            }
                        }
                    ]
                }
            }
            
            block = client.blocks.children.append(page_id, children=[link_data])
            
            return {
                "success": True,
                "block": {
                    "id": block["results"][0]["id"] if block["results"] else None,
                    "type": "paragraph",
                    "url": url,
                    "text": link_text,
                    "message": f"External link added successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def move_page(page_id: str, new_parent_id: str) -> Dict[str, Any]:
        """Move a page to a different parent.
        
        Args:
            page_id: Page ID to move
            new_parent_id: New parent page ID
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            updated_page = client.pages.update(
                page_id,
                parent={"page_id": new_parent_id}
            )
            
            return {
                "success": True,
                "page": {
                    "id": updated_page["id"],
                    "url": updated_page.get("url", ""),
                    "message": f"Page moved successfully to new parent"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def duplicate_page(page_id: str, new_title: str = None) -> Dict[str, Any]:
        """Duplicate a page with all its content.
        
        Args:
            page_id: Page ID to duplicate
            new_title: New title for the duplicated page
            
        Returns:
            Dict containing duplicated page details with success status
        """
        try:
            client = get_notion_client()
            
            # Get the original page
            original_page = client.pages.retrieve(page_id)
            
            # Get the parent of the original page
            parent_id = original_page.get("parent", {}).get("page_id")
            if not parent_id:
                return {
                    "success": False,
                    "error": "Cannot duplicate page without a parent"
                }
            
            # Create new page with same properties
            new_title_text = new_title or f"Copy of {original_page.get('properties', {}).get('title', {}).get('title', [{}])[0].get('plain_text', 'Untitled')}"
            
            new_page = client.pages.create(
                parent={"page_id": parent_id},
                properties={
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": new_title_text
                                }
                            }
                        ]
                    }
                }
            )
            
            # Copy blocks from original page
            blocks = client.blocks.children.list(page_id)
            if blocks.get("results"):
                client.blocks.children.append(new_page["id"], children=blocks["results"])
            
            return {
                "success": True,
                "page": {
                    "id": new_page["id"],
                    "title": new_title_text,
                    "url": new_page.get("url", ""),
                    "message": f"Page duplicated successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def add_comment_to_page(page_id: str, comment_text: str) -> Dict[str, Any]:
        """Add a comment to a page.
        
        Args:
            page_id: Page ID to add comment to
            comment_text: Comment text
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_notion_client()
            
            comment = client.comments.create(
                parent={"page_id": page_id},
                rich_text=[
                    {
                        "type": "text",
                        "text": {
                            "content": comment_text
                        }
                    }
                ]
            )
            
            return {
                "success": True,
                "comment": {
                    "id": comment["id"],
                    "text": comment_text,
                    "message": f"Comment added successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_page_comments(page_id: str) -> Dict[str, Any]:
        """Get all comments on a page.
        
        Args:
            page_id: Page ID
            
        Returns:
            Dict containing page comments with success status
        """
        try:
            client = get_notion_client()
            
            comments = client.comments.list(block_id=page_id)
            
            comment_list = []
            for comment in comments.get("results", []):
                comment_text = ""
                if "rich_text" in comment and comment["rich_text"]:
                    comment_text = "".join([text["plain_text"] for text in comment["rich_text"]])
                
                comment_info = {
                    "id": comment["id"],
                    "text": comment_text,
                    "created_time": comment.get("created_time", ""),
                    "last_edited_time": comment.get("last_edited_time", "")
                }
                comment_list.append(comment_info)
            
            return {
                "success": True,
                "comments": comment_list,
                "count": len(comment_list)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "comments": []
            }
    
    @staticmethod
    def create_project_template(title: str, parent_id: str, project_type: str = "general") -> Dict[str, Any]:
        """Create a project management template.
        
        Args:
            title: Project title
            parent_id: Parent page ID
            project_type: Type of project ('general', 'development', 'design', 'marketing')
            
        Returns:
            Dict containing created page details with success status
        """
        try:
            # Create the page
            page_result = NotionTools.create_page(title, parent_id)
            if not page_result["success"]:
                return page_result
            
            page_id = page_result["page"]["id"]
            
            # Define template content based on project type
            if project_type == "development":
                content_blocks = [
                    ("heading_1", f"🚀 {title}"),
                    ("paragraph", "Project Overview"),
                    ("paragraph", "[Add project description here]"),
                    ("heading_2", "📋 Requirements"),
                    ("bulleted_list_item", "• [Add requirements here]"),
                    ("heading_2", "🛠️ Technical Stack"),
                    ("bulleted_list_item", "• [List technologies]"),
                    ("heading_2", "📅 Timeline"),
                    ("paragraph", "[Add project timeline]"),
                    ("heading_2", "👥 Team"),
                    ("bulleted_list_item", "• [List team members]"),
                    ("heading_2", "📝 Notes"),
                    ("paragraph", "[Add project notes here]"),
                    ("heading_2", "✅ Milestones"),
                    ("bulleted_list_item", "• [Add milestones here]")
                ]
            elif project_type == "design":
                content_blocks = [
                    ("heading_1", f"🎨 {title}"),
                    ("paragraph", "Design Brief"),
                    ("paragraph", "[Add design brief here]"),
                    ("heading_2", "🎯 Objectives"),
                    ("bulleted_list_item", "• [Add design objectives]"),
                    ("heading_2", "👥 Target Audience"),
                    ("paragraph", "[Define target audience]"),
                    ("heading_2", "🎨 Design Elements"),
                    ("bulleted_list_item", "• [List design elements]"),
                    ("heading_2", "📅 Deliverables"),
                    ("bulleted_list_item", "• [List deliverables]"),
                    ("heading_2", "📝 Notes"),
                    ("paragraph", "[Add design notes here]")
                ]
            else:  # general
                content_blocks = [
                    ("heading_1", f"📋 {title}"),
                    ("paragraph", "Project Overview"),
                    ("paragraph", "[Add project description here]"),
                    ("heading_2", "🎯 Goals"),
                    ("bulleted_list_item", "• [Add project goals]"),
                    ("heading_2", "📅 Timeline"),
                    ("paragraph", "[Add project timeline]"),
                    ("heading_2", "👥 Team"),
                    ("bulleted_list_item", "• [List team members]"),
                    ("heading_2", "📝 Notes"),
                    ("paragraph", "[Add project notes here]"),
                    ("heading_2", "✅ Action Items"),
                    ("bulleted_list_item", "• [Add action items here]")
                ]
            
            # Add all content blocks
            for block_type, content in content_blocks:
                NotionTools.add_block_content(page_id, content, block_type)
            
            return {
                "success": True,
                "page": {
                    "id": page_id,
                    "title": title,
                    "url": page_result["page"]["url"],
                    "message": f"Project template '{title}' created successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "page": None
            }
    
    @staticmethod
    def create_knowledge_base_template(title: str, parent_id: str) -> Dict[str, Any]:
        """Create a knowledge base template.
        
        Args:
            title: Knowledge base title
            parent_id: Parent page ID
            
        Returns:
            Dict containing created page details with success status
        """
        try:
            # Create the page
            page_result = NotionTools.create_page(title, parent_id)
            if not page_result["success"]:
                return page_result
            
            page_id = page_result["page"]["id"]
            
            # Add knowledge base template content
            content_blocks = [
                ("heading_1", f"📚 {title}"),
                ("paragraph", "Knowledge Base Overview"),
                ("paragraph", "[Add knowledge base description here]"),
                ("heading_2", "📖 Categories"),
                ("bulleted_list_item", "• Getting Started"),
                ("bulleted_list_item", "• Tutorials"),
                ("bulleted_list_item", "• Reference"),
                ("bulleted_list_item", "• FAQs"),
                ("heading_2", "🔍 Search"),
                ("paragraph", "[Add search functionality or tips]"),
                ("heading_2", "📅 Recent Updates"),
                ("paragraph", "[Track recent changes and updates]"),
                ("heading_2", "📞 Contact"),
                ("paragraph", "[Add contact information for questions]")
            ]
            
            # Add all content blocks
            for block_type, content in content_blocks:
                NotionTools.add_block_content(page_id, content, block_type)
            
            return {
                "success": True,
                "page": {
                    "id": page_id,
                    "title": title,
                    "url": page_result["page"]["url"],
                    "message": f"Knowledge base template '{title}' created successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "page": None
            }
    
    @staticmethod
    def create_personal_dashboard_template(title: str, parent_id: str) -> Dict[str, Any]:
        """Create a personal productivity dashboard template.
        
        Args:
            title: Dashboard title
            parent_id: Parent page ID
            
        Returns:
            Dict containing created page details with success status
        """
        try:
            # Create the page
            page_result = NotionTools.create_page(title, parent_id)
            if not page_result["success"]:
                return page_result
            
            page_id = page_result["page"]["id"]
            
            # Add dashboard template content
            content_blocks = [
                ("heading_1", f"📊 {title}"),
                ("paragraph", "Personal Productivity Dashboard"),
                ("paragraph", "[Customize this dashboard for your needs]"),
                ("heading_2", "📅 Today's Focus"),
                ("bulleted_list_item", "• [Add today's priorities]"),
                ("heading_2", "✅ Daily Habits"),
                ("bulleted_list_item", "• [Track daily habits]"),
                ("heading_2", "📝 Quick Notes"),
                ("paragraph", "[Add quick notes and ideas]"),
                ("heading_2", "🎯 Goals"),
                ("bulleted_list_item", "• [List your goals]"),
                ("heading_2", "📚 Resources"),
                ("bulleted_list_item", "• [Add useful links and resources]"),
                ("heading_2", "📊 Metrics"),
                ("paragraph", "[Track your productivity metrics]")
            ]
            
            # Add all content blocks
            for block_type, content in content_blocks:
                NotionTools.add_block_content(page_id, content, block_type)
            
            return {
                "success": True,
                "page": {
                    "id": page_id,
                    "title": title,
                    "url": page_result["page"]["url"],
                    "message": f"Personal dashboard template '{title}' created successfully"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "page": None
            }