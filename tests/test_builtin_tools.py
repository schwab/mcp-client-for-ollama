import pytest
from unittest.mock import MagicMock
from mcp import Tool
from mcp_client_for_ollama.tools.builtin import BuiltinToolManager

@pytest.fixture
def mock_model_config_manager():
    """Fixture for a mocked ModelConfigManager."""
    mock = MagicMock()
    mock.system_prompt = None
    mock.get_system_prompt.side_effect = lambda: mock.system_prompt
    return mock

@pytest.fixture
def builtin_tool_manager(mock_model_config_manager):
    """Fixture for BuiltinToolManager with a mocked ModelConfigManager."""
    return BuiltinToolManager(mock_model_config_manager)

def test_get_builtin_tools(builtin_tool_manager):
    """Test that get_builtin_tools returns the correct Tool objects."""
    tools = builtin_tool_manager.get_builtin_tools()

    assert len(tools) == 3
    
    set_prompt_tool = next((t for t in tools if t.name == "builtin.set_system_prompt"), None)
    get_prompt_tool = next((t for t in tools if t.name == "builtin.get_system_prompt"), None)
    execute_python_code_tool = next((t for t in tools if t.name == "builtin.execute_python_code"), None)

    assert set_prompt_tool is not None
    assert get_prompt_tool is not None
    assert execute_python_code_tool is not None

    assert set_prompt_tool.description == "Update the system prompt for the assistant. Use this to change your instructions or persona."
    assert set_prompt_tool.inputSchema == {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The new system prompt. Use a concise and clear prompt to define the persona and instructions for the AI assistant."
            }
        },
        "required": ["prompt"]
    }

    assert get_prompt_tool.description == "Get the current system prompt for the assistant."
    assert get_prompt_tool.inputSchema == {
        "type": "object",
        "properties": {},
    }

    assert execute_python_code_tool.description == "Executes arbitrary Python code. Use with caution as this can perform system operations."
    assert execute_python_code_tool.inputSchema == {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute."
            }
        },
        "required": ["code"]
    }

def test_execute_tool_set_system_prompt_success(builtin_tool_manager, mock_model_config_manager):
    """Test setting the system prompt successfully."""
    tool_args = {"prompt": "You are a helpful AI assistant."}
    result = builtin_tool_manager.execute_tool("set_system_prompt", tool_args)

    assert result == "System prompt updated successfully."
    assert mock_model_config_manager.system_prompt == "You are a helpful AI assistant."

def test_execute_tool_set_system_prompt_missing_arg(builtin_tool_manager, mock_model_config_manager):
    """Test setting the system prompt with a missing 'prompt' argument."""
    tool_args = {}
    result = builtin_tool_manager.execute_tool("set_system_prompt", tool_args)

    assert result == "Error: 'prompt' argument is required."
    assert mock_model_config_manager.system_prompt is None

def test_execute_tool_get_system_prompt_with_prompt(builtin_tool_manager, mock_model_config_manager):
    """Test getting the system prompt when one is set."""
    mock_model_config_manager.system_prompt = "Existing system prompt."
    result = builtin_tool_manager.execute_tool("get_system_prompt", {})

    assert result == "The current system prompt is: 'Existing system prompt.'"

def test_execute_tool_get_system_prompt_no_prompt(builtin_tool_manager, mock_model_config_manager):
    """Test getting the system prompt when none is set."""
    mock_model_config_manager.system_prompt = None
    result = builtin_tool_manager.execute_tool("get_system_prompt", {})

    assert result == "There is no system prompt currently set."

def test_execute_tool_execute_python_code_success(builtin_tool_manager):
    """Test successful execution of Python code."""
    tool_args = {"code": "print('Hello from Python!')"}
    result = builtin_tool_manager.execute_tool("execute_python_code", tool_args)
    assert "Execution successful." in result
    assert "Hello from Python!" in result

def test_execute_tool_execute_python_code_with_error(builtin_tool_manager):
    """Test execution of Python code that raises an error."""
    tool_args = {"code": "raise ValueError('Test error')"}
    result = builtin_tool_manager.execute_tool("execute_python_code", tool_args)
    assert "Execution failed." in result
    assert "ValueError: Test error" in result

def test_execute_tool_execute_python_code_missing_arg(builtin_tool_manager):
    """Test execution of Python code with a missing 'code' argument."""
    tool_args = {}
    result = builtin_tool_manager.execute_tool("execute_python_code", tool_args)
    assert result == "Error: 'code' argument is required for execute_python_code."

def test_execute_tool_unknown_tool(builtin_tool_manager):
    """Test executing an unknown built-in tool."""
    result = builtin_tool_manager.execute_tool("unknown_tool", {})

    assert result == "Error: Unknown built-in tool 'unknown_tool'"



