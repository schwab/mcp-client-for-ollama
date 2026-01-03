"""Web wrapper for MCPClient to work with Flask"""
import asyncio
from typing import Optional, Dict, List, AsyncIterator
from contextlib import suppress
import ollama
from rich.console import Console


class WebMCPClient:
    """Wrapper for MCPClient to work with Flask web interface"""

    def __init__(self, session_id: str, config: Optional[Dict] = None):
        self.session_id = session_id
        self.config = config or {}
        self.chat_history: List[Dict] = []
        self.current_model = self.config.get('model', 'llama3.2:latest')
        self.ollama_host = self.config.get('ollama_host', 'http://localhost:11434')
        self.config_dir = self.config.get('config_dir')  # Config directory for loading settings
        self._ollama_client = None  # Create lazily
        self._loop = None
        self._initialized = False
        self._mcp_client = None  # Real MCP client for tool management
        self._tools_cache = None  # Cache tools list

    def _get_ollama_client(self):
        """Get or create ollama client in current event loop"""
        # Always create a new client to ensure it's in the current event loop
        return ollama.AsyncClient(host=self.ollama_host)

    async def initialize(self):
        """Initialize the client and load MCP tools"""
        if self._initialized:
            return True

        self._initialized = True

        # Initialize real MCP client for tool management
        try:
            from mcp_client_for_ollama.client import MCPClient

            # Create MCP client with correct parameters (model, host, config_dir)
            self._mcp_client = MCPClient(
                model=self.current_model,
                host=self.ollama_host,
                config_dir=self.config_dir
            )

            # Connect to MCP servers with auto-discovery enabled
            # This will load tools from MCP servers configured in the user's config
            await self._mcp_client.connect_to_servers(auto_discovery=True)

            # Load tools from the tool manager (includes both MCP server tools and built-in tools)
            await self._load_tools()

        except Exception as e:
            # If MCP initialization fails, continue without tools
            import traceback
            print(f"ERROR: Could not initialize MCP client for tools: {e}")
            print("Traceback:")
            traceback.print_exc()
            self._mcp_client = None
            self._tools_cache = []

        return True

    async def _load_tools(self):
        """Load tools from MCP client's tool manager"""
        if not self._mcp_client or not hasattr(self._mcp_client, 'tool_manager'):
            print("WARNING: No MCP client or tool_manager available")
            self._tools_cache = []
            return

        tool_manager = self._mcp_client.tool_manager
        print(f"Loading tools from tool_manager, available_tools: {len(tool_manager.available_tools)}")

        # Get all available tools with their status
        tools_list = []
        for tool in tool_manager.available_tools:
            tools_list.append({
                "name": tool.name,
                "description": tool.description or "No description",
                "enabled": tool_manager.enabled_tools.get(tool.name, False)
            })

        self._tools_cache = tools_list
        print(f"Loaded {len(tools_list)} tools: {[t['name'] for t in tools_list]}")

    async def send_message_streaming(self, message: str, status_queue=None) -> AsyncIterator[str]:
        """Send message and yield streaming response chunks

        Args:
            message: User message
            status_queue: Optional queue for sending status updates (status, agent_update, heartbeat)
        """
        if not self._initialized:
            await self.initialize()

        # Helper to send status updates
        def send_status(msg: str, msg_type: str = 'status'):
            if status_queue:
                status_queue.put((msg_type, msg))

        try:
            # Check if delegation is enabled and use appropriate processing method
            if self._mcp_client:
                # Add message to MCPClient's chat history for context
                # Note: MCPClient maintains its own chat history

                # Check if delegation is enabled
                use_delegation = self._mcp_client.is_delegation_enabled()

                if use_delegation:
                    send_status("🤖 Initializing delegation system...", 'status')

                    # Use delegation system (planner + agents)
                    # We need to intercept console output to show agent activity
                    from io import StringIO
                    import sys
                    from rich.console import Console

                    # Create a custom console that captures output
                    captured_output = StringIO()
                    capture_console = Console(file=captured_output, width=120)

                    # Replace MCPClient's console temporarily
                    original_console = self._mcp_client.console
                    self._mcp_client.console = capture_console

                    send_status("📋 Starting planning process...", 'status')

                    try:
                        # Get delegation client
                        delegation_client = self._mcp_client.get_delegation_client()

                        # Start a heartbeat task to prevent timeout
                        import asyncio
                        heartbeat_task = None
                        stop_heartbeat = False

                        async def send_heartbeats():
                            while not stop_heartbeat:
                                send_status("", 'heartbeat')
                                await asyncio.sleep(5)  # Every 5 seconds

                        heartbeat_task = asyncio.create_task(send_heartbeats())

                        # Process with delegation (includes full planner system)
                        response = await delegation_client.process_with_delegation(
                            message,
                            self._mcp_client.chat_history
                        )

                        # Stop heartbeat
                        stop_heartbeat = True
                        if heartbeat_task:
                            heartbeat_task.cancel()
                            try:
                                await heartbeat_task
                            except asyncio.CancelledError:
                                pass

                        # Get captured console output
                        console_output = captured_output.getvalue()
                        if console_output:
                            # Send console output as agent updates
                            for line in console_output.split('\n'):
                                if line.strip():
                                    send_status(line, 'agent_update')

                    finally:
                        # Restore original console
                        self._mcp_client.console = original_console

                    send_status("✅ Planning complete, generating response...", 'status')

                    # Yield response in chunks to simulate streaming
                    chunk_size = 50
                    for i in range(0, len(response), chunk_size):
                        yield response[i:i+chunk_size]

                else:
                    send_status("🔧 Processing query with tools...", 'status')

                    # Use standard process_query (handles tools but no delegation)
                    response = await self._mcp_client.process_query(message)

                    send_status("✅ Query processed", 'status')

                    # Yield response in chunks to simulate streaming
                    chunk_size = 50
                    for i in range(0, len(response), chunk_size):
                        yield response[i:i+chunk_size]

                # Add to local chat history for display
                self.chat_history.append({"role": "user", "content": message})
                self.chat_history.append({"role": "assistant", "content": response})

            else:
                # Fallback: No MCP client, just use basic ollama
                self.chat_history.append({"role": "user", "content": message})
                context_messages = self.chat_history[-20:]

                client = self._get_ollama_client()
                stream = await client.chat(
                    model=self.current_model,
                    messages=context_messages,
                    stream=True
                )

                full_response = ""
                async for chunk in stream:
                    if 'message' in chunk and 'content' in chunk['message']:
                        content = chunk['message']['content']
                        full_response += content
                        yield content

                self.chat_history.append({"role": "assistant", "content": full_response})

                # Close the client
                with suppress(Exception):
                    if hasattr(client, '_client') and hasattr(client._client, 'aclose'):
                        await client._client.aclose()

        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            print(f"ERROR in send_message_streaming: {error_msg}")
            yield f"Error: {str(e)}"
            self.chat_history.append({"role": "assistant", "content": f"Error: {str(e)}"})

    async def get_models(self) -> List[Dict]:
        """Get available Ollama models"""
        try:
            client = self._get_ollama_client()
            models = await client.list()
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

    def get_tools(self) -> List[Dict]:
        """Get all available tools with their status"""
        if self._tools_cache is None:
            return []
        return self._tools_cache

    def set_tool_enabled(self, tool_name: str, enabled: bool) -> bool:
        """Enable or disable a tool"""
        if not self._mcp_client or not hasattr(self._mcp_client, 'tool_manager'):
            return False

        tool_manager = self._mcp_client.tool_manager

        # Update the tool status in the tool manager
        if tool_name in tool_manager.enabled_tools:
            tool_manager.enabled_tools[tool_name] = enabled
            tool_manager._notify_server_connector(tool_name, enabled)

            # Update cache
            if self._tools_cache:
                for tool in self._tools_cache:
                    if tool['name'] == tool_name:
                        tool['enabled'] = enabled
                        break

            return True
        return False

    def get_enabled_tools(self) -> List[Dict]:
        """Get list of enabled tools"""
        return [tool for tool in self.get_tools() if tool['enabled']]

    def get_disabled_tools(self) -> List[Dict]:
        """Get list of disabled tools"""
        return [tool for tool in self.get_tools() if not tool['enabled']]

    async def reload_servers(self):
        """Reload MCP servers with auto-discovery"""
        if not self._mcp_client:
            raise Exception("MCP client not initialized")

        # Disconnect from existing servers
        if hasattr(self._mcp_client, 'disconnect_from_servers'):
            await self._mcp_client.disconnect_from_servers()

        # Reconnect with auto-discovery
        await self._mcp_client.connect_to_servers(auto_discovery=True)

        # Reload tools
        await self._load_tools()

    def get_servers(self) -> List[str]:
        """Get list of connected MCP servers"""
        if not self._mcp_client:
            return []

        # Get server names from the MCP client's server connector
        if hasattr(self._mcp_client, 'server_connector') and self._mcp_client.server_connector:
            connector = self._mcp_client.server_connector
            if hasattr(connector, 'servers'):
                return list(connector.servers.keys())

        return []

    async def cleanup(self):
        """Cleanup resources"""
        self._initialized = False
        with suppress(Exception):
            # Cleanup MCP client if it exists
            if self._mcp_client:
                await self._mcp_client.cleanup()
                self._mcp_client = None
