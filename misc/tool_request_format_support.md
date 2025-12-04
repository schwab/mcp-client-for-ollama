# Tool Request Format Support

## Overview

The JSON tool parser has been expanded to support tool calls embedded in JSON objects with auxiliary fields like "thoughts" and structured as "tool_request" objects. This format is commonly used by models that provide reasoning alongside their tool calls.

## Supported Format

### Tool Request with Thoughts

```json
{
  "thoughts": "To load the Writing Style Guide and apply it as my instructions, I need to follow these steps:\n\n1. Identify the location of the Writing Style Guide file within the `/root` project path.\n2. Read the contents of the file.\n3. Update the system prompt with the content of the Writing Style Guide.\n\nLet's start by listing all files in the current directory to find the Writing Style Guide.",
  "tool_request": {
    "name": "builtin.list_files",
    "parameters": {
      "path": "/root"
    }
  }
}
```

### Key Features

1. **Auxiliary Fields**: The parser now handles JSON objects with multiple fields where the tool call is nested
2. **Tool Request Field**: Recognizes `tool_request` as a container for the actual tool call
3. **Parameters Alias**: Accepts both `parameters` and `arguments` as the arguments field
4. **Nested Deduplication**: Prevents finding the same tool call multiple times when nested in outer objects

## Changes Made

### 1. Enhanced `_convert_json_to_tool_call()` Method

**File**: `mcp_client_for_ollama/utils/json_tool_parser.py`

Added support for:
- `tool_request` field containing `name` and `parameters`/`arguments`
- `parameters` as an alias for `arguments` in all formats
- Priority order: `tool_request` → `function` → flattened format

```python
# Check for tool_request format {'tool_request': {'name': ..., 'parameters': ...}}
if 'tool_request' in tc_json and isinstance(tc_json['tool_request'], dict):
    tool_req = tc_json['tool_request']
    name = tool_req.get('name') or tool_req.get('function_name')
    # Check for parameters or arguments
    if 'parameters' in tool_req:
        args = tool_req['parameters']
    elif 'arguments' in tool_req:
        args = tool_req['arguments']
    # ...
```

### 2. Updated `_parse_embedded_json()` Method

**File**: `mcp_client_for_ollama/utils/json_tool_parser.py`

Enhanced validation to recognize tool_request format:

```python
# Check for tool_request format
has_tool_request = 'tool_request' in parsed and isinstance(parsed['tool_request'], dict)
# Check for standard formats
has_name = 'name' in parsed or 'function_name' in parsed or 'function' in parsed
has_args = 'arguments' in parsed or 'function_args' in parsed or 'parameters' in parsed

if has_tool_request or (has_name and has_args):
    potential_tool_calls.append(parsed)
```

### 3. Deduplication Logic

Added range tracking to prevent parsing the same tool call multiple times:

```python
# Track ranges that have already been parsed to avoid duplicates
parsed_ranges = []

for start_index in start_indices:
    # Skip if this start_index is within an already-parsed range
    if any(start <= start_index <= end for start, end in parsed_ranges):
        continue

    # ... parse JSON ...

    if has_tool_request or (has_name and has_args):
        potential_tool_calls.append(parsed)
        # Mark this range as parsed
        parsed_ranges.append((start_index, end_index))
```

This prevents the parser from finding both:
1. The outer object with `tool_request` field
2. The inner `tool_request` object itself

## Supported Formats Summary

The JSON tool parser now supports all of these formats:

### 1. Standard Function Format
```json
{
  "function": {
    "name": "builtin.read_file",
    "arguments": {"path": "config.json"}
  }
}
```

### 2. Flattened Format
```json
{
  "name": "builtin.read_file",
  "arguments": {"path": "config.json"}
}
```

### 3. Tool Request Format (NEW)
```json
{
  "thoughts": "I need to read the config",
  "tool_request": {
    "name": "builtin.read_file",
    "parameters": {"path": "config.json"}
  }
}
```

### 4. Parameters Alias (NEW)
All formats now accept `parameters` in place of `arguments`:

```json
{
  "name": "builtin.read_file",
  "parameters": {"path": "config.json"}
}
```

## Testing

### New Tests Added

**File**: `tests/test_tool_parsers.py`

1. **`test_json_tool_parser_tool_request_format`**: Tests tool_request in markdown JSON blocks with thoughts
2. **`test_json_tool_parser_tool_request_embedded`**: Tests tool_request embedded in surrounding text
3. **`test_json_tool_parser_tool_request_with_arguments`**: Tests tool_request with 'arguments' instead of 'parameters'

All tests pass: **148/148** (up from 145 before this change)

### Example Test

```python
def test_json_tool_parser_tool_request_format(json_tool_parser):
    """Test parsing tool_request format with thoughts and parameters."""
    text = """```json
{
  "thoughts": "To load the Writing Style Guide...",
  "tool_request": {
    "name": "builtin.list_files",
    "parameters": {
      "path": "/root"
    }
  }
}
```"""
    tool_calls = json_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("builtin.list_files", {"path": "/root"})
```

## Use Cases

This format is particularly useful for:

1. **Reasoning Models**: Models that provide step-by-step reasoning before taking action
2. **Chain-of-Thought**: LLMs that explain their thought process alongside tool calls
3. **Debugging**: Developers can see the model's reasoning in the `thoughts` field
4. **Multi-Step Planning**: Models can outline their plan while making the first tool call

## Example Workflow

```
User: "Load the Writing Style Guide and apply it"

Model Response:
{
  "thoughts": "To load the Writing Style Guide and apply it as my instructions, I need to:
  1. Identify the location of the Writing Style Guide file
  2. Read the contents of the file
  3. Update the system prompt with the content

  Let's start by listing all files to find the Writing Style Guide.",
  "tool_request": {
    "name": "builtin.list_files",
    "parameters": {
      "path": "/root"
    }
  }
}

→ Parser extracts: builtin.list_files(path="/root")
→ Executes tool and returns results
→ Model continues with next step
```

## Backwards Compatibility

✅ **Fully backwards compatible**

All existing formats continue to work:
- Standard function format with `arguments`
- Flattened format
- OpenAI format
- Embedded JSON
- Markdown JSON blocks

The new format is additive and doesn't affect existing parsing behavior.

## Performance Impact

**Minimal impact**:
- Adds one additional field check (`tool_request`) in validation
- Range tracking adds O(n) space where n = number of parsed tool calls (typically 1-3)
- Deduplication check is O(m) where m = number of parsed ranges (also typically 1-3)

Overall: **Negligible performance impact** for typical use cases.

## Related Files

- `mcp_client_for_ollama/utils/json_tool_parser.py` - JSON tool parser implementation
- `tests/test_tool_parsers.py` - Test coverage
- `mcp_client_for_ollama/utils/tool_parser.py` - Composite parser that uses JsonToolParser

## Future Enhancements

Potential improvements:
1. Support for multiple tool requests in a single response
2. Structured validation of the `thoughts` field
3. Logging/display of model reasoning in the TUI
4. Configuration option to show/hide thoughts in output

## Version

- **Added**: Version 0.22.0+
- **Status**: Stable
- **Breaking Changes**: None
