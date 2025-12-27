#!/usr/bin/env python3
"""
Update EXECUTOR to require builtin.validate_file_path for file operations.
"""

import json
from pathlib import Path

executor_path = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/executor.json"

with open(executor_path, 'r') as f:
    executor_config = json.load(f)

# Replace the PATH HANDLING PROTOCOL with a simpler version that requires validate_file_path
old_protocol_start = "*** PATH HANDLING PROTOCOL - READ THIS FIRST ***"
old_protocol_end = "This protocol is MANDATORY for ALL tasks involving file paths."

prompt = executor_config['system_prompt']

start_idx = prompt.find(old_protocol_start)
if start_idx == -1:
    print("✗ Could not find PATH HANDLING PROTOCOL")
    exit(1)

# Find the end of the protocol
end_marker = "\n\n\nCapabilities:"
end_idx = prompt.find(end_marker, start_idx)

if end_idx == -1:
    print("✗ Could not find end of PATH HANDLING PROTOCOL")
    exit(1)

# New simplified protocol that requires validate_file_path
new_protocol = '''*** PATH LOCKING PROTOCOL - MANDATORY FOR FILE OPERATIONS ***

⚠️ CRITICAL: For ANY task involving file paths, you MUST follow this protocol EXACTLY:

STEP 1: CALL builtin.validate_file_path FIRST
- Extract the EXACT file path from your task description (copy character-for-character)
- Call builtin.validate_file_path with:
  * path: The exact path from task description
  * task_description: Your full task description
- This tool will return the LOCKED path you must use
- Example:
  Task: "Process /home/user/docs/file.pdf using pdf_extract.process_document"
  First action: builtin.validate_file_path(path="/home/user/docs/file.pdf", task_description="Process...")
  Tool returns: "✓ PATH LOCKED: /home/user/docs/file.pdf"

STEP 2: USE ONLY THE LOCKED PATH
- The path returned by validate_file_path is NOW LOCKED
- Use this EXACT path for ALL subsequent file operations
- NEVER modify, shorten, or change this path
- NEVER use any other path variations
- NEVER use placeholder paths like "/path/to/file.pdf"

STEP 3: IF OPERATIONS FAIL
- Report the error using the LOCKED path
- DO NOT try different path variations
- DO NOT hallucinate new paths
- DO NOT use paths from error messages
- State: "Tool failed with LOCKED path: [path]. Error: [error]"

WHY THIS IS CRITICAL:
- Prevents path hallucination across iterations
- Makes path extraction explicit and verifiable
- Ensures you use the exact path from your task description
- Stops path drift (using "/path/to/" or "file1.pdf" instead of actual paths)

EXAMPLES:

✅ CORRECT USAGE:
  Task: "Import file Daily/October/20251006_ratecon_tql.pdf"
  Action 1: builtin.validate_file_path(path="Daily/October/20251006_ratecon_tql.pdf", task_description="Import file...")
  Response: "✓ PATH LOCKED: /home/mcstar/Nextcloud/VTCLLC/Daily/October/20251006_ratecon_tql.pdf"
  Action 2: pdf_extract.process_document(file_path="/home/mcstar/Nextcloud/VTCLLC/Daily/October/20251006_ratecon_tql.pdf")
  Action 3 (if needed): Use the SAME locked path for any other operations

❌ WRONG - Skip validate_file_path:
  Task: "Import file Daily/October/20251006_ratecon_tql.pdf"
  Action: pdf_extract.process_document(file_path="/path/to/20251006_ratecon_tql.pdf")  ← HALLUCINATED PATH!

❌ WRONG - Change path after validation:
  Task: "Import file Daily/October/20251006_ratecon_tql.pdf"
  Action 1: builtin.validate_file_path(...) returns "/abs/path/20251006_ratecon_tql.pdf"
  Action 2: pdf_extract.process_document(file_path="20251006_ratecon_tql.pdf")  ← CHANGED THE PATH!

❌ WRONG - Use different path in later iterations:
  Iteration 1: Use "/abs/path/file.pdf"
  Iteration 2: Use "/path/to/file.pdf"  ← PATH DRIFT! Should use same locked path

REMEMBER:
1. ALWAYS call validate_file_path FIRST for file tasks
2. NEVER skip this step
3. Use ONLY the locked path returned
4. NEVER change or modify the locked path


'''

# Replace the old protocol
executor_config['system_prompt'] = (
    prompt[:start_idx] +
    new_protocol +
    prompt[end_idx:]
)

# Also add validate_file_path to the default_tools list
if "builtin.validate_file_path" not in executor_config['default_tools']:
    # Insert it right after builtin.read_file
    read_file_idx = executor_config['default_tools'].index("builtin.read_file")
    executor_config['default_tools'].insert(read_file_idx + 1, "builtin.validate_file_path")
    print("✓ Added builtin.validate_file_path to EXECUTOR's default_tools")

# Save the updated configuration
with open(executor_path, 'w') as f:
    json.dump(executor_config, f, indent=2)

print("✓ Successfully updated EXECUTOR with PATH LOCKING PROTOCOL")
print("✓ EXECUTOR now REQUIRES calling builtin.validate_file_path before file operations")
print("✓ Simplified protocol focuses on mandatory validate_file_path usage")
