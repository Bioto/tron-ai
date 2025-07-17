import os
import glob
import subprocess
from typing import List, Dict, Optional
from datetime import datetime

class RepoScannerTools:
    @staticmethod
    def scan_directory(directory: str, file_pattern: str = '*') -> List[str]:
        """
        Scan a directory and return a list of file paths matching the pattern.
        
        Args:
            directory (str): The directory path to scan.
            file_pattern (str): Glob pattern for files (default: '*').
            
        Returns:
            List[str]: List of matching file paths.
        """
        return glob.glob(os.path.join(directory, '**', file_pattern), recursive=True)
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, any]:
        """
        Get metadata for a file.
        
        Args:
            file_path (str): Path to the file.
            
        Returns:
            Dict[str, any]: File info including size, mtime, etc.
        """
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_directory": os.path.isdir(file_path),
        }
    
    @staticmethod
    def grep_search(directory: str, pattern: str) -> List[str]:
        """
        Search for text pattern in files within directory using grep.
        
        Args:
            directory (str): Directory to search.
            pattern (str): Search pattern.
            
        Returns:
            List[str]: Lines matching the pattern with file names.
        """
        try:
            result = subprocess.run(['grep', '-rn', pattern, directory], capture_output=True, text=True)
            return result.stdout.splitlines()
        except Exception as e:
            return [str(e)]
    
    @staticmethod
    def git_status(directory: Optional[str] = None) -> str:
        """
        Get git status for the repository.
        
        Args:
            directory (str, optional): Repository path. Defaults to current working directory.
            
        Returns:
            str: Git status output.
        """
        cwd = directory if directory else os.getcwd()
        try:
            result = subprocess.run(['git', '-C', cwd, 'status'], capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            return str(e) 
    
    @staticmethod
    def read_file(file_path: str) -> str:
        """
        Read the contents of a file.
        
        Args:
            file_path (str): Path to the file.
            
        Returns:
            str: File contents or error message.
        """
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    @staticmethod
    def write_file(file_path: str, content: str) -> str:
        """
        Write content to a file.
        
        Args:
            file_path (str): Path to the file.
            content (str): Content to write.
            
        Returns:
            str: Success message or error.
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            return "File written successfully."
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    @staticmethod
    def delete_file(file_path: str) -> str:
        """
        Delete a file.
        
        Args:
            file_path (str): Path to the file.
            
        Returns:
            str: Success message or error.
        """
        try:
            os.remove(file_path)
            return "File deleted successfully."
        except Exception as e:
            return f"Error deleting file: {str(e)}"
    
    @staticmethod
    def create_directory(directory_path: str) -> str:
        """
        Create a directory.
        
        Args:
            directory_path (str): Path to the directory.
            
        Returns:
            str: Success message or error.
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            return "Directory created successfully."
        except Exception as e:
            return f"Error creating directory: {str(e)}"
    
    @staticmethod
    def delete_directory(directory_path: str) -> str:
        """
        Delete a directory and its contents.
        
        Args:
            directory_path (str): Path to the directory.
            
        Returns:
            str: Success message or error.
        """
        import shutil
        try:
            shutil.rmtree(directory_path)
            return "Directory deleted successfully."
        except Exception as e:
            return f"Error deleting directory: {str(e)}" 