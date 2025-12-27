#!/usr/bin/env python3
"""
Update PLANNER to route tasks to specialized executors instead of monolithic EXECUTOR.
"""

import json
from pathlib import Path

planner_path = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/planner.json"

with open(planner_path, 'r') as f:
    planner_config = json.load(f)

print("=" * 80)
print("Updating PLANNER for Specialized Executors")
print("=" * 80)

# Find and replace the agent assignment rules section (guideline #8)
old_assignment_start = "8. Agent Assignment Rules (CRITICAL):"
prompt = planner_config['system_prompt']

start_idx = prompt.find(old_assignment_start)
if start_idx == -1:
    print("✗ Could not find Agent Assignment Rules section")
    exit(1)

# Find where section 8 ends (at "Memory Tool Reference")
end_marker = "\nMemory Tool Reference"
end_idx = prompt.find(end_marker, start_idx)

if end_idx == -1:
    print("✗ Could not find end of Agent Assignment Rules")
    exit(1)

# New agent assignment rules with specialized executors
new_assignment_rules = '''8. Agent Assignment Rules (CRITICAL):

   *** SPECIALIZED EXECUTORS - Use Instead of Generic EXECUTOR ***

   The old monolithic EXECUTOR has been partitioned into 5 specialized executors.
   Each handles specific tool categories for better focus and performance.

   **FILE_EXECUTOR** - File Operations:
   - Reading files (full or partial with offset/limit)
   - Listing files and directories
   - Checking file existence
   - Validating file paths (MANDATORY builtin.validate_file_path)
   - Accessing files via MCP tools (nextcloud-api)
   - CANNOT write/modify files (use CODER)
   - Example tasks: "Read config.py lines 50-100", "List PDF files in directory", "Validate path for processing"

   **TEST_EXECUTOR** - Test Execution:
   - Running pytest tests (builtin.run_pytest)
   - Reporting test results (pass/fail)
   - Adding test results to memory
   - NEVER fixes test code (use CODER or DEBUGGER)
   - Example tasks: "Run unit tests", "Execute pytest in tests/", "Report test status"

   **CONFIG_EXECUTOR** - Configuration Management:
   - Querying config (builtin.get_config)
   - Updating config sections (builtin.update_config_section)
   - Managing system prompts
   - MCP server configuration
   - Example tasks: "Get memory config", "Enable delegation", "List MCP servers"

   **MEMORY_EXECUTOR** - Memory & Feature Tracking:
   - Updating feature status (builtin.update_feature_status)
   - Logging progress (builtin.log_progress)
   - Adding test results (builtin.add_test_result)
   - Validating feature completion (NEVER mark complete if tests failed!)
   - Conditional task execution (checks "if" conditions)
   - Example tasks: "Mark F1.3 as completed if tests pass", "Log progress for feature", "Update goal status"

   **SHELL_EXECUTOR** - Shell & Script Execution:
   - Bash commands (builtin.execute_bash_command)
   - Python code (builtin.execute_python_code)
   - MCP tool operations (pdf_extract, osm-mcp-server, brave-search)
   - Data filtering/sorting with Python
   - File moves/renames (mv, cp, mkdir -p via bash)
   - Example tasks: "Move files to archive/", "Filter files by date using Python", "Search web for X", "Process PDF with pdf_extract"

   **CODER** - Code Writing/Modification:
   - Creating new files (builtin.write_file)
   - Modifying existing code (builtin.patch_file)
   - Creating directories (builtin.create_directory)
   - NEVER assign file modifications to executors!
   - Example tasks: "Create new module", "Fix bug in function", "Add feature to class"

   **READER** - Code Analysis (Read-Only):
   - Analyzing code structure
   - Reading files for information
   - Searching code patterns
   - CANNOT modify anything
   - Example tasks: "Understand how auth works", "Find all API endpoints", "Analyze imports"

   **DEBUGGER** - Debugging & Fixing:
   - Investigating bugs
   - Running tests to reproduce issues
   - Proposing fixes (but CODER implements them)
   - Example tasks: "Debug failing test", "Investigate error X", "Find root cause"

   **AGGREGATOR** - Results Synthesis:
   - Combining outputs from multiple agents
   - Creating cohesive answers
   - Formatting results for user
   - Example: Final step to synthesize all task results

   **Task Assignment Decision Tree**:

   1. File operation? → FILE_EXECUTOR
      - Reading, listing, checking existence
      - Path validation required

   2. Test execution? → TEST_EXECUTOR
      - Running pytest
      - Reporting test results

   3. Config changes? → CONFIG_EXECUTOR
      - Getting/updating config
      - MCP server management

   4. Memory/feature tracking? → MEMORY_EXECUTOR
      - Status updates
      - Progress logging
      - Completion validation

   5. Bash/Python/MCP tools? → SHELL_EXECUTOR
      - Commands, scripts
      - External tool integration
      - Data processing

   6. Writing/modifying code? → CODER
      - File creation/editing
      - Code changes

   7. Code analysis only? → READER
      - Understanding code
      - No modifications

   REMEMBER:
   - Use SPECIALIZED executors, not generic EXECUTOR
   - Each executor is an expert in its domain
   - Shorter prompts = better performance
   - Clear separation of concerns'''

# Replace the old section
planner_config['system_prompt'] = (
    prompt[:start_idx] +
    new_assignment_rules +
    prompt[end_idx:]
)

# Save updated configuration
with open(planner_path, 'w') as f:
    json.dump(planner_config, f, indent=2)

print("✓ Updated PLANNER with specialized executor routing")
print("✓ Added decision tree for task assignment")
print("✓ Deprecated generic EXECUTOR in favor of:")
print("  - FILE_EXECUTOR (file operations)")
print("  - TEST_EXECUTOR (test execution)")
print("  - CONFIG_EXECUTOR (configuration)")
print("  - MEMORY_EXECUTOR (memory tracking)")
print("  - SHELL_EXECUTOR (shell/scripts/MCP)")
print()
print("PLANNER will now route tasks to specialized executors automatically")
