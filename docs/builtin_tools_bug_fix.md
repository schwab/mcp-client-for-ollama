# Built-in Tools Bug Fix - v0.22.0

## Bug Fix Summary

### The Problem

When users ran `reload-servers` without any MCP servers configured, all builtin tools would show as enabled (✓) in the UI, but would actually be disabled. Users would see the following warning when trying to use tools:

```
Warning: No tools are enabled. Model will respond without tool access.
```

This created a confusing situation where the UI displayed:
```
╭─────────────────────────────── 🔧 Available Tools ───────────────────────────────╮
│ ✓ builtin.set_system_prompt           ✓ builtin.get_system_prompt              │
│ ✓ builtin.execute_python_code         ✓ builtin.execute_bash_command           │
│ ✓ builtin.read_file                   ✓ builtin.write_file                     │
│ ✓ builtin.list_files                  ✓ builtin.list_directories               │
│ ✓ builtin.create_directory            ✓ builtin.delete_file                    │
│ ✓ builtin.file_exists                 ✓ builtin.get_file_info                  │
╰──────────────────────────────── 12/12 tools enabled ─────────────────────────────╯
```

But internally, `enabled_tool_objects` would return an empty list, preventing the model from using any tools.

### Root Cause

The bug was caused by a **shared reference issue** between `ToolManager` and `ServerConnector`:

#### Step-by-Step Bug Progression

1. **Initial State**: ToolManager has `enabled_tools = {'builtin.tool1': True, 'builtin.tool2': True, ...}`

2. **reload_servers() Called**:
   - Line 1336 in `client.py`: Saves current tool states
   - Line 1339: Calls `disconnect_all_servers()`

3. **disconnect_all_servers() in ServerConnector** (`server/connector.py:443`):
   ```python
   self.enabled_tools.clear()  # Clears ServerConnector's enabled_tools dict
   ```

4. **The Problem**: In `ToolManager.set_enabled_tools()` (line 75 of `tools/manager.py`):
   ```python
   self.enabled_tools = server_enabled_tools  # Direct reference, not a copy!
   ```

   This made both `ToolManager.enabled_tools` and `ServerConnector.enabled_tools` point to the **same dict object in memory**.

5. **The Cascade**: When `ServerConnector.enabled_tools.clear()` was called, it also cleared `ToolManager.enabled_tools` because they were the same object!

6. **Failed Preservation**: When `set_enabled_tools({})` tried to preserve builtin tools:
   ```python
   builtin_enabled = {
       name: status for name, status in self.enabled_tools.items() if name.startswith('builtin.')
   }
   ```

   The dict was already empty, so `builtin_enabled = {}`, and nothing could be preserved.

### The Fix

**File**: `mcp_client_for_ollama/tools/manager.py`
**Line**: 75

**Before**:
```python
def set_enabled_tools(self, server_enabled_tools: Dict[str, bool]) -> None:
    """Set the enabled status of tools from servers, preserving built-in tool statuses."""
    # Preserve the enabled status of built-in tools that were set during init
    builtin_enabled = {
        name: status for name, status in self.enabled_tools.items() if name.startswith('builtin.')
    }

    # The new state is the server tools...
    self.enabled_tools = server_enabled_tools  # BUG: Direct reference!
    # ...updated with the built-in tools.
    self.enabled_tools.update(builtin_enabled)
```

**After**:
```python
def set_enabled_tools(self, server_enabled_tools: Dict[str, bool]) -> None:
    """Set the enabled status of tools from servers, preserving built-in tool statuses."""
    # Preserve the enabled status of built-in tools that were set during init
    builtin_enabled = {
        name: status for name, status in self.enabled_tools.items() if name.startswith('builtin.')
    }

    # The new state is the server tools (make a copy to avoid shared references)...
    self.enabled_tools = server_enabled_tools.copy()  # FIXED: Create independent copy
    # ...updated with the built-in tools.
    self.enabled_tools.update(builtin_enabled)
```

### Impact

This fix ensures that:
- ✅ Builtin tools work correctly when no MCP servers are configured
- ✅ Builtin tools persist through `reload-servers` operations
- ✅ ToolManager maintains its own independent copy of enabled tool states
- ✅ No shared reference issues between ToolManager and ServerConnector

### Testing

#### Reproduction Test
Created test that successfully reproduced the bug:
```python
async def test_reload_servers_with_autodiscovery_no_servers():
    client = MCPClient()
    await client.connect_to_servers(auto_discovery=True)  # No servers found
    await client.reload_servers()  # Bug triggered here

    # Before fix: enabled_tools = {} (empty)
    # After fix: enabled_tools = {'builtin.tool1': True, ...} (all 12 tools)
```

#### Test Results
- **Before Fix**:
  - `available_tools`: 12 tools
  - `enabled_tools`: {} (empty dict)
  - `enabled_tool_objects`: 0 (empty list)
  - Result: ❌ No tools available to model

- **After Fix**:
  - `available_tools`: 12 tools
  - `enabled_tools`: 12 entries (all builtin tools)
  - `enabled_tool_objects`: 12 tools
  - Result: ✅ All builtin tools available to model

#### Full Test Suite
- ✅ All 138 existing tests pass
- ✅ 46 tests for builtin tools (including 34 new file access tool tests)
- ✅ No regressions detected

## Complete Changes in v0.22.0

### 1. Added 8 New File Access Built-in Tools

New tools added to `mcp_client_for_ollama/tools/builtin.py`:

#### builtin.read_file
```json
{
  "path": "src/main.py"
}
```
Reads and returns the contents of a file.

#### builtin.write_file
```json
{
  "path": "output/result.txt",
  "content": "Hello, World!"
}
```
Writes content to a file (creates or overwrites). Automatically creates parent directories.

#### builtin.list_files
```json
{
  "path": "src",
  "recursive": true
}
```
Lists all files in a directory. Supports recursive listing.

#### builtin.list_directories
```json
{
  "path": "."
}
```
Lists all subdirectories in a directory.

#### builtin.create_directory
```json
{
  "path": "build/output/logs"
}
```
Creates a new directory with parent directories (like `mkdir -p`).

#### builtin.delete_file
```json
{
  "path": "temp/cache.txt"
}
```
Deletes a file. Includes safety checks to prevent deleting directories.

#### builtin.file_exists
```json
{
  "path": "config.json"
}
```
Checks if a file or directory exists and returns its type.

#### builtin.get_file_info
```json
{
  "path": "README.md"
}
```
Gets detailed metadata: type, size, modification time, creation time, permissions.

### 2. Security Features

All file operations include robust security measures:

- **Path Validation**: Only relative paths allowed
- **Sandboxing**: Operations restricted to current working directory
- **Path Traversal Prevention**: Blocks attempts like `../../../etc/passwd`
- **Type Checking**: Prevents operations on wrong file types (e.g., delete_file won't delete directories)

Implementation in `_validate_path()` method:
```python
def _validate_path(self, path: str) -> tuple[bool, str]:
    """Validates that a path is safe to use (within working directory)."""
    # Reject absolute paths
    if os.path.isabs(path):
        return False, "Error: Absolute paths are not allowed."

    # Resolve path and check it's within working directory
    resolved_path = os.path.abspath(os.path.join(self.working_directory, path))

    if not resolved_path.startswith(os.path.abspath(self.working_directory)):
        return False, "Error: Path traversal outside working directory is not allowed."

    return True, resolved_path
```

### 3. Test Coverage

Added comprehensive tests in `tests/test_builtin_tools.py`:

- **Functional Tests** (34 tests):
  - Read operations (success, missing file, directory error, missing path)
  - Write operations (success, subdirectories, overwrite, missing args)
  - List files (success, recursive, empty, nonexistent)
  - List directories (success, empty, nonexistent)
  - Create directory (success, nested, already exists, missing path)
  - Delete file (success, missing file, directory error, missing path)
  - File exists (file, directory, not found, missing path)
  - Get file info (file, directory, not found, missing path)

- **Security Tests** (3 tests):
  - Absolute path rejection
  - Path traversal prevention
  - Complex path traversal prevention

- **Total**: 46 tests for builtin tools (up from 12)

### 4. Documentation

Created comprehensive documentation:
- **File**: `docs/builtin_file_access_tools.md`
- Includes usage examples, best practices, security features
- Documents all 8 new tools with parameters and examples

## Affected Files

### Modified Files
1. `mcp_client_for_ollama/tools/builtin.py`
   - Added 8 new file access tools
   - Added `_validate_path()` security method
   - Increased from 4 to 12 builtin tools

2. `mcp_client_for_ollama/tools/manager.py`
   - **Bug Fix**: Line 75 changed to use `.copy()`
   - Updated to handle 12 builtin tools

3. `tests/test_builtin_tools.py`
   - Updated tool count from 4 to 12
   - Added 34 new tests for file access tools
   - Total tests increased from 12 to 46

### New Documentation
1. `docs/builtin_file_access_tools.md`
   - Complete reference for new file access tools
   - Usage examples and security information

2. `docs/builtin_tools_bug_fix.md` (this file)
   - Bug analysis and fix documentation

## Migration Guide

### For Users

No migration needed! The changes are backward compatible:

1. **New Tools**: All 8 new file access tools are automatically available
2. **Bug Fix**: Transparent fix - builtin tools now work correctly in all scenarios
3. **Existing Configs**: Saved configurations will work as before

### For Developers

If you're developing MCP servers or extending the codebase:

1. **New Pattern**: When accepting dict parameters from other components, always use `.copy()` if you need an independent copy
2. **Builtin Tools**: New tools follow the same pattern as existing ones
3. **Security**: Use `_validate_path()` as a template for path validation

## Known Issues

None. All tests pass and no regressions detected.

## Future Enhancements

Potential additions for future versions:
- `builtin.copy_file` - Copy files within working directory
- `builtin.move_file` - Move/rename files
- `builtin.delete_directory` - Delete directories (with safety checks)
- `builtin.search_files` - Search for files by pattern
- `builtin.read_file_lines` - Read specific line ranges from large files

## Version History

- **v0.22.0**:
  - Added 8 file access builtin tools
  - Fixed shared reference bug in `set_enabled_tools()`
  - Added 34 new tests
  - Total builtin tools: 12 (up from 4)
