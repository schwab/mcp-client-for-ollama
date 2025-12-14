"""
Implementation code for builtin.patch_file tool

This file contains the complete implementation that needs to be added to:
mcp_client_for_ollama/tools/builtin.py

Follow the instructions in the comments to integrate this code.
"""

# ============================================================================
# STEP 1: Add handler to _tool_handlers dict in __init__ (around line 37)
# ============================================================================
# Add this line to the _tool_handlers dictionary:
# "patch_file": self._handle_patch_file,


# ============================================================================
# STEP 2: Add Tool definition in get_builtin_tools() (around line 247)
# ============================================================================

from mcp import Tool

patch_file_tool = Tool(
    name="builtin.patch_file",
    description=(
        "Apply multiple search-replace changes to a file efficiently without writing entire contents. "
        "RECOMMENDED for: (1) files larger than 500 lines, (2) making small targeted changes to any file, "
        "(3) multiple related edits in one operation. More efficient than write_file as it reduces "
        "context window usage significantly. Changes are applied sequentially in the order provided. "
        "All changes must succeed or the file is left unchanged (atomic operation). "
        "Path must be relative to the current working directory."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The relative path to the file to patch."
            },
            "changes": {
                "type": "array",
                "description": (
                    "Array of search-replace operations to apply sequentially. "
                    "Each change must find exactly one match unless 'occurrence' is specified."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": "string",
                            "description": (
                                "Exact text to find in the file. Must be unique unless 'occurrence' "
                                "is specified. Can span multiple lines."
                            )
                        },
                        "replace": {
                            "type": "string",
                            "description": (
                                "Text to replace the search text with. Use empty string to delete. "
                                "Preserves surrounding content."
                            )
                        },
                        "occurrence": {
                            "type": "integer",
                            "description": (
                                "Which occurrence to replace (1-indexed). If omitted, the search "
                                "text must appear exactly once in the file. Use this when the same "
                                "text appears multiple times."
                            ),
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
)

# Then add patch_file_tool to the returned list in get_builtin_tools() (around line 249-254)
# Change the return statement from:
#   return [
#       set_prompt_tool, get_prompt_tool, execute_python_code_tool, execute_bash_command_tool,
#       read_file_tool, write_file_tool, list_files_tool, list_directories_tool,
#       create_directory_tool, delete_file_tool, file_exists_tool, get_file_info_tool,
#       read_image_tool
#   ]
# To:
#   return [
#       set_prompt_tool, get_prompt_tool, execute_python_code_tool, execute_bash_command_tool,
#       read_file_tool, write_file_tool, list_files_tool, list_directories_tool,
#       create_directory_tool, delete_file_tool, file_exists_tool, get_file_info_tool,
#       read_image_tool, patch_file_tool
#   ]


# ============================================================================
# STEP 3: Add handler method to BuiltinToolManager class (around line 940)
# ============================================================================

def _handle_patch_file(self, args: Dict[str, Any]) -> str:
    """
    Handles the 'patch_file' tool call.

    Applies multiple search-replace operations to a file efficiently.
    All changes are validated before any are applied (atomic operation).

    Args:
        args: Dictionary containing 'path' and 'changes' arguments

    Returns:
        Success message with details of applied changes, or error message
    """
    path = args.get("path")
    changes = args.get("changes")

    if not path:
        return "Error: 'path' argument is required for patch_file."

    if not changes:
        return "Error: 'changes' argument is required for patch_file."

    if not isinstance(changes, list) or len(changes) == 0:
        return "Error: 'changes' must be a non-empty array of change operations."

    # Validate path
    allow_absolute = args.get("__internal_allow_absolute", False)
    is_valid, result = self._validate_path(path, allow_absolute)
    if not is_valid:
        return result

    resolved_path = result

    try:
        # Check if file exists
        if not os.path.exists(resolved_path):
            return f"Error: File '{path}' does not exist."

        if not os.path.isfile(resolved_path):
            return f"Error: '{path}' is not a file."

        # Read the entire file
        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except UnicodeDecodeError:
            return f"Error: File '{path}' is not a text file or uses an unsupported encoding."

        # Keep track of content as we apply changes
        current_content = original_content
        applied_changes = []

        # Validate and apply each change
        for idx, change in enumerate(changes, 1):
            if not isinstance(change, dict):
                return f"Error: Change #{idx} is not a valid object."

            search_text = change.get("search")
            replace_text = change.get("replace")
            occurrence = change.get("occurrence")

            if search_text is None:
                return f"Error: Change #{idx} is missing required 'search' field."

            if replace_text is None:
                return f"Error: Change #{idx} is missing required 'replace' field."

            if not isinstance(search_text, str):
                return f"Error: Change #{idx} has non-string 'search' field."

            if not isinstance(replace_text, str):
                return f"Error: Change #{idx} has non-string 'replace' field."

            if occurrence is not None:
                if not isinstance(occurrence, int) or occurrence < 1:
                    return f"Error: Change #{idx} has invalid 'occurrence' field. Must be a positive integer."

            # Count occurrences of search text
            count = current_content.count(search_text)

            if count == 0:
                return (
                    f"Error: Change #{idx} failed - search text not found in file.\n"
                    f"Search text: {repr(search_text[:100])}{'...' if len(search_text) > 100 else ''}\n"
                    f"Hint: The text may have already been changed by a previous operation, "
                    f"or it may not exist in the file."
                )

            if occurrence is None:
                # No occurrence specified - search text must be unique
                if count > 1:
                    return (
                        f"Error: Change #{idx} failed - search text appears {count} times in file.\n"
                        f"Search text: {repr(search_text[:100])}{'...' if len(search_text) > 100 else ''}\n"
                        f"Please specify which occurrence to replace using the 'occurrence' field (1-{count})."
                    )
                # Unique match - apply the change
                current_content = current_content.replace(search_text, replace_text, 1)
                applied_changes.append(f"  {idx}. Replaced unique occurrence")
            else:
                # Occurrence specified
                if occurrence > count:
                    return (
                        f"Error: Change #{idx} failed - requested occurrence {occurrence} but search text "
                        f"only appears {count} time{'s' if count != 1 else ''} in file.\n"
                        f"Search text: {repr(search_text[:100])}{'...' if len(search_text) > 100 else ''}"
                    )

                # Find and replace the specific occurrence
                parts = current_content.split(search_text)
                if len(parts) < occurrence + 1:
                    return f"Error: Change #{idx} failed - internal error splitting text."

                # Reconstruct with the replacement at the specific occurrence
                new_parts = []
                for i, part in enumerate(parts):
                    new_parts.append(part)
                    if i < len(parts) - 1:
                        if i == occurrence - 1:
                            new_parts.append(replace_text)
                        else:
                            new_parts.append(search_text)

                current_content = ''.join(new_parts)
                applied_changes.append(f"  {idx}. Replaced occurrence {occurrence} of {count}")

        # All changes validated and applied successfully - write the file
        try:
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(current_content)
        except Exception as e:
            # Attempt to restore original content if write fails
            try:
                with open(resolved_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                return f"Error: Failed to write patched file, original restored: {type(e).__name__}: {e}"
            except Exception:
                return f"Error: Failed to write patched file AND failed to restore original: {type(e).__name__}: {e}"

        # Calculate statistics
        original_lines = original_content.count('\n') + 1
        new_lines = current_content.count('\n') + 1
        line_diff = new_lines - original_lines
        size_diff = len(current_content) - len(original_content)

        # Build success message
        success_msg = f"File '{path}' patched successfully.\n"
        success_msg += f"Applied {len(applied_changes)} change{'s' if len(applied_changes) != 1 else ''}:\n"
        success_msg += '\n'.join(applied_changes)
        success_msg += f"\n\nFile statistics:"
        success_msg += f"\n  Lines: {original_lines} → {new_lines} ({line_diff:+d})"
        success_msg += f"\n  Size: {len(original_content)} → {len(current_content)} bytes ({size_diff:+d})"

        return success_msg

    except Exception as e:
        return f"Error patching file '{path}': {type(e).__name__}: {e}"


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
Example 1: Simple single replacement
{
    "path": "config.py",
    "changes": [
        {
            "search": "DEBUG = True",
            "replace": "DEBUG = False"
        }
    ]
}

Example 2: Multiple changes in sequence
{
    "path": "src/server.py",
    "changes": [
        {
            "search": "def old_function():",
            "replace": "def new_function():"
        },
        {
            "search": "old_function()",
            "replace": "new_function()"
        }
    ]
}

Example 3: Handling duplicate text with occurrence
{
    "path": "tests/test_api.py",
    "changes": [
        {
            "search": "assert result == expected",
            "replace": "assert result == expected, f\\"Got {result}\\"",
            "occurrence": 2
        }
    ]
}

Example 4: Multi-line replacement
{
    "path": "database.py",
    "changes": [
        {
            "search": "def connect():\\n    return sqlite3.connect('db.sqlite')",
            "replace": "def connect():\\n    conn = sqlite3.connect('db.sqlite')\\n    conn.row_factory = sqlite3.Row\\n    return conn"
        }
    ]
}

Example 5: Deleting content (empty replace)
{
    "path": "README.md",
    "changes": [
        {
            "search": "## TODO\\n- Add tests\\n- Write docs\\n\\n",
            "replace": ""
        }
    ]
}
"""
