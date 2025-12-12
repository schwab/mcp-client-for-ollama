"""Built-in tools for MCP Client for Ollama."""

import io, sys, os, shutil, fnmatch, base64
from pathlib import Path
from typing import List, Dict, Any, Callable, Set
from mcp import Tool
from datetime import datetime

class BuiltinToolManager:
    """Manages the definition and execution of built-in tools."""

    def __init__(self, model_config_manager: Any):
        """
        Initializes the BuiltinToolManager.

        Args:
            model_config_manager: An instance of ModelConfigManager to interact with model settings.
        """
        self.model_config_manager = model_config_manager
        self.working_directory = os.getcwd()  # Store the working directory for security checks
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], str]] = {
            "set_system_prompt": self._handle_set_system_prompt,
            "get_system_prompt": self._handle_get_system_prompt,
            "execute_python_code": self._handle_execute_python_code,
            "execute_bash_command": self._handle_execute_bash_command,
            "read_file": self._handle_read_file,
            "write_file": self._handle_write_file,
            "list_files": self._handle_list_files,
            "list_directories": self._handle_list_directories,
            "create_directory": self._handle_create_directory,
            "delete_file": self._handle_delete_file,
            "file_exists": self._handle_file_exists,
            "get_file_info": self._handle_get_file_info,
            "read_image": self._handle_read_image,
        }

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

        read_file_tool = Tool(
            name="builtin.read_file",
            description="Read the contents of a file. Path must be relative to the current working directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file to read."
                    }
                },
                "required": ["path"]
            }
        )

        write_file_tool = Tool(
            name="builtin.write_file",
            description="Write content to a file. Creates the file if it doesn't exist. Path must be relative to the current working directory.",
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

        return [
            set_prompt_tool, get_prompt_tool, execute_python_code_tool, execute_bash_command_tool,
            read_file_tool, write_file_tool, list_files_tool, list_directories_tool,
            create_directory_tool, delete_file_tool, file_exists_tool, get_file_info_tool,
            read_image_tool
        ]

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
            return "Error: 'code' argument is required for execute_python_code."

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
            return f"Execution successful.\nOutput:\n{output}"
        except Exception as e:
            output = redirected_output.getvalue()
            return f"Execution failed.\nError: {type(e).__name__}: {e}\nOutput:\n{output}"
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _handle_execute_bash_command(self, args: Dict[str, Any]) -> str:
        """Handles the 'execute_bash_command' tool call."""
        import subprocess
        command = args.get("command")
        if command is None:
            return "Error: 'command' argument is required for execute_bash_command."

        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            output = result.stdout
            return f"Execution successful.\nOutput:\n{output}"
        except subprocess.CalledProcessError as e:
            return f"Execution failed.\nError: {e}\nOutput:\n{e.stdout}\nStderr:\n{e.stderr}"
        except Exception as e:
            return f"Execution failed.\nError: {type(e).__name__}: {e}"

    def _validate_path(self, path: str, allow_absolute: bool = False) -> tuple[bool, str]:
        """
        Validates that a path is safe to use (within working directory).

        Args:
            path: The path to validate
            allow_absolute: If True, allows absolute paths (for internal use only)

        Returns:
            Tuple of (is_valid, resolved_path or error_message)
        """
        try:
            # Convert to absolute path and resolve any .. or . components
            if os.path.isabs(path):
                if not allow_absolute:
                    return False, "Error: Absolute paths are not allowed. Use relative paths only."
                # For absolute paths, just expand ~ and return
                resolved_path = os.path.abspath(os.path.expanduser(path))
            else:
                # Resolve the path relative to working directory
                resolved_path = os.path.abspath(os.path.join(self.working_directory, path))

            # For relative paths, ensure they're within the working directory
            if not allow_absolute and not resolved_path.startswith(os.path.abspath(self.working_directory)):
                return False, "Error: Path traversal outside working directory is not allowed."

            return True, resolved_path
        except Exception as e:
            return False, f"Error: Invalid path. {type(e).__name__}: {e}"

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

    def _handle_read_file(self, args: Dict[str, Any]) -> str:
        """Handles the 'read_file' tool call."""
        path = args.get("path")
        if not path:
            return "Error: 'path' argument is required for read_file."

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            if not os.path.exists(resolved_path):
                return f"Error: File '{path}' does not exist."

            if not os.path.isfile(resolved_path):
                return f"Error: '{path}' is not a file."

            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return f"File '{path}' read successfully.\n\nContent:\n{content}"
        except UnicodeDecodeError:
            return f"Error: File '{path}' is not a text file or uses an unsupported encoding."
        except Exception as e:
            return f"Error reading file '{path}': {type(e).__name__}: {e}"

    def _handle_write_file(self, args: Dict[str, Any]) -> str:
        """Handles the 'write_file' tool call."""
        path = args.get("path")
        content = args.get("content")

        if not path:
            return "Error: 'path' argument is required for write_file."
        if content is None:
            return "Error: 'content' argument is required for write_file."

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)
        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
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
            return f"File '{path}' written successfully. Size: {file_size} bytes."
        except Exception as e:
            return f"Error writing file '{path}': {type(e).__name__}: {e}"

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

            # Get Ollama API URL from config or use default
            ollama_url = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')

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
                        vision_models = ['llava', 'bakllava', 'cogvlm', 'cogvlm2', 'moondream', 'minicpm-v', 'obsidian', 'llava-llama3', 'llava-phi3']
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

