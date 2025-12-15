# Diff-Based File Editing Tool Design

## Problem Statement

The current file editing workflow requires agents to:
1. Read entire file contents into context
2. Modify the contents in memory
3. Write the entire file back using `builtin.write_file`

For long files, this creates several issues:
- **Context Window Exhaustion**: Large files consume significant context tokens
- **Loop Behavior**: Agents may get stuck trying to write files that don't fit in context
- **Inefficiency**: Small changes require transmitting entire file contents
- **Error Prone**: Higher chance of truncation or corruption with large files

## Design Goals

1. **Minimize Context Usage**: Only transmit changed sections, not entire files
2. **Agent-Friendly**: Use a format that LLMs can reliably generate
3. **Safe**: Validate changes before applying, with rollback capability
4. **Multiple Edits**: Support batch operations to reduce round trips
5. **Clear Feedback**: Provide detailed success/error messages

## Design Options Considered

### Option 1: Unified Diff Format (Traditional Patch)
```diff
--- file.py
+++ file.py
@@ -10,7 +10,7 @@
 def example():
-    old line
+    new line
     context
```

**Pros**: Standard format, widely understood
**Cons**:
- Complex for LLMs to generate correctly
- Requires exact context lines
- Line number calculations error-prone
- Harder to validate

### Option 2: Line Number-Based Edits
```json
{
  "edits": [
    {"line": 42, "old": "old text", "new": "new text"},
    {"line": 100, "delete": true}
  ]
}
```

**Pros**: Simple to understand
**Cons**:
- Line numbers shift after each edit (order-dependent)
- File changes between read and edit break this
- Agents struggle with accurate line counting

### Option 3: Search-Replace Blocks (RECOMMENDED)
```json
{
  "changes": [
    {
      "search": "exact text to find",
      "replace": "exact text to replace with",
      "occurrence": 1  // optional: which match (default: fail if not unique)
    }
  ]
}
```

**Pros**:
- LLMs excel at understanding text patterns
- No line number calculations needed
- Resilient to file changes between operations
- Clear error messages when text not found
- Similar to existing Edit tool in Claude Code CLI

**Cons**:
- Requires exact text matching
- May need context for ambiguous matches

## Recommended Implementation: `builtin.patch_file`

### Tool Specification

**Name**: `builtin.patch_file`

**Description**: Apply multiple search-replace changes to a file without reading/writing entire contents. More efficient than write_file for small changes to large files.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "File path relative to working directory"
    },
    "changes": {
      "type": "array",
      "description": "Array of search-replace operations to apply sequentially",
      "items": {
        "type": "object",
        "properties": {
          "search": {
            "type": "string",
            "description": "Exact text to find (must be unique unless occurrence specified)"
          },
          "replace": {
            "type": "string",
            "description": "Text to replace with"
          },
          "occurrence": {
            "type": "integer",
            "description": "Which occurrence to replace (1-indexed). If omitted, search must be unique.",
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
```

### Handler Implementation Details

**File**: `mcp_client_for_ollama/tools/builtin.py`

**Key Features**:
1. **Atomic Operations**: All changes succeed or all fail (with rollback)
2. **Sequential Application**: Changes applied in order specified
3. **Validation**: Check each search pattern exists before applying
4. **Detailed Feedback**: Report what changed and where
5. **UTF-8 Handling**: Proper encoding support

**Error Handling**:
- File not found → descriptive error
- Search text not found → report which change failed
- Search text ambiguous (multiple matches without occurrence) → report count, require occurrence
- Invalid occurrence number → report actual count
- Encoding errors → report and suggest binary mode

**Success Response Format**:
```
File patched successfully: path/to/file.py
Applied 3 changes:
  1. Line 42: Updated function signature
  2. Line 156: Fixed import statement
  3. Line 203: Corrected variable name
```

### Usage Examples

#### Example 1: Single Change
```json
{
  "path": "src/server.py",
  "changes": [
    {
      "search": "def old_function_name(arg):",
      "replace": "def new_function_name(arg):"
    }
  ]
}
```

#### Example 2: Multiple Changes (Batch)
```json
{
  "path": "src/config.py",
  "changes": [
    {
      "search": "DEBUG = True",
      "replace": "DEBUG = False"
    },
    {
      "search": "MAX_CONNECTIONS = 10",
      "replace": "MAX_CONNECTIONS = 100"
    },
    {
      "search": "# TODO: implement caching",
      "replace": ""
    }
  ]
}
```

#### Example 3: Handling Duplicate Text
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

#### Example 4: Multi-line Changes
```json
{
  "path": "src/database.py",
  "changes": [
    {
      "search": "def connect():\n    return sqlite3.connect('db.sqlite')",
      "replace": "def connect():\n    conn = sqlite3.connect('db.sqlite')\n    conn.row_factory = sqlite3.Row\n    return conn"
    }
  ]
}
```

## Implementation Checklist

- [ ] Add tool definition to `get_builtin_tools()` in `builtin.py`
- [ ] Implement `_handle_patch_file()` handler method
- [ ] Register handler in `_tool_handlers` dict
- [ ] Add comprehensive error handling
- [ ] Test with various file sizes and change patterns
- [ ] Add unit tests for edge cases
- [ ] Update documentation

## Advanced Features (Future Enhancements)

1. **Fuzzy Matching**: Allow approximate matches with similarity threshold
2. **Regex Support**: Enable pattern-based replacements
3. **Preview Mode**: Show what would change without applying
4. **Line Context**: Optionally show surrounding lines for verification
5. **Backup Creation**: Automatically create .bak files before patching
6. **Dry Run**: Validate all changes before applying any

## Integration Benefits

Once implemented, agents can:
- Edit large configuration files efficiently
- Make targeted code changes without full file rewrites
- Batch multiple related changes in one operation
- Avoid context window issues with large files
- Provide clearer intent about what's changing

## Migration Path

Existing code using `write_file` continues to work. Agents can adopt `patch_file`:
- **When**: Making small changes to large files
- **Why**: Reduce context usage and improve reliability
- **How**: Read file once (or use grep), identify changes, apply patch

The tool complements rather than replaces existing file operations.
