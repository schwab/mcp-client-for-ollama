#!/usr/bin/env python3
"""
Update READER and EXECUTOR agent prompts to mention partial file reading capability.
"""

import json
from pathlib import Path

agents_dir = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions"

# Update READER agent
reader_path = agents_dir / "reader.json"
with open(reader_path, 'r') as f:
    reader_config = json.load(f)

# Add partial file reading info to READER's capabilities section
old_capabilities = "Capabilities:\n- Read file contents from working directory"
new_capabilities = """Capabilities:
- Read file contents from working directory
  * builtin.read_file supports partial reading with offset/limit parameters
  * For large files: Use offset (line number to start) and limit (lines to read)
  * Example: {"path": "large_file.py", "offset": 100, "limit": 50} reads lines 100-150
  * Output includes line numbers for easy navigation
  * Reduces context usage by reading only needed sections"""

reader_config['system_prompt'] = reader_config['system_prompt'].replace(
    old_capabilities,
    new_capabilities
)

with open(reader_path, 'w') as f:
    json.dump(reader_config, f, indent=2)

print(f"✓ Updated READER agent: {reader_path}")

# Update EXECUTOR agent
executor_path = agents_dir / "executor.json"
with open(executor_path, 'r') as f:
    executor_config = json.load(f)

# Add partial file reading info to EXECUTOR's Tool Selection section
old_tool_selection = "Tool Selection:\n- LOCAL files -> builtin.list_files, builtin.read_file, builtin.file_exists"
new_tool_selection = """Tool Selection:
- LOCAL files -> builtin.list_files, builtin.read_file, builtin.file_exists
  * builtin.read_file supports partial reading: {"path": "file.py", "offset": 50, "limit": 100}
  * Use offset/limit for large files to reduce context usage
  * Returns content with line numbers for easy reference"""

executor_config['system_prompt'] = executor_config['system_prompt'].replace(
    old_tool_selection,
    new_tool_selection
)

with open(executor_path, 'w') as f:
    json.dump(executor_config, f, indent=2)

print(f"✓ Updated EXECUTOR agent: {executor_path}")

print("\n✓ Both agents now aware of partial file reading capability")
print("  - offset: Line number to start reading (1-indexed)")
print("  - limit: Number of lines to read")
print("  - Output includes line numbers (cat -n format)")
