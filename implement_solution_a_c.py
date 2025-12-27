#!/usr/bin/env python3
"""
Implement Solution A (Structured Path Locking) and Solution C (Strengthen PLANNER guideline #3c)
for v0.27.1
"""

import json
from pathlib import Path

print("=" * 80)
print("Implementing Solution A: Structured Path Locking with builtin.validate_file_path")
print("=" * 80)

# Read the builtin.py file
builtin_path = Path(__file__).parent / "mcp_client_for_ollama/tools/builtin.py"
with open(builtin_path, 'r') as f:
    builtin_content = f.read()

# Step 1: Add validate_file_path tool definition after list_directories_tool
# Find the insertion point (after list_directories_tool definition)
insertion_marker = '''        list_directories_tool = Tool(
            name="builtin.list_directories",
            description="List all subdirectories in a directory. Path must be relative to the current working directory. If no path is provided, lists directories in the current directory.",
            inputSchema={'''

# Find where list_directories_tool ends (find the next tool after it)
# We'll insert the new tool definition before file_exists_tool

new_tool_definition = '''
        validate_file_path_tool = Tool(
            name="builtin.validate_file_path",
            description=(
                "REQUIRED FIRST STEP for file operations: Extract and validate a file path from your task description. "
                "This tool locks the path and returns the validated absolute path that you MUST use for all subsequent file operations. "
                "Call this BEFORE any file operations (read_file, write_file, patch_file, file_exists, process_document, etc.). "
                "This prevents path hallucination and ensures you use the exact path from your task description."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "The exact file path extracted from your task description. "
                            "Copy it character-for-character from the task. "
                            "Can be absolute (starts with /) or relative to working directory."
                        )
                    },
                    "task_description": {
                        "type": "string",
                        "description": (
                            "Your complete task description. "
                            "This helps verify you extracted the path correctly."
                        )
                    }
                },
                "required": ["path", "task_description"]
            }
        )
'''

# Find file_exists_tool to insert before it
file_exists_marker = '''        file_exists_tool = Tool(
            name="builtin.file_exists",'''

if file_exists_marker in builtin_content:
    builtin_content = builtin_content.replace(
        file_exists_marker,
        new_tool_definition + "\n" + file_exists_marker
    )
    print("✓ Added validate_file_path tool definition")
else:
    print("✗ Could not find insertion point for tool definition")
    exit(1)

# Step 2: Add validate_file_path to the tools list
tools_list_marker = '''        tools = [
            set_prompt_tool, get_prompt_tool, execute_python_code_tool, execute_bash_command_tool, run_pytest_tool,
            read_file_tool, write_file_tool, patch_file_tool, list_files_tool, list_directories_tool,'''

tools_list_addition = '''        tools = [
            set_prompt_tool, get_prompt_tool, execute_python_code_tool, execute_bash_command_tool, run_pytest_tool,
            read_file_tool, validate_file_path_tool, write_file_tool, patch_file_tool, list_files_tool, list_directories_tool,'''

if tools_list_marker in builtin_content:
    builtin_content = builtin_content.replace(tools_list_marker, tools_list_addition)
    print("✓ Added validate_file_path to tools list")
else:
    print("✗ Could not find tools list")
    exit(1)

# Step 3: Add handler method for validate_file_path
# Find where to insert the handler (before _handle_read_file)
handler_insertion_point = '''    def _handle_read_file(self, args: Dict[str, Any]) -> str:
        """Handles the 'read_file' tool call with optional partial reading support."""'''

new_handler = '''    def _handle_validate_file_path(self, args: Dict[str, Any]) -> str:
        """Validates and locks a file path from the task description.

        This is a REQUIRED first step for file operations. It:
        1. Extracts the path from task description
        2. Validates it's correct (absolute or relative)
        3. Converts relative to absolute using working directory
        4. Returns the LOCKED path that must be used for all operations
        """
        path = args.get("path")
        task_desc = args.get("task_description", "")

        if not path:
            return (
                "Error: 'path' argument is required.\\n"
                "Extract the EXACT file path from your task description and provide it here.\\n"
                "Example: {\\"path\\": \\"/home/user/docs/file.pdf\\", \\"task_description\\": \\"...your task...\\"}"
            )

        # Validate the path
        is_valid, result = self._validate_path(path, allow_absolute=True)

        if not is_valid:
            return result

        resolved_path = result

        # Check if path exists (informational, not required)
        exists = os.path.exists(resolved_path)
        exists_msg = "✓ File exists" if exists else "⚠ File does not exist yet (will be created if you write to it)"

        # Return the locked path
        return (
            f"✓ PATH LOCKED: {resolved_path}\\n"
            f"\\n"
            f"Status: {exists_msg}\\n"
            f"\\n"
            f"CRITICAL: You MUST use this EXACT path for ALL subsequent file operations in this task.\\n"
            f"DO NOT modify, shorten, or change this path.\\n"
            f"DO NOT use any other path variations.\\n"
            f"\\n"
            f"For reference, your task was:\\n"
            f"{task_desc[:200]}{'...' if len(task_desc) > 200 else ''}\\n"
            f"\\n"
            f"Next: Use this locked path in your file operations (read_file, write_file, etc.)"
        )

    def _handle_read_file(self, args: Dict[str, Any]) -> str:
        """Handles the 'read_file' tool call with optional partial reading support."""'''

builtin_content = builtin_content.replace(handler_insertion_point, new_handler)
print("✓ Added _handle_validate_file_path handler")

# Step 4: Register the handler in _tool_handlers dictionary
# Find the handlers dictionary initialization
handlers_marker = '''        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], str]] = {
            "set_system_prompt": self._handle_set_system_prompt,
            "get_system_prompt": self._handle_get_system_prompt,
            "execute_python_code": self._handle_execute_python_code,
            "execute_bash_command": self._handle_execute_bash_command,
            "run_pytest": self._handle_run_pytest,
            "read_file": self._handle_read_file,'''

handlers_addition = '''        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], str]] = {
            "set_system_prompt": self._handle_set_system_prompt,
            "get_system_prompt": self._handle_get_system_prompt,
            "execute_python_code": self._handle_execute_python_code,
            "execute_bash_command": self._handle_execute_bash_command,
            "run_pytest": self._handle_run_pytest,
            "validate_file_path": self._handle_validate_file_path,
            "read_file": self._handle_read_file,'''

if handlers_marker in builtin_content:
    builtin_content = builtin_content.replace(handlers_marker, handlers_addition)
    print("✓ Added validate_file_path to handlers dictionary")
else:
    print("✗ Could not find handlers dictionary")
    exit(1)

# Write back the updated builtin.py
with open(builtin_path, 'w') as f:
    f.write(builtin_content)

print("✓ Successfully updated builtin.py with validate_file_path tool")
print()

print("=" * 80)
print("Implementing Solution C: Strengthening PLANNER Guideline #3c")
print("=" * 80)

# Read planner configuration
planner_path = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/planner.json"
with open(planner_path, 'r') as f:
    planner_config = json.load(f)

# Find and enhance guideline #3c
old_guideline_start = "3c. Include Complete Data Dependencies (CRITICAL - Data Passing Between Tasks):"

if old_guideline_start in planner_config['system_prompt']:
    # Replace the entire guideline #3c with a much stronger version

    # Find where #3c starts and ends (ends at guideline 4)
    prompt = planner_config['system_prompt']
    start_idx = prompt.find(old_guideline_start)
    end_marker = "\n4. Right-Size Tasks"
    end_idx = prompt.find(end_marker, start_idx)

    if start_idx != -1 and end_idx != -1:
        new_guideline_3c = '''3c. Include Complete Data Dependencies (CRITICAL - Data Passing Between Tasks):
   ⚠️  ABSOLUTE RULE: NEVER reference previous task outputs. Each task must include ALL data it needs.

   ❌ FORBIDDEN PATTERNS (These cause EXECUTOR to hallucinate):
   - "for each file name found in task_2" ← EXECUTOR can't access task_2 output!
   - "using the results from task_1" ← EXECUTOR can't access task_1 output!
   - "process the files from the previous task" ← EXECUTOR doesn't know which files!
   - "use the data gathered earlier" ← EXECUTOR doesn't have that data!
   - "with the information from task_X" ← EXECUTOR can't read task_X!

   WHY THIS IS CRITICAL:
   - Each agent execution is STATELESS and ISOLATED
   - Agents CANNOT access outputs from previous tasks
   - Task descriptions are the ONLY way to pass data
   - References like "from task_2" cause agents to HALLUCINATE placeholder data

   REAL EXAMPLE OF FAILURE (from trace 20251226_112028):
   ❌ WRONG (caused hallucination):
     task_2: "Extract file names from rate confirmations"  → Found: 20251003_ratecon_revised.pdf
     task_3: "Use pdf_extract.lookup_file_details to get details for each file name found in task_2"
     → EXECUTOR hallucinated: "Let's say the filenames are: file1.pdf, file2.pdf, file3.pdf"
     → Wasted 3 tool calls on non-existent files!

   ✅ RIGHT (includes actual data):
     task_2: "Extract file names from rate confirmations"  → Found: 20251003_ratecon_revised.pdf
     task_3: "Use pdf_extract.lookup_file_details(file_name='20251003_ratecon_revised.pdf')"
     → EXECUTOR uses the actual filename provided!

   BATCH OPERATIONS (Multiple Files):
   ❌ WRONG (reference to previous task):
     task_1: "List PDF files in /path/to/dir"
     task_2: "Process the files from task_1" ← Which files? EXECUTOR will hallucinate!

   ✅ RIGHT (complete file list):
     task_1: "List PDF files in /path/to/dir"
     task_2: "Process these files: pdf_extract.batch_process(['/path/to/dir/file1.pdf', '/path/to/dir/file2.pdf', '/path/to/dir/file3.pdf'])"

   FILE PATH REQUIREMENTS:
   - ALWAYS use ABSOLUTE paths (start with /)
   - ALWAYS include the COMPLETE path in EVERY task that uses it
   - User provides relative path? YOU convert to absolute using working directory
   - NEVER create a task to "convert path" - YOU do it inline

   PARAMETER VALUES (Not Names):
   ❌ WRONG: "Check file using pdf_extract.check_file_exists(file_path)" ← file_path undefined!
   ✅ RIGHT: "Check file using pdf_extract.check_file_exists(file_path='/abs/path/file.pdf')"

   WHEN YOU MUST INCLUDE COMPLETE DATA:
   1. File paths → Include full absolute path in every task
   2. File lists → Include complete array of all file paths
   3. IDs → Include explicit IDs (feature_id='F1.3', goal_id='G1')
   4. Configuration → Include complete config objects
   5. Query results → Include actual data, not references

   REMEMBER:
   - Think of each task as a STANDALONE unit that will execute in ISOLATION
   - If task_2 depends on task_1, task_2 must include the DATA (not reference to task_1)
   - "Task dependencies" mean execution order, NOT data access
   - When in doubt: Include the complete data explicitly

'''

        # Replace the old guideline with the new one
        planner_config['system_prompt'] = (
            prompt[:start_idx] +
            new_guideline_3c +
            prompt[end_idx:]
        )

        print("✓ Enhanced PLANNER guideline #3c with stronger examples and emphasis")
    else:
        print("✗ Could not find guideline #3c boundaries")
        exit(1)
else:
    print("✗ Could not find guideline #3c")
    exit(1)

# Save updated planner configuration
with open(planner_path, 'w') as f:
    json.dump(planner_config, f, indent=2)

print("✓ Successfully updated planner.json")
print()

print("=" * 80)
print("Summary of Changes")
print("=" * 80)
print("Solution A - Structured Path Locking:")
print("  ✓ Added builtin.validate_file_path tool")
print("  ✓ Tool extracts path from task description")
print("  ✓ Tool validates and returns LOCKED absolute path")
print("  ✓ EXECUTOR must call this BEFORE file operations")
print()
print("Solution C - Strengthened PLANNER:")
print("  ✓ Enhanced guideline #3c with:")
print("    - Clear FORBIDDEN patterns")
print("    - Real failure example from trace")
print("    - Emphasis on stateless/isolated execution")
print("    - Complete data requirements")
print()
print("Next step: Update EXECUTOR to require validate_file_path usage")
