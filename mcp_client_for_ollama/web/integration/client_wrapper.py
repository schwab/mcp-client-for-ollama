"""Web wrapper for MCPClient to work with Flask"""
import asyncio
from typing import Optional, Dict, List, AsyncIterator
from contextlib import suppress
import ollama


class WebMCPClient:
    """Wrapper for MCPClient to work with Flask web interface"""

    def __init__(self, session_id: str, config: Optional[Dict] = None):
        self.session_id = session_id
        self.config = config or {}
        self.chat_history: List[Dict] = []
        self.current_model = self.config.get('model', 'llama3.2:latest')
        self.ollama_host = self.config.get('ollama_host', 'http://localhost:11434')
        self.ollama_client = ollama.AsyncClient(host=self.ollama_host)
        self._loop = None
        self._initialized = False

    async def initialize(self):
        """Initialize the client"""
        self._initialized = True
        # For MVP, we'll use a simple ollama client
        # Future enhancement: integrate full MCPClient with MCP servers
        return True

    async def send_message_streaming(self, message: str) -> AsyncIterator[str]:
        """Send message and yield streaming response chunks"""
        if not self._initialized:
            await self.initialize()

        # Add user message to history
        self.chat_history.append({
            "role": "user",
            "content": message
        })

        # Prepare messages for ollama (use last 20 messages for context)
        context_messages = self.chat_history[-20:]

        try:
            # Stream response from Ollama
            stream = await self.ollama_client.chat(
                model=self.current_model,
                messages=context_messages,
                stream=True
            )

            # Accumulate full response for history
            full_response = ""

            async for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    full_response += content
                    yield content

            # Add assistant response to history
            self.chat_history.append({
                "role": "assistant",
                "content": full_response
            })

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield error_msg
            self.chat_history.append({
                "role": "assistant",
                "content": error_msg
            })

    async def get_models(self) -> List[Dict]:
        """Get available Ollama models"""
        try:
            models = await self.ollama_client.list()
            return models.get('models', [])
        except Exception as e:
            return []

    def set_model(self, model_name: str):
        """Set current model"""
        self.current_model = model_name

    def get_model(self) -> str:
        """Get current model"""
        return self.current_model

    def get_history(self) -> List[Dict]:
        """Get chat history"""
        return self.chat_history

    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []

    async def cleanup(self):
        """Cleanup resources"""
        self._initialized = False
        with suppress(Exception):
            # Close ollama client if needed
            pass
