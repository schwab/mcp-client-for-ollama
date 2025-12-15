# Session Management: Migration to Builtin Tools

## Overview

The session save/load functionality has been migrated from using the external filesystem MCP server to using builtin file access tools. This change removes the dependency on external MCP servers for core session management functionality.

## Changes Made

### 1. Enhanced Builtin Tools to Support Absolute Paths

**File**: `mcp_client_for_ollama/tools/builtin.py`

Added support for an internal-only parameter `__internal_allow_absolute` that allows absolute paths for internal operations while maintaining security restrictions for LLM-initiated calls.

**Modified Methods**:
- `_validate_path()`: Added `allow_absolute` parameter (default: `False`)
  - When `False`: Only allows relative paths within working directory (security-sandboxed for LLM use)
  - When `True`: Allows absolute paths (for internal client operations like session management)

**Updated Handlers**:
- `_handle_read_file()`
- `_handle_write_file()`
- `_handle_list_files()`
- `_handle_list_directories()`
- `_handle_create_directory()`
- `_handle_delete_file()`
- `_handle_file_exists()`
- `_handle_get_file_info()`

All handlers now check for the `__internal_allow_absolute` parameter in args and pass it to `_validate_path()`.

### 2. Updated Client Session Management

**File**: `mcp_client_for_ollama/client.py`

**`save_session()` Method**:
- Changed from filesystem MCP server calls to builtin tools
- Now uses:
  - `builtin_tool_manager.execute_tool('create_directory', ...)` to create session directory
  - `builtin_tool_manager.execute_tool('write_file', ...)` to save session JSON
- Passes `__internal_allow_absolute: True` to support absolute paths

**`load_session()` Method**:
- Changed from filesystem MCP server calls to builtin tools
- Now uses:
  - `builtin_tool_manager.execute_tool('list_files', ...)` to list available sessions
  - `builtin_tool_manager.execute_tool('read_file', ...)` to load session JSON
- Passes `__internal_allow_absolute: True` to support absolute paths

**Removed Code**:
- `_has_filesystem_tool()` method (lines 102-104) - no longer needed
- Filesystem service checks in command handlers (lines 836-842)
- Filesystem requirement note from help text (line 950)
- Filesystem check from `_change_session_save_location()` (lines 284-288)

## Security Model

### Two-Tier Path Validation

1. **LLM-Initiated Calls** (via tool execution during chat):
   - Only relative paths allowed
   - Paths must be within working directory
   - Prevents directory traversal attacks
   - Example: LLM calling `builtin.read_file` with path `../../etc/passwd` → **BLOCKED**

2. **Internal Client Calls** (session management):
   - Can use absolute paths via `__internal_allow_absolute` parameter
   - Supports user-configured session directories (e.g., `/tmp/sessions`, `~/.config/ollmcp/sessions`)
   - Parameter is not exposed in tool schema, only available to internal code
   - Example: Client saving session to `/tmp/test_sessions/my-session.json` → **ALLOWED**

### Why This Approach?

- **Security**: LLMs cannot access arbitrary file system locations
- **Flexibility**: Internal code can use absolute paths for user-configured directories
- **Simplicity**: Single set of file tools serves both use cases
- **No Breaking Changes**: Session management behavior unchanged for users

## Benefits

1. **Reduced Dependencies**: No need to run filesystem MCP server for basic session operations
2. **Improved Reliability**: Session save/load always available, even without MCP servers
3. **Better UX**: Users can save/load sessions immediately after installation
4. **Maintained Security**: LLM access remains sandboxed to working directory
5. **Backwards Compatible**: Existing session files and workflows unchanged

## Testing

### Test Coverage

All existing tests pass (53 tests in `tests/test_builtin_tools.py`):
- File operation tests
- Path validation tests
- Gitignore filtering tests
- Security tests (absolute path blocking, path traversal prevention)

### Manual Testing

Created and verified `test_session.py` demonstrating:
- Creating session directory with absolute path
- Writing session file with absolute path
- Listing session files with absolute path
- Reading session file with absolute path
- All operations successful with `__internal_allow_absolute: True`

## Usage Examples

### For Users (No Change)

```bash
# Session management works exactly as before
ollmcp
> save-session my-work
Session 'my-work' saved successfully.

> load-session
# Interactive selection of saved sessions
```

### For Developers (Internal API)

```python
# Session save with absolute path
dir_result = self.builtin_tool_manager.execute_tool('create_directory', {
    'path': '/tmp/my-sessions',
    '__internal_allow_absolute': True  # Internal-only parameter
})

write_result = self.builtin_tool_manager.execute_tool('write_file', {
    'path': '/tmp/my-sessions/session.json',
    'content': json.dumps(data),
    '__internal_allow_absolute': True
})

# Session load with absolute path
list_result = self.builtin_tool_manager.execute_tool('list_files', {
    'path': '/tmp/my-sessions',
    '__internal_allow_absolute': True
})

read_result = self.builtin_tool_manager.execute_tool('read_file', {
    'path': '/tmp/my-sessions/session.json',
    '__internal_allow_absolute': True
})
```

### For LLMs (Restricted)

```json
// LLM can only use relative paths
{
  "name": "builtin.read_file",
  "arguments": {
    "path": "config/settings.json"  // ✓ Allowed (relative, within working dir)
  }
}

{
  "name": "builtin.read_file",
  "arguments": {
    "path": "/etc/passwd"  // ✗ BLOCKED (absolute path)
  }
}

{
  "name": "builtin.read_file",
  "arguments": {
    "path": "../../sensitive.txt"  // ✗ BLOCKED (path traversal)
  }
}
```

## Configuration

### Default Session Directory

Default: `./.ollmcp_sessions` (relative to working directory)

### User-Configured Directory

Users can change via the `session-dir` / `sd` command:
- Supports absolute paths (e.g., `/tmp/ollmcp-sessions`)
- Supports home directory expansion (e.g., `~/.config/ollmcp/sessions`)
- Configuration persists in `~/.config/ollmcp/config.json`

## Future Enhancements

Potential improvements:
1. Add session export/import functionality
2. Support for session templates
3. Session tagging and search
4. Automatic session backups
5. Session compression for large histories

## Related Files

- `mcp_client_for_ollama/tools/builtin.py` - Builtin tool implementations
- `mcp_client_for_ollama/client.py` - Session management methods
- `tests/test_builtin_tools.py` - Test coverage
- `docs/builtin_file_access_tools.md` - Builtin tools documentation

## Version

- **Added**: Version 0.22.0
- **Status**: Stable
- **Breaking Changes**: None
