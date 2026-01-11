"""Built-in tools for MCP Client for Ollama."""

import io, sys, os, shutil, fnmatch, base64
from pathlib import Path
from typing import List, Dict, Any, Callable, Set, Optional
from mcp import Tool
from datetime import datetime
from rich.console import Console
from rich.prompt import Confirm

class BuiltinToolManager:
    """Manages the definition and execution of built-in tools."""

    def __init__(self, model_config_manager: Any, ollama_host: str = None, config_manager: Any = None, console: Optional[Console] = None, parent_tool_manager: Any = None):
        """
        Initializes the BuiltinToolManager.

        Args:
            model_config_manager: An instance of ModelConfigManager to interact with model settings.
            ollama_host: Optional Ollama server URL. If not provided, uses OLLAMA_HOST env var or default.
            config_manager: An instance of ConfigManager to interact with application config.
            console: Rich console for user prompts and output.
            parent_tool_manager: Optional reference to parent ToolManager (for accessing MCP tools).
        """
        self.model_config_manager = model_config_manager
        self.ollama_host = ollama_host or os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        self.config_manager = config_manager
        self.console = console or Console()
        self.working_directory = os.getcwd()  # Store the working directory for security checks
        self._approved_paths: Set[str] = set()  # Store approved base directories for file access
        self.memory_tools = None  # Reference to MemoryTools instance (set when memory system is enabled)
        self.parent_tool_manager = parent_tool_manager  # Reference to parent ToolManager with all tools (builtin + MCP)
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], str]] = {
            "set_system_prompt": self._handle_set_system_prompt,
            "get_system_prompt": self._handle_get_system_prompt,
            "execute_python_code": self._handle_execute_python_code,
            "execute_bash_command": self._handle_execute_bash_command,
            "run_pytest": self._handle_run_pytest,
            "validate_file_path": self._handle_validate_file_path,
            "read_file": self._handle_read_file,
            "write_file": self._handle_write_file,
            "patch_file": self._handle_patch_file,
            "list_files": self._handle_list_files,
            "list_directories": self._handle_list_directories,
            "create_directory": self._handle_create_directory,
            "delete_file": self._handle_delete_file,
            "file_exists": self._handle_file_exists,
            "get_file_info": self._handle_get_file_info,
            "read_image": self._handle_read_image,
            "open_file": self._handle_open_file,
            "get_config": self._handle_get_config,
            "update_config_section": self._handle_update_config_section,
            "add_mcp_server": self._handle_add_mcp_server,
            "remove_mcp_server": self._handle_remove_mcp_server,
            "list_mcp_servers": self._handle_list_mcp_servers,
            "get_config_path": self._handle_get_config_path,
            # Memory tools (only available when memory system is enabled)
            "update_feature_status": self._handle_update_feature_status,
            "log_progress": self._handle_log_progress,
            "add_test_result": self._handle_add_test_result,
            "get_memory_state": self._handle_get_memory_state,
            "get_feature_details": self._handle_get_feature_details,
            "get_goal_details": self._handle_get_goal_details,
            # Interactive memory management tools
            "add_goal": self._handle_add_goal,
            "update_goal": self._handle_update_goal,
            "remove_goal": self._handle_remove_goal,
            "add_feature": self._handle_add_feature,
            "update_feature": self._handle_update_feature,
            "remove_feature": self._handle_remove_feature,
            "update_session_description": self._handle_update_session_description,
            "move_feature": self._handle_move_feature,
            "get_project_context": self._handle_get_project_context,
            "rescan_project_context": self._handle_rescan_project_context,
            # Artifact generation tools
            "generate_tool_form": self._handle_generate_tool_form,
            "generate_query_builder": self._handle_generate_query_builder,
            "generate_tool_wizard": self._handle_generate_tool_wizard,
            "generate_batch_tool": self._handle_generate_batch_tool,
        }

    def set_memory_tools(self, memory_tools: Any) -> None:
        """
        Set the MemoryTools instance for memory-related builtin tools.

        This should be called when the delegation client is created with memory enabled.

        Args:
            memory_tools: MemoryTools instance from delegation_client
        """
        self.memory_tools = memory_tools

    def get_builtin_tools(self) -> List[Tool]:
        """
        Returns a list of all built-in Tool objects.

        Returns:
            A list of Tool objects for the built-in tools.
        """
        set_prompt_tool = Tool(
            name="builtin.set_system_prompt",
            description="Update the system prompt for the assistant. Use this to change your instructions or persona.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The new system prompt. Use a concise and clear prompt to define the persona and instructions for the AI assistant."
                    }
                },
                "required": ["prompt"]
            }
        )
        
        get_prompt_tool = Tool(
            name="builtin.get_system_prompt",
            description="Get the current system prompt for the assistant.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        )

        execute_python_code_tool = Tool(
            name="builtin.execute_python_code",
            description="Executes arbitrary Python code. Use with caution as this can perform system operations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute."
                    }
                },
                "required": ["code"]
            }
        )

        execute_bash_command_tool = Tool(
            name="builtin.execute_bash_command",
            description="Executes arbitrary bash commands. Use with caution as this can perform system operations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute."
                    }
                },
                "required": ["command"]
            }
        )

        run_pytest_tool = Tool(
            name="builtin.run_pytest",
            description="Run pytest tests with automatic virtualenv detection. More reliable than execute_bash_command for running tests. Returns test results directly without file I/O.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Optional path/directory to test. Defaults to current directory if not specified."
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Run pytest in verbose mode (-v). Default: false"
                    },
                    "markers": {
                        "type": "string",
                        "description": "Pytest marker expression to filter tests (e.g., 'unit', 'not slow')"
                    },
                    "extra_args": {
                        "type": "string",
                        "description": "Additional pytest arguments as a single string (e.g., '-x --tb=short')"
                    }
                },
                "required": []
            }
        )

        read_file_tool = Tool(
            name="builtin.read_file",
            description=(
                "Read the contents of a file. Path must be relative to the current working directory. "
                "Supports partial file reading with offset and limit parameters for efficient handling of large files. "
                "Returns content with line numbers (cat -n format)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file to read."
                    },
                    "offset": {
                        "type": "integer",
                        "description": (
                            "The line number to start reading from (1-indexed). "
                            "If not specified, reads from the beginning of the file. "
                            "Example: offset=50 starts reading from line 50."
                        ),
                        "minimum": 1
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            "The maximum number of lines to read. "
                            "If not specified, reads all lines from offset to end of file. "
                            "Useful for reading large files in chunks. "
                            "Example: offset=1, limit=100 reads lines 1-100."
                        ),
                        "minimum": 1
                    }
                },
                "required": ["path"]
            }
        )

        write_file_tool = Tool(
            name="builtin.write_file",
            description="Write content to a file. Creates the file if it doesn't exist. Path must be relative to the current working directory. Note: For large files (>500 lines) or small targeted changes, consider using builtin.patch_file instead to reduce context usage.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file to write."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file."
                    }
                },
                "required": ["path", "content"]
            }
        )

        patch_file_tool = Tool(
            name="builtin.patch_file",
            description=(
                "Apply multiple search-replace changes to a file efficiently without writing entire contents. "
                "RECOMMENDED for: (1) files larger than 500 lines, (2) making small targeted changes to any file, "
                "(3) multiple related edits in one operation. More efficient than write_file as it reduces "
                "context window usage significantly. Changes are applied sequentially in the order provided. "
                "All changes must succeed or the file is left unchanged (atomic operation). "
                "Path must be relative to the current working directory."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file to patch."
                    },
                    "changes": {
                        "type": "array",
                        "description": (
                            "Array of search-replace operations to apply sequentially. "
                            "Each change must find exactly one match unless 'occurrence' is specified."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "search": {
                                    "type": "string",
                                    "description": (
                                        "Exact text to find in the file. Must be unique unless 'occurrence' "
                                        "is specified. Can span multiple lines."
                                    )
                                },
                                "replace": {
                                    "type": "string",
                                    "description": (
                                        "Text to replace the search text with. Use empty string to delete. "
                                        "Preserves surrounding content."
                                    )
                                },
                                "occurrence": {
                                    "type": "integer",
                                    "description": (
                                        "Which occurrence to replace (1-indexed). If omitted, the search "
                                        "text must appear exactly once in the file. Use this when the same "
                                        "text appears multiple times."
                                    ),
                                    "minimum": 1
                                }
                            },
                            "required": ["search", "replace"]
                        },
                        "minItems": 1
                    }
                },
                "required": ["path", "changes"]
            }
        )

        list_files_tool = Tool(
            name="builtin.list_files",
            description="List all files in a directory. Path must be relative to the current working directory. If no path is provided, lists files in the current directory. By default, respects .gitignore patterns to show only relevant files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the directory. Defaults to current directory if not provided."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to list files recursively in subdirectories. Defaults to false."
                    },
                    "respect_gitignore": {
                        "type": "boolean",
                        "description": "Whether to filter out files matching .gitignore patterns. Defaults to true."
                    }
                }
            }
        )

        list_directories_tool = Tool(
            name="builtin.list_directories",
            description="List all subdirectories in a directory. Path must be relative to the current working directory. If no path is provided, lists directories in the current directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the directory. Defaults to current directory if not provided."
                    }
                }
            }
        )

        create_directory_tool = Tool(
            name="builtin.create_directory",
            description="Create a new directory. Path must be relative to the current working directory. Creates parent directories if needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the directory to create."
                    }
                },
                "required": ["path"]
            }
        )

        delete_file_tool = Tool(
            name="builtin.delete_file",
            description="Delete a file. Path must be relative to the current working directory. Use with caution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file to delete."
                    }
                },
                "required": ["path"]
            }
        )


        validate_file_path_tool = Tool(
            name="builtin.validate_file_path",
            description=(
                "REQUIRED FIRST STEP for file operations: Extract and validate a file path from your task description. "
                "This tool locks the path and returns the validated absolute path that you MUST use for all subsequent file operations. "
                "Call this BEFORE any file operations (read_file, write_file, patch_file, file_exists, process_document, etc.). "
                "This prevents path hallucination and ensures you use the exact path from your task description."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "The exact file path extracted from your task description. "
                            "Copy it character-for-character from the task. "
                            "Can be absolute (starts with /) or relative to working directory."
                        )
                    },
                    "task_description": {
                        "type": "string",
                        "description": (
                            "Your complete task description. "
                            "This helps verify you extracted the path correctly."
                        )
                    }
                },
                "required": ["path", "task_description"]
            }
        )

        file_exists_tool = Tool(
            name="builtin.file_exists",
            description="Check if a file or directory exists. Path must be relative to the current working directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to check."
                    }
                },
                "required": ["path"]
            }
        )

        get_file_info_tool = Tool(
            name="builtin.get_file_info",
            description="Get metadata about a file (size, modification time, permissions, etc.). Path must be relative to the current working directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file."
                    }
                },
                "required": ["path"]
            }
        )

        read_image_tool = Tool(
            name="builtin.read_image",
            description="Analyze an image using a vision model (llava, bakllava, etc.). Reads an image file, converts it to base64, and uses a vision-capable model to analyze it. Automatically detects available vision models on the Ollama server.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file (relative to current working directory). Supported formats: PNG, JPG, JPEG, GIF, BMP, WEBP."
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Question or instruction about the image. Defaults to 'Describe what you see in this image in detail.'"
                    }
                },
                "required": ["image_path"]
            }
        )

        open_file_tool = Tool(
            name="builtin.open_file",
            description="Open a file with its default system application using xdg-open (Linux). Useful for opening PDFs, images, documents, and other files in their native viewers. The command runs in the background and returns immediately.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file to open."
                    }
                },
                "required": ["path"]
            }
        )

        get_config_tool = Tool(
            name="builtin.get_config",
            description="Get the current application configuration or a specific section. Returns the config as JSON. Available sections: delegation, memory, mcpServers, modelConfig, displaySettings, hilSettings, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": "Optional section name to retrieve (e.g., 'delegation', 'memory', 'mcpServers'). If omitted, returns the entire config."
                    }
                },
                "required": []
            }
        )

        update_config_section_tool = Tool(
            name="builtin.update_config_section",
            description="Update a specific section of the application configuration. Changes are saved to the config file immediately. Note: Some changes may require restart or reload to take effect.",
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": "The section to update (e.g., 'delegation', 'memory', 'displaySettings', 'hilSettings')."
                    },
                    "data": {
                        "type": "object",
                        "description": "The new data for the section as a JSON object."
                    }
                },
                "required": ["section", "data"]
            }
        )

        add_mcp_server_tool = Tool(
            name="builtin.add_mcp_server",
            description="Add a new MCP server to the configuration. For stdio servers, provide command and args. For HTTP/SSE servers, provide url. Server will be available after reloading servers with 'reload-servers' command.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique name for the MCP server."
                    },
                    "type": {
                        "type": "string",
                        "description": "Server type: 'stdio', 'sse', or 'streamable_http'.",
                        "enum": ["stdio", "sse", "streamable_http"]
                    },
                    "command": {
                        "type": "string",
                        "description": "Command to run (for stdio servers). E.g., 'python', 'node', 'npx'."
                    },
                    "args": {
                        "type": "array",
                        "description": "Command arguments (for stdio servers). E.g., ['-m', 'my_mcp_server'].",
                        "items": {"type": "string"}
                    },
                    "url": {
                        "type": "string",
                        "description": "Server URL (for sse/streamable_http servers). E.g., 'http://localhost:8000'."
                    },
                    "env": {
                        "type": "object",
                        "description": "Environment variables for the server (optional).",
                        "additionalProperties": {"type": "string"}
                    },
                    "disabled": {
                        "type": "boolean",
                        "description": "Whether the server should be disabled initially (default: false)."
                    }
                },
                "required": ["name", "type"]
            }
        )

        remove_mcp_server_tool = Tool(
            name="builtin.remove_mcp_server",
            description="Remove an MCP server from the configuration. Use 'reload-servers' command after removal to disconnect the server.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the MCP server to remove."
                    }
                },
                "required": ["name"]
            }
        )

        list_mcp_servers_tool = Tool(
            name="builtin.list_mcp_servers",
            description="List all configured MCP servers with their types and status. Returns a JSON array of server configurations.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )

        get_config_path_tool = Tool(
            name="builtin.get_config_path",
            description="Get the absolute path to the current configuration file. Useful for knowing where the config is stored.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )

        # Memory tools - only available when memory system is enabled
        update_feature_status_tool = Tool(
            name="builtin.update_feature_status",
            description="Update the status of a feature in the current memory session. Use this to mark features as pending, in_progress, completed, failed, or blocked. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "string",
                        "description": "ID of the feature to update (e.g., 'F1', 'F2')"
                    },
                    "status": {
                        "type": "string",
                        "description": "New status for the feature",
                        "enum": ["pending", "in_progress", "completed", "failed", "blocked"]
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the status update"
                    }
                },
                "required": ["feature_id", "status"]
            }
        )

        log_progress_tool = Tool(
            name="builtin.log_progress",
            description="Log a progress entry to the current memory session. Use this to record what actions you took and their outcomes. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "description": "Type of agent making the entry (e.g., 'CODER', 'EXECUTOR', 'DEBUGGER')"
                    },
                    "action": {
                        "type": "string",
                        "description": "Short description of the action taken (e.g., 'Implemented login endpoint')"
                    },
                    "outcome": {
                        "type": "string",
                        "description": "Outcome of the action",
                        "enum": ["success", "failure", "partial", "blocked"]
                    },
                    "details": {
                        "type": "string",
                        "description": "Detailed description of what was done"
                    },
                    "feature_id": {
                        "type": "string",
                        "description": "Optional feature ID this relates to"
                    },
                    "artifacts_changed": {
                        "type": "array",
                        "description": "Optional list of files/artifacts modified",
                        "items": {"type": "string"}
                    }
                },
                "required": ["agent_type", "action", "outcome", "details"]
            }
        )

        add_test_result_tool = Tool(
            name="builtin.add_test_result",
            description="Add a test result to a feature in the current memory session. Use this to record test execution results. Feature status will be auto-updated based on test results. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "string",
                        "description": "ID of the feature being tested"
                    },
                    "test_id": {
                        "type": "string",
                        "description": "ID/name of the test (e.g., 'test_login_success')"
                    },
                    "passed": {
                        "type": "boolean",
                        "description": "Whether the test passed"
                    },
                    "details": {
                        "type": "string",
                        "description": "Optional details about the test"
                    },
                    "output": {
                        "type": "string",
                        "description": "Optional test output"
                    }
                },
                "required": ["feature_id", "test_id", "passed"]
            }
        )

        get_memory_state_tool = Tool(
            name="builtin.get_memory_state",
            description="Get a summary of the current memory session state, including all goals, features, and progress. Use this to check what work has been completed and what remains. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )

        get_feature_details_tool = Tool(
            name="builtin.get_feature_details",
            description="Get detailed information about a specific feature, including acceptance criteria, test results, and notes. Use this to understand what a feature requires. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "string",
                        "description": "ID of the feature to get details for"
                    }
                },
                "required": ["feature_id"]
            }
        )

        get_goal_details_tool = Tool(
            name="builtin.get_goal_details",
            description="Get detailed information about a specific goal and its features. Use this when users ask about a specific goal (e.g., 'show me G1', 'what's in goal 2'). Shows goal description, constraints, progress, and feature summary. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "ID of the goal to get details for (e.g., 'G1', 'G2')"
                    }
                },
                "required": ["goal_id"]
            }
        )

        # Interactive memory management tools
        add_goal_tool = Tool(
            name="builtin.add_goal",
            description="Add a new goal to the current memory session. Use this when users want to add new high-level goals as their plans evolve. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Clear description of the goal"
                    },
                    "constraints": {
                        "type": "array",
                        "description": "Optional list of constraints or requirements",
                        "items": {"type": "string"}
                    }
                },
                "required": ["description"]
            }
        )

        update_goal_tool = Tool(
            name="builtin.update_goal",
            description="Update an existing goal's description or constraints. Use this when users want to modify goals as their plans change. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "ID of the goal to update (e.g., 'G1')"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description for the goal"
                    },
                    "add_constraints": {
                        "type": "array",
                        "description": "List of constraints to add",
                        "items": {"type": "string"}
                    },
                    "remove_constraints": {
                        "type": "array",
                        "description": "List of constraints to remove",
                        "items": {"type": "string"}
                    }
                },
                "required": ["goal_id"]
            }
        )

        remove_goal_tool = Tool(
            name="builtin.remove_goal",
            description="Remove a goal and all its features from the current memory session. Use this when users want to delete goals that are no longer needed. Requires confirmation. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "ID of the goal to remove (e.g., 'G1')"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true to confirm deletion (safety check)"
                    }
                },
                "required": ["goal_id"]
            }
        )

        add_feature_tool = Tool(
            name="builtin.add_feature",
            description="Add a new feature to an existing goal. Use this when users want to add new requirements or tasks as they emerge. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "ID of the goal to add the feature to (e.g., 'G1')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear description of the feature"
                    },
                    "criteria": {
                        "type": "array",
                        "description": "Optional list of pass/fail acceptance criteria",
                        "items": {"type": "string"}
                    },
                    "tests": {
                        "type": "array",
                        "description": "Optional list of test names",
                        "items": {"type": "string"}
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority level",
                        "enum": ["high", "medium", "low"]
                    },
                    "assigned_to": {
                        "type": "string",
                        "description": "Optional assignee (agent type or person name)"
                    }
                },
                "required": ["goal_id", "description"]
            }
        )

        update_feature_tool = Tool(
            name="builtin.update_feature",
            description="Update an existing feature's properties (description, criteria, tests, priority, assignee). Use this when users want to modify features as requirements evolve. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "string",
                        "description": "ID of the feature to update (e.g., 'F1')"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description for the feature"
                    },
                    "add_criteria": {
                        "type": "array",
                        "description": "List of criteria to add",
                        "items": {"type": "string"}
                    },
                    "remove_criteria": {
                        "type": "array",
                        "description": "List of criteria to remove",
                        "items": {"type": "string"}
                    },
                    "add_tests": {
                        "type": "array",
                        "description": "List of test names to add",
                        "items": {"type": "string"}
                    },
                    "remove_tests": {
                        "type": "array",
                        "description": "List of test names to remove",
                        "items": {"type": "string"}
                    },
                    "priority": {
                        "type": "string",
                        "description": "New priority level",
                        "enum": ["high", "medium", "low"]
                    },
                    "assigned_to": {
                        "type": "string",
                        "description": "New assignee (agent type or person name)"
                    }
                },
                "required": ["feature_id"]
            }
        )

        remove_feature_tool = Tool(
            name="builtin.remove_feature",
            description="Remove a feature from its parent goal. Use this when users want to delete features that are no longer needed. Requires confirmation. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "string",
                        "description": "ID of the feature to remove (e.g., 'F1')"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true to confirm deletion (safety check)"
                    }
                },
                "required": ["feature_id"]
            }
        )

        update_session_description_tool = Tool(
            name="builtin.update_session_description",
            description="Update the current memory session's description. Use this when users want to update the session metadata as their focus changes. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "New session description"
                    }
                },
                "required": ["description"]
            }
        )

        move_feature_tool = Tool(
            name="builtin.move_feature",
            description="Move a feature from one goal to another. Use this when users want to reorganize features as their goal structure changes. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "string",
                        "description": "ID of the feature to move (e.g., 'F1')"
                    },
                    "target_goal_id": {
                        "type": "string",
                        "description": "ID of the goal to move it to (e.g., 'G2')"
                    }
                },
                "required": ["feature_id", "target_goal_id"]
            }
        )

        get_project_context_tool = Tool(
            name="builtin.get_project_context",
            description="View the cached project context including working directory, project type, key folders, and important files. Use this to understand the project structure without re-scanning. Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )

        rescan_project_context_tool = Tool(
            name="builtin.rescan_project_context",
            description="Force a rescan of the project structure to update the cached context. Use this when the project structure has changed during the session (new files/folders added, etc.). Only available when memory system is active.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )

        # Artifact generation tools
        generate_tool_form_tool = Tool(
            name="builtin.generate_tool_form",
            description="Generate an interactive form artifact for a specific MCP tool. Creates a user-friendly input panel with smart widget selection and parameter suggestions. The form will be displayed in the web UI for easy tool execution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "The name of the tool to generate a form for (e.g., 'builtin.read_file')"
                    },
                    "prefill": {
                        "type": "object",
                        "description": "Optional dictionary of prefilled parameter values"
                    }
                },
                "required": ["tool_name"]
            }
        )

        generate_query_builder_tool = Tool(
            name="builtin.generate_query_builder",
            description="Generate a query builder artifact that helps users discover and use available tools. Creates an interactive interface with categorized tools, common patterns, and context-aware suggestions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_category": {
                        "type": "string",
                        "description": "Optional category to filter tools (e.g., 'File Operations', 'Memory Management')"
                    }
                },
                "required": []
            }
        )

        generate_tool_wizard_tool = Tool(
            name="builtin.generate_tool_wizard",
            description="Generate a multi-step wizard artifact for a complex tool. Breaks the tool's parameters into logical steps with validation and progress tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "The name of the tool to create a wizard for"
                    }
                },
                "required": ["tool_name"]
            }
        )

        generate_batch_tool_tool = Tool(
            name="builtin.generate_batch_tool",
            description="Generate a batch processing artifact for executing a tool multiple times with different inputs. Useful for bulk operations on multiple files or items.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "The name of the tool to create a batch interface for"
                    },
                    "initial_inputs": {
                        "type": "array",
                        "description": "Optional array of initial input parameter sets",
                        "items": {"type": "object"}
                    }
                },
                "required": ["tool_name"]
            }
        )

        # Build the tool list - include memory tools only if memory_tools is available
        tools = [
            set_prompt_tool, get_prompt_tool, execute_python_code_tool, execute_bash_command_tool, run_pytest_tool,
            read_file_tool, validate_file_path_tool, write_file_tool, patch_file_tool, list_files_tool, list_directories_tool,
            create_directory_tool, delete_file_tool, file_exists_tool, get_file_info_tool,
            read_image_tool, open_file_tool, get_config_tool, update_config_section_tool,
            add_mcp_server_tool, remove_mcp_server_tool, list_mcp_servers_tool, get_config_path_tool,
            # Artifact generation tools
            generate_tool_form_tool, generate_query_builder_tool, generate_tool_wizard_tool, generate_batch_tool_tool
        ]

        # Add memory tools if memory system is enabled
        if self.memory_tools is not None:
            tools.extend([
                # Status and progress tracking
                update_feature_status_tool,
                log_progress_tool,
                add_test_result_tool,
                get_memory_state_tool,
                get_feature_details_tool,
                get_goal_details_tool,
                # Interactive memory management
                add_goal_tool,
                update_goal_tool,
                remove_goal_tool,
                add_feature_tool,
                update_feature_tool,
                remove_feature_tool,
                update_session_description_tool,
                move_feature_tool,
                # Project context tools
                get_project_context_tool,
                rescan_project_context_tool,
            ])

        return tools

    def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        Executes a built-in tool and returns the result.

        Args:
            tool_name: The name of the tool to execute.
            tool_args: The arguments for the tool.

        Returns:
            A string containing the result of the tool execution.
        """
        handler = self._tool_handlers.get(tool_name)
        if handler:
            return handler(tool_args)
        return f"Error: Unknown built-in tool '{tool_name}'"

    def _handle_set_system_prompt(self, args: Dict[str, Any]) -> str:
        """Handles the 'set_system_prompt' tool call."""
        new_prompt = args.get("prompt")
        if new_prompt is not None:
            self.model_config_manager.system_prompt = new_prompt
            return "System prompt updated successfully."
        return "Error: 'prompt' argument is required."

    def _handle_get_system_prompt(self, args: Dict[str, Any]) -> str:
        """Handles the 'get_system_prompt' tool call."""
        current_prompt = self.model_config_manager.get_system_prompt()
        return f"The current system prompt is: '{current_prompt}'" if current_prompt else "There is no system prompt currently set."

    def _handle_execute_python_code(self, args: Dict[str, Any]) -> str:
        """Handles the 'execute_python_code' tool call."""
        code = args.get("code")
        if code is None:
            return (
                "Error: 'code' argument is required for execute_python_code.\n"
                "Example: {\"code\": \"print('Hello, World!')\"}"
            )

        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        sys.stderr = redirected_output

        try:
            exec(code)  # Execute the code in the current environment
            output = redirected_output.getvalue()
            if output:
                return f"✓ Python code executed successfully.\n\nOutput:\n{output}"
            else:
                return "✓ Python code executed successfully (no output)."
        except SyntaxError as e:
            output = redirected_output.getvalue()
            return (
                f"✗ Python syntax error on line {e.lineno}:\n{e.msg}\n"
                f"Code snippet: {e.text}\n"
                "💡 Tips:\n"
                "  - Check for missing colons, parentheses, or quotes\n"
                "  - Verify proper indentation\n"
                "  - Ensure all brackets are balanced"
            )
        except NameError as e:
            output = redirected_output.getvalue()
            return (
                f"✗ Python execution failed - NameError: {e}\n"
                "💡 Possible causes:\n"
                "  - Variable or function not defined\n"
                "  - Typo in variable/function name\n"
                "  - Module not imported (ensure the module is installed in your venv)"
            )
        except ImportError as e:
            output = redirected_output.getvalue()
            return (
                f"✗ Python execution failed - ImportError: {e}\n"
                "💡 Possible causes:\n"
                "  - The module is not installed in your virtual environment.\n"
                "  - Ensure you have activated the correct venv and the package is installed."
            )
        except Exception as e:
            output = redirected_output.getvalue()
            error_type = type(e).__name__
            error_msg = f"✗ Python execution failed - {error_type}: {e}\n"
            if output:
                error_msg += f"\nOutput before error:\n{output}\n"
            error_msg += (
                "\n💡 Troubleshooting tips:\n"
                "  - Check the error message for specific issues\n"
                "  - Verify variable types match expected operations\n"
                "  - Use print() statements to debug intermediate values\n"
                "  - Consider breaking complex code into smaller parts"
            )
            return error_msg
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
    def _handle_execute_python_code_sandbox(self, args: Dict[str, Any]) -> str:
        """Handles the 'execute_python_code' tool call."""
        code = args.get("code")
        if code is None:
            return (
                "Error: 'code' argument is required for execute_python_code.\n"
                "Example: {\"code\": \"print('Hello, World!')\"}"
            )

        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        sys.stderr = redirected_output

        try:
            # Create a restricted execution environment
            # Only built-in functions and a few safe modules are available
            # This is a basic sandbox and can be bypassed by malicious code.
            # For production, consider more robust sandboxing solutions.
            exec_globals = {"__builtins__": {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'type': type,
                'isinstance': isinstance,
                'issubclass': issubclass,
                'Exception': Exception,
                'TypeError': TypeError,
                'ValueError': ValueError,
                'KeyError': KeyError,
                'AttributeError': AttributeError,
                'IndexError': IndexError,
                'StopIteration': StopIteration,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sorted': sorted,
                'all': all,
                'any': any,
                'getattr': getattr,
                'setattr': setattr,
                'hasattr': hasattr,
                'dir': dir,
                'repr': repr,
                'hash': hash,
                'id': id,
                'callable': callable,
                'next': next,
                'iter': iter,
                'super': super,
                'object': object,
                'property': property,
                'classmethod': classmethod,
                'staticmethod': staticmethod,
                '__import__': __import__, # Allow imports but they will be restricted by the environment
            }}
            exec_locals = {}
            exec(code, exec_globals, exec_locals)
            output = redirected_output.getvalue()
            if output:
                return f"✓ Python code executed successfully.\n\nOutput:\n{output}"
            else:
                return "✓ Python code executed successfully (no output)."
        except SyntaxError as e:
            output = redirected_output.getvalue()
            return (
                f"✗ Python syntax error on line {e.lineno}:\n{e.msg}\n"
                f"Code snippet: {e.text}\n"
                "💡 Tips:\n"
                "  - Check for missing colons, parentheses, or quotes\n"
                "  - Verify proper indentation\n"
                "  - Ensure all brackets are balanced"
            )
        except NameError as e:
            output = redirected_output.getvalue()
            return (
                f"✗ Python execution failed - NameError: {e}\n"
                "💡 Possible causes:\n"
                "  - Variable or function not defined\n"
                "  - Typo in variable/function name\n"
                "  - Module not imported (limited imports available in sandbox)"
            )
        except ImportError as e:
            output = redirected_output.getvalue()
            return (
                f"✗ Python execution failed - ImportError: {e}\n"
                "💡 Note: This tool runs in a restricted sandbox environment.\n"
                "Only basic built-in functions are available. External modules may not work.\n"
                "Tip: For complex code requiring external modules, consider using builtin.execute_bash_command with 'python script.py'"
            )
        except Exception as e:
            output = redirected_output.getvalue()
            error_type = type(e).__name__
            error_msg = f"✗ Python execution failed - {error_type}: {e}\n"
            if output:
                error_msg += f"\nOutput before error:\n{output}\n"
            error_msg += (
                "\n💡 Troubleshooting tips:\n"
                "  - Check the error message for specific issues\n"
                "  - Verify variable types match expected operations\n"
                "  - Use print() statements to debug intermediate values\n"
                "  - Consider breaking complex code into smaller parts"
            )
            return error_msg
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _detect_virtualenv(self) -> Optional[str]:
        """
        Detect if a Python virtualenv exists in the working directory.

        Returns:
            Path to the virtualenv directory, or None if not found
        """
        common_venv_names = ['.venv', 'venv', 'env', '.virtualenv', 'virtualenv']

        for venv_name in common_venv_names:
            venv_path = os.path.join(self.working_directory, venv_name)
            # Check if venv exists and has a bin/activate or Scripts/activate.bat
            if os.path.isdir(venv_path):
                # Unix-like systems
                if os.path.exists(os.path.join(venv_path, 'bin', 'activate')):
                    return venv_path
                # Windows
                if os.path.exists(os.path.join(venv_path, 'Scripts', 'activate.bat')):
                    return venv_path

        return None

    def _handle_execute_bash_command(self, args: Dict[str, Any]) -> str:
        """Handles the 'execute_bash_command' tool call."""
        import subprocess
        command = args.get("command")
        if command is None:
            return (
                "Error: 'command' argument is required for execute_bash_command.\n"
                "Example: {\"command\": \"ls -la\"}"
            )

        # Detect virtualenv and modify command if needed
        venv_path = self._detect_virtualenv()
        if venv_path:
            # Commands that should use virtualenv
            venv_commands = ['pytest', 'python', 'pip', 'python3', 'pip3']
            command_parts = command.strip().split()

            if command_parts and command_parts[0] in venv_commands:
                # Check platform
                if os.name == 'nt':  # Windows
                    venv_bin_dir = os.path.join(venv_path, 'Scripts')
                else:  # Unix-like
                    venv_bin_dir = os.path.join(venv_path, 'bin')

                # Replace command with venv version
                cmd = command_parts[0]
                venv_cmd = os.path.join(venv_bin_dir, cmd)

                # For Python commands, use -m for better compatibility
                if cmd in ['python', 'python3'] and len(command_parts) > 1 and command_parts[1] == '-m':
                    # Already using -m, just replace python path
                    command = f"{venv_cmd} {' '.join(command_parts[1:])}"
                elif cmd == 'pytest':
                    # Use python -m pytest for better venv compatibility
                    python_path = os.path.join(venv_bin_dir, 'python')
                    command = f"{python_path} -m pytest {' '.join(command_parts[1:])}"
                else:
                    # Just replace the command with venv version
                    command = f"{venv_cmd} {' '.join(command_parts[1:])}"

        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            output = result.stdout
            if output:
                return f"✓ Command executed successfully.\n\nOutput:\n{output}"
            else:
                return "✓ Command executed successfully (no output)."
        except subprocess.CalledProcessError as e:
            exit_code = e.returncode
            error_msg = f"✗ Command failed with exit code {exit_code}.\n\nCommand: {command}\n"
            if e.stdout:
                error_msg += f"\nStdout:\n{e.stdout}"
            if e.stderr:
                error_msg += f"\nStderr:\n{e.stderr}"
            error_msg += (
                "\n💡 Troubleshooting tips:\n"
                "  - Check if the command syntax is correct\n"
                "  - Verify required files/directories exist\n"
                "  - Ensure you have necessary permissions\n"
                "  - Check if required tools are installed"
            )
            return error_msg
        except FileNotFoundError as e:
            return (
                f"Error: Command execution failed - shell not found.\n"
                f"Details: {e}\n"
                "💡 This usually means the system shell (bash/sh) is not available."
            )
        except Exception as e:
            return (
                f"Error executing command: {type(e).__name__}: {e}\n"
                f"Command: {command}\n"
                "💡 Tip: Verify the command syntax is valid for bash/sh."
            )

    def _handle_run_pytest(self, args: Dict[str, Any]) -> str:
        """Handles the 'run_pytest' tool call with automatic virtualenv detection."""
        import subprocess

        # Build pytest command
        pytest_args = []

        # Add path if specified
        path = args.get("path", "")
        if path:
            pytest_args.append(path)

        # Add verbose flag
        if args.get("verbose", False):
            pytest_args.append("-v")

        # Add markers
        markers = args.get("markers")
        if markers:
            pytest_args.extend(["-m", markers])

        # Add extra args
        extra_args = args.get("extra_args")
        if extra_args:
            pytest_args.extend(extra_args.split())

        # Detect virtualenv
        venv_path = self._detect_virtualenv()

        if venv_path:
            # Use venv's python to run pytest
            if os.name == 'nt':  # Windows
                python_path = os.path.join(venv_path, 'Scripts', 'python')
            else:  # Unix-like
                python_path = os.path.join(venv_path, 'bin', 'python')

            command_parts = [python_path, '-m', 'pytest'] + pytest_args
        else:
            # No venv detected, use system pytest
            command_parts = ['pytest'] + pytest_args

        try:
            # Run pytest with check=False to capture both success and failure
            result = subprocess.run(
                command_parts,
                capture_output=True,
                text=True,
                cwd=self.working_directory,
                check=False  # Don't raise on non-zero exit code
            )

            # Build result message
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr

            # Parse test results from output
            exit_code = result.returncode

            # Exit codes: 0 = all passed, 1 = tests failed, 2 = interrupted/error, 3+ = internal error
            if exit_code == 0:
                status_msg = "✓ All tests passed"
            elif exit_code == 1:
                status_msg = "⚠ Some tests failed"
            elif exit_code == 2:
                status_msg = "✗ Test execution interrupted or collection errors"
            else:
                status_msg = f"✗ Pytest error (exit code {exit_code})"

            venv_msg = f" (using virtualenv: {venv_path})" if venv_path else " (using system pytest)"

            return f"{status_msg}{venv_msg}\n\nCommand: {' '.join(command_parts)}\n\nOutput:\n{output}"

        except FileNotFoundError:
            return (
                "✗ Error: pytest not found.\n"
                f"Virtualenv detected: {venv_path if venv_path else 'No'}\n"
                "💡 Troubleshooting:\n"
                "  - Ensure pytest is installed: pip install pytest\n"
                "  - If using a venv, ensure it's activated or contains pytest\n"
                "  - Check that you're in the correct project directory"
            )
        except Exception as e:
            return (
                f"✗ Error running pytest: {type(e).__name__}: {e}\n"
                f"Virtualenv detected: {venv_path if venv_path else 'No'}\n"
                "💡 Tip: Use builtin.execute_bash_command for custom test commands"
            )

    def _validate_path(self, path: str, allow_absolute: bool = False, require_permission: bool = True) -> tuple[bool, str]:
        """
        Validates that a path is safe to use, prompting for user permission if outside working directory.

        Args:
            path: The path to validate
            allow_absolute: If True, allows absolute paths (for internal use only)
            require_permission: If True, prompts user for permission when accessing files outside working directory

        Returns:
            Tuple of (is_valid, resolved_path or error_message)
        """
        try:
            # Convert to absolute path and resolve any .. or . components
            if os.path.isabs(path):
                # For absolute paths, just expand ~ and resolve
                resolved_path = os.path.abspath(os.path.expanduser(path))
            else:
                # Resolve the path relative to working directory
                resolved_path = os.path.abspath(os.path.join(self.working_directory, path))

            working_dir_abs = os.path.abspath(self.working_directory)

            # Check if path is outside working directory
            if not resolved_path.startswith(working_dir_abs):
                # Path is outside working directory
                if not allow_absolute:
                    # Not internally allowed, check if we should request permission
                    if not require_permission:
                        return False, "Error: Path traversal outside working directory is not allowed."

                    # Check if we've already approved this path or a parent directory
                    if not self._is_path_approved(resolved_path):
                        # Prompt user for permission
                        if not self._request_path_permission(path, resolved_path):
                            return False, "Error: Permission denied to access file outside working directory."

            return True, resolved_path
        except Exception as e:
            return False, f"Error: Invalid path. {type(e).__name__}: {e}"

    def _is_path_approved(self, resolved_path: str) -> bool:
        """
        Check if a path or any of its parent directories has been approved.

        Args:
            resolved_path: The absolute resolved path to check

        Returns:
            True if the path is approved, False otherwise
        """
        resolved_path = os.path.abspath(resolved_path)

        # Check if path itself or any parent is approved
        for approved_path in self._approved_paths:
            if resolved_path.startswith(approved_path):
                return True

        return False

    def _request_path_permission(self, original_path: str, resolved_path: str) -> bool:
        """
        Request user permission to access a file outside the working directory.

        Args:
            original_path: The original path requested by the user
            resolved_path: The absolute resolved path

        Returns:
            True if permission granted, False otherwise
        """
        # Get the directory containing the file
        if os.path.isfile(resolved_path) or not os.path.exists(resolved_path):
            base_dir = os.path.dirname(resolved_path)
        else:
            base_dir = resolved_path

        self.console.print()
        self.console.print(f"[yellow]⚠️  File Access Permission Request[/yellow]")
        self.console.print(f"[dim]The agent wants to access a file outside the working directory:[/dim]")
        self.console.print(f"  Requested: [cyan]{original_path}[/cyan]")
        self.console.print(f"  Resolved:  [cyan]{resolved_path}[/cyan]")
        self.console.print(f"  Working directory: [dim]{self.working_directory}[/dim]")
        self.console.print()

        try:
            approved = Confirm.ask(
                "[yellow]Allow access to this location?[/yellow]",
                default=False
            )

            if approved:
                # Store the base directory for future access
                self._approved_paths.add(base_dir)
                self.console.print(f"[green]✓ Access granted to: {base_dir}[/green]")
                self.console.print(f"[dim]Future access to files in this directory will not require permission.[/dim]")
            else:
                self.console.print(f"[red]✗ Access denied[/red]")

            self.console.print()
            return approved

        except (KeyboardInterrupt, EOFError):
            self.console.print("[red]✗ Permission denied (interrupted)[/red]")
            return False

    def _parse_gitignore(self, gitignore_path: str) -> List[str]:
        """
        Parse a .gitignore file and return a list of patterns.

        Args:
            gitignore_path: Path to the .gitignore file

        Returns:
            List of gitignore patterns
        """
        patterns = []
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except FileNotFoundError:
            pass  # No .gitignore file
        except Exception:
            pass  # Ignore errors reading .gitignore

        return patterns

    def _matches_gitignore_pattern(self, file_path: str, pattern: str, is_dir: bool = False) -> bool:
        """
        Check if a file path matches a gitignore pattern.

        Args:
            file_path: Relative file path to check
            pattern: Gitignore pattern
            is_dir: Whether the path is a directory

        Returns:
            True if the path matches the pattern
        """
        # Handle negation patterns
        if pattern.startswith('!'):
            return False  # Negation patterns are handled separately

        # Normalize path separators
        file_path = file_path.replace(os.sep, '/')
        pattern = pattern.replace(os.sep, '/')

        # Handle directory-only patterns (ending with /)
        directory_only = pattern.endswith('/')
        if directory_only:
            pattern = pattern.rstrip('/')

        # Handle root-relative patterns (starting with /)
        if pattern.startswith('/'):
            pattern = pattern.lstrip('/')
            # Match from root only
            if fnmatch.fnmatch(file_path, pattern):
                return True
            # For directory patterns, also check if file is inside the directory
            if directory_only and file_path.startswith(pattern + '/'):
                return True
            return False

        # Handle ** patterns for directory matching
        if '**' in pattern:
            # Convert ** to match any path segment
            pattern = pattern.replace('**/', '*/')
            pattern = pattern.replace('/**', '/*')

        # Check if the file is inside a directory that matches the pattern
        if directory_only:
            parts = file_path.split('/')
            for i in range(len(parts)):
                # Check if this directory name matches
                if fnmatch.fnmatch(parts[i], pattern):
                    return True
                # Check if the path up to this point matches
                subpath = '/'.join(parts[:i+1])
                if fnmatch.fnmatch(subpath, pattern):
                    return True

        # Check if pattern matches the file or any parent directory
        parts = file_path.split('/')
        for i in range(len(parts)):
            # Check full path from this point
            subpath = '/'.join(parts[i:])
            if fnmatch.fnmatch(subpath, pattern):
                return True
            # Check just the name at this level
            if fnmatch.fnmatch(parts[i], pattern):
                return True

        return False

    def _is_ignored_by_gitignore(self, file_path: str, base_path: str, is_dir: bool = False) -> bool:
        """
        Check if a file should be ignored based on .gitignore rules.

        Args:
            file_path: Relative path to the file from base_path
            base_path: Base directory path
            is_dir: Whether the path is a directory

        Returns:
            True if the file should be ignored
        """
        gitignore_path = os.path.join(base_path, '.gitignore')
        patterns = self._parse_gitignore(gitignore_path)

        if not patterns:
            return False

        ignored = False
        for pattern in patterns:
            if pattern.startswith('!'):
                # Negation pattern - if it matches, un-ignore
                neg_pattern = pattern[1:]
                if self._matches_gitignore_pattern(file_path, neg_pattern, is_dir):
                    ignored = False
            else:
                # Normal pattern - if it matches, ignore
                if self._matches_gitignore_pattern(file_path, pattern, is_dir):
                    ignored = True

        return ignored

    def _handle_validate_file_path(self, args: Dict[str, Any]) -> str:
        """Validates and locks a file path from the task description.

        This is a REQUIRED first step for file operations. It:
        1. Extracts the path from task description
        2. Validates it's correct (absolute or relative)
        3. Converts relative to absolute using working directory
        4. Returns the LOCKED path that must be used for all operations
        """
        path = args.get("path")
        task_desc = args.get("task_description", "")

        if not path:
            return (
                "Error: 'path' argument is required.\n"
                "Extract the EXACT file path from your task description and provide it here.\n"
                "Example: {\"path\": \"/home/user/docs/file.pdf\", \"task_description\": \"...your task...\"}"
            )

        # Validate the path
        is_valid, result = self._validate_path(path, allow_absolute=True)

        if not is_valid:
            return result

        resolved_path = result

        # Check if path exists (informational, not required)
        exists = os.path.exists(resolved_path)
        exists_msg = "✓ File exists" if exists else "⚠ File does not exist yet (will be created if you write to it)"

        # Return the locked path
        return (
            f"✓ PATH LOCKED: {resolved_path}\n"
            f"\n"
            f"Status: {exists_msg}\n"
            f"\n"
            f"CRITICAL: You MUST use this EXACT path for ALL subsequent file operations in this task.\n"
            f"DO NOT modify, shorten, or change this path.\n"
            f"DO NOT use any other path variations.\n"
            f"\n"
            f"For reference, your task was:\n"
            f"{task_desc[:200]}{'...' if len(task_desc) > 200 else ''}\n"
            f"\n"
            f"Next: Use this locked path in your file operations (read_file, write_file, etc.)"
        )

    def _handle_read_file(self, args: Dict[str, Any]) -> str:
        """Handles the 'read_file' tool call with optional partial reading support."""
        path = args.get("path")
        offset = args.get("offset")  # 1-indexed line number to start from
        limit = args.get("limit")    # Number of lines to read

        if not path:
            return (
                "Error: 'path' argument is required for read_file.\n"
                "Example: {\"path\": \"src/main.py\"}\n"
                "Example with partial read: {\"path\": \"src/main.py\", \"offset\": 50, \"limit\": 100}"
            )

        # Validate offset and limit if provided
        if offset is not None and offset < 1:
            return "Error: 'offset' must be a positive integer (1-indexed line number)."

        if limit is not None and limit < 1:
            return "Error: 'limit' must be a positive integer (number of lines to read)."

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)

        # Special case: Allow reading the config file even if it's an absolute path
        # This is needed because get_config_path returns an absolute path
        if not allow_absolute and os.path.isabs(path):
            try:
                from mcp_client_for_ollama.utils.constants import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE
                config_file = os.path.abspath(os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE))
                if os.path.abspath(path) == config_file:
                    allow_absolute = True
            except Exception:
                pass  # If we can't determine config path, continue with normal validation

        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            if not os.path.exists(resolved_path):
                return (
                    f"Error: File '{path}' does not exist.\n"
                    f"💡 Tips:\n"
                    f"  - Verify the path is correct\n"
                    f"  - Use builtin.list_files to see available files\n"
                    f"  - Check if the file is in a subdirectory"
                )

            if not os.path.isfile(resolved_path):
                return (
                    f"Error: '{path}' exists but is not a file (it's a directory).\n"
                    "💡 Tips:\n"
                    "  - Use builtin.list_files to read directory contents\n"
                    "  - Specify the actual file path within the directory"
                )

            # Read file with partial reading support
            with open(resolved_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Calculate the slice range
            if offset is None:
                start_line = 0  # 0-indexed for Python slicing
            else:
                start_line = offset - 1  # Convert 1-indexed to 0-indexed

            if limit is None:
                end_line = total_lines
            else:
                end_line = start_line + limit

            # Validate range
            if start_line >= total_lines:
                return (
                    f"Error: offset={offset} is beyond the end of the file.\n"
                    f"File '{path}' has {total_lines} lines.\n"
                    f"💡 Tip: Use offset between 1 and {total_lines}"
                )

            # Extract the requested lines
            selected_lines = lines[start_line:end_line]
            actual_end = min(end_line, total_lines)

            # Format output with line numbers (cat -n style)
            numbered_lines = []
            for i, line in enumerate(selected_lines, start=start_line + 1):
                # Remove trailing newline for display, add back for consistent formatting
                line_content = line.rstrip('\n')
                numbered_lines.append(f"{i:6d}→{line_content}")

            content_with_numbers = '\n'.join(numbered_lines)

            # Build response message
            if offset is None and limit is None:
                # Full file read
                file_size = sum(len(line) for line in lines)
                return (
                    f"✓ File '{path}' read successfully. Size: {file_size} bytes, {total_lines} lines\n\n"
                    f"Content:\n{content_with_numbers}"
                )
            else:
                # Partial file read
                display_start = start_line + 1
                display_end = start_line + len(selected_lines)
                return (
                    f"✓ File '{path}' read successfully (lines {display_start}-{display_end} of {total_lines})\n\n"
                    f"Content:\n{content_with_numbers}"
                )
        except UnicodeDecodeError:
            return (
                f"Error: File '{path}' is not a text file or uses an unsupported encoding.\n"
                "💡 This file may be:\n"
                "  - A binary file (executable, image, etc.)\n"
                "  - Encoded in a non-UTF-8 format\n"
                "Tip: Only text files can be read with this tool."
            )
        except PermissionError as e:
            return (
                f"Error: Permission denied reading '{path}'.\n"
                f"Details: {e}\n"
                "💡 Possible solutions:\n"
                "  - Check file permissions\n"
                "  - Ensure the file is not locked by another program"
            )
        except Exception as e:
            return (
                f"Error reading file '{path}': {type(e).__name__}: {e}\n"
                "💡 Tip: Verify the file path and try builtin.file_exists to check if the file exists."
            )

    def _handle_write_file(self, args: Dict[str, Any]) -> str:
        """Handles the 'write_file' tool call."""
        path = args.get("path")
        content = args.get("content")

        if not path:
            return (
                "Error: 'path' argument is required for write_file.\n"
                "Example: {\"path\": \"src/example.py\", \"content\": \"...\"}"
            )
        if content is None:
            return (
                "Error: 'content' argument is required for write_file.\n"
                "Example: {\"path\": \"src/example.py\", \"content\": \"print('hello')\"}\n"
                "Note: Content can be an empty string for creating empty files."
            )

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            # Enhance path validation errors with suggestions
            if "outside working directory" in result.lower():
                result += "\n💡 Tip: Use relative paths, or the system will request user permission for external locations."
            elif "absolute paths" in result.lower():
                result += "\n💡 Tip: Use relative paths (e.g., 'src/file.py' instead of '/absolute/path/file.py')."
            return result

        resolved_path = result

        try:
            # Create parent directories if they don't exist
            parent_dir = os.path.dirname(resolved_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)

            file_size = os.path.getsize(resolved_path)
            # Enhanced success message with actual location
            if os.path.isabs(path):
                return f"✓ File written successfully to: {resolved_path}\nSize: {file_size} bytes"
            else:
                return f"✓ File '{path}' written successfully. Size: {file_size} bytes\nActual location: {resolved_path}"
        except PermissionError as e:
            return (
                f"Error: Permission denied writing to '{path}'.\n"
                f"Details: {e}\n"
                "💡 Possible solutions:\n"
                "  - Check file/directory permissions\n"
                "  - Ensure the file is not open in another program\n"
                "  - Try a different location"
            )
        except OSError as e:
            return (
                f"Error: OS error writing file '{path}'.\n"
                f"Details: {e}\n"
                "💡 Possible solutions:\n"
                "  - Check disk space\n"
                "  - Verify the path is valid for your OS\n"
                "  - Ensure parent directory is writable"
            )
        except Exception as e:
            return (
                f"Error writing file '{path}': {type(e).__name__}: {e}\n"
                "💡 Tip: Double-check the path and try using read_file to verify the location after writing."
            )

    def _handle_list_files(self, args: Dict[str, Any]) -> str:
        """Handles the 'list_files' tool call."""
        path = args.get("path", ".")
        recursive = args.get("recursive", False)
        respect_gitignore = args.get("respect_gitignore", True)

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            if not os.path.exists(resolved_path):
                return f"Error: Directory '{path}' does not exist."

            if not os.path.isdir(resolved_path):
                return f"Error: '{path}' is not a directory."

            files = []
            if recursive:
                for root, _, filenames in os.walk(resolved_path):
                    for filename in filenames:
                        full_path = os.path.join(root, filename)
                        # Make path relative to working directory (not the requested directory)
                        rel_path = os.path.relpath(full_path, self.working_directory)

                        # For gitignore check, we need path relative to resolved_path
                        gitignore_rel_path = os.path.relpath(full_path, resolved_path)
                        if respect_gitignore and self._is_ignored_by_gitignore(gitignore_rel_path, resolved_path, False):
                            continue

                        files.append(rel_path)
            else:
                for item in os.listdir(resolved_path):
                    item_path = os.path.join(resolved_path, item)
                    if os.path.isfile(item_path):
                        # Apply gitignore filtering if enabled
                        if respect_gitignore and self._is_ignored_by_gitignore(item, resolved_path, False):
                            continue

                        # Make path relative to working directory
                        rel_path = os.path.relpath(item_path, self.working_directory)
                        files.append(rel_path)

            files.sort()

            if files:
                files_list = "\n".join(f"  - {f}" for f in files)
                return f"Files in '{path}' ({len(files)} file{'s' if len(files) != 1 else ''}):\n{files_list}"
            else:
                return f"No files found in '{path}'."
        except Exception as e:
            return f"Error listing files in '{path}': {type(e).__name__}: {e}"

    def _handle_list_directories(self, args: Dict[str, Any]) -> str:
        """Handles the 'list_directories' tool call."""
        path = args.get("path", ".")

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            if not os.path.exists(resolved_path):
                return f"Error: Directory '{path}' does not exist."

            if not os.path.isdir(resolved_path):
                return f"Error: '{path}' is not a directory."

            directories = []
            for item in os.listdir(resolved_path):
                item_path = os.path.join(resolved_path, item)
                if os.path.isdir(item_path):
                    directories.append(item)

            directories.sort()

            if directories:
                dirs_list = "\n".join(f"  - {d}/" for d in directories)
                return f"Directories in '{path}' ({len(directories)} director{'ies' if len(directories) != 1 else 'y'}):\n{dirs_list}"
            else:
                return f"No subdirectories found in '{path}'."
        except Exception as e:
            return f"Error listing directories in '{path}': {type(e).__name__}: {e}"

    def _handle_create_directory(self, args: Dict[str, Any]) -> str:
        """Handles the 'create_directory' tool call."""
        path = args.get("path")

        if not path:
            return "Error: 'path' argument is required for create_directory."

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            if os.path.exists(resolved_path):
                if os.path.isdir(resolved_path):
                    return f"Directory '{path}' already exists."
                else:
                    return f"Error: '{path}' exists but is not a directory."

            os.makedirs(resolved_path, exist_ok=True)
            return f"Directory '{path}' created successfully."
        except Exception as e:
            return f"Error creating directory '{path}': {type(e).__name__}: {e}"

    def _handle_delete_file(self, args: Dict[str, Any]) -> str:
        """Handles the 'delete_file' tool call."""
        path = args.get("path")

        if not path:
            return "Error: 'path' argument is required for delete_file."

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            if not os.path.exists(resolved_path):
                return f"Error: File '{path}' does not exist."

            if os.path.isdir(resolved_path):
                return f"Error: '{path}' is a directory. Use a directory deletion tool instead."

            os.remove(resolved_path)
            return f"File '{path}' deleted successfully."
        except Exception as e:
            return f"Error deleting file '{path}': {type(e).__name__}: {e}"

    def _handle_file_exists(self, args: Dict[str, Any]) -> str:
        """Handles the 'file_exists' tool call."""
        path = args.get("path")

        if not path:
            return "Error: 'path' argument is required for file_exists."

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            exists = os.path.exists(resolved_path)
            if exists:
                if os.path.isfile(resolved_path):
                    return f"'{path}' exists and is a file."
                elif os.path.isdir(resolved_path):
                    return f"'{path}' exists and is a directory."
                else:
                    return f"'{path}' exists but is neither a file nor a directory."
            else:
                return f"'{path}' does not exist."
        except Exception as e:
            return f"Error checking existence of '{path}': {type(e).__name__}: {e}"

    def _handle_get_file_info(self, args: Dict[str, Any]) -> str:
        """Handles the 'get_file_info' tool call."""
        path = args.get("path")

        if not path:
            return "Error: 'path' argument is required for get_file_info."

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            if not os.path.exists(resolved_path):
                return f"Error: '{path}' does not exist."

            stat_info = os.stat(resolved_path)

            # Format file size
            size_bytes = stat_info.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.2f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

            # Format timestamps
            modified_time = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            created_time = datetime.fromtimestamp(stat_info.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

            # Determine type
            if os.path.isfile(resolved_path):
                file_type = "File"
            elif os.path.isdir(resolved_path):
                file_type = "Directory"
            else:
                file_type = "Other"

            info = f"""File information for '{path}':
  Type: {file_type}
  Size: {size_str} ({size_bytes} bytes)
  Modified: {modified_time}
  Created: {created_time}
  Permissions: {oct(stat_info.st_mode)[-3:]}"""

            return info
        except Exception as e:
            return f"Error getting file info for '{path}': {type(e).__name__}: {e}"

    def _handle_read_image(self, args: Dict[str, Any]) -> str:
        """Handles the 'read_image' tool call."""
        import json
        import urllib.request
        import urllib.error

        image_path = args.get("image_path")
        prompt = args.get("prompt", "Describe what you see in this image in detail.")

        if not image_path:
            return "Error: 'image_path' argument is required for read_image."

        # Validate path
        is_valid, result = self._validate_path(image_path)
        if not is_valid:
            return result

        resolved_path = result

        try:
            # Check if file exists and is a file
            if not os.path.exists(resolved_path):
                return f"Error: Image file '{image_path}' does not exist."

            if not os.path.isfile(resolved_path):
                return f"Error: '{image_path}' is not a file."

            # Check if it's an image file by extension
            valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext not in valid_extensions:
                return f"Error: '{image_path}' does not appear to be a supported image file. Supported formats: {', '.join(valid_extensions)}"

            # Read image file and convert to base64
            with open(resolved_path, 'rb') as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Get Ollama API URL from the configured host
            ollama_url = self.ollama_host

            # Check if a vision model is configured
            configured_vision_model = None
            try:
                from mcp_client_for_ollama.config import ConfigManager
                config_manager = ConfigManager()
                user_config = config_manager.load_configuration("default")
                if user_config and "vision_model" in user_config:
                    configured_vision_model = user_config["vision_model"]
            except Exception:
                pass  # If config can't be loaded, fall back to auto-detection

            # Get list of available models to verify the model exists
            try:
                tags_url = f"{ollama_url}/api/tags"
                tags_request = urllib.request.Request(tags_url, method='GET')
                with urllib.request.urlopen(tags_request, timeout=5) as response:
                    tags_data = json.loads(response.read().decode('utf-8'))
                    models = tags_data.get('models', [])
                    available_model_names = [m.get('name', '') for m in models]

                    # If a vision model is configured, verify it exists
                    if configured_vision_model:
                        if configured_vision_model in available_model_names:
                            available_vision_model = configured_vision_model
                        else:
                            return f"Error: Configured vision model '{configured_vision_model}' not found on Ollama server. Available models: {', '.join(available_model_names)}"
                    else:
                        # Auto-detect a vision model
                        vision_models = ['llava', 'bakllava', 'cogvlm', 'cogvlm2', 'moondream', 'minicpm-v', 'obsidian', 'llava-llama3', 'llava-phi3', 'llama3.2-vision', 'llama3-vision', 'vision']
                        available_vision_model = None

                        for model in models:
                            model_name = model.get('name', '').lower()
                            for vision_model in vision_models:
                                if vision_model in model_name:
                                    available_vision_model = model.get('name')
                                    break
                            if available_vision_model:
                                break

                        if not available_vision_model:
                            return f"Error: No vision-capable model found on Ollama server. Please install a vision model like 'llava' using: ollama pull llava\nOr set a specific model using the vision model configuration."

            except Exception as e:
                return f"Error: Failed to connect to Ollama server at {ollama_url}. Make sure Ollama is running. Error: {type(e).__name__}: {e}"

            # Call Ollama API with vision model
            api_url = f"{ollama_url}/api/generate"
            request_data = {
                "model": available_vision_model,
                "prompt": prompt,
                "stream": False,
                "images": [image_base64]
            }

            request_body = json.dumps(request_data).encode('utf-8')
            request = urllib.request.Request(
                api_url,
                data=request_body,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(request, timeout=60) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                response_text = response_data.get('response', '')

                return f"Image analysis using {available_vision_model}:\n\n{response_text}"

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            return f"Error calling Ollama API: HTTP {e.code} - {e.reason}\n{error_body}"
        except urllib.error.URLError as e:
            return f"Error connecting to Ollama server: {e.reason}"
        except Exception as e:
            return f"Error analyzing image '{image_path}': {type(e).__name__}: {e}"

    def _handle_patch_file(self, args: Dict[str, Any]) -> str:
        """
        Handles the 'patch_file' tool call.

        Applies multiple search-replace operations to a file efficiently.
        All changes are validated before any are applied (atomic operation).

        Args:
            args: Dictionary containing 'path' and 'changes' arguments

        Returns:
            Success message with details of applied changes, or error message
        """
        path = args.get("path")
        changes = args.get("changes")

        if not path:
            return "Error: 'path' argument is required for patch_file."

        if not changes:
            return "Error: 'changes' argument is required for patch_file."

        if not isinstance(changes, list) or len(changes) == 0:
            return "Error: 'changes' must be a non-empty array of change operations."

        # Validate path
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            # Check if file exists
            if not os.path.exists(resolved_path):
                return f"Error: File '{path}' does not exist."

            if not os.path.isfile(resolved_path):
                return f"Error: '{path}' is not a file."

            # Read the entire file
            try:
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except UnicodeDecodeError:
                return f"Error: File '{path}' is not a text file or uses an unsupported encoding."

            # Keep track of content as we apply changes
            current_content = original_content
            applied_changes = []

            # Validate and apply each change
            for idx, change in enumerate(changes, 1):
                if not isinstance(change, dict):
                    return f"Error: Change #{idx} is not a valid object."

                search_text = change.get("search")
                replace_text = change.get("replace")
                occurrence = change.get("occurrence")

                if search_text is None:
                    return f"Error: Change #{idx} is missing required 'search' field."

                if replace_text is None:
                    return f"Error: Change #{idx} is missing required 'replace' field."

                if not isinstance(search_text, str):
                    return f"Error: Change #{idx} has non-string 'search' field."

                if not isinstance(replace_text, str):
                    return f"Error: Change #{idx} has non-string 'replace' field."

                if occurrence is not None:
                    if not isinstance(occurrence, int) or occurrence < 1:
                        return f"Error: Change #{idx} has invalid 'occurrence' field. Must be a positive integer."

                # Count occurrences of search text
                count = current_content.count(search_text)

                if count == 0:
                    return (
                        f"Error: Change #{idx} failed - search text not found in file.\n"
                        f"Search text: {repr(search_text[:100])}{'...' if len(search_text) > 100 else ''}\n"
                        f"Hint: The text may have already been changed by a previous operation, "
                        f"or it may not exist in the file."
                    )

                if occurrence is None:
                    # No occurrence specified - search text must be unique
                    if count > 1:
                        return (
                            f"Error: Change #{idx} failed - search text appears {count} times in file.\n"
                            f"Search text: {repr(search_text[:100])}{'...' if len(search_text) > 100 else ''}\n"
                            f"Please specify which occurrence to replace using the 'occurrence' field (1-{count})."
                        )
                    # Unique match - apply the change
                    current_content = current_content.replace(search_text, replace_text, 1)
                    applied_changes.append(f"  {idx}. Replaced unique occurrence")
                else:
                    # Occurrence specified
                    if occurrence > count:
                        return (
                            f"Error: Change #{idx} failed - requested occurrence {occurrence} but search text "
                            f"only appears {count} time{'s' if count != 1 else ''} in file.\n"
                            f"Search text: {repr(search_text[:100])}{'...' if len(search_text) > 100 else ''}"
                        )

                    # Find and replace the specific occurrence
                    parts = current_content.split(search_text)
                    if len(parts) < occurrence + 1:
                        return f"Error: Change #{idx} failed - internal error splitting text."

                    # Reconstruct with the replacement at the specific occurrence
                    new_parts = []
                    for i, part in enumerate(parts):
                        new_parts.append(part)
                        if i < len(parts) - 1:
                            if i == occurrence - 1:
                                new_parts.append(replace_text)
                            else:
                                new_parts.append(search_text)

                    current_content = ''.join(new_parts)
                    applied_changes.append(f"  {idx}. Replaced occurrence {occurrence} of {count}")

            # All changes validated and applied successfully - write the file
            try:
                with open(resolved_path, 'w', encoding='utf-8') as f:
                    f.write(current_content)
            except Exception as e:
                # Attempt to restore original content if write fails
                try:
                    with open(resolved_path, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                    return f"Error: Failed to write patched file, original restored: {type(e).__name__}: {e}"
                except Exception:
                    return f"Error: Failed to write patched file AND failed to restore original: {type(e).__name__}: {e}"

            # Calculate statistics
            original_lines = original_content.count('\n') + 1
            new_lines = current_content.count('\n') + 1
            line_diff = new_lines - original_lines
            size_diff = len(current_content) - len(original_content)

            # Build success message
            success_msg = f"File '{path}' patched successfully.\n"
            success_msg += f"Applied {len(applied_changes)} change{'s' if len(applied_changes) != 1 else ''}:\n"
            success_msg += '\n'.join(applied_changes)
            success_msg += f"\n\nFile statistics:"
            success_msg += f"\n  Lines: {original_lines} → {new_lines} ({line_diff:+d})"
            success_msg += f"\n  Size: {len(original_content)} → {len(current_content)} bytes ({size_diff:+d})"

            return success_msg

        except Exception as e:
            return f"Error patching file '{path}': {type(e).__name__}: {e}"

    def _handle_open_file(self, args: Dict[str, Any]) -> str:
        """
        Handles the 'open_file' tool call.

        Opens a file with its default system application using xdg-open.
        Useful for PDFs, images, documents, etc.

        Args:
            args: Dictionary containing 'path' argument

        Returns:
            Success message or error message
        """
        import subprocess

        path = args.get("path")

        if not path:
            return "Error: 'path' argument is required for open_file."

        # Validate path
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            # Check if file exists
            if not os.path.exists(resolved_path):
                return f"Error: File '{path}' does not exist."

            if not os.path.isfile(resolved_path):
                return f"Error: '{path}' is not a file."

            # Use xdg-open to open the file with default application
            # Run in background with stdout/stderr redirected to devnull
            # to prevent output from cluttering the terminal
            subprocess.Popen(
                ['xdg-open', resolved_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            return f"File '{path}' opened successfully with default system application."

        except FileNotFoundError:
            return "Error: xdg-open command not found. This tool requires xdg-open (typically available on Linux systems)."
        except Exception as e:
            return f"Error opening file '{path}': {type(e).__name__}: {e}"

    def _handle_get_config(self, args: Dict[str, Any]) -> str:
        """
        Handles the 'get_config' tool call.

        Gets the current application configuration or a specific section.

        Args:
            args: Dictionary containing optional 'section' argument

        Returns:
            JSON string with the config or section, or error message
        """
        import json

        if not self.config_manager:
            return "Error: Config manager not available. This tool requires config_manager to be set."

        try:
            # Load the current configuration
            config = self.config_manager.load_configuration()

            if not config:
                return "Error: Could not load configuration."

            # Get specific section if requested
            section = args.get("section")
            if section:
                if section in config:
                    return json.dumps(config[section], indent=2)
                else:
                    return f"Error: Section '{section}' not found in config. Available sections: {', '.join(config.keys())}"

            # Return full config
            return json.dumps(config, indent=2)

        except Exception as e:
            return f"Error getting config: {type(e).__name__}: {e}"

    def _handle_update_config_section(self, args: Dict[str, Any]) -> str:
        """
        Handles the 'update_config_section' tool call.

        Updates a specific section of the application configuration.

        Args:
            args: Dictionary containing 'section' and 'data' arguments

        Returns:
            Success message or error message
        """
        import json

        if not self.config_manager:
            return "Error: Config manager not available. This tool requires config_manager to be set."

        section = args.get("section")
        data = args.get("data")

        if not section:
            return (
                "Error: 'section' argument is required for update_config_section.\n"
                "Example: {\"section\": \"memory\", \"data\": {\"enabled\": true}}"
            )

        if data is None:
            return (
                "Error: 'data' argument is required for update_config_section.\n"
                "Example: {\"section\": \"memory\", \"data\": {\"enabled\": true, \"storage_dir\": \".memory\"}}\n"
                "Note: 'data' must be a JSON object (dict), not a string."
            )

        try:
            # Parse data if it's a JSON string (common mistake from agents)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                    # Successfully parsed - provide a helpful message about this common mistake
                    # Continue processing but don't return yet
                except json.JSONDecodeError as e:
                    return (
                        f"Error: 'data' argument is a string but not valid JSON.\n"
                        f"Details: {e}\n"
                        "💡 Common mistake: Pass data as a JSON object, not a JSON string:\n"
                        "   ❌ WRONG: {\"section\": \"memory\", \"data\": \"{\\\"enabled\\\": true}\"}\n"
                        "   ✅ RIGHT: {\"section\": \"memory\", \"data\": {\"enabled\": true}}\n"
                        "Tip: Remove the quotes around the data value and pass the object directly."
                    )

            # Validate data is a dict/object
            if not isinstance(data, dict):
                return (
                    f"Error: 'data' must be a JSON object (dict), got {type(data).__name__}.\n"
                    "💡 Correct format:\n"
                    "   {\"section\": \"memory\", \"data\": {\"enabled\": true, \"storage_dir\": \".memory\"}}\n"
                    "Note: The 'data' parameter should be an object with the configuration fields for this section."
                )

            # Load the current configuration
            config = self.config_manager.load_configuration()

            if not config:
                config = {}

            # Get current section data for reporting
            old_data = config.get(section, {})
            changed_fields = []
            for key, value in data.items():
                if key not in old_data or old_data[key] != value:
                    changed_fields.append(key)

            # Update the section
            config[section] = data

            # Save the configuration
            success = self.config_manager.save_configuration(config)

            if success:
                if changed_fields:
                    fields_str = ", ".join(f"'{f}'" for f in changed_fields)
                    return (
                        f"✓ Configuration section '{section}' updated successfully.\n"
                        f"Changed fields: {fields_str}\n"
                        "Note: Some changes may require restart or reload to take effect."
                    )
                else:
                    return (
                        f"✓ Configuration section '{section}' updated (no changes detected).\n"
                        "Note: The data matches the current configuration."
                    )
            else:
                return (
                    f"Error: Failed to save configuration for section '{section}'.\n"
                    "💡 Possible solutions:\n"
                    "  - Check config file permissions\n"
                    "  - Verify the config file is not open in another program\n"
                    "  - Check disk space"
                )

        except PermissionError as e:
            return (
                f"Error: Permission denied writing config for section '{section}'.\n"
                f"Details: {e}\n"
                "💡 Possible solutions:\n"
                "  - Check config file permissions\n"
                "  - Ensure the config file is not open in another program"
            )
        except Exception as e:
            return (
                f"Error updating config section '{section}': {type(e).__name__}: {e}\n"
                "💡 Tip: Use builtin.get_config to check the current configuration structure."
            )

    def _handle_add_mcp_server(self, args: Dict[str, Any]) -> str:
        """
        Handles the 'add_mcp_server' tool call.

        Adds a new MCP server to the configuration.

        Args:
            args: Dictionary containing server configuration

        Returns:
            Success message or error message
        """
        import json

        if not self.config_manager:
            return "Error: Config manager not available. This tool requires config_manager to be set."

        name = args.get("name")
        server_type = args.get("type")

        if not name:
            return (
                "Error: 'name' argument is required for add_mcp_server.\n"
                "Example: {\"name\": \"my-server\", \"type\": \"stdio\", \"command\": \"python\", \"args\": [\"-m\", \"my_mcp_server\"]}"
            )

        if not server_type:
            return (
                "Error: 'type' argument is required for add_mcp_server.\n"
                "Valid types: 'stdio', 'sse', 'streamable_http'\n"
                "Examples:\n"
                "  stdio: {\"name\": \"local\", \"type\": \"stdio\", \"command\": \"node\", \"args\": [\"server.js\"]}\n"
                "  sse: {\"name\": \"remote\", \"type\": \"sse\", \"url\": \"https://example.com/mcp\"}"
            )

        if server_type not in ["stdio", "sse", "streamable_http"]:
            return (
                f"Error: Invalid server type '{server_type}'.\n"
                "💡 Valid types:\n"
                "  - 'stdio': Local process communication\n"
                "  - 'sse': Server-Sent Events over HTTP\n"
                "  - 'streamable_http': Streamable HTTP protocol\n"
                "Example: {\"name\": \"my-server\", \"type\": \"stdio\", \"command\": \"python\", \"args\": [\"-m\", \"server\"]}"
            )

        try:
            # Load the current configuration
            config = self.config_manager.load_configuration()

            if not config:
                config = {}

            # Ensure mcpServers section exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Check if server already exists
            if name in config["mcpServers"]:
                return (
                    f"Error: MCP server '{name}' already exists.\n"
                    "💡 Options:\n"
                    "  - Use builtin.remove_mcp_server to remove it first\n"
                    "  - Use a different name for the new server\n"
                    "  - Use builtin.update_config_section to modify the existing server"
                )

            # Build server configuration
            server_config = {"type": server_type}

            # Add type-specific fields
            if server_type == "stdio":
                command = args.get("command")
                if not command:
                    return (
                        "Error: 'command' argument is required for stdio servers.\n"
                        "Example: {\"name\": \"my-server\", \"type\": \"stdio\", \"command\": \"python\", \"args\": [\"-m\", \"my_mcp_server\"]}"
                    )
                server_config["command"] = command

                if "args" in args:
                    server_config["args"] = args["args"]

            elif server_type in ["sse", "streamable_http"]:
                url = args.get("url")
                if not url:
                    return (
                        f"Error: 'url' argument is required for {server_type} servers.\n"
                        f"Example: {{\"name\": \"my-server\", \"type\": \"{server_type}\", \"url\": \"https://example.com/mcp\"}}"
                    )
                server_config["url"] = url

            # Add optional fields
            if "env" in args:
                server_config["env"] = args["env"]

            if "disabled" in args:
                server_config["disabled"] = args["disabled"]

            # Add server to config
            config["mcpServers"][name] = server_config

            # Save the configuration
            success = self.config_manager.save_configuration(config)

            if success:
                return (
                    f"✓ MCP server '{name}' added successfully.\n\n"
                    f"Server configuration:\n{json.dumps(server_config, indent=2)}\n\n"
                    "💡 Next step: Use 'reload-servers' command to connect to the new server."
                )
            else:
                return (
                    "Error: Failed to save configuration.\n"
                    "💡 Possible solutions:\n"
                    "  - Check config file permissions\n"
                    "  - Verify the config file is not open in another program\n"
                    "  - Check disk space"
                )

        except PermissionError as e:
            return (
                f"Error: Permission denied writing config for MCP server '{name}'.\n"
                f"Details: {e}\n"
                "💡 Possible solutions:\n"
                "  - Check config file permissions\n"
                "  - Ensure the config file is not open in another program"
            )
        except Exception as e:
            return (
                f"Error adding MCP server '{name}': {type(e).__name__}: {e}\n"
                "💡 Tip: Use builtin.list_mcp_servers to see current servers."
            )

    def _handle_remove_mcp_server(self, args: Dict[str, Any]) -> str:
        """
        Handles the 'remove_mcp_server' tool call.

        Removes an MCP server from the configuration.

        Args:
            args: Dictionary containing 'name' argument

        Returns:
            Success message or error message
        """
        if not self.config_manager:
            return "Error: Config manager not available. This tool requires config_manager to be set."

        name = args.get("name")

        if not name:
            return "Error: 'name' argument is required."

        try:
            # Load the current configuration
            config = self.config_manager.load_configuration()

            if not config:
                return "Error: Could not load configuration."

            # Check if mcpServers section exists
            if "mcpServers" not in config:
                return "Error: No MCP servers configured."

            # Check if server exists
            if name not in config["mcpServers"]:
                return f"Error: MCP server '{name}' not found. Available servers: {', '.join(config['mcpServers'].keys())}"

            # Remove the server
            del config["mcpServers"][name]

            # Save the configuration
            success = self.config_manager.save_configuration(config)

            if success:
                return f"MCP server '{name}' removed successfully. Use 'reload-servers' command to disconnect the server."
            else:
                return "Error: Failed to save configuration."

        except Exception as e:
            return f"Error removing MCP server '{name}': {type(e).__name__}: {e}"

    def _handle_list_mcp_servers(self, args: Dict[str, Any]) -> str:
        """
        Handles the 'list_mcp_servers' tool call.

        Lists all configured MCP servers.

        Args:
            args: Dictionary (empty for this tool)

        Returns:
            JSON array of server configurations or error message
        """
        import json

        if not self.config_manager:
            return "Error: Config manager not available. This tool requires config_manager to be set."

        try:
            # Load the current configuration
            config = self.config_manager.load_configuration()

            if not config:
                return "Error: Could not load configuration."

            # Get mcpServers section
            mcp_servers = config.get("mcpServers", {})

            if not mcp_servers:
                return "No MCP servers configured."

            # Build server list with relevant info
            server_list = []
            for name, server_config in mcp_servers.items():
                server_info = {
                    "name": name,
                    "type": server_config.get("type", "unknown"),
                    "disabled": server_config.get("disabled", False)
                }

                # Add type-specific info
                if server_config.get("type") == "stdio":
                    server_info["command"] = server_config.get("command")
                    server_info["args"] = server_config.get("args", [])
                elif server_config.get("type") in ["sse", "streamable_http"]:
                    server_info["url"] = server_config.get("url")

                server_list.append(server_info)

            return json.dumps(server_list, indent=2)

        except Exception as e:
            return f"Error listing MCP servers: {type(e).__name__}: {e}"

    def _handle_get_config_path(self, args: Dict[str, Any]) -> str:
        """
        Handles the 'get_config_path' tool call.

        Gets the absolute path to the current configuration file.

        Args:
            args: Dictionary (empty for this tool)

        Returns:
            Absolute path to config file or error message
        """
        try:
            from mcp_client_for_ollama.utils.constants import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE

            config_dir = os.path.abspath(DEFAULT_CONFIG_DIR)
            config_file = os.path.join(config_dir, DEFAULT_CONFIG_FILE)

            exists = os.path.exists(config_file)

            result = f"Configuration file path: {config_file}\n"
            result += f"File exists: {exists}\n"

            if exists:
                size = os.path.getsize(config_file)
                mtime = datetime.fromtimestamp(os.path.getmtime(config_file)).strftime('%Y-%m-%d %H:%M:%S')
                result += f"File size: {size} bytes\n"
                result += f"Last modified: {mtime}"

            return result

        except Exception as e:
            return f"Error getting config path: {type(e).__name__}: {e}"

    def _handle_update_feature_status(self, args: Dict[str, Any]) -> str:
        """Handles the 'update_feature_status' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Restart the application\n"
                "  3. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        feature_id = args.get("feature_id")
        status = args.get("status")
        notes = args.get("notes")

        if not feature_id:
            return "Error: 'feature_id' argument is required for update_feature_status."

        if not status:
            return "Error: 'status' argument is required for update_feature_status."

        return self.memory_tools.update_feature_status(
            feature_id=feature_id,
            status=status,
            notes=notes
        )

    def _handle_log_progress(self, args: Dict[str, Any]) -> str:
        """Handles the 'log_progress' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Restart the application\n"
                "  3. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        agent_type = args.get("agent_type")
        action = args.get("action")
        outcome = args.get("outcome")
        details = args.get("details")
        feature_id = args.get("feature_id")
        artifacts_changed = args.get("artifacts_changed")

        if not agent_type:
            return "Error: 'agent_type' argument is required for log_progress."

        if not action:
            return "Error: 'action' argument is required for log_progress."

        if not outcome:
            return "Error: 'outcome' argument is required for log_progress."

        if not details:
            return "Error: 'details' argument is required for log_progress."

        return self.memory_tools.log_progress(
            agent_type=agent_type,
            action=action,
            outcome=outcome,
            details=details,
            feature_id=feature_id,
            artifacts_changed=artifacts_changed
        )

    def _handle_add_test_result(self, args: Dict[str, Any]) -> str:
        """Handles the 'add_test_result' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Restart the application\n"
                "  3. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        feature_id = args.get("feature_id")
        test_id = args.get("test_id")
        passed = args.get("passed")
        details = args.get("details")
        output = args.get("output")

        if not feature_id:
            return "Error: 'feature_id' argument is required for add_test_result."

        if not test_id:
            return "Error: 'test_id' argument is required for add_test_result."

        if passed is None:
            return "Error: 'passed' argument is required for add_test_result."

        return self.memory_tools.add_test_result(
            feature_id=feature_id,
            test_id=test_id,
            passed=passed,
            details=details,
            output=output
        )

    def _handle_get_memory_state(self, args: Dict[str, Any]) -> str:
        """Handles the 'get_memory_state' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Restart the application\n"
                "  3. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        return self.memory_tools.get_memory_state()

    def _handle_get_feature_details(self, args: Dict[str, Any]) -> str:
        """Handles the 'get_feature_details' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Restart the application\n"
                "  3. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        feature_id = args.get("feature_id")

        if not feature_id:
            return "Error: 'feature_id' argument is required for get_feature_details."

        return self.memory_tools.get_feature_details(feature_id=feature_id)

    def _handle_get_goal_details(self, args: Dict[str, Any]) -> str:
        """Handles the 'get_goal_details' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        goal_id = args.get("goal_id")

        if not goal_id:
            return "Error: 'goal_id' argument is required for get_goal_details."

        return self.memory_tools.get_goal_details(goal_id=goal_id)

    # ========================================================================
    # INTERACTIVE MEMORY MANAGEMENT TOOL HANDLERS
    # ========================================================================

    def _handle_add_goal(self, args: Dict[str, Any]) -> str:
        """Handles the 'add_goal' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        description = args.get("description")
        constraints = args.get("constraints")

        if not description:
            return "Error: 'description' argument is required for add_goal."

        return self.memory_tools.add_goal(
            description=description,
            constraints=constraints
        )

    def _handle_update_goal(self, args: Dict[str, Any]) -> str:
        """Handles the 'update_goal' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        goal_id = args.get("goal_id")
        description = args.get("description")
        add_constraints = args.get("add_constraints")
        remove_constraints = args.get("remove_constraints")

        if not goal_id:
            return "Error: 'goal_id' argument is required for update_goal."

        return self.memory_tools.update_goal(
            goal_id=goal_id,
            description=description,
            add_constraints=add_constraints,
            remove_constraints=remove_constraints
        )

    def _handle_remove_goal(self, args: Dict[str, Any]) -> str:
        """Handles the 'remove_goal' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        goal_id = args.get("goal_id")
        confirm = args.get("confirm", False)

        if not goal_id:
            return "Error: 'goal_id' argument is required for remove_goal."

        return self.memory_tools.remove_goal(
            goal_id=goal_id,
            confirm=confirm
        )

    def _handle_add_feature(self, args: Dict[str, Any]) -> str:
        """Handles the 'add_feature' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        goal_id = args.get("goal_id")
        description = args.get("description")
        criteria = args.get("criteria")
        tests = args.get("tests")
        priority = args.get("priority", "medium")
        assigned_to = args.get("assigned_to")

        if not goal_id:
            return "Error: 'goal_id' argument is required for add_feature."
        if not description:
            return "Error: 'description' argument is required for add_feature."

        return self.memory_tools.add_feature(
            goal_id=goal_id,
            description=description,
            criteria=criteria,
            tests=tests,
            priority=priority,
            assigned_to=assigned_to
        )

    def _handle_update_feature(self, args: Dict[str, Any]) -> str:
        """Handles the 'update_feature' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        feature_id = args.get("feature_id")
        description = args.get("description")
        add_criteria = args.get("add_criteria")
        remove_criteria = args.get("remove_criteria")
        add_tests = args.get("add_tests")
        remove_tests = args.get("remove_tests")
        priority = args.get("priority")
        assigned_to = args.get("assigned_to")

        if not feature_id:
            return "Error: 'feature_id' argument is required for update_feature."

        return self.memory_tools.update_feature(
            feature_id=feature_id,
            description=description,
            add_criteria=add_criteria,
            remove_criteria=remove_criteria,
            add_tests=add_tests,
            remove_tests=remove_tests,
            priority=priority,
            assigned_to=assigned_to
        )

    def _handle_remove_feature(self, args: Dict[str, Any]) -> str:
        """Handles the 'remove_feature' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        feature_id = args.get("feature_id")
        confirm = args.get("confirm", False)

        if not feature_id:
            return "Error: 'feature_id' argument is required for remove_feature."

        return self.memory_tools.remove_feature(
            feature_id=feature_id,
            confirm=confirm
        )

    def _handle_update_session_description(self, args: Dict[str, Any]) -> str:
        """Handles the 'update_session_description' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        description = args.get("description")

        if not description:
            return "Error: 'description' argument is required for update_session_description."

        return self.memory_tools.update_session_description(description=description)

    def _handle_move_feature(self, args: Dict[str, Any]) -> str:
        """Handles the 'move_feature' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        feature_id = args.get("feature_id")
        target_goal_id = args.get("target_goal_id")

        if not feature_id:
            return "Error: 'feature_id' argument is required for move_feature."
        if not target_goal_id:
            return "Error: 'target_goal_id' argument is required for move_feature."

        return self.memory_tools.move_feature(
            feature_id=feature_id,
            target_goal_id=target_goal_id
        )

    def _handle_get_project_context(self, args: Dict[str, Any]) -> str:
        """Handles the 'get_project_context' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        return self.memory_tools.get_project_context()

    def _handle_rescan_project_context(self, args: Dict[str, Any]) -> str:
        """Handles the 'rescan_project_context' tool call."""
        if not self.memory_tools:
            return (
                "Error: Memory system is not enabled or no active memory session.\n"
                "💡 To use memory tools:\n"
                "  1. Enable memory system: type 'memory-enable' or 'me'\n"
                "  2. Create or resume a memory session: 'memory-new' or 'memory-resume'"
            )

        return self.memory_tools.rescan_project_context()

    # Artifact generation tool handlers

    def _handle_generate_tool_form(self, args: Dict[str, Any]) -> str:
        """Handles the 'generate_tool_form' tool call."""
        import json
        from ..artifacts.tool_schema_parser import ToolSchemaParser

        tool_name = args.get("tool_name")
        prefill = args.get("prefill")

        if not tool_name:
            return "Error: 'tool_name' argument is required for generate_tool_form."

        # Parse prefill if it's a JSON string
        if isinstance(prefill, str):
            try:
                prefill = json.loads(prefill) if prefill else None
            except json.JSONDecodeError:
                prefill = None

        # Initialize parser with parent tool manager (has all tools) if available, otherwise self
        # This allows ToolSchemaParser to find both builtin and MCP tools
        tool_manager = self.parent_tool_manager if self.parent_tool_manager else self
        parser = ToolSchemaParser(tool_manager=tool_manager)

        try:
            # Generate the artifact
            artifact = parser.generate_form_artifact(
                tool_name=tool_name,
                prefill=prefill,
                context=None  # Could pass chat history if available
            )

            # Return as formatted artifact code block
            # Extract type from top level, not from data
            artifact_type = artifact['type'].replace('artifact:', '')
            artifact_json = json.dumps(artifact, indent=2)
            return f"```artifact:{artifact_type}\n{artifact_json}\n```"

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error generating tool form: {str(e)}"

    def _handle_generate_query_builder(self, args: Dict[str, Any]) -> str:
        """Handles the 'generate_query_builder' tool call."""
        import json
        from ..artifacts.tool_schema_parser import ToolSchemaParser

        filter_category = args.get("filter_category")

        # Initialize parser with parent tool manager (has all tools) if available, otherwise self
        tool_manager = self.parent_tool_manager if self.parent_tool_manager else self
        parser = ToolSchemaParser(tool_manager=tool_manager)

        try:
            # Get available tools
            available_tools = [tool.name for tool in self.get_builtin_tools()]

            # Filter by category if specified
            if filter_category:
                # This is a simple implementation - could be enhanced
                filtered_tools = [
                    name for name in available_tools
                    if self._tool_matches_category(name, filter_category)
                ]
                available_tools = filtered_tools

            # Generate the artifact
            artifact = parser.generate_query_builder_artifact(
                available_tools=available_tools,
                context=None  # Could pass chat history if available
            )

            # Return as formatted artifact code block
            # Extract type from top level, not from data
            artifact_type = artifact['type'].replace('artifact:', '')
            artifact_json = json.dumps(artifact, indent=2)
            return f"```artifact:{artifact_type}\n{artifact_json}\n```"

        except Exception as e:
            return f"Error generating query builder: {str(e)}"

    def _handle_generate_tool_wizard(self, args: Dict[str, Any]) -> str:
        """Handles the 'generate_tool_wizard' tool call."""
        import json
        from ..artifacts.tool_schema_parser import ToolSchemaParser

        tool_name = args.get("tool_name")

        if not tool_name:
            return "Error: 'tool_name' argument is required for generate_tool_wizard."

        # Initialize parser with parent tool manager (has all tools) if available, otherwise self
        tool_manager = self.parent_tool_manager if self.parent_tool_manager else self
        parser = ToolSchemaParser(tool_manager=tool_manager)

        try:
            # Generate the artifact
            artifact = parser.generate_wizard_artifact(
                tool_name=tool_name,
                context=None  # Could pass chat history if available
            )

            # Return as formatted artifact code block
            # Extract type from top level, not from data
            artifact_type = artifact['type'].replace('artifact:', '')
            artifact_json = json.dumps(artifact, indent=2)
            return f"```artifact:{artifact_type}\n{artifact_json}\n```"

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error generating tool wizard: {str(e)}"

    def _handle_generate_batch_tool(self, args: Dict[str, Any]) -> str:
        """Handles the 'generate_batch_tool' tool call."""
        import json
        from ..artifacts.tool_schema_parser import ToolSchemaParser

        tool_name = args.get("tool_name")
        initial_inputs = args.get("initial_inputs")

        if not tool_name:
            return "Error: 'tool_name' argument is required for generate_batch_tool."

        # Initialize parser with parent tool manager (has all tools) if available, otherwise self
        tool_manager = self.parent_tool_manager if self.parent_tool_manager else self
        parser = ToolSchemaParser(tool_manager=tool_manager)

        try:
            # Generate the artifact
            artifact = parser.generate_batch_artifact(
                tool_name=tool_name,
                batch_inputs=initial_inputs
            )

            # Return as formatted artifact code block
            # Extract type from top level, not from data
            artifact_type = artifact['type'].replace('artifact:', '')
            artifact_json = json.dumps(artifact, indent=2)
            return f"```artifact:{artifact_type}\n{artifact_json}\n```"

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error generating batch tool: {str(e)}"

    def _tool_matches_category(self, tool_name: str, category: str) -> bool:
        """Check if a tool matches a given category."""
        name_lower = tool_name.lower()
        category_lower = category.lower()

        category_keywords = {
            "file operations": ["file", "read", "write", "directory", "list", "delete", "create"],
            "code execution": ["execute", "python", "bash", "pytest", "run"],
            "configuration": ["config", "set_system", "mcp_server", "settings"],
            "memory management": ["memory", "feature", "goal", "progress", "session"],
            "system": ["validate", "exists", "info", "open", "path"],
        }

        keywords = category_keywords.get(category_lower, [])
        return any(kw in name_lower for kw in keywords)

