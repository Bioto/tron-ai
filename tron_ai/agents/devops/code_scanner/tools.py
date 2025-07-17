import os
import glob
from typing import List, Dict
import tree_sitter_python as tspy
import tree_sitter
import networkx as nx
import json
from neo4j import GraphDatabase

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
    
    @staticmethod
    def build_dependency_graph(directory: str) -> nx.DiGraph:
        """
        Build a dependency graph for the repository using NetworkX.
        
        Args:
            directory (str): Directory to scan.
            
        Returns:
            nx.DiGraph: The constructed graph.
        """
        structure_map = CodeScannerTools.build_structure_map(directory)
        G = nx.DiGraph()
        for file_path, structure in structure_map.items():
            G.add_node(file_path, type='file')
            for func in structure.get('functions', []):
                func_node = f"{file_path}:{func['name']}"
                G.add_node(func_node, type='function')
                G.add_edge(file_path, func_node)
            for cls in structure.get('classes', []):
                cls_node = f"{file_path}:{cls['name']}"
                G.add_node(cls_node, type='class')
                G.add_edge(file_path, cls_node)
            for imp in structure.get('imports', []):
                imp_module = imp['module']
                G.add_edge(file_path, imp_module, type='import')
            
            # Compute PageRank
            ranks = nx.pagerank(G)
            for node in G.nodes:
                G.nodes[node]['pagerank'] = ranks.get(node, 0.0)
            
            return G
    
    @staticmethod
    def store_graph_to_neo4j(graph: nx.DiGraph, graph_name: str = 'RepoGraph') -> str:
        """
        Store a NetworkX graph in Neo4j.
        
        Args:
            graph (nx.DiGraph): The graph to store.
            graph_name (str): Name for the graph in Neo4j.
            
        Returns:
            str: Confirmation message.
        """
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD')
        if not password:
            raise ValueError("NEO4J_PASSWORD environment variable is required.")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # Clear existing graph
            session.run(f"MATCH (n:{graph_name}) DETACH DELETE n")
            for node, data in graph.nodes(data=True):
                session.run(
                    f"CREATE (n:{graph_name} {{id: $id, type: $type, pagerank: $pagerank}})",
                    id=node, type=data.get('type', 'unknown'), pagerank=data.get('pagerank', 0.0)
                )
            for source, target, data in graph.edges(data=True):
                rel_type = data.get('type', 'DEPENDS_ON')
                session.run(
                    f"MATCH (a:{graph_name} {{id: $source}}), (b:{graph_name} {{id: $target}}) "
                    f"CREATE (a)-[:{rel_type}]->(b)",
                    source=source, target=target
                )
        driver.close()
        return f"Graph '{graph_name}' stored in Neo4j successfully." 

    @staticmethod
    def query_relevant_context(query: str, graph_name: str = 'RepoGraph', top_k: int = 10) -> str:
        """
        Query Neo4j for relevant nodes matching the query, sorted by PageRank.
        
        Args:
            query (str): Search query.
            graph_name (str): Graph label in Neo4j.
            top_k (int): Number of top results to return.
            
        Returns:
            str: JSON string of relevant nodes.
        """
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD')
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run(
                f"MATCH (n:{graph_name}) "
                "WHERE toLower(n.id) CONTAINS toLower($query) OR toLower(n.type) CONTAINS toLower($query) "
                "RETURN n.id as id, n.type as type, n.pagerank as pagerank "
                "ORDER BY n.pagerank DESC LIMIT $top_k",
                query=query, top_k=top_k
            )
            nodes = [dict(record) for record in result]
        driver.close()
        return json.dumps(nodes) 