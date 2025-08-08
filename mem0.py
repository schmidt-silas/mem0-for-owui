from pydantic import BaseModel, Field
from typing import Optional, Literal

class Filter:
    """
    A Filter function for Open WebUI to integrate mem0 with Qdrant and Ollama.
    This filter can be toggled on or off and configured via admin and user valves.
    """

    class Valves(BaseModel):
        # Qdrant configuration
        qdrant_host: str = Field(
            default="localhost",
            description="Qdrant server hostname"
        )
        qdrant_port: int = Field(
            default=6333,
            description="Qdrant server port"
        )
        qdrant_collection: str = Field(
            default="mem0_memories",
            description="Qdrant collection name for storing memories"
        )
        
        # Ollama configuration
        ollama_host: str = Field(
            default="http://localhost:11434",
            description="Ollama server URL"
        )
        ollama_embedding_model: str = Field(
            default="nomic-embed-text",
            description="Ollama model for embeddings"
        )
        
        # Memory settings
        top_k_memories: int = Field(
            default=3,
            description="Number of relevant memories to retrieve"
        )
        
        priority: int = Field(
            default=0,
            description="Priority level for the filter. Lower values run first."
        )
        pass

    class UserValves(BaseModel):
        memory_enabled: bool = Field(
            default=True,
            description="Enable/disable memory for this user"
        )
        user_memory_tag: str = Field(
            default="",
            description="Optional tag to categorize your memories"
        )
        pass

    def __init__(self):
        """
        Initializes the filter with toggle and icon.
        """
        self.valves = self.Valves()
        self.toggle = True  # Creates a toggle switch in the UI
        
        # SVG icon for the toggle button (brain/lightbulb icon)
        self.icon = """data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGZpbGw9Im5vbmUiIHZpZXdCb3g9IjAgMCAyNCAyNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZT0iY3VycmVudENvbG9yIiBjbGFzcz0ic2l6ZS02Ij4KICA8cGF0aCBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiIGQ9Ik0xMiAxOHYtNS4yNW0wIDBhNi4wMSA2LjAxIDAgMCAwIDEuNS0uMTg5bS0xLjUuMTg5YTYuMDEgNi4wMSAwIDAgMS0xLjUtLjE4OW0zLjc1IDcuNDc4YTEyLjA2IDEyLjA2IDAgMCAxLTQuNSAwbTMuNzUgMi4zODNhMTQuNDA2IDE0LjQwNiAwIDAgMS0zIDBNMTQuMjUgMTh2LS4xOTJjMC0uOTgzLjY1OC0xLjgyMyAxLjUwOC0yLjMxNmE3LjUgNy41IDAgMSAwLTcuNTE3IDBjLjg1LjQ5MyAxLjUwOSAxLjMzMyAxLjUwOSAyLjMxNlYxOCIgLz4KPC9zdmc+Cg=="""
        
        # Initialize clients as None
        self.mem0_client = None
        self.qdrant_client = None
        self.initialized = False
        pass

    def initialize_clients(self):
        """
        Initialize mem0, Qdrant, and Ollama clients.
        This is called only once when first needed.
        """
        if self.initialized:
            return
            
        try:
            # Import required libraries
            from mem0 import Memory
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams
            
            print(f"Initializing Qdrant client at {self.valves.qdrant_host}:{self.valves.qdrant_port}")
            
            # Initialize Qdrant client
            self.qdrant_client = QdrantClient(
                host=self.valves.qdrant_host,
                port=self.valves.qdrant_port
            )
            
            # Create collection if it doesn't exist
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.valves.qdrant_collection not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.valves.qdrant_collection,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )
                print(f"Created Qdrant collection: {self.valves.qdrant_collection}")
            
            # Initialize mem0 with Qdrant and Ollama
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "host": self.valves.qdrant_host,
                        "port": self.valves.qdrant_port,
                        "collection_name": self.valves.qdrant_collection
                    }
                },
                "embedder": {
                    "provider": "ollama",
                    "config": {
                        "model": self.valves.ollama_embedding_model,
                        "ollama_base_url": self.valves.ollama_host
                    }
                },
                "version": "v1.1"
            }
            
            self.mem0_client = Memory.from_config(config)
            self.initialized = True
            print("Mem0 client initialized successfully with Qdrant and Ollama")
            
        except ImportError as e:
            print(f"Import error: {e}. Please install required packages: pip install mem0ai qdrant-client")
            self.initialized = False
        except Exception as e:
            print(f"Error initializing clients: {e}")
            self.initialized = False

    async def inlet(self, body: dict, __event_emitter__, __user__: Optional[dict] = None) -> dict:
        """
        Process incoming messages before they are sent to the LLM.
        Note: __user__ parameter must use double underscores.
        """
        
        # Handle when toggle is off
        if not self.toggle:
            return body
        
        # Handle user valves - __user__ might be None
        if __user__ and "valves" in __user__:
            user_valves = self.UserValves(**__user__["valves"])
        else:
            user_valves = self.UserValves()
        
        # Check if user has disabled memory
        if not user_valves.memory_enabled:
            return body
        
        # Get user info safely
        user_id = __user__.get("id", "default") if __user__ else "default"
        user_name = __user__.get("name", "User") if __user__ else "User"
        
        print(f"Mem0 Filter processing for user: {user_name} (ID: {user_id})")
        
        # Emit status
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": f"Searching memories (top {self.valves.top_k_memories})...",
                    "done": False,
                    "hidden": False,
                },
            }
        )
        
        try:
            # Initialize clients if needed
            if not self.initialized:
                self.initialize_clients()
            
            if not self.mem0_client:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "Mem0 not configured",
                            "done": True,
                        },
                    }
                )
                return body
            
            # Get the last user message
            if body.get("messages") and len(body["messages"]) > 0:
                last_message = body["messages"][-1].get("content", "")
                
                # Search for relevant memories
                search_results = self.mem0_client.search(
                    query=last_message,
                    user_id=user_id,
                    limit=self.valves.top_k_memories
                )
                
                # Add context from memories if found
                if search_results and len(search_results) > 0:
                    context_lines = ["[Memory Context]"]
                    for memory in search_results:
                        memory_text = memory.get("memory", memory.get("text", ""))
                        context_lines.append(f"- {memory_text}")
                    
                    context = "\n".join(context_lines)
                    
                    # Prepend context to the user's message
                    original_message = body["messages"][-1]["content"]
                    body["messages"][-1]["content"] = f"{context}\n\n[Current Message]\n{original_message}"
                    
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": f"Added {len(search_results)} memories",
                                "done": True,
                            },
                        }
                    )
                
                # Store the current message as a new memory
                metadata = {}
                if user_valves.user_memory_tag:
                    metadata["tag"] = user_valves.user_memory_tag
                
                self.mem0_client.add(
                    messages=[{"role": "user", "content": last_message}],
                    user_id=user_id,
                    metadata=metadata
                )
                
        except Exception as e:
            print(f"Error in mem0 filter: {e}")
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Memory error: {str(e)}",
                        "done": True,
                    },
                }
            )
        
        return body

    async def outlet(self, body: dict, __event_emitter__, __user__: Optional[dict] = None) -> dict:
        """
        Process outgoing responses from the LLM.
        Can be used to store assistant responses in memory.
        """
        
        if not self.toggle or not self.initialized or not self.mem0_client:
            return body
        
        # Handle user valves
        if __user__ and "valves" in __user__:
            user_valves = self.UserValves(**__user__["valves"])
        else:
            user_valves = self.UserValves()
        
        if not user_valves.memory_enabled:
            return body
        
        user_id = __user__.get("id", "default") if __user__ else "default"
        
        try:
            # Store assistant response if available
            if body.get("messages") and len(body["messages"]) > 0:
                last_message = body["messages"][-1]
                if last_message.get("role") == "assistant":
                    metadata = {}
                    if user_valves.user_memory_tag:
                        metadata["tag"] = user_valves.user_memory_tag
                    
                    self.mem0_client.add(
                        messages=[last_message],
                        user_id=user_id,
                        metadata=metadata
                    )
                    
        except Exception as e:
            print(f"Error storing assistant response: {e}")
        
        return body