# Built-in File Access Tools

This document describes the built-in file access tools added to MCP Client for Ollama to enable local file system operations for editing code and managing files.

## Overview

Eight new file access tools have been added to help models interact with the local file system safely. All operations are restricted to the current working directory for security.

## Available Tools

### 1. builtin.read_file

Reads the contents of a file.

**Parameters:**
- `path` (required): The relative path to the file to read

**Returns:**
- File contents as a string

**Example:**
```json
{
  "path": "src/main.py"
}
```

### 2. builtin.write_file

Writes content to a file. Creates the file if it doesn't exist, or overwrites it if it does.

**Parameters:**
- `path` (required): The relative path to the file to write
- `content` (required): The content to write to the file

**Features:**
- Automatically creates parent directories if needed

**Example:**
```json
{
  "path": "output/result.txt",
  "content": "Hello, World!"
}
```

### 3. builtin.list_files

Lists all files in a directory.

**Parameters:**
- `path` (optional): The relative path to the directory (defaults to current directory)
- `recursive` (optional): Whether to list files recursively in subdirectories (defaults to false)

**Example:**
```json
{
  "path": "src",
  "recursive": true
}
```

### 4. builtin.list_directories

Lists all subdirectories in a directory.

**Parameters:**
- `path` (optional): The relative path to the directory (defaults to current directory)

**Example:**
```json
{
  "path": "."
}
```

### 5. builtin.create_directory

Creates a new directory. Creates parent directories if needed (like `mkdir -p`).

**Parameters:**
- `path` (required): The relative path to the directory to create

**Example:**
```json
{
  "path": "build/output/logs"
}
```

### 6. builtin.delete_file

Deletes a file. Includes safety checks to prevent accidentally deleting directories.

**Parameters:**
- `path` (required): The relative path to the file to delete

**Example:**
```json
{
  "path": "temp/cache.txt"
}
```

### 7. builtin.file_exists

Checks if a file or directory exists.

**Parameters:**
- `path` (required): The relative path to check

**Returns:**
- Information about whether the path exists and whether it's a file or directory

**Example:**
```json
{
  "path": "config.json"
}
```

### 8. builtin.get_file_info

Gets detailed metadata about a file or directory.

**Parameters:**
- `path` (required): The relative path to the file

**Returns:**
- Type (file or directory)
- Size (in bytes, KB, or MB)
- Modification time
- Creation time
- Permissions (in octal format)

**Example:**
```json
{
  "path": "README.md"
}
```

## Security Features

All file operations include robust security measures to protect the system:

### 1. Path Validation
- Only relative paths are allowed
- Absolute paths (e.g., `/etc/passwd`) are rejected

### 2. Sandboxing
- All operations are restricted to the current working directory
- Files outside the working directory cannot be accessed

### 3. Path Traversal Prevention
- Attempts to access parent directories are blocked
- Examples of blocked paths:
  - `../../../etc/passwd`
  - `subdir/../../etc/passwd`
  - Any path that resolves outside the working directory

### 4. Type Checking
- `delete_file` will not delete directories
- `read_file` will not read directories
- Appropriate error messages for type mismatches

## Implementation Details

### Location
- **Source**: `mcp_client_for_ollama/tools/builtin.py`
- **Tests**: `tests/test_builtin_tools.py`

### Integration
File access tools are automatically registered as built-in tools when the `BuiltinToolManager` is initialized. They appear in the tool selection interface alongside other built-in tools like:
- `builtin.set_system_prompt`
- `builtin.get_system_prompt`
- `builtin.execute_python_code`
- `builtin.execute_bash_command`

### Path Validation Method
The `_validate_path()` method:
1. Rejects absolute paths
2. Resolves the path relative to the working directory
3. Checks if the resolved path is within the working directory
4. Returns validation status and resolved path or error message

### Working Directory
The working directory is captured when `BuiltinToolManager` is initialized using `os.getcwd()`. All file operations are validated against this directory.

## Testing

Comprehensive test coverage includes:

### Functional Tests (34 tests)
- Read operations (success, missing file, directory error, missing path)
- Write operations (success, subdirectories, overwrite, missing args)
- List files (success, recursive, empty, nonexistent)
- List directories (success, empty, nonexistent)
- Create directory (success, nested, already exists, missing path)
- Delete file (success, missing file, directory error, missing path)
- File exists (file, directory, not found, missing path)
- Get file info (file, directory, not found, missing path)

### Security Tests (3 tests)
- Absolute path rejection
- Path traversal prevention
- Complex path traversal prevention

### Test Results
All 46 tests pass successfully, ensuring reliable and secure operation.

## Usage Examples

### Reading and Modifying Code

```python
# Model can read a file
read_file(path="src/app.py")

# Model can modify and write back
write_file(
    path="src/app.py",
    content="# Updated code here\nprint('Hello')"
)
```

### Exploring Project Structure

```python
# List all Python files recursively
list_files(path=".", recursive=True)

# Check project directories
list_directories(path="src")

# Get info about a specific file
get_file_info(path="setup.py")
```

### File Management

```python
# Check if config exists
file_exists(path="config.json")

# Create a new directory for logs
create_directory(path="logs/debug")

# Clean up temporary files
delete_file(path="temp/cache.txt")
```

## Best Practices

1. **Always use relative paths**: Never use absolute paths or path traversal
2. **Check existence first**: Use `file_exists` before reading files to handle missing files gracefully
3. **Get file info**: Use `get_file_info` to check file metadata before operations
4. **List before operations**: Use `list_files` and `list_directories` to explore structure first
5. **Error handling**: All tools return descriptive error messages - models should handle errors appropriately

## Future Enhancements

Potential additions for future versions:
- `builtin.copy_file` - Copy files within the working directory
- `builtin.move_file` - Move/rename files
- `builtin.delete_directory` - Delete directories (with safety checks)
- `builtin.search_files` - Search for files by pattern
- `builtin.read_file_lines` - Read specific line ranges from large files

## Version History

- **v0.22.0**: Initial implementation of file access tools
  - Added 8 file access tools
  - Implemented security validation
  - Added comprehensive test suite (46 tests)
