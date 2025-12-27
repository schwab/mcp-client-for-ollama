# Changelog v0.27.0

## Feature: Partial File Reading with Offset/Limit Parameters

### Summary
Enhanced `builtin.read_file` tool with partial file reading capability, allowing efficient reading of specific line ranges from large files. This feature significantly reduces context usage and improves performance when working with large codebases.

### Motivation
Similar to Claude Code's Read tool, agents often need to explore large files incrementally rather than loading entire files into context. This is especially important for:
- Large source code files (>500 lines)
- Log files
- Data files
- Configuration files with many entries

### Changes

#### 1. Enhanced `builtin.read_file` Tool Schema
Added two optional parameters:

- **`offset`** (integer, minimum: 1):
  - Line number to start reading from (1-indexed)
  - If not specified, reads from the beginning of the file
  - Example: `offset=50` starts reading from line 50

- **`limit`** (integer, minimum: 1):
  - Maximum number of lines to read
  - If not specified, reads all lines from offset to end of file
  - Useful for reading large files in chunks
  - Example: `offset=1, limit=100` reads lines 1-100

#### 2. Line-Numbered Output (cat -n Format)
All file content is now returned with line numbers for easy navigation:
```
     1→"""MCP Client for Ollama package."""
     2→
     3→__version__ = "0.27.0"
```

Benefits:
- Easy reference to specific lines
- Clear indication of position within file
- Consistent with Unix `cat -n` convention

#### 3. Enhanced Response Messages
The tool now provides context about partial reads:

**Full file read:**
```
✓ File 'src/main.py' read successfully. Size: 15234 bytes, 450 lines

Content:
     1→import os
     2→import sys
...
```

**Partial file read:**
```
✓ File 'src/main.py' read successfully (lines 100-150 of 450)

Content:
   100→def process_data():
   101→    """Process incoming data."""
...
```

#### 4. Agent Awareness
Updated agent system prompts to make them aware of this capability:

**READER agent:**
- Added guidance on using offset/limit for large files
- Examples of partial reading usage
- Emphasis on reducing context usage

**EXECUTOR agent:**
- Tool selection notes updated with partial reading examples
- Guidance on when to use offset/limit

### Implementation Details

**File**: `mcp_client_for_ollama/tools/builtin.py`

**Key changes in `_handle_read_file` method:**
1. Parse optional `offset` and `limit` parameters
2. Validate parameters (must be positive integers)
3. Read file and convert to lines array
4. Calculate slice range (convert 1-indexed offset to 0-indexed for Python)
5. Extract requested lines
6. Format with line numbers (cat -n style)
7. Return with appropriate success message

**Error handling:**
- Validates offset is within file bounds
- Clear error messages if offset exceeds file length
- Suggestions for valid offset range

### Usage Examples

**Read entire file with line numbers:**
```json
{
  "path": "src/main.py"
}
```

**Read first 100 lines:**
```json
{
  "path": "src/main.py",
  "offset": 1,
  "limit": 100
}
```

**Read lines 50-150:**
```json
{
  "path": "src/main.py",
  "offset": 50,
  "limit": 100
}
```

**Read from line 200 to end:**
```json
{
  "path": "src/main.py",
  "offset": 200
}
```

### Benefits

1. **Reduced Context Usage**: Read only the portion of the file you need
2. **Better Performance**: Faster response times with smaller payloads
3. **Incremental Exploration**: Agents can explore large files section by section
4. **Familiar UX**: Similar to Claude Code's Read tool, making it intuitive for users
5. **Line Numbers**: Easy navigation and reference to specific code locations

### Backward Compatibility

✅ **Fully backward compatible**

- `offset` and `limit` parameters are optional
- Existing code calling `builtin.read_file` with just `{"path": "..."}` continues to work exactly as before
- Only difference: all output now includes line numbers (improvement, not breaking change)

### Related Tools

This enhancement complements existing file tools:
- **`builtin.write_file`**: Write entire file content
- **`builtin.patch_file`**: Apply targeted search-replace edits (already efficient for large files)
- **`builtin.list_files`**: List directory contents

Together, these provide a complete file I/O toolset with both full-file and partial-file operations.

### Future Enhancements (Potential)

- Add `pattern` parameter for grep-like filtering within file ranges
- Support for reading multiple non-contiguous ranges
- Binary file support with hex dump output
- Automatic chunking suggestions for very large files

---

**Version**: 0.27.0
**Date**: 2025-12-26
**Category**: Feature Enhancement
**Impact**: Agents, File I/O, Performance
