class TronTools:
    @staticmethod
    def query_memory(query: str) -> str:
        """
        Query the agent's memory system to retrieve relevant information about the user.
        
        This function searches through the agent's persistent memory store to find
        information that matches the provided query. The memory system uses vector
        similarity search to identify the most relevant stored memories.
        
        Args:
            query (str): The search query to find relevant memories
            
        Returns:
            str: A JSON-formatted string containing search results with the following structure:
                {
                    "results": [
                        {
                            "memory": str,  # The stored memory text
                            "similarity": float,  # Similarity score (0-1)
                            "metadata": dict  # Additional metadata about the memory
                        }
                    ]
                }
                
        The search is performed with these parameters:
        - user_id: "tron" (identifies this agent's memory space)
        - limit: 5 (maximum number of results returned)
        - threshold: 0.5 (minimum similarity score for inclusion)
        
        This enables the agent to access context about previous conversations,
        user preferences, and stored information to provide more personalized
        and contextually aware responses.
        """
        from .utils import memory
        return memory.search(query=query, user_id="tron", limit=5, threshold=0.5)