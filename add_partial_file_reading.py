#!/usr/bin/env python3
"""
Add partial file reading capability to builtin.read_file tool.
This enhancement allows reading specific line ranges from files, reducing context usage.
"""

# First, let's read the current builtin.py file to understand its structure
from pathlib import Path

builtin_path = Path(__file__).parent / "mcp_client_for_ollama/tools/builtin.py"

with open(builtin_path, 'r') as f:
    content = f.read()

# Find and replace the read_file_tool definition
old_tool_def = '''        read_file_tool = Tool(
            name="builtin.read_file",
            description="Read the contents of a file. Path must be relative to the current working directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file to read."
                    }
                },
                "required": ["path"]
            }
        )'''

new_tool_def = '''        read_file_tool = Tool(
            name="builtin.read_file",
            description=(
                "Read the contents of a file. Path must be relative to the current working directory. "
                "Supports partial file reading with offset and limit parameters for efficient handling of large files. "
                "Returns content with line numbers (cat -n format)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file to read."
                    },
                    "offset": {
                        "type": "integer",
                        "description": (
                            "The line number to start reading from (1-indexed). "
                            "If not specified, reads from the beginning of the file. "
                            "Example: offset=50 starts reading from line 50."
                        ),
                        "minimum": 1
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            "The maximum number of lines to read. "
                            "If not specified, reads all lines from offset to end of file. "
                            "Useful for reading large files in chunks. "
                            "Example: offset=1, limit=100 reads lines 1-100."
                        ),
                        "minimum": 1
                    }
                },
                "required": ["path"]
            }
        )'''

# Replace the tool definition
content = content.replace(old_tool_def, new_tool_def)

# Now update the _handle_read_file implementation
old_impl = '''    def _handle_read_file(self, args: Dict[str, Any]) -> str:
        """Handles the 'read_file' tool call."""
        path = args.get("path")
        if not path:
            return (
                "Error: 'path' argument is required for read_file.\\n"
                "Example: {\\"path\\": \\"src/main.py\\"}"
            )

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)

        # Special case: Allow reading the config file even if it's an absolute path
        # This is needed because get_config_path returns an absolute path
        if not allow_absolute and os.path.isabs(path):
            try:
                from mcp_client_for_ollama.utils.constants import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE
                config_file = os.path.abspath(os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE))
                if os.path.abspath(path) == config_file:
                    allow_absolute = True
            except Exception:
                pass  # If we can't determine config path, continue with normal validation

        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            if not os.path.exists(resolved_path):
                return (
                    f"Error: File '{path}' does not exist.\\n"
                    f"💡 Tips:\\n"
                    f"  - Verify the path is correct\\n"
                    f"  - Use builtin.list_files to see available files\\n"
                    f"  - Check if the file is in a subdirectory"
                )

            if not os.path.isfile(resolved_path):
                return (
                    f"Error: '{path}' exists but is not a file (it's a directory).\\n"
                    "💡 Tips:\\n"
                    "  - Use builtin.list_files to read directory contents\\n"
                    "  - Specify the actual file path within the directory"
                )

            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()

            file_size = len(content)
            return f"✓ File '{path}' read successfully. Size: {file_size} bytes\\n\\nContent:\\n{content}"'''

new_impl = '''    def _handle_read_file(self, args: Dict[str, Any]) -> str:
        """Handles the 'read_file' tool call with optional partial reading support."""
        path = args.get("path")
        offset = args.get("offset")  # 1-indexed line number to start from
        limit = args.get("limit")    # Number of lines to read

        if not path:
            return (
                "Error: 'path' argument is required for read_file.\\n"
                "Example: {\\"path\\": \\"src/main.py\\"}\\n"
                "Example with partial read: {\\"path\\": \\"src/main.py\\", \\"offset\\": 50, \\"limit\\": 100}"
            )

        # Validate offset and limit if provided
        if offset is not None and offset < 1:
            return "Error: 'offset' must be a positive integer (1-indexed line number)."

        if limit is not None and limit < 1:
            return "Error: 'limit' must be a positive integer (number of lines to read)."

        # Check for internal-only parameter to allow absolute paths
        allow_absolute = args.get("__internal_allow_absolute", False)

        # Special case: Allow reading the config file even if it's an absolute path
        # This is needed because get_config_path returns an absolute path
        if not allow_absolute and os.path.isabs(path):
            try:
                from mcp_client_for_ollama.utils.constants import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE
                config_file = os.path.abspath(os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE))
                if os.path.abspath(path) == config_file:
                    allow_absolute = True
            except Exception:
                pass  # If we can't determine config path, continue with normal validation

        is_valid, result = self._validate_path(path, allow_absolute)
        if not is_valid:
            return result

        resolved_path = result

        try:
            if not os.path.exists(resolved_path):
                return (
                    f"Error: File '{path}' does not exist.\\n"
                    f"💡 Tips:\\n"
                    f"  - Verify the path is correct\\n"
                    f"  - Use builtin.list_files to see available files\\n"
                    f"  - Check if the file is in a subdirectory"
                )

            if not os.path.isfile(resolved_path):
                return (
                    f"Error: '{path}' exists but is not a file (it's a directory).\\n"
                    "💡 Tips:\\n"
                    "  - Use builtin.list_files to read directory contents\\n"
                    "  - Specify the actual file path within the directory"
                )

            # Read file with partial reading support
            with open(resolved_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Calculate the slice range
            if offset is None:
                start_line = 0  # 0-indexed for Python slicing
            else:
                start_line = offset - 1  # Convert 1-indexed to 0-indexed

            if limit is None:
                end_line = total_lines
            else:
                end_line = start_line + limit

            # Validate range
            if start_line >= total_lines:
                return (
                    f"Error: offset={offset} is beyond the end of the file.\\n"
                    f"File '{path}' has {total_lines} lines.\\n"
                    f"💡 Tip: Use offset between 1 and {total_lines}"
                )

            # Extract the requested lines
            selected_lines = lines[start_line:end_line]
            actual_end = min(end_line, total_lines)

            # Format output with line numbers (cat -n style)
            numbered_lines = []
            for i, line in enumerate(selected_lines, start=start_line + 1):
                # Remove trailing newline for display, add back for consistent formatting
                line_content = line.rstrip('\\n')
                numbered_lines.append(f"{i:6d}→{line_content}")

            content_with_numbers = '\\n'.join(numbered_lines)

            # Build response message
            if offset is None and limit is None:
                # Full file read
                file_size = sum(len(line) for line in lines)
                return (
                    f"✓ File '{path}' read successfully. Size: {file_size} bytes, {total_lines} lines\\n\\n"
                    f"Content:\\n{content_with_numbers}"
                )
            else:
                # Partial file read
                display_start = start_line + 1
                display_end = start_line + len(selected_lines)
                return (
                    f"✓ File '{path}' read successfully (lines {display_start}-{display_end} of {total_lines})\\n\\n"
                    f"Content:\\n{content_with_numbers}"
                )'''

# Replace the implementation
content = content.replace(old_impl, new_impl)

# Write the updated content back
with open(builtin_path, 'w') as f:
    f.write(content)

print("✓ Successfully enhanced builtin.read_file with partial reading capability")
print("✓ Added parameters: offset (line to start from), limit (number of lines)")
print("✓ Output now includes line numbers (cat -n format)")
print(f"✓ Updated file: {builtin_path}")
