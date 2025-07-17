import os
import glob
from typing import List, Dict
import tree_sitter_python as tspy
import tree_sitter

class CodeScannerTools:
    @staticmethod
    def scan_directory(directory: str, file_pattern: str = '*.py') -> List[str]:
        """
        Scan a directory and return a list of file paths matching the pattern.
        
        Args:
            directory (str): The directory path to scan.
            file_pattern (str): Glob pattern for files (default: '*.py').
            
        Returns:
            List[str]: List of matching file paths.
        """
        return glob.glob(os.path.join(directory, '**', file_pattern), recursive=True)
    
    @staticmethod
    def read_file(file_path: str) -> str:
        """
        Read the contents of a file.
        
        Args:
            file_path (str): Path to the file.
            
        Returns:
            str: File contents.
        """
        with open(file_path, 'r') as f:
            return f.read()
    
    @staticmethod
    def parse_file(file_path: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Parse a Python file using tree-sitter and extract structure (functions, classes, imports).
        
        Args:
            file_path (str): Path to the Python file.
            
        Returns:
            Dict[str, List[Dict[str, str]]]: Structured map with 'functions', 'classes', 'imports'.
        """
        language = tree_sitter.Language(tspy.language())
        parser = tree_sitter.Parser()
        parser.language = language
        with open(file_path, 'r') as f:
            code = f.read().encode('utf-8')
        tree = parser.parse(code)
        # Simple extraction example
        functions = []
        classes = []
        imports = []
        def traverse(node):
            if node.type == 'function_definition':
                functions.append({'name': node.child_by_field_name('name').text.decode('utf-8')})
            elif node.type == 'class_definition':
                classes.append({'name': node.child_by_field_name('name').text.decode('utf-8')})
            elif node.type == 'import_statement':
                imports.append({'module': node.text.decode('utf-8')})
            for child in node.children:
                traverse(child)
        traverse(tree.root_node)
        return {
            'functions': functions,
            'classes': classes,
            'imports': imports
        }
    
    @staticmethod
    def build_structure_map(directory: str) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """
        Build a structure map for all Python files in the directory using tree-sitter.
        
        Args:
            directory (str): Directory to scan.
            
        Returns:
            Dict[str, Dict[str, List[Dict[str, str]]]]: Map of file_path to its parsed structure.
        """
        files = CodeScannerTools.scan_directory(directory)
        return {file: CodeScannerTools.parse_file(file) for file in files if file.endswith('.py')} 