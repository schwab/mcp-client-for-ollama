#!/usr/bin/env python3
"""Update PLANNER configuration for v0.26.30 - Add data dependency guideline."""

import json
from pathlib import Path

# Read current configuration
planner_path = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/planner.json"
with open(planner_path, 'r') as f:
    config = json.load(f)

# The new guideline text to insert after guideline #3a
new_guideline = """3c. Include Complete Data Dependencies (CRITICAL - Data Passing Between Tasks):
   ABSOLUTE RULE: When a task needs outputs from previous tasks, include the COMPLETE data in the task description - NEVER use references like "the first batch" or "the files from task_2".

   WHY THIS MATTERS: Agents executing later tasks CANNOT access outputs from previous tasks. Each task description must be completely self-contained.

   PATH CONVERSION (YOU do this, don't create a task for it):
   - If user provides relative path, YOU convert it to absolute - do NOT create a task to convert it
   - WRONG: Create task_1: "Convert Daily/October/file.pdf to absolute path"
   - RIGHT: Just use "/home/mcstar/Nextcloud/VTCLLC/Daily/October/file.pdf" in your task descriptions

   USE ACTUAL PATH VALUES (not parameter names):
   - Include the ACTUAL path string in task descriptions, not just "file_path" as a parameter name
   - CRITICAL WRONG EXAMPLES (parameter name without value):
     ✗ "Check if file exists using pdf_extract.check_file_exists(file_path)" - file_path is undefined!
     ✗ "Process document using pdf_extract.process_document(file_path, save_to_db=True)" - file_path is undefined!
     ✗ "Process the first batch of files" - which files? No file paths provided!
     ✗ "Use the files from task_2" - agent can't access task_2's output!

   - CRITICAL RIGHT EXAMPLES (parameter with actual value):
     ✓ "Check if file exists using pdf_extract.check_file_exists(file_path='/home/user/docs/report.pdf')"
     ✓ "Process document using pdf_extract.process_document(file_path='/home/user/docs/report.pdf', save_to_db=True)"
     ✓ "Process these files using pdf_extract.batch_process_documents(file_paths=['/home/user/docs/file1.pdf', '/home/user/docs/file2.pdf', '/home/user/docs/file3.pdf'])"

   BATCH OPERATIONS (file lists, groups of items):
   - When user requests batch processing (e.g., "process files in groups of 10"):
     1. Task 1: List/gather the files (EXECUTOR collects the data)
     2. Task 2 onwards: Include COMPLETE file path lists, NOT references

   - WRONG APPROACH (reference to previous task):
     task_1: "List PDF files in /path/to/dir"
     task_2: "Group the files from task_1 into batches of 10"
     task_3: "Process the first batch" ← Agent doesn't know which files!

   - RIGHT APPROACH (complete data in each task):
     task_1: "Use builtin.list_files(path='/path/to/dir', pattern='*.pdf') to gather all PDF files"
     task_2: "Process these files in first batch using pdf_extract.batch_process_documents(file_paths=['/path/to/dir/file1.pdf', '/path/to/dir/file2.pdf', ...first 10...])"
     task_3: "Process these files in second batch using pdf_extract.batch_process_documents(file_paths=['/path/to/dir/file11.pdf', '/path/to/dir/file12.pdf', ...next 10...])"

   - NOTE: You must know the actual files upfront (from context) OR create ONE task that handles the entire batch operation internally

   MEMORY CONTEXT FOR BATCH DATA (Optional Enhancement):
   - When dealing with large batch operations, you MAY create a goal/feature structure to organize the work:
     * Create a goal for the batch operation
     * Create features for each batch/group
     * Include file lists in feature descriptions or constraints
   - BUT: Task descriptions must STILL include complete file paths - memory is supplementary, not a replacement for data in task descriptions

   DATA TYPES TO INCLUDE:
   - File path lists: Always use absolute paths in arrays
   - Configuration data: Include complete config objects, not "the config from task_1"
   - Query results: Include actual data, not "the results from task_2"
   - IDs/references: Include explicit IDs (feature_id='F1.3'), not "the feature we created"

   REMEMBER: "file_path" is a parameter NAME. You must provide the path VALUE like '/home/user/docs/report.pdf'.
   REMEMBER: Agents cannot read previous task outputs. Each task must include ALL data it needs."""

# Find where to insert the new guideline (after guideline #3a)
# We'll insert it in the system_prompt by finding the right location
system_prompt = config['system_prompt']

# Find the end of guideline #3a
marker = "   - Always specify the exact feature ID (e.g., F1.3) or goal ID (e.g., G1) from the memory context"
if marker in system_prompt:
    # Insert the new guideline after #3a
    insert_pos = system_prompt.find(marker) + len(marker)
    new_system_prompt = system_prompt[:insert_pos] + "\n" + new_guideline + system_prompt[insert_pos:]
    config['system_prompt'] = new_system_prompt

    # Write updated configuration
    with open(planner_path, 'w') as f:
        json.dump(config, f, indent=2)

    print("✓ Successfully updated PLANNER configuration with data dependency guideline #3c")
    print(f"✓ Updated file: {planner_path}")
else:
    print("✗ Could not find insertion point for guideline #3c")
    print(f"Marker not found: {marker[:50]}...")
