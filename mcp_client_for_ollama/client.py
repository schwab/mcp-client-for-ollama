"""MCP Client for Ollama - A TUI client for interacting with Ollama models and MCP servers"""
import asyncio
import os
import sys
import json
import re
from contextlib import AsyncExitStack
from typing import List, Optional

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
import ollama

from . import __version__
from .config.manager import ConfigManager
from .utils.version import check_for_updates
from .utils.constants import DEFAULT_CLAUDE_CONFIG, DEFAULT_MODEL, DEFAULT_OLLAMA_HOST, DEFAULT_COMPLETION_STYLE
from .server.connector import ServerConnector
from .models.manager import ModelManager
from .models.config_manager import ModelConfigManager
from .tools.manager import ToolManager
from .tools.builtin import BuiltinToolManager
from .utils.streaming import StreamingManager
from .utils.tool_display import ToolDisplayManager
from .utils.hil_manager import HumanInTheLoopManager
from .utils.fzf_style_completion import FZFStyleCompleter
from .utils.tool_parser import ToolParser
from .agents.delegation_client import DelegationClient


class MCPClient:
    """Main client class for interacting with Ollama and MCP servers"""


    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_OLLAMA_HOST):
        # Initialize session and client objects
        self.exit_stack = AsyncExitStack()
        self.ollama = ollama.AsyncClient(host=host)
        self.console = Console()
        self.config_manager = ConfigManager(self.console)
        # Initialize the server connector
        self.server_connector = ServerConnector(self.exit_stack, self.console)
        # Initialize the model manager
        self.model_manager = ModelManager(console=self.console, default_model=model, ollama=self.ollama)
        # Initialize the model config manager
        self.model_config_manager = ModelConfigManager(console=self.console)
        # Initialize the built-in tool manager
        self.builtin_tool_manager = BuiltinToolManager(model_config_manager=self.model_config_manager)
        # Initialize the tool manager with server connector reference
        self.tool_manager = ToolManager(
            console=self.console, 
            server_connector=self.server_connector,
            model_config_manager=self.model_config_manager
        )
        # Initialize the streaming manager
        self.streaming_manager = StreamingManager(console=self.console)
        # Initialize the tool display manager
        self.tool_display_manager = ToolDisplayManager(console=self.console)
        # Initialize the HIL manager
        self.hil_manager = HumanInTheLoopManager(console=self.console, tool_manager=self.tool_manager)
        # Initialize the tool parser
        self.tool_parser = ToolParser()
        # Store server and tool data
        self.sessions = {}  # Dict to store multiple sessions
        # UI components
        self.chat_history = []  # Add chat history list to store interactions
        self.status_messages = [] # List to store temporary status/error messages for display in toolbar
        # Create keyboard bindings
        self.kb = self._create_key_bindings()
        # Command completer for interactive prompts
        self.prompt_session = PromptSession(
            completer=FZFStyleCompleter(sessions=self.sessions, console=self.console, status_messages=self.status_messages),
            style=Style.from_dict(DEFAULT_COMPLETION_STYLE),
            key_bindings=self.kb
        )
        # Context retention settings
        self.retain_context = True  # By default, retain conversation context
        self.actual_token_count = 0  # Actual token count from Ollama metrics
        # Thinking mode settings
        self.thinking_mode = True  # By default, thinking mode is enabled for models that support it
        self.show_thinking = False   # By default, thinking text is hidden after completion
        # Tool display settings
        self.show_tool_execution = True  # By default, show tool execution displays
        # Metrics display settings
        self.show_metrics = False  # By default, don't show metrics after each query
        # Agent mode settings
        self.loop_limit = 3  # Maximum follow-up tool loops per query
        self.default_configuration_status = False  # Track if default configuration was loaded successfully
        self.session_save_directory = ".config" # Session storage in .config subfolder of current directory

        # Plan/Act mode settings
        self.plan_mode = False  # By default, start in ACT mode
        self.act_mode_system_prompt = None  # Backup of the ACT mode system prompt
        # Tools that should be disabled in plan mode (write operations)
        self.plan_mode_disabled_tools = {
            "builtin.write_file",
            "builtin.execute_python_code",
            "builtin.execute_bash_command",
            "builtin.create_directory",
            "builtin.delete_file",
            "builtin.set_system_prompt"  # Disable system prompt changes in plan mode
        }

        # Track auto-loaded files for startup message
        self.auto_loaded_files = []

        # Quiet mode for non-interactive execution
        self.quiet_mode = False

        # Store server connection parameters for reloading
        self.server_connection_params = {
            'server_paths': None,
            'config_path': None,
            'auto_discovery': False
        }

        # Agent delegation settings
        self.delegation_client = None  # Lazy initialization
        self.delegation_enabled = False

    def _create_key_bindings(self) -> KeyBindings:
        """Create keyboard bindings for the application"""
        kb = KeyBindings()

        @kb.add('s-tab')  # Shift+Tab
        def _(event):
            """Toggle between PLAN and ACT modes"""
            # Clear current input and insert the toggle command
            event.app.current_buffer.text = '#TOGGLE_PLAN_MODE#'
            # Submit the command
            event.app.current_buffer.validate_and_handle()

        return kb

    def display_current_model(self):
        """Display the currently selected model"""
        self.model_manager.display_current_model()

    async def save_session(self):
        """Save the current chat history to a named session file using builtin file operations."""
        try:
            if not self.chat_history:
                self.console.print("[yellow]Chat history is empty. Nothing to save.[/yellow]")
                return

            session_name = await self.get_user_input("Session name (e.g., 'my-writing-session')")
            if not session_name:
                self.console.print("[yellow]Save cancelled.[/yellow]")
                return

            # Sanitize name to be a valid filename
            filename = "".join(c for c in session_name if c.isalnum() or c in ('-', '_')).rstrip()
            if not filename:
                self.console.print("[red]Invalid session name. Use letters, numbers, hyphens, or underscores.[/red]")
                return

            file_path = f"{self.session_save_directory}/{filename}.json"

            # Ensure directory exists using builtin tool
            dir_result = self.builtin_tool_manager.execute_tool('create_directory', {
                'path': self.session_save_directory
            })
            if "Error:" in dir_result and "already exists" not in dir_result:
                self.console.print(f"[yellow]Warning: {dir_result}[/yellow]")

            # Serialize chat history
            history_json = json.dumps(self.chat_history, indent=2)

            # Write file using builtin tool
            with self.console.status(f"[cyan]Saving session '{session_name}'...[/cyan]"):
                write_result = self.builtin_tool_manager.execute_tool(
                    'write_file',
                    {'path': file_path, 'content': history_json}
                )

            # Check for errors in the result
            if "Error:" in write_result:
                raise Exception(f"Failed to write session file: {write_result}")

            self.console.print(f"[green]Session '{session_name}' saved successfully to {file_path}[/green]")

        except Exception as e:
            self.console.print(f"[red]An error occurred while saving the session: {e}[/red]")

    async def load_project_context(self):
        """Load project context from .config/CLAUDE.md if it exists."""
        try:
            claude_md_path = f"{self.session_save_directory}/CLAUDE.md"

            # Check if the file exists
            exists_result = self.builtin_tool_manager.execute_tool('file_exists', {
                'path': claude_md_path
            })

            # If file doesn't exist, return silently
            if "does not exist" in exists_result or "Error:" in exists_result:
                return None

            # Read the CLAUDE.md file
            read_result = self.builtin_tool_manager.execute_tool('read_file', {
                'path': claude_md_path
            })

            # Check for errors
            if "Error:" in read_result:
                return None

            # Extract content
            if "Content:" in read_result:
                content = read_result.split("Content:")[1].strip()
            else:
                content = read_result

            return content

        except Exception as e:
            # Silently fail - this is optional functionality
            return None

    async def apply_project_context(self):
        """Load and apply project context from .config/CLAUDE.md to the system prompt.

        This should be called after other configuration is loaded so that the project
        context is prepended to any existing system prompt.
        """
        project_context = await self.load_project_context()
        if project_context:
            # Get current system prompt (if any)
            current_prompt = self.model_config_manager.get_system_prompt()

            # Prepend the project context to the system prompt
            # This gives project-specific context priority
            if current_prompt:
                combined_prompt = f"{project_context}\n\n{current_prompt}"
            else:
                combined_prompt = project_context

            self.model_config_manager.set_system_prompt(combined_prompt)

            # Track auto-loaded file
            self.auto_loaded_files.append(f"{self.session_save_directory}/CLAUDE.md")

            # Notify user that project context was loaded
            self.console.print(f"[green]📋 Loaded project context from {self.session_save_directory}/CLAUDE.md[/green]")

    async def load_session(self):
        """Load a chat history from a named session file using builtin file operations."""
        try:
            with self.console.status("[cyan]Fetching saved sessions...[/cyan]"):
                list_result = self.builtin_tool_manager.execute_tool(
                    'list_files',
                    {'path': self.session_save_directory}
                )

            session_items = []

            # Check if there was an error
            if "Error:" in list_result or "No files found" in list_result:
                # Directory might not exist or be empty
                if not session_items:
                    self.console.print(f"[yellow]No saved sessions found in {self.session_save_directory}[/yellow]")
                    return
            else:
                # Parse the list of files from the builtin tool result
                # The format is "Files in '...' (N files):\n  - file1.json\n  - file2.json"
                for line in list_result.split('\n'):
                    line = line.strip()
                    if line.startswith('- ') and line.endswith('.json'):
                        filename = line[2:].strip()  # Remove "- " prefix
                        session_items.append({'name': filename, 'type': 'file'})

            if not session_items:
                self.console.print(f"[yellow]No saved sessions found in {self.session_save_directory}[/yellow]")
                return

            self.clear_console()
            self.console.print(Panel("[bold]Load a Session[/bold]", border_style="blue"))
            
            for i, item in enumerate(session_items):
                display_name = item['name'].replace('.json', '')
                display_type = f"[{item.get('type', 'file').upper()}]"
                self.console.print(f"[magenta]{i + 1}[/magenta]. {display_type} {display_name}")
            
            self.console.print("\nEnter the number of the session to load, or 'q' to cancel.")

            while True:
                selection = await self.get_user_input("Load session")
                if not selection or selection.lower() in ['q', 'quit']:
                    self.clear_console()
                    self.display_available_tools()
                    self.display_current_model()
                    self._display_chat_history()
                    return
                
                try:
                    index = int(selection.strip()) - 1
                except (ValueError, TypeError):
                    self.console.print("[red]Invalid input. Please enter a number or 'q'.[/red]")
                    continue

                if 0 <= index < len(session_items):
                    try:
                        selected_filename = session_items[index]['name']
                        file_path = f"{self.session_save_directory}/{selected_filename}"

                        with self.console.status(f"[cyan]Loading session '{selected_filename.replace('.json', '')}'...[/cyan]"):
                            read_result = self.builtin_tool_manager.execute_tool(
                                'read_file',
                                {'path': file_path}
                            )

                        # Check for errors
                        if "Error:" in read_result:
                            raise Exception(f"Failed to read session file: {read_result}")

                        # Extract the JSON content from the result
                        # The format is "File '...' read successfully.\n\nContent:\n<json>"
                        if "Content:" in read_result:
                            history_json = read_result.split("Content:")[1].strip()
                        else:
                            history_json = read_result

                        self.chat_history = json.loads(history_json)
                        self.actual_token_count = 0

                        self.clear_console()
                        self.console.print(f"[green]Session '{selected_filename.replace('.json', '')}' loaded successfully.[/green]")
                        self.display_available_tools()
                        self.display_current_model()
                        self._display_chat_history()
                        return
                    except Exception as e:
                        self.console.print(f"[red]Error loading session file: {e}[/red]")
                        return
                else:
                    self.console.print("[red]Invalid number. Please try again.[/red]")

        except Exception as e:
            if "no such file or directory" in str(e).lower():
                self.console.print(f"[yellow]No saved sessions found (session directory does not exist: {self.session_save_directory}).[/yellow]")
            else:
                self.console.print(f"[red]An error occurred while loading sessions: {e}[/red]")

    async def reparse_last(self):
        """Re-run the tool parser on the last model response for debugging."""
        if not self.chat_history:
            self.console.print("[yellow]No chat history available to re-parse.[/yellow]")
            return

        last_entry = self.chat_history[-1]
        last_response_text = last_entry.get("response", "")

        if not last_response_text:
            self.console.print("[yellow]The last response was empty. Nothing to parse.[/yellow]")
            return

        self.console.print(Panel(last_response_text, title="[bold cyan]Input to Parser[/bold cyan]", border_style="cyan"))

        parsed_tool_calls = self.tool_parser.parse(last_response_text)

        if not parsed_tool_calls:
            self.console.print(Panel("[yellow]No tool calls were parsed from the response.[/yellow]", title="[bold yellow]Parser Result[/bold yellow]", border_style="yellow"))
            return
        
        self.console.print(Panel(f"[green]Successfully parsed {len(parsed_tool_calls)} tool call(s):[/green]", title="[bold green]Parser Result[/bold green]", border_style="green"))

        for i, tool_call in enumerate(parsed_tool_calls):
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            
            args_str = json.dumps(tool_args, indent=2)
            
            self.console.print(Panel(
                f"[bold]Name:[/bold] {tool_name}\n[bold]Arguments:[/bold]\n{args_str}",
                title=f"Tool Call #{i+1}",
                border_style="magenta",
                expand=False
            ))

    async def _change_session_save_location(self):
        """Allow the user to change the directory where sessions are saved."""
        self.clear_console()
        self.console.print(Panel("[bold]Change Session Save Location[/bold]", border_style="blue"))
        self.console.print(f"Current session save directory: [cyan]{self.session_save_directory}[/cyan]\n")
        self.console.print("Enter a relative path for session storage (e.g., '.config', '.sessions', 'my_sessions').")
        self.console.print("The directory will be created in the current working directory if it doesn't exist.")
        self.console.print("Type 'q' or 'quit' to cancel.")

        while True:
            new_dir = await self.get_user_input("Session directory name")
            if not new_dir or new_dir.lower() in ['q', 'quit']:
                self.console.print("[yellow]Session save location change cancelled.[/yellow]")
                break

            new_dir = new_dir.strip()

            # Validate that it's a relative path (no absolute paths or path traversal)
            if os.path.isabs(new_dir) or '..' in new_dir:
                self.console.print("[red]Error: Please use a relative directory name without '..' (e.g., '.config', 'sessions')[/red]")
                continue

            # Check if the directory can be created using built-in tools
            try:
                # Try to create the directory using built-in tool
                dir_result = self.builtin_tool_manager.execute_tool('create_directory', {
                    'path': new_dir
                })

                # Check for errors (but "already exists" is OK)
                if "Error:" in dir_result and "already exists" not in dir_result:
                    raise Exception(dir_result)

                self.session_save_directory = new_dir
                self.save_configuration() # Save the updated configuration
                self.console.print(f"[green]Session save directory updated to: {self.session_save_directory}[/green]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: Could not set session save directory to '{new_dir}'. Reason: {e}[/red]")
                continue

        self.display_available_tools()
        self.display_current_model()
        self._display_chat_history()


    async def supports_thinking_mode(self) -> bool:
        """Check if the current model supports thinking mode by checking its capabilities

        Returns:
            bool: True if the current model supports thinking mode, False otherwise
        """
        try:
            current_model = self.model_manager.get_current_model()
            # Query the model's capabilities using ollama.show()
            model_info = await self.ollama.show(current_model)

            # Check if the model has 'thinking' capability
            if 'capabilities' in model_info and model_info['capabilities']:
                return 'thinking' in model_info['capabilities']

            return False
        except Exception:
            # If we can't determine capabilities, assume no thinking support
            return False

    async def select_model(self):
        """Let the user select an Ollama model from the available ones"""
        await self.model_manager.select_model_interactive(clear_console_func=self.clear_console)

        # After model selection, redisplay context
        self.display_available_tools()
        self.display_current_model()
        self._display_chat_history()

    def clear_console(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_available_tools(self):
        """Display available tools with their enabled/disabled status"""
        self.tool_manager.display_available_tools()

    async def connect_to_servers(self, server_paths=None, server_urls=None, config_path=None, auto_discovery=False):
        """Connect to one or more MCP servers using the ServerConnector

        Args:
            server_paths: List of paths to server scripts (.py or .js)
            server_urls: List of URLs for SSE or Streamable HTTP servers
            config_path: Path to JSON config file with server configurations
            auto_discovery: Whether to automatically discover servers
        """
        # Store connection parameters for potential reload
        self.server_connection_params = {
            'server_paths': server_paths,
            'server_urls': server_urls,
            'config_path': config_path,
            'auto_discovery': auto_discovery
        }

        # Connect to servers using the server connector
        sessions, available_tools, enabled_tools, system_prompt_from_config = await self.server_connector.connect_to_servers(
            server_paths=server_paths,
            server_urls=server_urls,
            config_path=config_path,
            auto_discovery=auto_discovery
        )

        # Store the results
        self.sessions = sessions

        # Set up the tool manager with the available tools and their enabled status
        self.tool_manager.set_available_tools(available_tools)
        self.tool_manager.set_enabled_tools(enabled_tools)

        # Update the FZFStyleCompleter with the new sessions
        if hasattr(self.prompt_session.completer, 'update_sessions'):
            self.prompt_session.completer.update_sessions(self.sessions)

        # If a system prompt was loaded from the config, set it in the ModelConfigManager
        if system_prompt_from_config:
            self.model_config_manager.set_system_prompt(system_prompt_from_config)

    def select_tools(self):
        """Let the user select which tools to enable using interactive prompts with server-based grouping"""
        # Call the tool manager's select_tools method
        self.tool_manager.select_tools(clear_console_func=self.clear_console)

        # Display the chat history and current state after selection
        self.display_available_tools()
        self.display_current_model()
        self._display_chat_history()

    def configure_model_options(self):
        """Let the user configure model parameters like system prompt, temperature, etc."""
        self.model_config_manager.configure_model_interactive(clear_console_func=self.clear_console)

        # Display the chat history and current state after selection
        self.display_available_tools()
        self.display_current_model()
        self._display_chat_history()

    def _display_chat_history(self):
        """Display chat history when returning to the main chat interface"""
        if self.chat_history:
            self.console.print(Panel("[bold]Chat History[/bold]", border_style="blue", expand=False))

            # Display the last few conversations (limit to keep the interface clean)
            max_history = 3
            history_to_show = self.chat_history[-max_history:]

            for i, entry in enumerate(history_to_show):
                # Calculate query number starting from 1 for the first query
                query_number = len(self.chat_history) - len(history_to_show) + i + 1
                self.console.print(f"[bold green]Query {query_number}:[/bold green]")
                self.console.print(Text(entry["query"].strip(), style="green"))
                self.console.print("[bold blue]Answer:[/bold blue]")
                self.console.print(Markdown(entry["response"].strip()))
                self.console.print()

            if len(self.chat_history) > max_history:
                self.console.print(f"[dim](Showing last {max_history} of {len(self.chat_history)} conversations)[/dim]")

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        # Create base message with current query
        current_message = {
            "role": "user",
            "content": query
        }

        # Build messages array based on context retention setting
        if self.retain_context and self.chat_history:
            # Include previous messages for context
            messages = []
            for entry in self.chat_history:
                # Add user message
                messages.append({
                    "role": "user",
                    "content": entry["query"]
                })
                # Add assistant response
                messages.append({
                    "role": "assistant",
                    "content": entry["response"]
                })
            # Add the current query
            messages.append(current_message)
        else:
            # No context retention - just use current query
            messages = [current_message]

        # Add system prompt if one is configured
        system_prompt = self.model_config_manager.get_system_prompt()
        if system_prompt:
            messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })

        # Get enabled tools based on current mode (PLAN or ACT)
        enabled_tool_objects = self.get_filtered_tools_for_current_mode()

        if not enabled_tool_objects:
            if self.plan_mode:
                self.console.print("[yellow]Note: Running in PLAN mode with read-only tools. Use Shift+Tab to switch to ACT mode for write operations.[/yellow]")
            else:
                self.console.print("[yellow]Warning: No tools are enabled. Model will respond without tool access.[/yellow]")

        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in enabled_tool_objects]

        # Get current model from the model manager
        model = self.model_manager.get_current_model()

        # Get model options in Ollama format
        model_options = self.model_config_manager.get_ollama_options()

        # Prepare chat parameters
        chat_params = {
            "model": model,
            "messages": messages,
            "stream": True,
            "tools": available_tools,
            "options": model_options
        }

        # Add thinking parameter if thinking mode is enabled and model supports it
        supports_thinking = await self.supports_thinking_mode()
        if supports_thinking:
            chat_params["think"] = self.thinking_mode

        # Initial Ollama API call with the query and available tools
        stream = await self.ollama.chat(**chat_params)

        # Process the streaming response with thinking mode support
        response_text = ""
        tool_calls = []
        response_text, tool_calls, metrics = await self.streaming_manager.process_streaming_response(
            stream,
            thinking_mode=self.thinking_mode,
            show_thinking=self.show_thinking,
            show_metrics=self.show_metrics
        )

        # response_text will be either empty or contain a response
        # Append the assistant's response to messages helps maintain context and fix ollama cloud tool call issues
        messages.append({
            "role": "assistant",
            "content": response_text,
            "tool_calls": tool_calls
        })

        # Update actual token count from metrics if available
        if metrics and metrics.get('eval_count'):
            self.actual_token_count += metrics['eval_count']

        enabled_tools = self.get_filtered_tools_for_current_mode()

        loop_count = 0
        pending_tool_calls = tool_calls

        # Keep looping while the model requests tools and we have capacity
        while pending_tool_calls and enabled_tools:
            if loop_count >= self.loop_limit:
                self.console.print(Panel(
                    f"[yellow]Your current loop limit is set to [bold]{self.loop_limit}[/bold] and has been reached. Skipping additional tool calls.[/yellow]\n"
                    f"You will probably want to increase this limit if your model requires more tool interactions to complete tasks.\n"
                    f"You can change the loop limit with the [bold cyan]loop-limit[/bold cyan] command.",
                    title="[bold]Loop Limit Reached[/bold]", border_style="yellow", expand=False
                ))
                break

            loop_count += 1

            for tool in pending_tool_calls:
                tool_name = tool.function.name
                tool_args = tool.function.arguments

                # Parse server name and actual tool name from the qualified name
                server_name, actual_tool_name = tool_name.split('.', 1) if '.' in tool_name else (None, tool_name)

                # Handle built-in tools
                if server_name == "builtin":
                    tool_response = self.builtin_tool_manager.execute_tool(actual_tool_name, tool_args)
                    messages.append({
                        "role": "tool",
                        "content": tool_response,
                        "tool_name": tool_name
                    })
                    self.tool_display_manager.display_tool_response(tool_name, tool_args, tool_response, show=self.show_tool_execution)
                    continue

                if not server_name or server_name not in self.sessions:
                    self.console.print(f"[red]Error: Unknown server for tool {tool_name}[/red]")
                    continue

                # Execute tool call
                self.tool_display_manager.display_tool_execution(tool_name, tool_args, show=self.show_tool_execution)

                # Request HIL confirmation if enabled
                should_execute = await self.hil_manager.request_tool_confirmation(
                    tool_name, tool_args
                )

                if not should_execute:
                    tool_response = "Tool call was skipped by user"
                    self.tool_display_manager.display_tool_response(tool_name, tool_args, tool_response, show=self.show_tool_execution)
                    messages.append({
                        "role": "tool",
                        "content": tool_response,
                        "tool_name": tool_name
                    })
                    continue

                # Call the tool on the specified server
                result = None
                with self.console.status(f"[cyan]⏳ Running {tool_name}...[/cyan]"):
                    result = await self.sessions[server_name]["session"].call_tool(actual_tool_name, tool_args)
                    if result.content:
                        tool_response = f"{result.content[0].text}"

                        # Display the tool response
                        self.tool_display_manager.display_tool_response(tool_name, tool_args, tool_response, show=self.show_tool_execution)

                        messages.append({
                            "role": "tool",
                            "content": tool_response,
                            "tool_name": tool_name
                        })
                    else:
                        messages.append("No tool response found.")

            # Get stream response from Ollama with the tool results
            chat_params_followup = {
                "model": model,
                "messages": messages,
                "stream": True,
                "tools": available_tools,
                "options": model_options
            }

            # Add thinking parameter if thinking mode is enabled and model supports it
            if supports_thinking:
                chat_params_followup["think"] = self.thinking_mode

            stream = await self.ollama.chat(**chat_params_followup)

            # Process the streaming response with thinking mode support
            followup_response, pending_tool_calls, followup_metrics = await self.streaming_manager.process_streaming_response(
                stream,
                thinking_mode=self.thinking_mode,
                show_thinking=self.show_thinking,
                show_metrics=self.show_metrics
            )

            messages.append({
                "role": "assistant",
                "content": followup_response,
                "tool_calls": pending_tool_calls
            })

            # Update actual token count from followup metrics if available
            if followup_metrics and followup_metrics.get('eval_count'):
                self.actual_token_count += followup_metrics['eval_count']

            if followup_response:
                response_text = followup_response

            enabled_tools = self.tool_manager.get_enabled_tool_objects()

        if not response_text:
            self.console.print("[red]No content response received.[/red]")
            response_text = ""

        # Append query and response to chat history
        self.chat_history.append({"query": query, "response": response_text})

        return response_text

    async def get_user_input(self, prompt_text: str = None) -> str:
        """Get user input with full keyboard navigation support"""
        try:
            if prompt_text is None:
                model_name = self.model_manager.get_current_model().split(':')[0]
                tool_count = len(self.tool_manager.get_enabled_tool_objects())

                # Simple and readable
                prompt_text = f"{model_name}"

                # Add mode indicator (PLAN or ACT)
                mode_indicator = "[PLAN]" if self.plan_mode else "[ACT]"
                prompt_text += f"/{mode_indicator}"

                # Add thinking indicator
                if self.thinking_mode and await self.supports_thinking_mode():
                    prompt_text += "/show-thinking" if self.show_thinking else "/thinking"

                # Add tool count (show filtered count in PLAN mode)
                filtered_tool_count = len(self.get_filtered_tools_for_current_mode())
                if filtered_tool_count > 0:
                    prompt_text += f"/{filtered_tool_count}-tool" if filtered_tool_count == 1 else f"/{filtered_tool_count}-tools"

            user_input = await self.prompt_session.prompt_async(
                f"{prompt_text}❯ ",
                bottom_toolbar=self._get_bottom_toolbar_content
            )
            # Clear messages after they have been displayed
            self.status_messages.clear()
            return user_input
        except KeyboardInterrupt:
            # Clear messages on exit
            self.status_messages.clear()
            return "quit"
        except EOFError:
            # Clear messages on exit
            self.status_messages.clear()
            return "quit"

    async def display_check_for_updates(self):
        # Check for updates
        try:
            update_available, current_version, latest_version = check_for_updates()
            if update_available:
                self.console.print(Panel(
                    f"[bold yellow]New version available![/bold yellow]\n\n"
                    f"Current version: [cyan]{current_version}[/cyan]\n"
                    f"Latest version: [green]{latest_version}[/green]\n\n"
                    f"Upgrade with: [bold white]pip install --upgrade mcp-client-for-ollama[/bold white]",
                    title="Update Available", border_style="yellow", expand=False
                ))
        except Exception:
            # Silently fail - version check should not block program usage
            pass

    def _get_bottom_toolbar_content(self):
        """Callable to get content for the bottom toolbar."""
        if self.status_messages:
            # Join messages with a newline, or format them as needed
            return Text("\n".join(self.status_messages), style="bold red")
        return None

    async def handle_user_input(self, query: str):
        """
        Handle a single user query non-interactively.

        This method processes a query without entering the interactive chat loop,
        making it suitable for command-line script execution.

        Args:
            query: The user's query to process
        """
        # Handle explicit delegation command prefix (forces delegation even if disabled)
        force_delegation = False
        actual_query = query

        if query.lower().startswith('delegate ') or query.lower().startswith('dt '):
            force_delegation = True
            # Extract the actual query after the command
            if query.lower().startswith('delegate '):
                actual_query = query[9:].strip()
            else:  # 'dt '
                actual_query = query[3:].strip()

        # Check if query is too short
        if len(actual_query.strip()) < 5:
            if not self.quiet_mode:
                self.console.print("[yellow]Query must be at least 5 characters long.[/yellow]")
            return

        # Decide whether to use delegation
        use_delegation = force_delegation or self.is_delegation_enabled()

        if use_delegation:
            # Use delegation
            try:
                # Get or create delegation client
                delegation_client = self.get_delegation_client()

                # Process with delegation
                response = await delegation_client.process_with_delegation(actual_query)

                # Display response
                if not self.quiet_mode:
                    self.console.print("\n[bold green]📋 Final Response:[/bold green]")
                    self.console.print(Panel(Markdown(response), border_style="green", expand=False))
                else:
                    # In quiet mode, print just the response text
                    print(response)

                # Add to chat history
                self.chat_history.append({
                    "query": f"[DELEGATED] {actual_query}",
                    "response": response
                })

            except Exception as e:
                if not self.quiet_mode:
                    self.console.print(f"[bold red]Delegation error:[/bold red] {str(e)}")
                    self.console.print_exception()
                else:
                    print(f"Error: {str(e)}", file=sys.stderr)

            return

        # Non-delegated processing
        try:
            # Process the query
            await self.process_query(actual_query)
        except ollama.ResponseError as e:
            error_msg = str(e)
            if not self.quiet_mode:
                if "does not support tools" in error_msg.lower():
                    model_name = self.model_manager.get_current_model()
                    self.console.print(Panel(
                        f"[bold red]Model Error:[/bold red] The model [bold blue]{model_name}[/bold blue] does not support tools.\n\n"
                        "To use tools, switch to a model that supports them.",
                        title="Tools Not Supported",
                        border_style="red", expand=False
                    ))
                else:
                    self.console.print(Panel(f"[bold red]Ollama Error:[/bold red] {error_msg}",
                                             border_style="red", expand=False))
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
        except Exception as e:
            if not self.quiet_mode:
                self.console.print(f"[bold red]Error:[/bold red] {str(e)}")
                self.console.print_exception()
            else:
                print(f"Error: {str(e)}", file=sys.stderr)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        self.clear_console()
        self.console.print(Panel(
            Text.from_markup(
                f"[bold green]Welcome to the MCP Client for Ollama 🦙[/bold green]\n"
                f"[dim]Version {__version__}[/dim]",
                justify="center"
            ),
            expand=True,
            border_style="green"
        ))
        self.display_available_tools()
        self.display_current_model()
        # Show minimal help hint instead of full help dialog
        self.console.print("[green]💡 Type [bold]help[/bold] or [bold]h[/bold] for available commands[/green]\n")
        self.print_auto_load_default_config_status()
        await self.display_check_for_updates()

        while True:
            try:
                # Use await to call the async method
                query = await self.get_user_input()

                if query.lower() in ['quit', 'q', 'exit', 'bye']:
                    self.console.print("[yellow]Exiting...[/yellow]")
                    break

                if query.lower() in ['tools', 't']:
                    self.select_tools()
                    continue

                if query.lower() in ['help', 'h']:
                    self.print_help()
                    continue

                if query.lower() in ['model', 'm']:
                    await self.select_model()
                    continue

                if query.lower() in ['model-config', 'mc']:
                    self.configure_model_options()
                    continue

                if query.lower() in ['context', 'c']:
                    self.toggle_context_retention()
                    continue

                if query.lower() in ['thinking-mode', 'tm']:
                    await self.toggle_thinking_mode()
                    continue

                if query.lower() in ['show-thinking', 'st']:
                    await self.toggle_show_thinking()
                    continue

                if query.lower() in ['loop-limit', 'll']:
                    await self.set_loop_limit()
                    continue

                if query in ['#TOGGLE_PLAN_MODE#'] or query.lower() in ['plan-mode', 'pm']:
                    self.toggle_plan_mode()
                    continue

                if query.lower() in ['show-tool-execution', 'ste']:
                    self.toggle_show_tool_execution()
                    continue

                if query.lower() in ['show-metrics', 'sm']:
                    self.toggle_show_metrics()
                    continue

                if query.lower() in ['clear', 'cc']:
                    self.clear_context()
                    continue

                if query.lower() in ['context-info', 'ci']:
                    self.display_context_stats()
                    continue

                if query.lower() in ['cls', 'clear-screen']:
                    self.clear_console()
                    self.display_available_tools()
                    self.display_current_model()
                    continue

                if query.lower() in ['save-config', 'sc']:
                    # Ask for config name, defaulting to "default"
                    config_name = await self.get_user_input("Config name (or press Enter for default)")
                    if not config_name or config_name.strip() == "":
                        config_name = "default"
                    self.save_configuration(config_name)
                    continue

                if query.lower() in ['load-config', 'lc']:
                    # Ask for config name, defaulting to "default"
                    config_name = await self.get_user_input("Config name to load (or press Enter for default)")
                    if not config_name or config_name.strip() == "":
                        config_name = "default"
                    self.load_configuration(config_name)
                    # Update display after loading
                    self.display_available_tools()
                    self.display_current_model()
                    continue

                if query.lower() in ['reset-config', 'rc']:
                    self.reset_configuration()
                    # Update display after resetting
                    self.display_available_tools()
                    self.display_current_model()
                    continue

                if query.lower() in ['reload-servers', 'rs']:
                    await self.reload_servers()
                    continue

                if query.lower() in ['human-in-the-loop', 'hil']:
                    self.hil_manager.toggle_global()
                    continue

                if query.lower() in ['toggle-delegation', 'td']:
                    await self.toggle_delegation()
                    continue

                if query.lower() in ['delegation-trace', 'dtt', 'trace-config', 'tc']:
                    await self.configure_delegation_trace()
                    continue

                if query.lower() in ['hil-config', 'hc']:
                    self.hil_manager.configure_hil_interactive(self.clear_console)
                    # After configuring, redisplay context
                    self.display_available_tools()
                    self.display_current_model()
                    self._display_chat_history()
                    continue

                if query.lower() in ['save-session', 'ss']:
                    await self.save_session()
                    continue

                if query.lower() in ['load-session', 'ls']:
                    await self.load_session()
                    continue

                if query.lower() in ['reparse-last', 'rl']:
                    await self.reparse_last()
                    continue

                if query.lower() in ['session-dir', 'sd']:
                    await self._change_session_save_location()
                    continue

                if query.lower() in ['execute-python-code', 'epc']:
                    self.clear_console()
                    self.console.print(Panel("[bold]Execute Python Code[/bold]", border_style="blue"))
                    self.console.print("Enter the Python code to execute. Type 'EOF' on a new line to finish and execute.")
                    self.console.print("Type 'q' or 'quit' to cancel.")
                    
                    code_lines = []
                    while True:
                        line = await self.get_user_input(">>> ")
                        if line.lower() == 'eof':
                            break
                        if line.lower() in ['q', 'quit']:
                            self.console.print("[yellow]Python code execution cancelled.[/yellow]")
                            break
                        code_lines.append(line)
                    
                    if code_lines:
                        code_to_execute = "\n".join(code_lines)
                        self.console.print(f"[cyan]Executing Python code...[/cyan]")
                        result = self.builtin_tool_manager.execute_tool("execute_python_code", {"code": code_to_execute})
                        self.console.print(Panel(result, title="[bold green]Python Execution Result[/bold green]", border_style="green", expand=False))
                    
                    self.display_available_tools()
                    self.display_current_model()
                    self._display_chat_history()
                    continue

                # Handle delegation (explicit prefix or enabled by default)
                force_delegation = False
                actual_query = query

                if query.lower().startswith('delegate ') or query.lower().startswith('dt '):
                    force_delegation = True
                    # Extract the actual query after the command
                    if query.lower().startswith('delegate '):
                        actual_query = query[9:].strip()
                    else:  # 'dt '
                        actual_query = query[3:].strip()

                # Check if query is too short
                if len(actual_query.strip()) < 5:
                    self.console.print("[yellow]Query must be at least 5 characters long.[/yellow]")
                    continue

                # Decide whether to use delegation
                use_delegation = force_delegation or self.is_delegation_enabled()

                if use_delegation:
                    # Use delegation
                    try:
                        # Get or create delegation client
                        delegation_client = self.get_delegation_client()

                        # Process with delegation
                        response = await delegation_client.process_with_delegation(actual_query)

                        # Display response
                        self.console.print("\n[bold green]📋 Final Response:[/bold green]")
                        self.console.print(Panel(Markdown(response), border_style="green", expand=False))

                        # Add to chat history
                        self.chat_history.append({
                            "query": f"[DELEGATED] {actual_query}",
                            "response": response
                        })

                    except Exception as e:
                        self.console.print(f"[bold red]Delegation error:[/bold red] {str(e)}")
                        self.console.print_exception()

                    continue

                # Non-delegated processing
                try:
                    await self.process_query(actual_query)
                except ollama.ResponseError as e:
                    # Extract error message without the traceback
                    error_msg = str(e)
                    if "does not support tools" in error_msg.lower():
                        model_name = self.model_manager.get_current_model()
                        self.console.print(Panel(
                            f"[bold red]Model Error:[/bold red] The model [bold blue]{model_name}[/bold blue] does not support tools.\n\n"
                            "To use tools, switch to a model that supports them by typing [bold cyan]model[/bold cyan] or [bold cyan]m[/bold cyan]\n\n"
                            "You can still use this model without tools by [bold]disabling all tools[/bold] with [bold cyan]tools[/bold cyan] or [bold cyan]t[/bold cyan]",
                            title="Tools Not Supported",
                            border_style="red", expand=False
                        ))
                    else:
                        self.console.print(Panel(f"[bold red]Ollama Error:[/bold red] {error_msg}",
                                                 border_style="red", expand=False))

                    # If it's a "model not found" error, suggest how to fix it
                    if "not found" in error_msg.lower() and "try pulling it first" in error_msg.lower():
                        model_name = self.model_manager.get_current_model()
                        self.console.print(Panel(
                            "[bold yellow]Model Not Found[/bold yellow]\n\n"
                            "To download this model, run the following command in a new terminal window:\n"
                            f"[bold cyan]ollama pull {model_name}[/bold cyan]\n\n"
                            "Or, you can use a different model by typing [bold cyan]model[/bold cyan] or [bold cyan]m[/bold cyan] to select from available models",
                            title="Model Not Available",
                            border_style="yellow", expand=False
                        ))

            except Exception as e:
                self.console.print(Panel(f"[bold red]Error:[/bold red] {str(e)}", title="Exception", border_style="red", expand=False))
                self.console.print_exception()

    def print_help(self):
        """Print available commands"""
        self.console.print(Panel(
            "[bold yellow]Available Commands:[/bold yellow]\n\n"

            "[bold cyan]Model:[/bold cyan]\n"
            "• Type [bold]model[/bold] or [bold]m[/bold] to select a model\n"
            "• Type [bold]model-config[/bold] or [bold]mc[/bold] to configure system prompt and model parameters\n"
            f"• Type [bold]thinking-mode[/bold] or [bold]tm[/bold] to toggle thinking mode\n"
            "• Type [bold]show-thinking[/bold] or [bold]st[/bold] to toggle thinking text visibility\n"
            "• Type [bold]show-metrics[/bold] or [bold]sm[/bold] to toggle performance metrics display\n\n"

            "[bold cyan]Agent Mode:[/bold cyan] [bold magenta](New!)[/bold magenta]\n"
            "• Type [bold]loop-limit[/bold] or [bold]ll[/bold] to set the maximum tool loop iterations\n"
            "• Type [bold]plan-mode[/bold] or [bold]pm[/bold] to toggle between PLAN (read-only) and ACT (full access) modes\n"
            "• Press [bold]Shift+Tab[/bold] to quickly toggle between PLAN and ACT modes\n\n"

            "[bold cyan]Agent Delegation:[/bold cyan] [bold green](Enabled by Default)[/bold green]\n"
            "• Queries are automatically delegated to specialized agents for better results\n"
            "• Type [bold]toggle-delegation[/bold] or [bold]td[/bold] to enable/disable delegation mode\n"
            "• Type [bold]delegation-trace[/bold] or [bold]dtt[/bold] to configure trace logging for debugging\n"
            "• Type [bold]dt <query>[/bold] to force delegation for a specific query (when disabled)\n"
            "• Agent delegation breaks down complex tasks into focused subtasks for specialized agents\n"
            "• Best for: multi-file edits, complex refactoring, or tasks requiring multiple steps\n\n"

            "[bold cyan]MCP Servers and Tools:[/bold cyan]\n"
            "• Type [bold]tools[/bold] or [bold]t[/bold] to configure tools\n"
            "• Type [bold]show-tool-execution[/bold] or [bold]ste[/bold] to toggle tool execution display\n"
            "• Type [bold]human-in-the-loop[/bold] or [bold]hil[/bold] to toggle [bold]global[/bold] Human-in-the-Loop confirmations\n"
            "• Type [bold]hil-config[/bold] or [bold]hc[/bold] to configure granular HIL settings\n"
            "• Type [bold]reload-servers[/bold] or [bold]rs[/bold] to reload MCP servers\n\n"

            "[bold cyan]Context:[/bold cyan]\n"
            "• Type [bold]context[/bold] or [bold]c[/bold] to toggle context retention\n"
            "• Type [bold]clear[/bold] or [bold]cc[/bold] to clear conversation context\n"
            "• Type [bold]context-info[/bold] or [bold]ci[/bold] to display context info\n\n"

            "[bold cyan]Configuration:[/bold cyan]\n"
            "• Type [bold]save-config[/bold] or [bold]sc[/bold] to save the current configuration\n"
            "• Type [bold]load-config[/bold] or [bold]lc[/bold] to load a configuration\n"
            "• Type [bold]reset-config[/bold] or [bold]rc[/bold] to reset configuration to defaults\n\n"

            "[bold cyan]Session Management:[/bold cyan]\n"
            "• Type [bold]save-session[/bold] or [bold]ss[/bold] to save the current chat session\n"
            "• Type [bold]load-session[/bold] or [bold]ls[/bold] to load a previous chat session\n"
            "• Type [bold]session-dir[/bold] or [bold]sd[/bold] to change the session save directory\n\n"

            "[bold cyan]Auto-Loading (on startup):[/bold cyan]\n"
            "• Create [bold].config/CLAUDE.md[/bold] to automatically load project context\n"
            "• Create [bold].config/config.json[/bold] to automatically load server configuration\n\n"

            "[bold cyan]Debugging:[/bold cyan]\n"
            "• Type [bold]reparse-last[/bold] or [bold]rl[/bold] to re-run the tool parser on the last response\n\n"


            "[bold cyan]Basic Commands:[/bold cyan]\n"
            "• Type [bold]help[/bold] or [bold]h[/bold] to show this help message\n"
            "• Type [bold]clear-screen[/bold] or [bold]cls[/bold] to clear the terminal screen\n"
            "• Type [bold]quit[/bold], [bold]q[/bold], [bold]exit[/bold], [bold]bye[/bold], or [bold]Ctrl+D[/bold] to exit the client\n",
            title="[bold]Help[/bold]", border_style="yellow", expand=False))

    def toggle_context_retention(self):
        """Toggle whether to retain previous conversation context when sending queries"""
        self.retain_context = not self.retain_context
        status = "enabled" if self.retain_context else "disabled"
        self.console.print(f"[green]Context retention {status}![/green]")
        # Display current context stats
        self.display_context_stats()

    async def toggle_thinking_mode(self):
        """Toggle thinking mode on/off (only for supported models)"""
        if not await self.supports_thinking_mode():
            current_model = self.model_manager.get_current_model()
            model_base_name = current_model.split(":")[0]
            self.console.print(Panel(
                f"[bold red]Thinking mode is not supported for model '{model_base_name}'[/bold red]\n\n"
                f"Thinking mode is only available for models that have the 'thinking' capability.\n"
                f"\nCurrent model: [yellow]{current_model}[/yellow]\n"
                f"Use [bold cyan]model[/bold cyan] or [bold cyan]m[/bold cyan] to switch to a supported model.",
                title="Thinking Mode Not Available", border_style="red", expand=False
            ))
            return

        self.thinking_mode = not self.thinking_mode
        status = "enabled" if self.thinking_mode else "disabled"
        self.console.print(f"[green]Thinking mode {status}![/green]")

        if self.thinking_mode:
            self.console.print("[cyan]🤔 The model will now show its reasoning process.[/cyan]")
        else:
            self.console.print("[cyan]The model will now provide direct responses.[/cyan]")

    async def toggle_show_thinking(self):
        """Toggle whether thinking text remains visible after completion"""
        if not self.thinking_mode:
            self.console.print(Panel(
                f"[bold yellow]Thinking mode is currently disabled[/bold yellow]\n\n"
                f"Enable thinking mode first using [bold cyan]thinking-mode[/bold cyan] or [bold cyan]tm[/bold cyan] command.\n"
                f"This setting only applies when thinking mode is active.",
                title="Show Thinking Setting", border_style="yellow", expand=False
            ))
            return

        if not await self.supports_thinking_mode():
            current_model = self.model_manager.get_current_model()
            model_base_name = current_model.split(":")[0]
            self.console.print(Panel(
                f"[bold red]Thinking mode is not supported for model '{model_base_name}'[/bold red]\n\n"
                f"This setting only applies to models that have the 'thinking' capability.",
                title="Show Thinking Not Available", border_style="red", expand=False
            ))
            return

        self.show_thinking = not self.show_thinking
        status = "visible" if self.show_thinking else "hidden"
        self.console.print(f"[green]Thinking text will be {status} after completion![/green]")

        if self.show_thinking:
            self.console.print("[cyan]💭 The reasoning process will remain visible in the final response.[/cyan]")
        else:
            self.console.print("[cyan]🧹 The reasoning process will be hidden, showing only the final answer.[/cyan]")

    def toggle_show_tool_execution(self):
        """Toggle whether tool execution displays are shown"""
        self.show_tool_execution = not self.show_tool_execution
        status = "visible" if self.show_tool_execution else "hidden"
        self.console.print(f"[green]Tool execution displays will be {status}![/green]")

        if self.show_tool_execution:
            self.console.print("[cyan]🔧 Tool execution details will be displayed when tools are called.[/cyan]")
        else:
            self.console.print("[cyan]🔇 Tool execution details will be hidden for a cleaner output.[/cyan]")

    def toggle_show_metrics(self):
        """Toggle whether performance metrics are shown after each query"""
        self.show_metrics = not self.show_metrics
        status = "enabled" if self.show_metrics else "disabled"
        self.console.print(f"[green]Performance metrics display {status}![/green]")

        if self.show_metrics:
            self.console.print("[cyan]📊 Performance metrics will be displayed after each query.[/cyan]")
        else:
            self.console.print("[cyan]🔇 Performance metrics will be hidden for a cleaner output.[/cyan]")

    async def set_loop_limit(self):
        """Configure the maximum number of follow-up tool loops per query."""
        user_input = await self.get_user_input(f"Loop limit (current: {self.loop_limit})")

        if user_input is None:
            return

        value = user_input.strip()

        if not value:
            self.console.print("[yellow]Loop limit unchanged.[/yellow]")
            return

        try:
            new_limit = int(value)
            if new_limit < 1:
                raise ValueError
            self.loop_limit = new_limit
            self.console.print(f"[green]🤖 Agent loop limit set to {self.loop_limit}![/green]")
        except ValueError:
            self.console.print("[red]Invalid loop limit. Please enter a positive integer.[/red]")

    def toggle_plan_mode(self):
        """Toggle between PLAN and ACT modes"""
        # Get current system prompt before toggling
        current_prompt = self.model_config_manager.get_system_prompt()

        if not self.plan_mode:
            # Switching to PLAN mode
            self.plan_mode = True
            # Backup the ACT mode system prompt
            self.act_mode_system_prompt = current_prompt

            # Create plan mode system prompt
            plan_mode_prompt = """You are in PLAN mode. Your role is to help the user think through problems and plan solutions WITHOUT making any changes.

IMPORTANT RESTRICTIONS IN PLAN MODE:
- DO NOT write files
- DO NOT execute code or bash commands
- DO NOT create or delete directories
- DO NOT make any modifications to the system
- You can ONLY read files, list directories, and analyze information

Your purpose in PLAN mode is to:
1. Help analyze the current state by reading files and exploring the codebase
2. Think through the problem and potential solutions
3. Create detailed plans and strategies
4. Discuss trade-offs and approaches

If the user asks you to make changes, remind them to switch to ACT mode (Shift+Tab) first.
"""
            # Append to existing prompt if one exists
            if current_prompt:
                plan_mode_prompt = current_prompt + "\n\n" + plan_mode_prompt

            self.model_config_manager.set_system_prompt(plan_mode_prompt)
            self.console.print("[bold yellow]📋 PLAN MODE activated![/bold yellow]")
            self.console.print("[cyan]Write operations are disabled. Use Shift+Tab to switch to ACT mode.[/cyan]")
        else:
            # Switching to ACT mode
            self.plan_mode = False
            # Restore the ACT mode system prompt
            if self.act_mode_system_prompt is not None:
                self.model_config_manager.set_system_prompt(self.act_mode_system_prompt)
            else:
                # If no backup exists, clear the plan mode prompt
                if current_prompt and "PLAN mode" in current_prompt:
                    # Try to extract original prompt before plan mode text
                    parts = current_prompt.split("\n\nYou are in PLAN mode.")
                    if len(parts) > 1:
                        self.model_config_manager.set_system_prompt(parts[0] if parts[0] else None)
                    else:
                        self.model_config_manager.set_system_prompt(None)

            self.console.print("[bold green]✅ ACT MODE activated![/bold green]")
            self.console.print("[cyan]All tools are now available. Use Shift+Tab to switch to PLAN mode.[/cyan]")

    async def toggle_delegation(self):
        """Toggle delegation mode on/off"""
        # Load current config
        current_config = self.config_manager.load_configuration("default")
        if not current_config:
            current_config = {}

        if "delegation" not in current_config or not isinstance(current_config["delegation"], dict):
            current_config["delegation"] = {}

        delegation = current_config["delegation"]

        # Get current state (default to True)
        current_state = delegation.get("enabled", True)

        # Toggle the state
        new_state = not current_state
        delegation["enabled"] = new_state

        # Save the configuration
        current_config["delegation"] = delegation
        self.config_manager.save_configuration("default", current_config)

        # Display the new state
        status = "[green]enabled[/green]" if new_state else "[yellow]disabled[/yellow]"
        self.console.print(f"\n[bold]Delegation is now {status}[/bold]")

        if new_state:
            self.console.print("[dim]Queries will be processed using the agent delegation system.[/dim]")
        else:
            self.console.print("[dim]Queries will be processed directly (legacy mode).[/dim]")
            self.console.print("[dim]You can still force delegation for specific queries using 'dt <query>'[/dim]")

        self.console.print()

    async def configure_delegation_trace(self):
        """Configure trace logging for delegation mode"""
        from prompt_toolkit.shortcuts import radiolist_dialog, yes_no_dialog
        from rich.table import Table

        # Load current config from file or create new one
        current_config = self.config_manager.load_configuration("default")
        if not current_config:
            # If no config exists, start with empty config
            current_config = {}

        if "delegation" not in current_config:
            current_config["delegation"] = {}

        delegation = current_config["delegation"]

        # Show current settings
        table = Table(title="Current Delegation Trace Settings", show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="yellow", width=20)
        table.add_column("Value", style="green")

        table.add_row("Delegation Enabled", str(delegation.get("enabled", True)))
        table.add_row("Trace Enabled", str(delegation.get("trace_enabled", False)))
        table.add_row("Trace Level", delegation.get("trace_level", "basic"))
        table.add_row("Trace Directory", delegation.get("trace_dir", ".trace"))
        table.add_row("Trace to Console", str(delegation.get("trace_console", False)))

        self.console.print()
        self.console.print(table)
        self.console.print()

        # Ask if user wants to enable delegation
        self.console.print("[cyan]Enable delegation? (required for trace logging)[/cyan]")
        enable_delegation = await self.get_user_input("Enable delegation? (yes/no, default: yes)")
        if enable_delegation.lower() in ['no', 'n']:
            delegation["enabled"] = False
            self.console.print("[yellow]Delegation disabled. Trace logging requires delegation to be enabled.[/yellow]")
            return
        else:
            delegation["enabled"] = True

        # Ask if user wants to enable trace logging
        self.console.print("[cyan]Enable trace logging?[/cyan]")
        enable_trace = await self.get_user_input("Enable trace logging? (yes/no, default: yes)")
        if enable_trace.lower() in ['no', 'n']:
            delegation["trace_enabled"] = False
            self.console.print("[yellow]Trace logging disabled.[/yellow]")
        else:
            delegation["trace_enabled"] = True

            # Select trace level
            self.console.print()
            self.console.print("[bold cyan]Select Trace Level:[/bold cyan]")
            self.console.print("  [yellow]1[/yellow] - OFF (no tracing)")
            self.console.print("  [yellow]2[/yellow] - SUMMARY (task start/end only)")
            self.console.print("  [yellow]3[/yellow] - BASIC (truncated prompts/responses) [recommended]")
            self.console.print("  [yellow]4[/yellow] - FULL (complete prompts/responses)")
            self.console.print("  [yellow]5[/yellow] - DEBUG (everything including tool calls)")
            self.console.print()

            level_choice = await self.get_user_input("Select trace level (1-5, default: 3)")
            level_map = {
                "1": "off",
                "2": "summary",
                "3": "basic",
                "4": "full",
                "5": "debug",
                "": "basic"  # default
            }
            delegation["trace_level"] = level_map.get(level_choice, "basic")

            # Ask for trace directory
            trace_dir = await self.get_user_input("Trace directory (default: .trace)")
            delegation["trace_dir"] = trace_dir if trace_dir.strip() else ".trace"

            # Ask if they want console output (only useful for DEBUG level)
            if delegation["trace_level"] == "debug":
                console_output = await self.get_user_input("Also print traces to console? (yes/no, default: no)")
                delegation["trace_console"] = console_output.lower() in ['yes', 'y']
            else:
                delegation["trace_console"] = False

            # Set default collapsible output settings if not present
            if "collapsible_output" not in delegation:
                delegation["collapsible_output"] = {
                    "auto_collapse": True,
                    "line_threshold": 20,
                    "char_threshold": 1000
                }

            # Set truncate length for BASIC level
            if delegation["trace_level"] == "basic":
                delegation["trace_truncate"] = 500

        # Save to config
        current_config["delegation"] = delegation

        # Show new settings
        self.console.print()
        table = Table(title="New Delegation Trace Settings", show_header=True, header_style="bold green")
        table.add_column("Setting", style="yellow", width=20)
        table.add_column("Value", style="green")

        table.add_row("Delegation Enabled", str(delegation.get("enabled", True)))
        table.add_row("Trace Enabled", str(delegation.get("trace_enabled", False)))
        table.add_row("Trace Level", delegation.get("trace_level", "basic"))
        table.add_row("Trace Directory", delegation.get("trace_dir", ".trace"))
        table.add_row("Trace to Console", str(delegation.get("trace_console", False)))

        self.console.print(table)
        self.console.print()

        # Ask if they want to save
        save_config = await self.get_user_input("Save configuration? (yes/no, default: yes)")
        if save_config.lower() not in ['no', 'n']:
            config_name = await self.get_user_input("Config name (default: default)")
            if not config_name or config_name.strip() == "":
                config_name = "default"

            # Update the current_config with delegation settings
            current_config["delegation"] = delegation

            # Save the updated config (preserving other keys like mcpServers)
            self.config_manager.save_configuration(current_config, config_name)

            # Add reminder to add .trace/ to .gitignore
            if delegation.get("trace_enabled", False):
                self.console.print()
                self.console.print(Panel(
                    "[yellow]⚠️  Important Reminder:[/yellow]\n\n"
                    "Don't forget to add the trace directory to your .gitignore:\n\n"
                    f"[cyan]echo '{delegation.get('trace_dir', '.trace')}/' >> .gitignore[/cyan]\n\n"
                    "[dim]Trace files can contain sensitive information and should not be committed.[/dim]",
                    title="Reminder",
                    border_style="yellow",
                    expand=False
                ))

                self.console.print()
                self.console.print(Panel(
                    "[bold green]✅ Trace logging configured![/bold green]\n\n"
                    "[cyan]To use trace logging:[/cyan]\n"
                    "  1. Use delegation: [bold]delegate <your query>[/bold] or [bold]d <your query>[/bold]\n"
                    "  2. Check trace summary at end of delegation\n"
                    f"  3. Analyze trace file: [bold]cat {delegation.get('trace_dir', '.trace')}/trace_*.json | jq .[/bold]\n\n"
                    "[dim]See TRACE_LOGGING_QUICK_REFERENCE.md for analysis commands[/dim]",
                    title="Usage",
                    border_style="green",
                    expand=False
                ))
        else:
            self.console.print("[yellow]Configuration not saved.[/yellow]")

    def is_delegation_enabled(self) -> bool:
        """
        Check if delegation is enabled in the configuration.

        Returns:
            True if delegation is enabled, False otherwise. Defaults to True.
        """
        user_config = self.config_manager.load_configuration("default")
        if user_config and "delegation" in user_config and isinstance(user_config["delegation"], dict):
            # Return the enabled flag, defaulting to True if not specified
            return user_config["delegation"].get("enabled", True)
        # Default to True if no delegation config exists
        return True

    def get_delegation_client(self):
        """
        Get or create the delegation client.

        For MVP, we recreate the delegation client each time to ensure
        it uses the current model selection. This will be optimized in
        future phases to update the model pool dynamically.

        Returns:
            DelegationClient instance
        """
        # Always use the current model (don't cache for MVP)
        # This ensures model changes are reflected in delegation
        config = {
            'planner_model': None,  # Will fall back to current model
            'model_pool': [{
                'url': DEFAULT_OLLAMA_HOST,  # Use the default host from constants
                'model': self.model_manager.get_current_model(),
                'max_concurrent': 3  # Allow up to 3 concurrent tasks per endpoint
            }],
            'execution_mode': 'parallel',  # Phase 2: parallel execution enabled
            'max_parallel_tasks': 3,  # Limit concurrent LLM calls to prevent overload
            'task_timeout': 300
        }

        # Merge in delegation settings from user config if present
        # Load config from file to get delegation settings
        user_config = self.config_manager.load_configuration("default")
        if user_config and "delegation" in user_config and isinstance(user_config["delegation"], dict):
            user_delegation = user_config["delegation"]

            # Override with user settings if present
            if "execution_mode" in user_delegation:
                config["execution_mode"] = user_delegation["execution_mode"]

            if "max_parallel_tasks" in user_delegation:
                config["max_parallel_tasks"] = user_delegation["max_parallel_tasks"]

            # Pass through trace logging settings
            if "trace_enabled" in user_delegation:
                config["trace_enabled"] = user_delegation["trace_enabled"]

            if "trace_level" in user_delegation:
                config["trace_level"] = user_delegation["trace_level"]

            if "trace_dir" in user_delegation:
                config["trace_dir"] = user_delegation["trace_dir"]

            if "trace_console" in user_delegation:
                config["trace_console"] = user_delegation["trace_console"]

            if "trace_truncate" in user_delegation:
                config["trace_truncate"] = user_delegation["trace_truncate"]

            # Pass through collapsible output settings
            if "collapsible_output" in user_delegation:
                config["collapsible_output"] = user_delegation["collapsible_output"]

        return DelegationClient(self, config)

    def get_filtered_tools_for_current_mode(self) -> List:
        """Get tools filtered based on current mode (PLAN vs ACT)

        Returns:
            List of enabled tools appropriate for the current mode
        """
        enabled_tools = self.tool_manager.get_enabled_tool_objects()

        if not self.plan_mode:
            # ACT mode: return all enabled tools
            return enabled_tools

        # PLAN mode: filter out write operations
        filtered_tools = [
            tool for tool in enabled_tools
            if tool.name not in self.plan_mode_disabled_tools
        ]

        return filtered_tools

    def clear_context(self):
        """Clear conversation history and token count"""
        original_history_length = len(self.chat_history)
        self.chat_history = []
        self.actual_token_count = 0
        self.console.print(f"[green]Context cleared! Removed {original_history_length} conversation entries.[/green]")

    def display_context_stats(self):
        """Display information about the current context window usage"""
        history_count = len(self.chat_history)

        # For thinking status, show a simplified message. The user can check model capabilities by trying to enable thinking mode
        thinking_status = ""
        if self.thinking_mode:
            thinking_status = f"Thinking mode: [green]Enabled[/green]\n"
            thinking_status += f"Show thinking text: [{'green' if self.show_thinking else 'red'}]{'Visible' if self.show_thinking else 'Hidden'}[/{'green' if self.show_thinking else 'red'}]\n"
        else:
            thinking_status = f"Thinking mode: [red]Disabled[/red]\n"

        self.console.print(Panel(
            f"Context retention: [{'green' if self.retain_context else 'red'}]{'Enabled' if self.retain_context else 'Disabled'}[/{'green' if self.retain_context else 'red'}]\n"
            f"{thinking_status}"
            f"Tool execution display: [{'green' if self.show_tool_execution else 'red'}]{'Enabled' if self.show_tool_execution else 'Disabled'}[/{'green' if self.show_tool_execution else 'red'}]\n"
            f"Performance metrics: [{'green' if self.show_metrics else 'red'}]{'Enabled' if self.show_metrics else 'Disabled'}[/{'green' if self.show_metrics else 'red'}]\n"
            f"Agent loop limit: [cyan]{self.loop_limit}[/cyan]\n"
            f"Human-in-the-Loop confirmations: [{'green' if self.hil_manager.get_config()['global_enabled'] else 'red'}]{'Enabled' if self.hil_manager.get_config()['global_enabled'] else 'Disabled'}[/{'green' if self.hil_manager.get_config()['global_enabled'] else 'red'}]\n"
            f"Conversation entries: {history_count}\n"
            f"Total tokens generated: {self.actual_token_count:,}",
            title="Context Info", border_style="cyan", expand=False
        ))

    def auto_load_default_config(self):
        """Automatically load the default configuration if it exists."""
        if self.config_manager.config_exists("default"):
            # self.console.print("[cyan]Default configuration found, loading...[/cyan]")
            self.default_configuration_status = self.load_configuration("default")
            if self.default_configuration_status:
                self.auto_loaded_files.append("~/.config/ollmcp/config.json")

    def print_auto_load_default_config_status(self):
        """Print the status of the auto-load default configuration and any auto-loaded files."""
        if self.default_configuration_status or self.auto_loaded_files:
            # Build the status message
            if self.default_configuration_status:
                message = "[green] ✓ Default configuration loaded successfully!"
            else:
                message = "[green] ✓ Auto-loaded configuration"

            # Add list of auto-loaded files if any
            if self.auto_loaded_files:
                files_list = ", ".join(self.auto_loaded_files)
                message += f" ({files_list})"

            message += "[/green]"
            self.console.print(message)
            self.console.print()

    def save_configuration(self, config_name=None):
        """Save current tool configuration and model settings to a file

        Args:
            config_name: Optional name for the config (defaults to 'default')
        """
        # Load existing config to preserve keys we don't manage (like mcpServers)
        existing_config = self.config_manager.load_configuration(config_name or "default")
        if not existing_config:
            existing_config = {}

        # Update with current client state (only overwrites keys we manage)
        existing_config.update({
            "model": self.model_manager.get_current_model(),
            "enabledTools": self.tool_manager.get_enabled_tools(),
            "contextSettings": {
                "retainContext": self.retain_context
            },
            "modelSettings": {
                "thinkingMode": self.thinking_mode,
                "showThinking": self.show_thinking
            },
            "agentSettings": {
                "loopLimit": self.loop_limit
            },
            "modelConfig": self.model_config_manager.get_config(),
            "displaySettings": {
                "showToolExecution": self.show_tool_execution,
                "showMetrics": self.show_metrics
            },
            "hilSettings": self.hil_manager.get_config(),
            "sessionSaveDirectory": self.session_save_directory
        })

        # Use the ConfigManager to save the merged configuration
        return self.config_manager.save_configuration(existing_config, config_name)

    def load_configuration(self, config_name=None):
        """Load tool configuration and model settings from a file

        Args:
            config_name: Optional name of the config to load (defaults to 'default')

        Returns:
            bool: True if loaded successfully, False otherwise
        """
        # Use the ConfigManager to load the configuration
        config_data = self.config_manager.load_configuration(config_name)

        if not config_data:
            return False

        # Apply the loaded configuration
        if "model" in config_data:
            self.model_manager.set_model(config_data["model"])

        # Load enabled tools if specified
        if "enabledTools" in config_data:
            loaded_tools = config_data["enabledTools"]

            # Only apply tools that actually exist in our available tools
            available_tool_names = {tool.name for tool in self.tool_manager.get_available_tools()}
            for tool_name, enabled in loaded_tools.items():
                if tool_name in available_tool_names:
                    # Update in the tool manager
                    self.tool_manager.set_tool_status(tool_name, enabled)
                    # Also update in the server connector
                    self.server_connector.set_tool_status(tool_name, enabled)

        # Load context settings if specified
        if "contextSettings" in config_data:
            if "retainContext" in config_data["contextSettings"]:
                self.retain_context = config_data["contextSettings"]["retainContext"]

        # Load model settings if specified
        if "modelSettings" in config_data:
            if "thinkingMode" in config_data["modelSettings"]:
                self.thinking_mode = config_data["modelSettings"]["thinkingMode"]
            if "showThinking" in config_data["modelSettings"]:
                self.show_thinking = config_data["modelSettings"]["showThinking"]

        if "agentSettings" in config_data:
            if "loopLimit" in config_data["agentSettings"]:
                try:
                    loop_limit = int(config_data["agentSettings"]["loopLimit"])
                    self.loop_limit = max(1, loop_limit)
                except (TypeError, ValueError):
                    pass

        # Load model configuration if specified
        if "modelConfig" in config_data:
            self.model_config_manager.set_config(config_data["modelConfig"])

        # Load display settings if specified
        if "displaySettings" in config_data:
            if "showToolExecution" in config_data["displaySettings"]:
                self.show_tool_execution = config_data["displaySettings"]["showToolExecution"]
            if "showMetrics" in config_data["displaySettings"]:
                self.show_metrics = config_data["displaySettings"]["showMetrics"]

        # Load HIL settings if specified
        if "hilSettings" in config_data:
            # Merge loaded HIL settings with default HIL settings to ensure all keys are present
            default_hil_config = self.hil_manager._get_default_hil_config()
            loaded_hil_config = config_data["hilSettings"]
            
            # Start with a copy of the default config
            merged_hil_config = default_hil_config.copy()
            
            # Update top-level keys from loaded config
            merged_hil_config.update(loaded_hil_config)
            
            # Handle nested 'servers' dictionary separately to merge deeply
            if "servers" in loaded_hil_config and isinstance(loaded_hil_config["servers"], dict):
                for server_name, server_settings in loaded_hil_config["servers"].items():
                    if server_name not in merged_hil_config["servers"]:
                        merged_hil_config["servers"][server_name] = {"enabled": True, "tools": {}} # Default for new server
                    
                    # Update server-level 'enabled' status
                    if "enabled" in server_settings:
                        merged_hil_config["servers"][server_name]["enabled"] = server_settings["enabled"]
                    
                    # Merge tools for this server
                    if "tools" in server_settings and isinstance(server_settings["tools"], dict):
                        merged_hil_config["servers"][server_name]["tools"].update(server_settings["tools"])

            self.hil_manager.set_config(merged_hil_config)

        # Load session save directory if specified
        if "sessionSaveDirectory" in config_data:
            self.session_save_directory = config_data["sessionSaveDirectory"]

        return True

    def reset_configuration(self):
        """Reset tool configuration to default (all tools enabled)"""
        # Use the ConfigManager to get the default configuration
        config_data = self.config_manager.reset_configuration()

        # Enable all tools in the tool manager
        self.tool_manager.enable_all_tools()
        # Enable all tools in the server connector
        self.server_connector.enable_all_tools()

        # Reset context settings from the default configuration
        if "contextSettings" in config_data:
            if "retainContext" in config_data["contextSettings"]:
                self.retain_context = config_data["contextSettings"]["retainContext"]

        # Reset model settings from the default configuration
        if "modelSettings" in config_data:
            if "thinkingMode" in config_data["modelSettings"]:
                self.thinking_mode = config_data["modelSettings"]["thinkingMode"]
            else:
                # Default thinking mode to False if not specified
                self.thinking_mode = False
            if "showThinking" in config_data["modelSettings"]:
                self.show_thinking = config_data["modelSettings"]["showThinking"]
            else:
                # Default show thinking to True if not specified
                self.show_thinking = True

        if "agentSettings" in config_data:
            if "loopLimit" in config_data["agentSettings"]:
                try:
                    self.loop_limit = max(1, int(config_data["agentSettings"]["loopLimit"]))
                except (TypeError, ValueError):
                    self.loop_limit = 3
            else:
                self.loop_limit = 3
        else:
            self.loop_limit = 3

        # Reset display settings from the default configuration
        if "displaySettings" in config_data:
            if "showToolExecution" in config_data["displaySettings"]:
                self.show_tool_execution = config_data["displaySettings"]["showToolExecution"]
            else:
                # Default show tool execution to True if not specified
                self.show_tool_execution = True
            if "showMetrics" in config_data["displaySettings"]:
                self.show_metrics = config_data["displaySettings"]["showMetrics"]
            else:
                # Default show metrics to False if not specified
                self.show_metrics = False

        # Reset HIL settings from the default configuration
        if "hilSettings" in config_data:
            self.hil_manager.set_config(config_data["hilSettings"])
        else:
            self.hil_manager.set_config(self.hil_manager._get_default_hil_config())

        return True

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

    async def reload_servers(self):
        """Reload all MCP servers with the same connection parameters"""
        if not any(self.server_connection_params.values()):
            self.console.print("[yellow]No server connection parameters stored. Cannot reload.[/yellow]")
            return

        self.console.print("[cyan]🔄 Reloading MCP servers...[/cyan]")

        try:
            # Store current tool enabled states
            current_enabled_tools = self.tool_manager.get_enabled_tools().copy()

            # Disconnect from all current servers
            await self.server_connector.disconnect_all_servers()

            # Update our exit_stack reference to the new one created by ServerConnector
            self.exit_stack = self.server_connector.exit_stack

            # Reconnect using stored parameters
            await self.connect_to_servers(
                server_paths=self.server_connection_params['server_paths'],
                server_urls=self.server_connection_params['server_urls'],
                config_path=self.server_connection_params['config_path'],
                auto_discovery=self.server_connection_params['auto_discovery']
            )

            # Restore enabled tool states for tools that still exist
            available_tool_names = {tool.name for tool in self.tool_manager.get_available_tools()}
            for tool_name, enabled in current_enabled_tools.items():
                if tool_name in available_tool_names:
                    self.tool_manager.set_tool_status(tool_name, enabled)
                    self.server_connector.set_tool_status(tool_name, enabled)

            self.console.print("[green]✅ MCP servers reloaded successfully![/green]")

            # Display updated status
            self.display_available_tools()

        except Exception as e:
            self.console.print(Panel(
                f"[bold red]Error reloading servers:[/bold red] {str(e)}\n\n"
                "You may need to restart the application if servers are not working properly.",
                title="Reload Failed", border_style="red", expand=False
            ))

app = typer.Typer(help="MCP Client for Ollama", context_settings={"help_option_names": ["-h", "--help"]})

@app.command()
def main(
    # MCP Server Configuration
    mcp_server: Optional[List[str]] = typer.Option(
        None, "--mcp-server", "-s",
        help="Path to a server script (.py or .js)",
        rich_help_panel="MCP Server Configuration"
    ),
    mcp_server_url: Optional[List[str]] = typer.Option(
        None, "--mcp-server-url", "-u",
        help="URL for SSE or Streamable HTTP MCP server (e.g., http://localhost:8000/sse, https://domain-name.com/mcp, etc)",
        rich_help_panel="MCP Server Configuration"
    ),
    servers_json: Optional[str] = typer.Option(
        None, "--servers-json", "-j",
        help="Path to a JSON file with server configurations. If not specified, .config/config.json will be auto-loaded if it exists.",
        rich_help_panel="MCP Server Configuration"
    ),
    auto_discovery: bool = typer.Option(
        False, "--auto-discovery", "-a",
        help=f"Auto-discover servers from Claude's config at {DEFAULT_CLAUDE_CONFIG} - If no other options are provided, this will be enabled by default",
        rich_help_panel="MCP Server Configuration"
    ),

    # Ollama Configuration
    model: str = typer.Option(
        DEFAULT_MODEL, "--model", "-m",
        help="Ollama model to use",
        rich_help_panel="Ollama Configuration"
    ),
    host: str = typer.Option(
        DEFAULT_OLLAMA_HOST, "--host", "-H",
        help="Ollama host URL",
        rich_help_panel="Ollama Configuration"
    ),

    # General Options
    version: Optional[bool] = typer.Option(
        None, "--version", "-v",
        help="Show version and exit",
    ),

    # Non-interactive Query Mode
    query: Optional[str] = typer.Option(
        None, "--query", "-q",
        help="Execute a single query non-interactively and exit (useful for scripts)",
        rich_help_panel="General Options"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-Q",
        help="Minimal output mode (use with --query for scripting)",
        rich_help_panel="General Options"
    ),

    # Delegation Trace Options
    trace_enabled: Optional[bool] = typer.Option(
        None, "--trace-enabled", "--trace",
        help="Enable delegation trace logging (use with delegation queries)",
        rich_help_panel="Delegation Options"
    ),
    trace_level: Optional[str] = typer.Option(
        None, "--trace-level",
        help="Trace detail level: off, summary, basic, full, debug (default: basic)",
        rich_help_panel="Delegation Options"
    ),
    trace_dir: Optional[str] = typer.Option(
        None, "--trace-dir",
        help="Directory for trace files (default: .trace)",
        rich_help_panel="Delegation Options"
    )
):
    """Run the MCP Client for Ollama with specified options."""

    if version:
        typer.echo(f"mcp-client-for-ollama {__version__}")
        raise typer.Exit()

    # If none of the server arguments are provided and no .config/config.json exists, enable auto-discovery
    if not (mcp_server or mcp_server_url or servers_json or auto_discovery):
        # Check if .config/config.json exists - if not, enable auto-discovery
        if not os.path.exists(".config/config.json"):
            auto_discovery = True

    # Run the async main function
    asyncio.run(async_main(mcp_server, mcp_server_url, servers_json, auto_discovery, model, host, query, quiet, trace_enabled, trace_level, trace_dir))

async def async_main(mcp_server, mcp_server_url, servers_json, auto_discovery, model, host, query=None, quiet=False, trace_enabled=None, trace_level=None, trace_dir=None):
    """Asynchronous main function to run the MCP Client for Ollama"""

    # Create console with minimal output if in quiet mode
    console = Console(quiet=quiet)

    # Handle trace options from command line
    if trace_enabled is not None or trace_level is not None or trace_dir is not None:
        # Load or create config
        from .config.manager import ConfigManager
        config_mgr = ConfigManager(console)
        current_config = config_mgr.load_configuration("default")
        if not current_config:
            current_config = {}

        if "delegation" not in current_config:
            current_config["delegation"] = {}

        delegation = current_config["delegation"]

        # Apply command-line trace options
        if trace_enabled is not None:
            delegation["enabled"] = True  # Auto-enable delegation if trace options provided
            delegation["trace_enabled"] = trace_enabled
            if not quiet:
                console.print(f"[green]Trace logging {'enabled' if trace_enabled else 'disabled'}[/green]")

        if trace_level is not None:
            valid_levels = ["off", "summary", "basic", "full", "debug"]
            if trace_level.lower() in valid_levels:
                delegation["trace_level"] = trace_level.lower()
                if trace_level.lower() == "basic":
                    delegation["trace_truncate"] = 500
                if not quiet:
                    console.print(f"[green]Trace level set to: {trace_level.lower()}[/green]")
            else:
                console.print(f"[yellow]Warning: Invalid trace level '{trace_level}'. Using 'basic'.[/yellow]")
                delegation["trace_level"] = "basic"

        if trace_dir is not None:
            delegation["trace_dir"] = trace_dir
            if not quiet:
                console.print(f"[green]Trace directory set to: {trace_dir}[/green]")

        # Set default collapsible output settings if not present
        if "collapsible_output" not in delegation:
            delegation["collapsible_output"] = {
                "auto_collapse": True,
                "line_threshold": 20,
                "char_threshold": 1000
            }

        # Save updated config
        current_config["delegation"] = delegation
        config_mgr.save_configuration(current_config, "default")

        if not quiet:
            console.print("[dim]Trace configuration saved to .config/config.json[/dim]\n")

    # Create a temporary client to check if Ollama is running
    client = MCPClient(model=model, host=host)
    if not await client.model_manager.check_ollama_running():
        console.print(Panel(
            "[bold red]Error: Ollama is not running![/bold red]\n\n"
            "This client requires Ollama to be running to process queries.\n"
            "Please start Ollama by running the 'ollama serve' command in a terminal.",
            title="Ollama Not Running", border_style="red", expand=False
        ))
        return

    # Handle server configuration options - only use one source to prevent duplicates
    config_path = None
    auto_discovery_final = auto_discovery

    # Check for .config/config.json and auto-load it if it exists (unless overridden by CLI options)
    default_config_json = ".config/config.json"
    if not servers_json and os.path.exists(default_config_json):
        config_path = default_config_json
        client.auto_loaded_files.append(default_config_json)
        console.print(f"[green]📋 Auto-loading server configuration from {default_config_json}[/green]")

    if servers_json:
        # If --servers-json is provided, use that and disable auto-discovery (overrides .config/config.json)
        if os.path.exists(servers_json):
            config_path = servers_json
        else:
            console.print(f"[bold red]Error: Specified JSON config file not found: {servers_json}[/bold red]")
            return
    elif auto_discovery:
        # If --auto-discovery is provided, use that and set config_path to None
        auto_discovery_final = True
        if os.path.exists(DEFAULT_CLAUDE_CONFIG):
            console.print(f"[cyan]Auto-discovering servers from Claude's config at {DEFAULT_CLAUDE_CONFIG}[/cyan]")
        else:
            console.print(f"[yellow]Warning: Claude config not found at {DEFAULT_CLAUDE_CONFIG}[/yellow]")
    else:
        # If neither is provided, check if DEFAULT_CLAUDE_CONFIG exists and use auto_discovery
        if not mcp_server and not mcp_server_url:
            if os.path.exists(DEFAULT_CLAUDE_CONFIG):
                console.print(f"[cyan]Auto-discovering servers from Claude's config at {DEFAULT_CLAUDE_CONFIG}[/cyan]")
                auto_discovery_final = True
            else:
                console.print("[yellow]Warning: No servers specified and Claude config not found.[/yellow]")

    # Validate mcp-server paths exist
    if mcp_server:
        for server_path in mcp_server:
            if not os.path.exists(server_path):
                console.print(f"[bold red]Error: Server script not found: {server_path}[/bold red]")
                return
    try:
        await client.connect_to_servers(mcp_server, mcp_server_url, config_path, auto_discovery_final)
        client.auto_load_default_config()

        # Load project context after configuration to ensure it's not overwritten
        await client.apply_project_context()

        # If model was explicitly provided via CLI flag (not default), override any loaded config
        if model != DEFAULT_MODEL:
            client.model_manager.set_model(model)

        # Handle non-interactive query mode
        if query:
            # Set quiet mode on client for minimal output
            client.quiet_mode = quiet

            # Execute single query and exit
            if not quiet:
                console.print(f"[cyan]Executing query: {query}[/cyan]\n")

            await client.handle_user_input(query)

            if not quiet:
                console.print("\n[green]Query completed successfully.[/green]")
        else:
            # Interactive mode - enter chat loop
            await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    app()
