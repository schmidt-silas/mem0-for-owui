from pydantic import BaseModel, Field
from typing import Optional, Literal

# This is a Filter function, which modifies data before it's sent to the AI
# or after it comes back. It includes a toggle switch and configuration valves.
class Filter:
    """
    A Filter function for Open WebUI to integrate mem0.
    This filter can be toggled on or off and configured via admin and user valves.
    When active, it will use mem0 to add context to prompts.
    """

    # Valves are configurations set by the Open WebUI admin.
    class Valves(BaseModel):
        # Example of a numerical valve
        top_k_memories: int = Field(
            default=3,
            description="Number of relevant memories to retrieve from mem0."
        )
        # Example of a multiple-choice valve
        mem0_llm_model: Literal["ollama/llama3", "ollama/mistral"] = Field(
            default="ollama/llama3",
            description="The Ollama model to use for mem0 processing.",
        )
        # Priority determines the execution order of multiple filters
        priority: int = Field(
            default=0,
            description="Priority level for the filter. Lower values run first."
        )
        pass

    # UserValves are configurations that each user can set for themselves.
    class UserValves(BaseModel):
        user_specific_memory_tag: str = Field(
            default="",
            description="A specific tag to filter memories for this user."
        )
        pass

    def __init__(self):
        """
        Initializes the filter, setting up the toggle switch and its icon.
        """
        self.valves = self.Valves()
        
        # This attribute creates a toggle switch in the Open WebUI interface.
        self.toggle = True 
        
        # The icon for the toggle switch, using SVG Data URI.
        self.icon = """data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGZpbGw9Im5vbmUiIHZpZXdCb3g9IjAgMCAyNCAyNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZT0iY3VycmVudENvbG9yIiBjbGFzcz0ic2l6ZS02Ij4KICA8cGF0aCBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiIGQ9Ik0xMiAxOHYtNS4yNW0wIDBhNi4wMSA2LjAxIDAgMCAwIDEuNS0uMTg5bS0xLjUuMTg5YTYuMDEgNi4wMSAwIDAgMS0xLjUtLjE4OW0zLjc1IDcuNDc4YTEyLjA2IDEyLjA2IDAgMCAxLTQuNSAwbTMuNzUgMi4zODNhMTQuNDA2IDE0LjQwNiAwIDAgMS0zIDBNMTQuMjUgMTh2LS4xOTJjMC0uOTgzLjY1OC0xLjgyMyAxLjUwOC0yLjMxNmE3LjUgNy41IDAgMSAwLTcuNTE3IDBjLjg1LjQ5MyAxLjUwOSAxLjMzMyAxLjUwOSAyLjMxNlYxOCIgLz4KPC9zdmc+Cg=="""
        
        # Placeholder for mem0 client. Initialization should be handled carefully
        # to avoid re-creating the client on every request.
        self.mem0_client = None
        print("Mem0 Filter initialized.")
        pass

    def setup(self):
        """
        This method is called once when the function is first loaded.
        Use it to initialize clients and other one-time setup tasks.
        """
        # from mem0 import Memory
        # from mem0.embeddings import OllamaEmbeddings
        # from mem0.vector_stores import QdrantVectorStore
        
        # print("Initializing mem0 client...")
        # self.mem0_client = Memory(
        #     vector_store=QdrantVectorStore(config={"host": "localhost", "port": 6333}),
        #     embedder=OllamaEmbeddings(model=self.valves.mem0_llm_model)
        # )
        # print("Mem0 client initialized successfully.")
        pass


    async def inlet(self, body: dict, __event_emitter__, user: Optional[dict] = None) -> dict:
        """
        This method is called when the toggle is ON.
        It processes incoming messages before they are sent to the LLM.
        """
        
        # Safely handle the user object to prevent errors when it's None.
        safe_user = user if user is not None else {}
        
        # User-specific valves are accessed from the 'user' dictionary
        user_valves = self.UserValves(**safe_user.get("valves", {}))
        user_tag = user_valves.user_specific_memory_tag
        
        print(f"Mem0 Filter inlet triggered for user: {safe_user.get('name')}")
        print(f"Admin valves: {self.valves}")
        print(f"User valves: {user_valves}")


        # You can emit status updates to the UI.
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": f"Processing with mem0 (Top K: {self.valves.top_k_memories})...",
                    "done": False, # Show as in-progress
                    "hidden": False,
                },
            }
        )

        # This is where you would add the logic to interact with mem0.
        # For example:
        # 1. Get the last user message.
        # 2. Search for relevant memories in mem0.
        # 3. Prepend the memories to the user's message as context.
        # 4. Add the new message to mem0.

        # try:
        #     if not self.mem0_client:
        #         self.setup()

        #     last_message = body["messages"][-1]["content"]
        #     user_id = safe_user.get("id")

        #     # Search for memories
        #     memories = self.mem0_client.search(
        #         query=last_message, 
        #         user_id=user_id, 
        #         limit=self.valves.top_k_memories,
        #         filters={"tag": user_tag} if user_tag else None
        #     )
            
        #     # Add memories to context
        #     if memories:
        #         context_header = "Here is some relevant context from past conversations:\n"
        #         context = "\n".join([m['text'] for m in memories])
        #         body["messages"][-1]["content"] = f"{context_header}{context}\n\nUser message: {last_message}"

        #     # Add current interaction to memory
        #     self.mem0_client.add(last_message, user_id=user_id, metadata={"tag": user_tag})
            
        #     await __event_emitter__({ "type": "status", "data": { "description": "Mem0 context added.", "done": True }})
        # except Exception as e:
        #     print(f"Error in mem0 filter: {e}")
        #     await __event_emitter__({ "type": "status", "data": { "description": f"Error: {e}", "done": True }})

        
        # For now, just returning the body as is.
        # The commented-out code above shows a potential implementation.
        return body
