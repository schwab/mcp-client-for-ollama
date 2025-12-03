"""Built-in tools for MCP Client for Ollama."""

import io, sys
from typing import List, Dict, Any, Callable
from mcp import Tool

class BuiltinToolManager:
    """Manages the definition and execution of built-in tools."""

    def __init__(self, model_config_manager: Any):
        """
        Initializes the BuiltinToolManager.

        Args:
            model_config_manager: An instance of ModelConfigManager to interact with model settings.
        """
        self.model_config_manager = model_config_manager
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], str]] = {
            "set_system_prompt": self._handle_set_system_prompt,
            "get_system_prompt": self._handle_get_system_prompt,
            "execute_python_code": self._handle_execute_python_code,
            "execute_bash_command": self._handle_execute_bash_command,
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
        return [set_prompt_tool, get_prompt_tool, execute_python_code_tool, execute_bash_command_tool]

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

