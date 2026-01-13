# Version 0.23.20 - Patch File Tool

## New Feature: `builtin.patch_file`

Added a new efficient file editing tool that solves context window exhaustion issues when working with long files.

### Problem Solved
- Agents were getting stuck in loops when trying to modify large files
- Context window was being consumed by repeatedly reading/writing entire file contents
- Small changes required transmitting entire file contents

### Solution
New `builtin.patch_file` tool that uses search-replace operations instead of full file rewrites.

### Key Benefits
1. **Reduced Context Usage**: Only changed text is transmitted, not entire files
2. **No More Loops**: Agents can modify large files without context exhaustion
3. **Batch Operations**: Multiple changes in one atomic operation
4. **Smart Validation**: Clear errors when text not found or ambiguous
5. **Safe**: All-or-nothing atomic updates with automatic rollback on failure

### Tool Specification

**Name**: `builtin.patch_file`

**Parameters**:
- `path` (required): Relative path to file to patch
- `changes` (required): Array of change objects:
  - `search` (required): Exact text to find
  - `replace` (required): Text to replace with (empty string to delete)
  - `occurrence` (optional): Which occurrence to replace (1-indexed)

**Features**:
- Sequential application of changes
- Atomic operations (all succeed or none apply)
- Automatic occurrence detection (errors if ambiguous)
- Detailed success/error messages
- File statistics in response

### Usage Examples

#### Simple Replacement
```json
{
  "path": "config.py",
  "changes": [
    {
      "search": "DEBUG = True",
      "replace": "DEBUG = False"
    }
  ]
}
```

#### Multiple Changes
```json
{
  "path": "src/server.py",
  "changes": [
    {
      "search": "MAX_CONNECTIONS = 10",
      "replace": "MAX_CONNECTIONS = 100"
    },
    {
      "search": "TIMEOUT = 30",
      "replace": "TIMEOUT = 60"
    }
  ]
}
```

#### Handling Duplicates
```json
{
  "path": "tests/test_api.py",
  "changes": [
    {
      "search": "assert result == expected",
      "replace": "assert result == expected, f\"Got {result}\"",
      "occurrence": 2
    }
  ]
}
```

#### Multi-line Changes
```json
{
  "path": "database.py",
  "changes": [
    {
      "search": "def connect():\n    return sqlite3.connect('db.sqlite')",
      "replace": "def connect():\n    conn = sqlite3.connect('db.sqlite')\n    conn.row_factory = sqlite3.Row\n    return conn"
    }
  ]
}
```

### Agent Guidance Enhancements

**Updated `builtin.write_file` description**:
- Now suggests using `patch_file` for large files (>500 lines) or targeted changes
- Helps agents choose the right tool automatically

**Enhanced `builtin.patch_file` description**:
- Clear guidance on when to use: large files, targeted changes, batch operations
- Emphasizes efficiency benefits for context window management

### Files Modified

1. **mcp_client_for_ollama/tools/builtin.py**:
   - Added `patch_file` to tool handlers registry (line 30)
   - Added `patch_file_tool` Tool definition (lines 135-192)
   - Added `patch_file_tool` to return list (line 311)
   - Implemented `_handle_patch_file()` method (lines 1002-1158)
   - Updated `write_file` description to suggest `patch_file` (line 117)

2. **mcp_client_for_ollama/__init__.py**:
   - Bumped version from 0.23.19 to 0.23.20

3. **pyproject.toml**:
   - Bumped version from 0.23.19 to 0.23.20

### Technical Details

**Implementation Highlights**:
- Full path validation and security checks
- UTF-8 encoding support with clear error messages
- Atomic operations with rollback on failure
- Detailed change tracking and statistics
- Comprehensive error handling for all edge cases

**Error Handling**:
- File not found
- Search text not found
- Ambiguous matches (multiple occurrences without specification)
- Invalid occurrence numbers
- Encoding errors
- Write failures (with automatic rollback)

**Success Response**:
```
File 'config.py' patched successfully.
Applied 2 changes:
  1. Replaced unique occurrence
  2. Replaced unique occurrence

File statistics:
  Lines: 42 → 42 (+0)
  Size: 1247 → 1267 bytes (+20)
```

### Automatic Discovery

The tool is automatically available to all agents once the code is deployed:
1. `BuiltinToolManager.get_builtin_tools()` includes it
2. `ToolManager` automatically enables all builtin tools
3. Tools are passed to Ollama with every chat API call
4. Agents see it in their available tools list

No configuration required - it just works!

### Next Steps for Users

1. Deploy the updated code
2. Agents will automatically see and use the new tool
3. Watch for reduced context usage in logs
4. Expect fewer timeout/loop issues with large files

### Future Enhancements (Potential)

- Fuzzy matching for approximate text matches
- Regex support for pattern-based replacements
- Preview/dry-run mode
- Automatic backup creation (.bak files)
- Line context display for verification
- Undo/revert functionality
