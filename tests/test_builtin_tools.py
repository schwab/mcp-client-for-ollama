import pytest
import os
import tempfile
import shutil
from pathlib import Path
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

@pytest.fixture
def temp_dir(builtin_tool_manager):
    """Fixture for creating a temporary directory for file operations."""
    # Create a temporary directory
    temp_path = tempfile.mkdtemp()

    # Store original working directory
    original_cwd = os.getcwd()

    # Change to temp directory and update builtin_tool_manager's working_directory
    os.chdir(temp_path)
    builtin_tool_manager.working_directory = temp_path

    yield temp_path

    # Cleanup: restore original directory and remove temp directory
    os.chdir(original_cwd)
    shutil.rmtree(temp_path, ignore_errors=True)

def test_get_builtin_tools(builtin_tool_manager):
    """Test that get_builtin_tools returns the correct Tool objects."""
    tools = builtin_tool_manager.get_builtin_tools()

    assert len(tools) == 12
    
    set_prompt_tool = next((t for t in tools if t.name == "builtin.set_system_prompt"), None)
    get_prompt_tool = next((t for t in tools if t.name == "builtin.get_system_prompt"), None)
    execute_python_code_tool = next((t for t in tools if t.name == "builtin.execute_python_code"), None)
    execute_bash_command_tool = next((t for t in tools if t.name == "builtin.execute_bash_command"), None)

    assert set_prompt_tool is not None
    assert get_prompt_tool is not None
    assert execute_python_code_tool is not None
    assert execute_bash_command_tool is not None

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

    assert execute_bash_command_tool.description == "Executes arbitrary bash commands. Use with caution as this can perform system operations."
    assert execute_bash_command_tool.inputSchema == {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute."
            }
        },
        "required": ["command"]
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

def test_execute_tool_execute_bash_command_success(builtin_tool_manager):
    """Test successful execution of a bash command."""
    tool_args = {"command": "echo 'Hello from Bash!'"}
    result = builtin_tool_manager.execute_tool("execute_bash_command", tool_args)
    assert "Execution successful." in result
    assert "Hello from Bash!" in result

def test_execute_tool_execute_bash_command_with_error(builtin_tool_manager):
    """Test execution of a bash command that raises an error."""
    tool_args = {"command": "exit 1"}
    result = builtin_tool_manager.execute_tool("execute_bash_command", tool_args)
    assert "Execution failed." in result

def test_execute_tool_execute_bash_command_missing_arg(builtin_tool_manager):
    """Test execution of a bash command with a missing 'command' argument."""
    tool_args = {}
    result = builtin_tool_manager.execute_tool("execute_bash_command", tool_args)
    assert result == "Error: 'command' argument is required for execute_bash_command."


# File Access Tool Tests

def test_read_file_success(builtin_tool_manager, temp_dir):
    """Test successfully reading a file."""
    # Create a test file
    test_content = "Hello, World!\nThis is a test file."
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write(test_content)

    result = builtin_tool_manager.execute_tool("read_file", {"path": "test.txt"})
    assert "read successfully" in result
    assert test_content in result

def test_read_file_not_found(builtin_tool_manager, temp_dir):
    """Test reading a file that doesn't exist."""
    result = builtin_tool_manager.execute_tool("read_file", {"path": "nonexistent.txt"})
    assert "does not exist" in result

def test_read_file_is_directory(builtin_tool_manager, temp_dir):
    """Test reading a directory instead of a file."""
    os.makedirs(os.path.join(temp_dir, "testdir"))
    result = builtin_tool_manager.execute_tool("read_file", {"path": "testdir"})
    assert "is not a file" in result

def test_read_file_missing_path(builtin_tool_manager, temp_dir):
    """Test reading a file with missing path argument."""
    result = builtin_tool_manager.execute_tool("read_file", {})
    assert "Error: 'path' argument is required" in result

def test_write_file_success(builtin_tool_manager, temp_dir):
    """Test successfully writing a file."""
    test_content = "Test content for writing"
    result = builtin_tool_manager.execute_tool("write_file", {
        "path": "output.txt",
        "content": test_content
    })
    assert "written successfully" in result

    # Verify file was created with correct content
    with open(os.path.join(temp_dir, "output.txt"), 'r') as f:
        assert f.read() == test_content

def test_write_file_with_subdirectory(builtin_tool_manager, temp_dir):
    """Test writing a file in a subdirectory that doesn't exist yet."""
    result = builtin_tool_manager.execute_tool("write_file", {
        "path": "subdir/nested/file.txt",
        "content": "nested content"
    })
    assert "written successfully" in result
    assert os.path.exists(os.path.join(temp_dir, "subdir", "nested", "file.txt"))

def test_write_file_overwrite(builtin_tool_manager, temp_dir):
    """Test overwriting an existing file."""
    test_file = os.path.join(temp_dir, "overwrite.txt")
    with open(test_file, 'w') as f:
        f.write("original content")

    result = builtin_tool_manager.execute_tool("write_file", {
        "path": "overwrite.txt",
        "content": "new content"
    })
    assert "written successfully" in result

    with open(test_file, 'r') as f:
        assert f.read() == "new content"

def test_write_file_missing_args(builtin_tool_manager, temp_dir):
    """Test writing a file with missing arguments."""
    result = builtin_tool_manager.execute_tool("write_file", {"path": "test.txt"})
    assert "Error: 'content' argument is required" in result

    result = builtin_tool_manager.execute_tool("write_file", {"content": "test"})
    assert "Error: 'path' argument is required" in result

def test_list_files_success(builtin_tool_manager, temp_dir):
    """Test listing files in a directory."""
    # Create some test files
    for i in range(3):
        with open(os.path.join(temp_dir, f"file{i}.txt"), 'w') as f:
            f.write(f"content {i}")

    result = builtin_tool_manager.execute_tool("list_files", {"path": "."})
    assert "Files in" in result
    assert "file0.txt" in result
    assert "file1.txt" in result
    assert "file2.txt" in result

def test_list_files_recursive(builtin_tool_manager, temp_dir):
    """Test listing files recursively."""
    # Create nested structure
    os.makedirs(os.path.join(temp_dir, "subdir"))
    with open(os.path.join(temp_dir, "root.txt"), 'w') as f:
        f.write("root")
    with open(os.path.join(temp_dir, "subdir", "nested.txt"), 'w') as f:
        f.write("nested")

    result = builtin_tool_manager.execute_tool("list_files", {"path": ".", "recursive": True})
    assert "root.txt" in result
    assert "nested.txt" in result or "subdir/nested.txt" in result or "subdir\\nested.txt" in result

def test_list_files_empty_directory(builtin_tool_manager, temp_dir):
    """Test listing files in an empty directory."""
    result = builtin_tool_manager.execute_tool("list_files", {"path": "."})
    assert "No files found" in result

def test_list_files_nonexistent_directory(builtin_tool_manager, temp_dir):
    """Test listing files in a directory that doesn't exist."""
    result = builtin_tool_manager.execute_tool("list_files", {"path": "nonexistent"})
    assert "does not exist" in result

def test_list_directories_success(builtin_tool_manager, temp_dir):
    """Test listing directories."""
    # Create some directories
    os.makedirs(os.path.join(temp_dir, "dir1"))
    os.makedirs(os.path.join(temp_dir, "dir2"))
    os.makedirs(os.path.join(temp_dir, "dir3"))

    result = builtin_tool_manager.execute_tool("list_directories", {"path": "."})
    assert "Directories in" in result
    assert "dir1/" in result
    assert "dir2/" in result
    assert "dir3/" in result

def test_list_directories_empty(builtin_tool_manager, temp_dir):
    """Test listing directories in a directory with no subdirectories."""
    result = builtin_tool_manager.execute_tool("list_directories", {"path": "."})
    assert "No subdirectories found" in result

def test_list_directories_nonexistent(builtin_tool_manager, temp_dir):
    """Test listing directories in a directory that doesn't exist."""
    result = builtin_tool_manager.execute_tool("list_directories", {"path": "nonexistent"})
    assert "does not exist" in result

def test_create_directory_success(builtin_tool_manager, temp_dir):
    """Test creating a directory."""
    result = builtin_tool_manager.execute_tool("create_directory", {"path": "newdir"})
    assert "created successfully" in result
    assert os.path.isdir(os.path.join(temp_dir, "newdir"))

def test_create_directory_nested(builtin_tool_manager, temp_dir):
    """Test creating nested directories."""
    result = builtin_tool_manager.execute_tool("create_directory", {"path": "a/b/c"})
    assert "created successfully" in result
    assert os.path.isdir(os.path.join(temp_dir, "a", "b", "c"))

def test_create_directory_already_exists(builtin_tool_manager, temp_dir):
    """Test creating a directory that already exists."""
    os.makedirs(os.path.join(temp_dir, "existing"))
    result = builtin_tool_manager.execute_tool("create_directory", {"path": "existing"})
    assert "already exists" in result

def test_create_directory_missing_path(builtin_tool_manager, temp_dir):
    """Test creating a directory with missing path argument."""
    result = builtin_tool_manager.execute_tool("create_directory", {})
    assert "Error: 'path' argument is required" in result

def test_delete_file_success(builtin_tool_manager, temp_dir):
    """Test deleting a file."""
    test_file = os.path.join(temp_dir, "delete_me.txt")
    with open(test_file, 'w') as f:
        f.write("delete this")

    result = builtin_tool_manager.execute_tool("delete_file", {"path": "delete_me.txt"})
    assert "deleted successfully" in result
    assert not os.path.exists(test_file)

def test_delete_file_not_found(builtin_tool_manager, temp_dir):
    """Test deleting a file that doesn't exist."""
    result = builtin_tool_manager.execute_tool("delete_file", {"path": "nonexistent.txt"})
    assert "does not exist" in result

def test_delete_file_is_directory(builtin_tool_manager, temp_dir):
    """Test deleting a directory instead of a file."""
    os.makedirs(os.path.join(temp_dir, "testdir"))
    result = builtin_tool_manager.execute_tool("delete_file", {"path": "testdir"})
    assert "is a directory" in result

def test_delete_file_missing_path(builtin_tool_manager, temp_dir):
    """Test deleting a file with missing path argument."""
    result = builtin_tool_manager.execute_tool("delete_file", {})
    assert "Error: 'path' argument is required" in result

def test_file_exists_file(builtin_tool_manager, temp_dir):
    """Test checking if a file exists."""
    test_file = os.path.join(temp_dir, "exists.txt")
    with open(test_file, 'w') as f:
        f.write("exists")

    result = builtin_tool_manager.execute_tool("file_exists", {"path": "exists.txt"})
    assert "exists and is a file" in result

def test_file_exists_directory(builtin_tool_manager, temp_dir):
    """Test checking if a directory exists."""
    os.makedirs(os.path.join(temp_dir, "existsdir"))
    result = builtin_tool_manager.execute_tool("file_exists", {"path": "existsdir"})
    assert "exists and is a directory" in result

def test_file_exists_not_found(builtin_tool_manager, temp_dir):
    """Test checking if a nonexistent path exists."""
    result = builtin_tool_manager.execute_tool("file_exists", {"path": "doesnotexist.txt"})
    assert "does not exist" in result

def test_file_exists_missing_path(builtin_tool_manager, temp_dir):
    """Test checking file existence with missing path argument."""
    result = builtin_tool_manager.execute_tool("file_exists", {})
    assert "Error: 'path' argument is required" in result

def test_get_file_info_success(builtin_tool_manager, temp_dir):
    """Test getting file information."""
    test_file = os.path.join(temp_dir, "info.txt")
    test_content = "File with info"
    with open(test_file, 'w') as f:
        f.write(test_content)

    result = builtin_tool_manager.execute_tool("get_file_info", {"path": "info.txt"})
    assert "File information for" in result
    assert "Type: File" in result
    assert "Size:" in result
    assert "Modified:" in result
    assert "Permissions:" in result

def test_get_file_info_directory(builtin_tool_manager, temp_dir):
    """Test getting information for a directory."""
    os.makedirs(os.path.join(temp_dir, "infodir"))
    result = builtin_tool_manager.execute_tool("get_file_info", {"path": "infodir"})
    assert "Type: Directory" in result

def test_get_file_info_not_found(builtin_tool_manager, temp_dir):
    """Test getting info for a file that doesn't exist."""
    result = builtin_tool_manager.execute_tool("get_file_info", {"path": "nonexistent.txt"})
    assert "does not exist" in result

def test_get_file_info_missing_path(builtin_tool_manager, temp_dir):
    """Test getting file info with missing path argument."""
    result = builtin_tool_manager.execute_tool("get_file_info", {})
    assert "Error: 'path' argument is required" in result

# Security Tests

def test_path_validation_absolute_path(builtin_tool_manager, temp_dir):
    """Test that absolute paths are rejected."""
    result = builtin_tool_manager.execute_tool("read_file", {"path": "/etc/passwd"})
    assert "Absolute paths are not allowed" in result

def test_path_validation_path_traversal(builtin_tool_manager, temp_dir):
    """Test that path traversal attempts are blocked."""
    result = builtin_tool_manager.execute_tool("read_file", {"path": "../../../etc/passwd"})
    assert "Path traversal outside working directory is not allowed" in result

def test_path_validation_complex_traversal(builtin_tool_manager, temp_dir):
    """Test that complex path traversal attempts are blocked."""
    result = builtin_tool_manager.execute_tool("read_file", {"path": "subdir/../../etc/passwd"})
    assert "Path traversal outside working directory is not allowed" in result



