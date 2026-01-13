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
        self.memory_domain = None  # Will be set when memory session is created

        # Create persistent config directory for this session
        # This directory will be used for memory storage and persist across requests
        import tempfile
        import os
        import json

        provided_config_dir = self.config.get('config_dir')
        if provided_config_dir:
            self.config_dir = provided_config_dir
            self._owns_config_dir = False
        else:
            # Create a persistent temp directory for this session
            # Use /tmp/mcp_web_sessions/ to keep sessions organized
            session_dir = os.path.join("/tmp", "mcp_web_sessions", session_id)
            os.makedirs(session_dir, exist_ok=True)
            self.config_dir = session_dir
            self._owns_config_dir = True

            # Create config.json with memory enabled
            config_data = {
                "memory": {
                    "enabled": True,
                    "storage_dir": os.path.join(session_dir, "memory"),
                    "default_domain": "web"
                }
            }
            config_path = os.path.join(session_dir, "config.json")
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)

        self._ollama_client = None  # Create lazily
        self._loop = None
        self._initialized = False
        self._mcp_client = None  # Real MCP client for tool management
        self._tools_cache = None  # Cache tools list

    def _get_ollama_client(self):
        """Get or create ollama client in current event loop"""
        # Always create a new client to ensure it's in the current event loop
        return ollama.AsyncClient(host=self.ollama_host)

    async def _create_mcp_client(self):
        """Create a fresh MCP client for this request (to avoid event loop issues)"""
        try:
            from mcp_client_for_ollama.client import MCPClient
            import os

            # Use the persistent config_dir created in __init__
            # This ensures memory storage persists across requests within the same session
            config_dir_to_use = self.config_dir

            # Create MCP client with correct parameters (model, host)
            # Note: MCPClient doesn't accept config_dir in __init__
            # We'll pass config path to connect_to_servers() below
            mcp_client = MCPClient(
                model=self.current_model,
                host=self.ollama_host
            )

            # Disable Human-in-the-Loop prompts for web interface
            # Web users can't respond to CLI prompts, so we auto-approve all actions
            if hasattr(mcp_client, 'hil_manager'):
                mcp_client.hil_manager._set_global_enabled(False)

            # Connect to MCP servers with auto-discovery enabled
            # This will load tools from MCP servers configured in the user's config
            config_path = os.path.join(config_dir_to_use, 'config.json')
            if not os.path.exists(config_path):
                config_path = None

            await mcp_client.connect_to_servers(
                config_path=config_path,
                auto_discovery=True
            )

            # Enable memory programmatically by getting delegation client
            # This will read the memory config from config.json
            delegation_client = mcp_client.get_delegation_client()

            return mcp_client

        except Exception as e:
            # If MCP initialization fails, return None
            import traceback
            print(f"ERROR: Could not create MCP client: {e}")
            print("Traceback:")
            traceback.print_exc()
            return None

    async def initialize(self):
        """Initialize the client and load MCP tools (tool list only)"""
        if self._initialized:
            return True

        self._initialized = True

        # Create a temporary MCP client just to load the tools list
        # We'll create fresh clients for each request to avoid event loop issues
        temp_client = await self._create_mcp_client()
        if temp_client:
            self._mcp_client = temp_client
            await self._load_tools()
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            self._mcp_client = None
        else:
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
            # Create a fresh MCP client for this request to avoid event loop issues
            # Each SSE request runs in its own event loop, so we need a fresh client
            send_status("🔧 Initializing MCP client...", 'status')
            mcp_client = await self._create_mcp_client()

            if mcp_client:
                # Add previous conversation history to the fresh MCP client
                # This ensures context is maintained across requests
                if self.chat_history:
                    # Copy our persistent chat history to the fresh MCP client
                    mcp_client.chat_history = self.chat_history.copy()

                # Check if delegation is enabled
                use_delegation = mcp_client.is_delegation_enabled()

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
                    original_console = mcp_client.console
                    mcp_client.console = capture_console

                    send_status("📋 Starting planning process...", 'status')

                    try:
                        # Get delegation client
                        delegation_client = mcp_client.get_delegation_client()

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
                            mcp_client.chat_history
                        )

                    except RuntimeError as e:
                        # Handle event loop issues by falling back to non-delegation mode
                        if "Event loop is closed" in str(e) or "no running event loop" in str(e):
                            send_status("⚠️  Event loop error, falling back to direct query mode...", 'status')
                            # Fall back to non-delegation mode
                            response = await mcp_client.process_query(message)
                        else:
                            raise
                    finally:
                        # Stop heartbeat
                        stop_heartbeat = True
                        if heartbeat_task:
                            heartbeat_task.cancel()
                            try:
                                await heartbeat_task
                            except (asyncio.CancelledError, NameError):
                                # NameError if heartbeat_task wasn't created due to error
                                pass

                        # Get captured console output
                        console_output = captured_output.getvalue()
                        if console_output:
                            # Send console output as agent updates
                            for line in console_output.split('\n'):
                                if line.strip():
                                    send_status(line, 'agent_update')

                        # Restore original console
                        mcp_client.console = original_console

                    send_status("✅ Planning complete, generating response...", 'status')

                    # Yield response in chunks to simulate streaming
                    chunk_size = 50
                    for i in range(0, len(response), chunk_size):
                        yield response[i:i+chunk_size]

                else:
                    send_status("🔧 Processing query with tools...", 'status')

                    # Use standard process_query (handles tools but no delegation)
                    response = await mcp_client.process_query(message)

                    send_status("✅ Query processed", 'status')

                    # Yield response in chunks to simulate streaming
                    chunk_size = 50
                    for i in range(0, len(response), chunk_size):
                        yield response[i:i+chunk_size]

                # Add to local chat history for display
                self.chat_history.append({"role": "user", "content": message})
                self.chat_history.append({"role": "assistant", "content": response})

                # Don't cleanup MCP client here - causes "Event loop closed" errors
                # The client will be garbage collected when no longer referenced
                # Cleanup only happens when the session itself is deleted

            else:
                # Fallback: No MCP client, just use basic ollama
                send_status("🔗 Connecting to Ollama...", 'status')
                self.chat_history.append({"role": "user", "content": message})
                context_messages = self.chat_history[-20:]

                try:
                    client = self._get_ollama_client()
                    send_status(f"📡 Sending request to model {self.current_model}...", 'status')
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
                    error_msg = f"❌ Failed to connect to Ollama at {self.ollama_host}: {str(e)}"
                    print(f"ERROR: {error_msg}")
                    yield error_msg
                    self.chat_history.append({"role": "assistant", "content": error_msg})

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
        # TODO: Implement config persistence for tool enabled/disabled state
        # Since we create fresh MCP clients for each request, we need to save
        # the tool state to config.json and load it when creating clients
        raise NotImplementedError(
            "Tool enable/disable persistence not yet implemented. "
            "This requires saving to config.json which is tracked in bug: "
            "'Tool selections not saving to config for the ui'"
        )

    def get_enabled_tools(self) -> List[Dict]:
        """Get list of enabled tools"""
        return [tool for tool in self.get_tools() if tool['enabled']]

    def get_disabled_tools(self) -> List[Dict]:
        """Get list of disabled tools"""
        return [tool for tool in self.get_tools() if not tool['enabled']]

    async def reload_servers(self):
        """Reload MCP servers with auto-discovery"""
        # Create a temporary MCP client to reload the tools list
        temp_client = await self._create_mcp_client()
        if temp_client:
            self._mcp_client = temp_client
            await self._load_tools()
            # Don't call cleanup() here - it causes cancel scope errors
            # when called from a different async context (Flask request).
            # The temp client will be garbage collected automatically.
            # Cleanup will happen when the WebMCPClient session is destroyed.
            self._mcp_client = None
        else:
            raise Exception("Failed to create MCP client for server reload")

    def get_servers(self) -> List[str]:
        """Get list of connected MCP servers"""
        # Extract unique server names from the tools cache
        # Tool names are in format "server_name.tool_name"
        servers = set()
        for tool in self._tools_cache or []:
            tool_name = tool.get('name', '')
            if '.' in tool_name:
                server_name = tool_name.split('.')[0]
                if server_name != 'builtin':
                    servers.add(server_name)
        return sorted(list(servers))

    async def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Execute a tool by name with the given arguments.

        Args:
            tool_name: Fully qualified tool name (e.g., "builtin.list_files" or "server.tool_name")
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Tool execution result as a string

        Raises:
            ValueError: If tool name format is invalid
            Exception: If tool execution fails
        """
        # Create a temporary MCP client for tool execution
        temp_client = await self._create_mcp_client()
        if not temp_client:
            raise Exception("Could not create MCP client for tool execution")

        try:
            # Execute the tool using the MCP client's execute_tool method
            result = await temp_client.execute_tool(tool_name, arguments)
            return result
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    # ========================================================================
    # MEMORY MANAGEMENT METHODS
    # ========================================================================

    async def get_memory_status(self) -> Optional[Dict]:
        """Get current memory session status"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return None

        try:
            # Check if memory is enabled
            if not hasattr(temp_client, 'memory_tools') or not temp_client.memory_tools:
                return {'active': False, 'message': 'Memory not enabled for this session'}

            # Call builtin.get_memory_state via tool
            from mcp_client_for_ollama.tools.manager import ToolCall
            result = await temp_client.call_tool('builtin.get_memory_state', {})

            # Parse the result and format for API
            # TODO: Parse the text result into structured data
            return {
                'active': True,
                'raw_state': result,
                'session_id': self.session_id
            }
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def create_memory_session(self, domain: str, description: str) -> Dict:
        """Create new memory session"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return {'error': 'Memory system is not enabled in configuration'}

            # Set current session on memory tools
            delegation_client.memory_tools.set_current_session(self.session_id, domain)

            # Create new memory via storage
            from mcp_client_for_ollama.memory.base_memory import DomainMemory, MemoryMetadata
            from datetime import datetime

            metadata = MemoryMetadata(
                session_id=self.session_id,
                domain=domain,
                description=description,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            memory = DomainMemory(metadata=metadata, goals=[])
            delegation_client.memory_tools.storage.save_memory(memory)

            # Store the domain for future operations
            self.memory_domain = domain

            return {
                'status': 'created',
                'domain': domain,
                'description': description,
                'session_id': self.session_id,
                'message': f'Memory session created for domain: {domain}'
            }
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def clear_memory(self) -> Dict:
        """Clear current memory session"""
        # TODO: Implement memory clearing
        return {
            'status': 'cleared',
            'message': 'Memory clearing not yet fully implemented'
        }

    async def export_memory(self) -> Dict:
        """Export memory session to JSON"""
        # TODO: Implement memory export
        return {
            'message': 'Memory export not yet fully implemented'
        }

    async def import_memory(self, memory_data: Dict) -> Dict:
        """Import memory session from JSON"""
        # TODO: Implement memory import
        return {
            'status': 'imported',
            'message': 'Memory import not yet fully implemented'
        }

    async def list_goals(self) -> List[Dict]:
        """List all goals with summary"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return []

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return []

            # Use stored domain if available, otherwise try to auto-detect or use default
            domain = self.memory_domain
            if not domain:
                # Try to auto-detect domain by checking common domains
                # Or use default "web" domain
                domain = "web"

            # Load memory directly from storage using session_id and domain
            memory = delegation_client.memory_tools.storage.load_memory(
                self.session_id,
                domain
            )

            if not memory:
                return []

            # Convert goals to dict format for JSON serialization
            goals_list = []
            for goal in memory.goals:
                goal_dict = {
                    'goal_id': goal.id,
                    'id': goal.id,
                    'description': goal.description,
                    'status': goal.status.value if hasattr(goal.status, 'value') else str(goal.status),
                    'constraints': goal.constraints,
                    'features': []
                }

                # Add features for this goal
                for feature in goal.features:
                    feature_dict = {
                        'feature_id': feature.id,
                        'id': feature.id,
                        'description': feature.description,
                        'status': feature.status.value if hasattr(feature.status, 'value') else str(feature.status),
                        'priority': feature.priority,
                        'assigned_to': feature.assigned_to,
                        'criteria': feature.criteria,
                        'tests': feature.tests,
                        'test_results': [
                            {
                                'test_id': tr.test_id,
                                'passed': tr.passed,
                                'timestamp': tr.timestamp.isoformat() if hasattr(tr.timestamp, 'isoformat') else str(tr.timestamp),
                                'details': tr.details,
                                'output': tr.output
                            }
                            for tr in feature.test_results
                        ] if hasattr(feature, 'test_results') else []
                    }
                    goal_dict['features'].append(feature_dict)

                goals_list.append(goal_dict)

            return goals_list
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def get_goal(self, goal_id: str) -> Optional[Dict]:
        """Get detailed goal information"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return None

        try:
            if not hasattr(temp_client, 'memory_tools') or not temp_client.memory_tools:
                return None

            # Call builtin.get_goal_details
            result = await temp_client.call_tool('builtin.get_goal_details', {'goal_id': goal_id})

            # TODO: Parse result into structured dict
            return {'raw': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def create_goal(self, goal_id: Optional[str], description: str, constraints: List[str]) -> Dict:
        """Create new goal"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return {'error': 'Memory system is not enabled'}

            # Use stored domain if available, otherwise use default
            domain = self.memory_domain if self.memory_domain else "web"

            # Try to load existing memory session from storage
            memory = delegation_client.memory_tools.storage.load_memory(
                self.session_id,
                domain
            )

            if not memory:
                return {'error': 'No active memory session. Create a session first.'}

            # Set the current session so memory_tools knows which session to use
            delegation_client.memory_tools.set_current_session(self.session_id, domain)

            # Call add_goal via memory_tools directly for reliability
            result = delegation_client.memory_tools.add_goal(
                goal_id=goal_id,
                description=description,
                constraints=constraints or []
            )

            # Check if result indicates error
            if result.startswith('Error:'):
                return {'error': result}

            return {'status': 'created', 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def update_goal(self, goal_id: str, description: Optional[str] = None,
                         add_constraints: Optional[List[str]] = None,
                         remove_constraints: Optional[List[str]] = None) -> Dict:
        """Update existing goal"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return {'error': 'Memory system is not enabled'}

            # Use stored domain if available, otherwise use default
            domain = self.memory_domain if self.memory_domain else "web"

            # Try to load existing memory session from storage
            memory = delegation_client.memory_tools.storage.load_memory(
                self.session_id,
                domain
            )

            if not memory:
                return {'error': 'No active memory session. Create a session first.'}

            # Set the current session so memory_tools knows which session to use
            delegation_client.memory_tools.set_current_session(self.session_id, domain)

            # Call update_goal via memory_tools directly for reliability
            result = delegation_client.memory_tools.update_goal(
                goal_id=goal_id,
                description=description,
                add_constraints=add_constraints,
                remove_constraints=remove_constraints
            )

            # Check if result indicates error
            if result.startswith('Error:'):
                return {'error': result}

            return {'status': 'updated', 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def delete_goal(self, goal_id: str, confirm: bool = False) -> Dict:
        """Delete goal"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return {'error': 'Memory system is not enabled'}

            # Use stored domain if available, otherwise use default
            domain = self.memory_domain if self.memory_domain else "web"

            # Try to load existing memory session from storage
            memory = delegation_client.memory_tools.storage.load_memory(
                self.session_id,
                domain
            )

            if not memory:
                return {'error': 'No active memory session. Create a session first.'}

            # Set the current session so memory_tools knows which session to use
            delegation_client.memory_tools.set_current_session(self.session_id, domain)

            # Call remove_goal via memory_tools directly for reliability
            result = delegation_client.memory_tools.remove_goal(
                goal_id=goal_id,
                confirm=confirm
            )

            # Check if result indicates error
            if result.startswith('Error:'):
                return {'error': result}

            return {'status': 'deleted' if confirm else 'confirm_required', 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def get_feature(self, feature_id: str) -> Optional[Dict]:
        """Get detailed feature information"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return None

        try:
            if not hasattr(temp_client, 'memory_tools') or not temp_client.memory_tools:
                return None

            # Call builtin.get_feature_details
            result = await temp_client.call_tool('builtin.get_feature_details', {'feature_id': feature_id})

            # TODO: Parse result into structured dict
            return {'raw': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def create_feature(self, goal_id: str, description: str, criteria: List[str] = None,
                            tests: List[str] = None, priority: str = 'medium',
                            assigned_to: Optional[str] = None) -> Dict:
        """Create new feature"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return {'error': 'Memory system is not enabled'}

            # Use stored domain if available, otherwise use default
            domain = self.memory_domain if self.memory_domain else "web"

            # Try to load existing memory session from storage
            memory = delegation_client.memory_tools.storage.load_memory(
                self.session_id,
                domain
            )

            if not memory:
                return {'error': 'No active memory session. Create a session first.'}

            # Set the current session so memory_tools knows which session to use
            delegation_client.memory_tools.set_current_session(self.session_id, domain)

            # Call add_feature via memory_tools directly for reliability
            result = delegation_client.memory_tools.add_feature(
                goal_id=goal_id,
                description=description,
                criteria=criteria or [],
                tests=tests or [],
                priority=priority,
                assigned_to=assigned_to
            )

            # Check if result indicates error
            if result.startswith('Error:'):
                return {'error': result}

            return {'status': 'created', 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def update_feature(self, feature_id: str, **kwargs) -> Dict:
        """Update existing feature"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return {'error': 'Memory system is not enabled'}

            # Use stored domain if available, otherwise use default
            domain = self.memory_domain if self.memory_domain else "web"

            # Try to load existing memory session from storage
            memory = delegation_client.memory_tools.storage.load_memory(
                self.session_id,
                domain
            )

            if not memory:
                return {'error': 'No active memory session. Create a session first.'}

            # Set the current session so memory_tools knows which session to use
            delegation_client.memory_tools.set_current_session(self.session_id, domain)

            # Call update_feature via memory_tools directly for reliability
            result = delegation_client.memory_tools.update_feature(
                feature_id=feature_id,
                description=kwargs.get('description'),
                add_criteria=kwargs.get('add_criteria'),
                remove_criteria=kwargs.get('remove_criteria'),
                add_tests=kwargs.get('add_tests'),
                remove_tests=kwargs.get('remove_tests'),
                priority=kwargs.get('priority'),
                assigned_to=kwargs.get('assigned_to')
            )

            # Check if result indicates error
            if result.startswith('Error:'):
                return {'error': result}

            return {'status': 'updated', 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def update_feature_status(self, feature_id: str, status: str, notes: Optional[str] = None) -> Dict:
        """Quick status update for feature"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return {'error': 'Memory system is not enabled'}

            # Use stored domain if available, otherwise use default
            domain = self.memory_domain if self.memory_domain else "web"

            # Try to load existing memory session from storage
            memory = delegation_client.memory_tools.storage.load_memory(
                self.session_id,
                domain
            )

            if not memory:
                return {'error': 'No active memory session. Create a session first.'}

            # Set the current session so memory_tools knows which session to use
            delegation_client.memory_tools.set_current_session(self.session_id, domain)

            # Call update_feature_status via memory_tools directly for reliability
            result = delegation_client.memory_tools.update_feature_status(
                feature_id=feature_id,
                status=status,
                notes=notes
            )

            # Check if result indicates error
            if result.startswith('Error:'):
                return {'error': result}

            return {'status': 'updated', 'new_status': status, 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def delete_feature(self, feature_id: str, confirm: bool = False) -> Dict:
        """Delete feature"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return {'error': 'Memory system is not enabled'}

            # Use stored domain if available, otherwise use default
            domain = self.memory_domain if self.memory_domain else "web"

            # Try to load existing memory session from storage
            memory = delegation_client.memory_tools.storage.load_memory(
                self.session_id,
                domain
            )

            if not memory:
                return {'error': 'No active memory session. Create a session first.'}

            # Set the current session so memory_tools knows which session to use
            delegation_client.memory_tools.set_current_session(self.session_id, domain)

            # Call remove_feature via memory_tools directly for reliability
            result = delegation_client.memory_tools.remove_feature(
                feature_id=feature_id,
                confirm=confirm
            )

            # Check if result indicates error
            if result.startswith('Error:'):
                return {'error': result}

            return {'status': 'deleted' if confirm else 'confirm_required', 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def move_feature(self, feature_id: str, target_goal_id: str) -> Dict:
        """Move feature to different goal"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            # Check if memory is enabled
            delegation_client = temp_client.get_delegation_client()
            if not delegation_client or not delegation_client.memory_enabled:
                return {'error': 'Memory system is not enabled'}

            # Use stored domain if available, otherwise use default
            domain = self.memory_domain if self.memory_domain else "web"

            # Try to load existing memory session from storage
            memory = delegation_client.memory_tools.storage.load_memory(
                self.session_id,
                domain
            )

            if not memory:
                return {'error': 'No active memory session. Create a session first.'}

            # Set the current session so memory_tools knows which session to use
            delegation_client.memory_tools.set_current_session(self.session_id, domain)

            # Call move_feature via memory_tools directly for reliability
            result = delegation_client.memory_tools.move_feature(
                feature_id=feature_id,
                target_goal_id=target_goal_id
            )

            # Check if result indicates error
            if result.startswith('Error:'):
                return {'error': result}

            return {'status': 'moved', 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def log_progress(self, agent_type: str, action: str, outcome: str, details: str,
                          feature_id: Optional[str] = None, artifacts_changed: Optional[List[str]] = None) -> Dict:
        """Log progress entry"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            if not hasattr(temp_client, 'memory_tools') or not temp_client.memory_tools:
                return {'error': 'Memory not enabled'}

            # Call builtin.log_progress
            args = {
                'agent_type': agent_type,
                'action': action,
                'outcome': outcome,
                'details': details
            }
            if feature_id:
                args['feature_id'] = feature_id
            if artifacts_changed:
                args['artifacts_changed'] = artifacts_changed

            result = await temp_client.call_tool('builtin.log_progress', args)

            return {'status': 'logged', 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def add_test_result(self, feature_id: str, test_id: str, passed: bool,
                             details: str = '', output: str = '') -> Dict:
        """Add test result to feature"""
        temp_client = await self._create_mcp_client()
        if not temp_client:
            return {'error': 'Could not create MCP client'}

        try:
            if not hasattr(temp_client, 'memory_tools') or not temp_client.memory_tools:
                return {'error': 'Memory not enabled'}

            # Call builtin.add_test_result
            result = await temp_client.call_tool('builtin.add_test_result', {
                'feature_id': feature_id,
                'test_id': test_id,
                'passed': passed,
                'details': details,
                'output': output
            })

            return {'status': 'added', 'message': result}
        finally:
            # Don't call cleanup() - causes cancel scope errors in Flask async context
            # Temp client will be garbage collected automatically
            pass

    async def cleanup(self):
        """Cleanup resources when session is deleted"""
        self._initialized = False

        # Don't call cleanup() on MCP client - causes cancel scope errors
        # Just set to None and let garbage collection handle it
        if self._mcp_client:
            self._mcp_client = None
