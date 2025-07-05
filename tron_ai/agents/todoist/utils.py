import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class TodoistAPIClient:
    """Client for interacting with the Todoist API."""
    
    def __init__(self, api_token: str = None):
        """Initialize the Todoist API client.
        
        Args:
            api_token: Todoist API token. If not provided, will look for TODOIST_API_TOKEN env var.
        """
        self.api_token = api_token or os.getenv("TODOIST_API_TOKEN")
        if not self.api_token:
            raise ValueError("Todoist API token not found. Set TODOIST_API_TOKEN environment variable or pass api_token parameter.")
        
        self.base_url = "https://api.todoist.com/rest/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the Todoist API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request data for POST/PUT requests
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=data)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle empty responses (e.g., from DELETE requests)
            if response.status_code == 204:
                return {"success": True}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Todoist API request failed: {str(e)}")
    
    def get_tasks(self, project_id: str = None, label_id: str = None, filter_query: str = None, 
                  lang: str = "en", ids: List[str] = None) -> List[Dict[str, Any]]:
        """Get all active tasks for the user.
        
        Args:
            project_id: Filter tasks by project ID
            label_id: Filter tasks by label ID
            filter_query: Filter tasks by query (e.g., "today", "overdue")
            lang: Language for dates (default: "en")
            ids: List of task IDs to retrieve
            
        Returns:
            List of task dictionaries
        """
        params = {}
        if project_id:
            params["project_id"] = project_id
        if label_id:
            params["label_id"] = label_id
        if filter_query:
            params["filter"] = filter_query
        if lang:
            params["lang"] = lang
        if ids:
            params["ids"] = ",".join(ids)
        
        return self._make_request("GET", "tasks", params)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get a specific task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task dictionary
        """
        return self._make_request("GET", f"tasks/{task_id}")
    
    def create_task(self, content: str, description: str = None, project_id: str = None,
                    section_id: str = None, parent_id: str = None, order: int = None,
                    label_ids: List[str] = None, priority: int = 1, due_string: str = None,
                    due_date: str = None, due_datetime: str = None, due_lang: str = "en",
                    assignee_id: str = None) -> Dict[str, Any]:
        """Create a new task.
        
        Args:
            content: Task content/title
            description: Task description
            project_id: Project ID to add task to
            section_id: Section ID to add task to
            parent_id: Parent task ID for subtasks
            order: Task order
            label_ids: List of label IDs to assign
            priority: Task priority (1-4, 4 being highest)
            due_string: Due date in natural language (e.g., "tomorrow", "next Monday")
            due_date: Due date in YYYY-MM-DD format
            due_datetime: Due datetime in RFC3339 format
            due_lang: Language for due_string parsing
            assignee_id: User ID to assign task to
            
        Returns:
            Created task dictionary
        """
        data = {"content": content}
        
        if description:
            data["description"] = description
        if project_id:
            data["project_id"] = project_id
        if section_id:
            data["section_id"] = section_id
        if parent_id:
            data["parent_id"] = parent_id
        if order:
            data["order"] = order
        if label_ids:
            data["label_ids"] = label_ids
        if priority:
            data["priority"] = priority
        if due_string:
            data["due_string"] = due_string
        if due_date:
            data["due_date"] = due_date
        if due_datetime:
            data["due_datetime"] = due_datetime
        if due_lang:
            data["due_lang"] = due_lang
        if assignee_id:
            data["assignee_id"] = assignee_id
        
        return self._make_request("POST", "tasks", data)
    
    def update_task(self, task_id: str, content: str = None, description: str = None,
                    label_ids: List[str] = None, priority: int = None, due_string: str = None,
                    due_date: str = None, due_datetime: str = None, due_lang: str = "en",
                    assignee_id: str = None) -> Dict[str, Any]:
        """Update an existing task.
        
        Args:
            task_id: Task ID to update
            content: New task content/title
            description: New task description
            label_ids: New list of label IDs
            priority: New task priority (1-4)
            due_string: New due date in natural language
            due_date: New due date in YYYY-MM-DD format
            due_datetime: New due datetime in RFC3339 format
            due_lang: Language for due_string parsing
            assignee_id: New assignee user ID
            
        Returns:
            Updated task dictionary
        """
        data = {}
        
        if content:
            data["content"] = content
        if description:
            data["description"] = description
        if label_ids is not None:
            data["label_ids"] = label_ids
        if priority:
            data["priority"] = priority
        if due_string:
            data["due_string"] = due_string
        if due_date:
            data["due_date"] = due_date
        if due_datetime:
            data["due_datetime"] = due_datetime
        if due_lang:
            data["due_lang"] = due_lang
        if assignee_id:
            data["assignee_id"] = assignee_id
        
        return self._make_request("POST", f"tasks/{task_id}", data)
    
    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as completed.
        
        Args:
            task_id: Task ID to complete
            
        Returns:
            Success status
        """
        return self._make_request("POST", f"tasks/{task_id}/close")
    
    def reopen_task(self, task_id: str) -> Dict[str, Any]:
        """Reopen a completed task.
        
        Args:
            task_id: Task ID to reopen
            
        Returns:
            Success status
        """
        return self._make_request("POST", f"tasks/{task_id}/reopen")
    
    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task.
        
        Args:
            task_id: Task ID to delete
            
        Returns:
            Success status
        """
        return self._make_request("DELETE", f"tasks/{task_id}")
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects for the user.
        
        Returns:
            List of project dictionaries
        """
        return self._make_request("GET", "projects")
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get a specific project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project dictionary
        """
        return self._make_request("GET", f"projects/{project_id}")
    
    def create_project(self, name: str, parent_id: str = None, color: str = None,
                      is_favorite: bool = False, view_style: str = "list") -> Dict[str, Any]:
        """Create a new project.
        
        Args:
            name: Project name
            parent_id: Parent project ID for subprojects
            color: Project color
            is_favorite: Whether project is favorite
            view_style: Project view style ("list" or "board")
            
        Returns:
            Created project dictionary
        """
        data = {"name": name}
        
        if parent_id:
            data["parent_id"] = parent_id
        if color:
            data["color"] = color
        if is_favorite:
            data["is_favorite"] = is_favorite
        if view_style:
            data["view_style"] = view_style
        
        return self._make_request("POST", "projects", data)
    
    def update_project(self, project_id: str, name: str = None, color: str = None,
                      is_favorite: bool = None, view_style: str = None) -> Dict[str, Any]:
        """Update an existing project.
        
        Args:
            project_id: Project ID to update
            name: New project name
            color: New project color
            is_favorite: New favorite status
            view_style: New view style
            
        Returns:
            Updated project dictionary
        """
        data = {}
        
        if name:
            data["name"] = name
        if color:
            data["color"] = color
        if is_favorite is not None:
            data["is_favorite"] = is_favorite
        if view_style:
            data["view_style"] = view_style
        
        return self._make_request("POST", f"projects/{project_id}", data)
    
    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a project.
        
        Args:
            project_id: Project ID to delete
            
        Returns:
            Success status
        """
        return self._make_request("DELETE", f"projects/{project_id}")
    
    def get_labels(self) -> List[Dict[str, Any]]:
        """Get all labels for the user.
        
        Returns:
            List of label dictionaries
        """
        return self._make_request("GET", "labels")
    
    def get_label(self, label_id: str) -> Dict[str, Any]:
        """Get a specific label by ID.
        
        Args:
            label_id: Label ID
            
        Returns:
            Label dictionary
        """
        return self._make_request("GET", f"labels/{label_id}")
    
    def create_label(self, name: str, color: str = None, order: int = None, 
                    is_favorite: bool = False) -> Dict[str, Any]:
        """Create a new label.
        
        Args:
            name: Label name
            color: Label color
            order: Label order
            is_favorite: Whether label is favorite
            
        Returns:
            Created label dictionary
        """
        data = {"name": name}
        
        if color:
            data["color"] = color
        if order:
            data["order"] = order
        if is_favorite:
            data["is_favorite"] = is_favorite
        
        return self._make_request("POST", "labels", data)
    
    def update_label(self, label_id: str, name: str = None, color: str = None,
                    order: int = None, is_favorite: bool = None) -> Dict[str, Any]:
        """Update an existing label.
        
        Args:
            label_id: Label ID to update
            name: New label name
            color: New label color
            order: New label order
            is_favorite: New favorite status
            
        Returns:
            Updated label dictionary
        """
        data = {}
        
        if name:
            data["name"] = name
        if color:
            data["color"] = color
        if order:
            data["order"] = order
        if is_favorite is not None:
            data["is_favorite"] = is_favorite
        
        return self._make_request("POST", f"labels/{label_id}", data)
    
    def delete_label(self, label_id: str) -> Dict[str, Any]:
        """Delete a label.
        
        Args:
            label_id: Label ID to delete
            
        Returns:
            Success status
        """
        return self._make_request("DELETE", f"labels/{label_id}")
    
    def get_comments(self, task_id: str = None, project_id: str = None) -> List[Dict[str, Any]]:
        """Get comments for a task or project.
        
        Args:
            task_id: Task ID to get comments for
            project_id: Project ID to get comments for
            
        Returns:
            List of comment dictionaries
        """
        params = {}
        if task_id:
            params["task_id"] = task_id
        if project_id:
            params["project_id"] = project_id
        
        return self._make_request("GET", "comments", params)
    
    def create_comment(self, content: str, task_id: str = None, project_id: str = None,
                      attachment: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new comment.
        
        Args:
            content: Comment content
            task_id: Task ID to comment on
            project_id: Project ID to comment on
            attachment: Attachment data
            
        Returns:
            Created comment dictionary
        """
        data = {"content": content}
        
        if task_id:
            data["task_id"] = task_id
        if project_id:
            data["project_id"] = project_id
        if attachment:
            data["attachment"] = attachment
        
        return self._make_request("POST", "comments", data)
    
    def get_comment(self, comment_id: str) -> Dict[str, Any]:
        """Get a specific comment by ID.
        
        Args:
            comment_id: Comment ID
            
        Returns:
            Comment dictionary
        """
        return self._make_request("GET", f"comments/{comment_id}")
    
    def update_comment(self, comment_id: str, content: str) -> Dict[str, Any]:
        """Update an existing comment.
        
        Args:
            comment_id: Comment ID to update
            content: New comment content
            
        Returns:
            Updated comment dictionary
        """
        data = {"content": content}
        return self._make_request("POST", f"comments/{comment_id}", data)
    
    def delete_comment(self, comment_id: str) -> Dict[str, Any]:
        """Delete a comment.
        
        Args:
            comment_id: Comment ID to delete
            
        Returns:
            Success status
        """
        return self._make_request("DELETE", f"comments/{comment_id}")


# Global client instance
_client = None

def get_todoist_client() -> TodoistAPIClient:
    """Get or create a Todoist API client instance.
    
    Returns:
        TodoistAPIClient instance
    """
    global _client
    if _client is None:
        _client = TodoistAPIClient()
    return _client 