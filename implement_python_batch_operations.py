#!/usr/bin/env python3
"""
Implement Option B: Single-Task Python Batch Operations (v0.28.5)

THE SOLUTION TO DATA PASSING PROBLEM:
Instead of fighting to pass data between tasks, use SHELL_EXECUTOR with Python
to do EVERYTHING in one task execution.

Example:
User: "get October files, delete each"

Instead of:
  task_1: Get list (returns data)
  task_2: Delete each (can't access task_1 data!) ❌

Do:
  task_1: Use SHELL_EXECUTOR with Python to get AND delete in one execution ✅

Python can call MCP tools directly, so everything stays in one agent's context!
"""

import json
from pathlib import Path

planner_file = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/planner.json"
shell_executor_file = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/shell_executor.json"

print("=" * 80)
print("Implementing Python Batch Operations (v0.28.5)")
print("=" * 80)
print()
print("Strategy: Use SHELL_EXECUTOR with Python for all batch operations")
print("  - No data passing needed")
print("  - Everything in one execution")
print("  - Python can call MCP tools in loops")
print()

# ============================================================================
# UPDATE PLANNER
# ============================================================================

print("1. Updating PLANNER...")

with open(planner_file, 'r') as f:
    planner_config = json.load(f)

planner_prompt = planner_config["system_prompt"]

# Find the SCENARIO 2 section and make Python batch the PRIMARY recommendation
old_scenario_2 = """   *** SCENARIO 2: Files Discovered from Query (NEW!) ***

   User: "get the list of rate con files for October 2025. Delete each of them."
   (Files don't exist yet - will be discovered by the query)

   ❌ WRONG (trace 20251226_145639):
     task_1: "Get the list of rate con files for October 2025"
     task_2: "Delete each rate con file from the business database" ← Can't specify files!

   Problem: PLANNER doesn't know which files exist at planning time!

   ✅ RIGHT (single task with iteration):
     task_1: "Use SHELL_EXECUTOR with Python to:
           (1) call pdf_extract.lookup_rate_cons_by_month(year=2025, month=10) to get files,
           (2) loop through results and call pdf_extract.delete_file(file_name=...) for each filename"

   OR EVEN BETTER (if batch delete tool exists):
     task_1: "Use pdf_extract.batch_delete_rate_cons(year=2025, month=10) to delete all October 2025 rate cons in one operation"

   ⚠️  CRITICAL DISTINCTION:
   - User already knows files → Create separate delete tasks per file
   - Files discovered from query → Create SINGLE task that queries AND deletes
   - NEVER create task_2 that says "delete each file" without filenames!
   - For query-based batch delete, use SHELL_EXECUTOR with Python loop"""

new_scenario_2 = """   *** SCENARIO 2: Files Discovered from Query - USE PYTHON BATCH! ***

   User: "get the list of rate con files for October 2025. Delete each of them."
   (Files don't exist yet - will be discovered by the query)

   ❌ WRONG (trace 20251226_145639, 20251226_150915):
     task_1: "Get the list of rate con files for October 2025"
     task_2: "Delete each rate con file from the business database" ← Can't specify files!

   Problem: PLANNER doesn't know which files exist at planning time!
   Result: task_2 hallucinates filenames, nothing gets deleted!

   ✅ RIGHT (PREFERRED - Python batch operation):
     task_1: "Use SHELL_EXECUTOR to execute this Python code:
             ```python
             # Get October 2025 rate cons
             result = tools.call('pdf_extract.lookup_rate_cons_by_month', year=2025, month=10)
             files = result.get('files', [])

             # Delete each file
             deleted_count = 0
             for file_data in files:
                 filename = file_data.get('filename')
                 tools.call('pdf_extract.delete_file', file_name=filename)
                 deleted_count += 1

             print(f'Successfully deleted {deleted_count} files')
             ```"

   WHY THIS WORKS:
   - Everything happens in ONE agent execution
   - No data passing between tasks needed
   - Python keeps file list in memory
   - SHELL_EXECUTOR can call MCP tools directly
   - Fast and reliable!

   TEMPLATE FOR BATCH OPERATIONS:
   ```
   Use SHELL_EXECUTOR to execute Python code:
   1. Call lookup/query tool to get items
   2. Loop through items
   3. Call processing tool for each item
   4. Print summary of what was done
   ```

   ⚠️  CRITICAL: For "get list, process each" queries, ALWAYS use Python batch!"""

if old_scenario_2 in planner_prompt:
    planner_prompt = planner_prompt.replace(old_scenario_2, new_scenario_2)
    planner_config["system_prompt"] = planner_prompt

    with open(planner_file, 'w') as f:
        json.dump(planner_config, f, indent=2)

    print("  ✓ Updated PLANNER with Python batch operation guidance")
else:
    print("  ⚠ Could not find SCENARIO 2 marker")

# ============================================================================
# UPDATE SHELL_EXECUTOR
# ============================================================================

print("2. Updating SHELL_EXECUTOR...")

with open(shell_executor_file, 'r') as f:
    shell_config = json.load(f)

shell_prompt = shell_config["system_prompt"]

# Add Python batch operations guidance at the top
python_batch_section = """
*** PYTHON BATCH OPERATIONS - PREFERRED FOR LOOPS ***

When your task involves calling MCP tools in a loop (e.g., "delete each file", "process each item"):

✅ USE PYTHON with tools.call() for batch operations:

```python
# Example: Get list and delete each file
result = tools.call('pdf_extract.lookup_rate_cons_by_month', year=2025, month=10)
files = result.get('files', [])

for file_data in files:
    filename = file_data.get('filename')
    tools.call('pdf_extract.delete_file', file_name=filename)
    print(f'Deleted {filename}')

print(f'Total deleted: {len(files)}')
```

HOW TO CALL MCP TOOLS IN PYTHON:
- Use: tools.call('tool_name', param1=value1, param2=value2)
- Returns: Dictionary with tool result
- Access result fields: result.get('field_name')

EXAMPLE PATTERNS:

1. **Lookup and Process**:
```python
items = tools.call('lookup_tool', param=value).get('items', [])
for item in items:
    tools.call('process_tool', item_id=item['id'])
```

2. **Batch Delete**:
```python
files = tools.call('list_files', directory='/path').get('files', [])
for f in files:
    tools.call('delete_file', file_name=f)
```

3. **Check and Update**:
```python
records = tools.call('get_records').get('records', [])
for record in records:
    if record['status'] == 'pending':
        tools.call('update_status', id=record['id'], status='processed')
```

WHY THIS IS BETTER THAN BASH:
- Keep data in Python variables (no need to parse bash output)
- Natural loops and conditionals
- Direct tool access with tools.call()
- Easy to handle errors and edge cases

"""

# Insert Python batch section at the beginning of the system prompt
shell_config["system_prompt"] = python_batch_section + shell_prompt

with open(shell_executor_file, 'w') as f:
    json.dump(shell_config, f, indent=2)

print("  ✓ Updated SHELL_EXECUTOR with Python batch examples")

print()
print("=" * 80)
print("Summary of Changes")
print("=" * 80)
print()
print("PLANNER:")
print("  - Made Python batch operations the PREFERRED approach for SCENARIO 2")
print("  - Added complete Python code example")
print("  - Emphasized: 'For get list, process each - ALWAYS use Python batch'")
print()
print("SHELL_EXECUTOR:")
print("  - Added 'PYTHON BATCH OPERATIONS' section at top")
print("  - Showed how to call MCP tools with tools.call()")
print("  - Provided 3 example patterns (lookup+process, batch delete, check+update)")
print("  - Explained why Python is better than bash for batch ops")
print()
print("RESULT:")
print("  ✓ No data passing between tasks needed")
print("  ✓ Everything in one execution context")
print("  ✓ Fast and reliable")
print("  ✓ Python keeps intermediate data in memory")
print()
print("=" * 80)
print("Next: Bump version to 0.28.5 and rebuild")
print("=" * 80)
