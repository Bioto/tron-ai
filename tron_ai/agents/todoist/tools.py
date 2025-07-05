from typing import List, Dict, Any, Optional
from tron_ai.agents.todoist.utils import get_todoist_client
import json


class TodoistTools:
    """Tools for interacting with the Todoist API."""
    
    @staticmethod
    def get_tasks(project_id: str = None, label_id: str = None, filter_query: str = None, 
                  lang: str = "en", ids: List[str] = None) -> Dict[str, Any]:
        """Get all active tasks for the user.
        
        Args:
            project_id: Filter tasks by project ID
            label_id: Filter tasks by label ID  
            filter_query: Filter tasks by query (e.g., "today", "overdue", "7 days")
            lang: Language for dates (default: "en")
            ids: List of task IDs to retrieve
            
        Returns:
            Dict containing list of task dictionaries with success status
        """
        try:
            client = get_todoist_client()
            tasks = client.get_tasks(
                project_id=project_id,
                label_id=label_id,
                filter_query=filter_query,
                lang=lang,
                ids=ids
            )
            return {
                "success": True,
                "tasks": tasks,
                "count": len(tasks)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tasks": []
            }
    
    @staticmethod
    def get_task(task_id: str) -> Dict[str, Any]:
        """Get a specific task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict containing task details with success status
        """
        try:
            client = get_todoist_client()
            task = client.get_task(task_id)
            return {
                "success": True,
                "task": task
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task": None
            }
    
    @staticmethod
    def create_task(content: str, description: str = None, project_id: str = None,
                    section_id: str = None, parent_id: str = None, order: int = None,
                    label_ids: List[str] = None, priority: int = 1, due_string: str = None,
                    due_date: str = None, due_datetime: str = None, due_lang: str = "en",
                    assignee_id: str = None) -> Dict[str, Any]:
        """Create a new task.
        
        Args:
            content: Task content/title (required)
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
            Dict containing created task details with success status
        """
        try:
            client = get_todoist_client()
            task = client.create_task(
                content=content,
                description=description,
                project_id=project_id,
                section_id=section_id,
                parent_id=parent_id,
                order=order,
                label_ids=label_ids,
                priority=priority,
                due_string=due_string,
                due_date=due_date,
                due_datetime=due_datetime,
                due_lang=due_lang,
                assignee_id=assignee_id
            )
            return {
                "success": True,
                "task": task,
                "message": f"Task '{content}' created successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task": None
            }
    
    @staticmethod
    def update_task(task_id: str, content: str = None, description: str = None,
                    label_ids: List[str] = None, priority: int = None, due_string: str = None,
                    due_date: str = None, due_datetime: str = None, due_lang: str = "en",
                    assignee_id: str = None) -> Dict[str, Any]:
        """Update an existing task.
        
        Args:
            task_id: Task ID to update (required)
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
            Dict containing updated task details with success status
        """
        try:
            client = get_todoist_client()
            task = client.update_task(
                task_id=task_id,
                content=content,
                description=description,
                label_ids=label_ids,
                priority=priority,
                due_string=due_string,
                due_date=due_date,
                due_datetime=due_datetime,
                due_lang=due_lang,
                assignee_id=assignee_id
            )
            return {
                "success": True,
                "task": task,
                "message": f"Task updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task": None
            }
    
    @staticmethod
    def complete_task(task_id: str) -> Dict[str, Any]:
        """Mark a task as completed.
        
        Args:
            task_id: Task ID to complete
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_todoist_client()
            result = client.complete_task(task_id)
            return {
                "success": True,
                "message": f"Task {task_id} completed successfully",
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def reopen_task(task_id: str) -> Dict[str, Any]:
        """Reopen a completed task.
        
        Args:
            task_id: Task ID to reopen
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_todoist_client()
            result = client.reopen_task(task_id)
            return {
                "success": True,
                "message": f"Task {task_id} reopened successfully",
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def delete_task(task_id: str) -> Dict[str, Any]:
        """Delete a task.
        
        Args:
            task_id: Task ID to delete
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_todoist_client()
            result = client.delete_task(task_id)
            return {
                "success": True,
                "message": f"Task {task_id} deleted successfully",
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_projects() -> Dict[str, Any]:
        """Get all projects for the user.
        
        Returns:
            Dict containing list of project dictionaries with success status
        """
        try:
            client = get_todoist_client()
            projects = client.get_projects()
            return {
                "success": True,
                "projects": projects,
                "count": len(projects)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "projects": []
            }
    
    @staticmethod
    def get_project(project_id: str) -> Dict[str, Any]:
        """Get a specific project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict containing project details with success status
        """
        try:
            client = get_todoist_client()
            project = client.get_project(project_id)
            return {
                "success": True,
                "project": project
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project": None
            }
    
    @staticmethod
    def create_project(name: str, parent_id: str = None, color: str = None,
                      is_favorite: bool = False, view_style: str = "list") -> Dict[str, Any]:
        """Create a new project.
        
        Args:
            name: Project name (required)
            parent_id: Parent project ID for subprojects
            color: Project color
            is_favorite: Whether project is favorite
            view_style: Project view style ("list" or "board")
            
        Returns:
            Dict containing created project details with success status
        """
        try:
            client = get_todoist_client()
            project = client.create_project(
                name=name,
                parent_id=parent_id,
                color=color,
                is_favorite=is_favorite,
                view_style=view_style
            )
            return {
                "success": True,
                "project": project,
                "message": f"Project '{name}' created successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project": None
            }
    
    @staticmethod
    def update_project(project_id: str, name: str = None, color: str = None,
                      is_favorite: bool = None, view_style: str = None) -> Dict[str, Any]:
        """Update an existing project.
        
        Args:
            project_id: Project ID to update (required)
            name: New project name
            color: New project color
            is_favorite: New favorite status
            view_style: New view style
            
        Returns:
            Dict containing updated project details with success status
        """
        try:
            client = get_todoist_client()
            project = client.update_project(
                project_id=project_id,
                name=name,
                color=color,
                is_favorite=is_favorite,
                view_style=view_style
            )
            return {
                "success": True,
                "project": project,
                "message": f"Project updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project": None
            }
    
    @staticmethod
    def delete_project(project_id: str) -> Dict[str, Any]:
        """Delete a project.
        
        Args:
            project_id: Project ID to delete
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_todoist_client()
            result = client.delete_project(project_id)
            return {
                "success": True,
                "message": f"Project {project_id} deleted successfully",
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_labels() -> Dict[str, Any]:
        """Get all labels for the user.
        
        Returns:
            Dict containing list of label dictionaries with success status
        """
        try:
            client = get_todoist_client()
            labels = client.get_labels()
            return {
                "success": True,
                "labels": labels,
                "count": len(labels)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "labels": []
            }
    
    @staticmethod
    def get_label(label_id: str) -> Dict[str, Any]:
        """Get a specific label by ID.
        
        Args:
            label_id: Label ID
            
        Returns:
            Dict containing label details with success status
        """
        try:
            client = get_todoist_client()
            label = client.get_label(label_id)
            return {
                "success": True,
                "label": label
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "label": None
            }
    
    @staticmethod
    def create_label(name: str, color: str = None, order: int = None, 
                    is_favorite: bool = False) -> Dict[str, Any]:
        """Create a new label.
        
        Args:
            name: Label name (required)
            color: Label color
            order: Label order
            is_favorite: Whether label is favorite
            
        Returns:
            Dict containing created label details with success status
        """
        try:
            client = get_todoist_client()
            label = client.create_label(
                name=name,
                color=color,
                order=order,
                is_favorite=is_favorite
            )
            return {
                "success": True,
                "label": label,
                "message": f"Label '{name}' created successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "label": None
            }
    
    @staticmethod
    def update_label(label_id: str, name: str = None, color: str = None,
                    order: int = None, is_favorite: bool = None) -> Dict[str, Any]:
        """Update an existing label.
        
        Args:
            label_id: Label ID to update (required)
            name: New label name
            color: New label color
            order: New label order
            is_favorite: New favorite status
            
        Returns:
            Dict containing updated label details with success status
        """
        try:
            client = get_todoist_client()
            label = client.update_label(
                label_id=label_id,
                name=name,
                color=color,
                order=order,
                is_favorite=is_favorite
            )
            return {
                "success": True,
                "label": label,
                "message": f"Label updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "label": None
            }
    
    @staticmethod
    def delete_label(label_id: str) -> Dict[str, Any]:
        """Delete a label.
        
        Args:
            label_id: Label ID to delete
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_todoist_client()
            result = client.delete_label(label_id)
            return {
                "success": True,
                "message": f"Label {label_id} deleted successfully",
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_comments(task_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """Get comments for a task or project.
        
        Args:
            task_id: Task ID to get comments for
            project_id: Project ID to get comments for
            
        Returns:
            Dict containing list of comment dictionaries with success status
        """
        try:
            client = get_todoist_client()
            comments = client.get_comments(task_id=task_id, project_id=project_id)
            return {
                "success": True,
                "comments": comments,
                "count": len(comments)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "comments": []
            }
    
    @staticmethod
    def create_comment(content: str, task_id: str = None, project_id: str = None,
                      attachment: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new comment.
        
        Args:
            content: Comment content (required)
            task_id: Task ID to comment on
            project_id: Project ID to comment on
            attachment: Attachment data
            
        Returns:
            Dict containing created comment details with success status
        """
        try:
            client = get_todoist_client()
            comment = client.create_comment(
                content=content,
                task_id=task_id,
                project_id=project_id,
                attachment=attachment
            )
            return {
                "success": True,
                "comment": comment,
                "message": f"Comment added successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "comment": None
            }
    
    @staticmethod
    def get_comment(comment_id: str) -> Dict[str, Any]:
        """Get a specific comment by ID.
        
        Args:
            comment_id: Comment ID
            
        Returns:
            Dict containing comment details with success status
        """
        try:
            client = get_todoist_client()
            comment = client.get_comment(comment_id)
            return {
                "success": True,
                "comment": comment
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "comment": None
            }
    
    @staticmethod
    def update_comment(comment_id: str, content: str) -> Dict[str, Any]:
        """Update an existing comment.
        
        Args:
            comment_id: Comment ID to update (required)
            content: New comment content (required)
            
        Returns:
            Dict containing updated comment details with success status
        """
        try:
            client = get_todoist_client()
            comment = client.update_comment(comment_id, content)
            return {
                "success": True,
                "comment": comment,
                "message": f"Comment updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "comment": None
            }
    
    @staticmethod
    def delete_comment(comment_id: str) -> Dict[str, Any]:
        """Delete a comment.
        
        Args:
            comment_id: Comment ID to delete
            
        Returns:
            Dict containing success status and message
        """
        try:
            client = get_todoist_client()
            result = client.delete_comment(comment_id)
            return {
                "success": True,
                "message": f"Comment {comment_id} deleted successfully",
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_today_tasks() -> Dict[str, Any]:
        """Get tasks due today.
        
        Returns:
            Dict containing list of today's tasks with success status
        """
        return TodoistTools.get_tasks(filter_query="today")
    
    @staticmethod
    def get_overdue_tasks() -> Dict[str, Any]:
        """Get overdue tasks.
        
        Returns:
            Dict containing list of overdue tasks with success status
        """
        return TodoistTools.get_tasks(filter_query="overdue")
    
    @staticmethod
    def get_next_7_days_tasks() -> Dict[str, Any]:
        """Get tasks due in the next 7 days.
        
        Returns:
            Dict containing list of tasks due in next 7 days with success status
        """
        return TodoistTools.get_tasks(filter_query="7 days")
    
    @staticmethod
    def get_high_priority_tasks() -> Dict[str, Any]:
        """Get high priority tasks (priority 4).
        
        Returns:
            Dict containing list of high priority tasks with success status
        """
        return TodoistTools.get_tasks(filter_query="p1")
    
    @staticmethod
    def quick_add_task(content: str, due_string: str = None, priority: int = 1, 
                      project_name: str = None) -> Dict[str, Any]:
        """Quickly add a task with minimal information.
        
        Args:
            content: Task content/title (required)
            due_string: Due date in natural language (e.g., "tomorrow", "next Monday")
            priority: Task priority (1-4, 4 being highest)
            project_name: Name of project to add task to (will find project ID)
            
        Returns:
            Dict containing created task details with success status
        """
        try:
            project_id = None
            if project_name:
                # Get all projects and find the one with matching name
                projects_result = TodoistTools.get_projects()
                if projects_result["success"]:
                    for project in projects_result["projects"]:
                        if project["name"].lower() == project_name.lower():
                            project_id = project["id"]
                            break
                    if not project_id:
                        return {
                            "success": False,
                            "error": f"Project '{project_name}' not found",
                            "task": None
                        }
            
            return TodoistTools.create_task(
                content=content,
                due_string=due_string,
                priority=priority,
                project_id=project_id
            )
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task": None
            } 