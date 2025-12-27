#!/usr/bin/env python3
"""
Fix PLANNER guideline #3c to explicitly state that ALL data must be in 'description' field.

The problem: PLANNER was putting file paths in 'expected_output' instead of 'description'.
Agents can only see 'description' during execution, causing them to hallucinate paths.

This script adds critical clarification to guideline #3c.
"""

import json
from pathlib import Path

planner_file = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/planner.json"

print("=" * 80)
print("Fixing PLANNER Guideline #3c - Data Must Be in 'description' Field")
print("=" * 80)
print()

# Read current planner config
with open(planner_file, 'r') as f:
    config = json.load(f)

system_prompt = config["system_prompt"]

# Find and replace guideline #3c
old_guideline_marker = """3c. Include Complete Data Dependencies (CRITICAL - Data Passing Between Tasks):
   ⚠️  ABSOLUTE RULE: NEVER reference previous task outputs. Each task must include ALL data it needs."""

new_guideline_3c = """3c. Include Complete Data Dependencies (CRITICAL - Data Passing Between Tasks):
   ⚠️  ABSOLUTE RULE: NEVER reference previous task outputs. Each task must include ALL data it needs.

   *** CRITICAL: Data Must Be in 'description' Field ***
   - Agents can ONLY see the 'description' field during execution
   - Agents CANNOT see 'expected_output' during execution
   - 'expected_output' is for humans/logging ONLY
   - ALL file paths, IDs, parameters MUST be in 'description'

   REAL FAILURE EXAMPLE (trace 20251226_122303):
   ❌ WRONG (data in wrong field):
     {
       "description": "Validate and lock the file path for processing.",
       "expected_output": "Validated file path: /home/mcstar/Nextcloud/VTCLLC/Daily/October/20251007_rate_con.pdf"
     }
     → FILE_EXECUTOR sees only description, says "no path provided"!

   ✅ RIGHT (data in description):
     {
       "description": "Use builtin.validate_file_path(path='/home/mcstar/Nextcloud/VTCLLC/Daily/October/20251007_rate_con.pdf', task_description='...') to validate and lock the file path.",
       "expected_output": "Confirmation that path is locked"
     }
     → FILE_EXECUTOR sees the complete path and can execute immediately!

   *** FILE PATHS - Include in EVERY Task That Uses Them ***
   If user says: "import this file: Daily/October/file.pdf"

   ❌ WRONG (path only in first task):
     task_1: "Validate path for processing" (no path!)
     task_2: "Check if document exists" (no path!)
     task_3: "Import the document" (no path!)

   ✅ RIGHT (path in every task):
     task_1: "Use builtin.validate_file_path(path='/abs/path/Daily/October/file.pdf', ...) to validate"
     task_2: "Use pdf_extract.check_file_exists(file_name='file.pdf') to check if /abs/path/Daily/October/file.pdf exists in database"
     task_3: "Use pdf_extract.process_document(file_path='/abs/path/Daily/October/file.pdf') to import"

   Each task is STANDALONE - if it needs a file path, include the COMPLETE path in its description!"""

if old_guideline_marker in system_prompt:
    # Find the end of guideline #3c (next guideline starts with "\n\n\n4. " or "\n4. ")
    start_idx = system_prompt.index(old_guideline_marker)
    # Find the end - look for next numbered guideline
    end_marker = "\n4. Right-Size Tasks"
    end_idx = system_prompt.index(end_marker, start_idx)

    # Extract everything after the first line of #3c until guideline #4
    old_guideline_full = system_prompt[start_idx:end_idx]

    # Replace with new version
    system_prompt = system_prompt.replace(old_guideline_full, new_guideline_3c)

    config["system_prompt"] = system_prompt

    # Write updated config
    with open(planner_file, 'w') as f:
        json.dump(config, f, indent=2)

    print("✓ Updated PLANNER guideline #3c with critical clarifications:")
    print()
    print("Added rules:")
    print("  1. ALL data must be in 'description' field (not 'expected_output')")
    print("  2. Agents cannot see 'expected_output' during execution")
    print("  3. File paths must be included in EVERY task that uses them")
    print("  4. Each task is STANDALONE - include complete data")
    print()
    print("Included real failure example from trace 20251226_122303")
    print()
    print(f"Updated: {planner_file}")
else:
    print("⚠ Could not find guideline #3c marker - manual update needed")
    print()

print()
print("=" * 80)
print("Next: Update version to 0.28.1 and rebuild")
print("=" * 80)
