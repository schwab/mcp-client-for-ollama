#!/usr/bin/env python3
"""
Fix PLANNER to handle batch delete operations correctly (v4).

THE PROBLEM:
User says: "get list of files, then delete each"
PLANNER doesn't know which files exist at planning time!
Files are discovered during execution, not at planning time.

TWO DIFFERENT SCENARIOS:
1. User provides explicit list: "delete these 6 files: file1.pdf, file2.pdf, ..."
   → PLANNER knows the files → Create separate delete task per file ✅

2. User says "get list then delete": "get October files, delete each"
   → PLANNER DOESN'T know files yet → Can't create per-file tasks ❌

SOLUTION FOR SCENARIO 2:
Create SINGLE task that queries AND deletes in one operation,
OR use SHELL_EXECUTOR with Python to loop through results.
"""

import json
from pathlib import Path

planner_file = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/planner.json"

print("=" * 80)
print("Fixing PLANNER for Batch Delete Operations (v4)")
print("=" * 80)
print()
print("Issue: PLANNER can't create per-file tasks when files are discovered at runtime!")
print()

# Read current planner config
with open(planner_file, 'r') as f:
    config = json.load(f)

system_prompt = config["system_prompt"]

# Find the DELETE example and enhance it with the batch query scenario
old_delete_marker = """   🚨 REAL FAILURE - DELETE OPERATIONS (trace 20251226_143431):"""

new_delete_section = """   🚨 REAL FAILURE - DELETE OPERATIONS:

   *** SCENARIO 1: User Provides Explicit File List ***

   User: "delete the 6 files above from the business database."
   (User already knows which files - they listed them or saw them in previous response)

   ❌ WRONG (trace 20251226_143431):
     task_1: "List all ratecon files for October 2025"
       → Found: 20251003_ratecon_revised.pdf, 20251006_ratecon_tql.pdf, ...
     task_2: "Delete each listed ratecon file from the business database."  ← NO FILE NAMES!

   💥 Result: EXECUTOR hallucinated "ratecon1.pdf", "ratecon2.pdf", "ratecon3.pdf"

   ✅ RIGHT (create separate task per file):
     task_1: "Use pdf_extract.delete_file(file_name='20251003_ratecon_revised.pdf')"
     task_2: "Use pdf_extract.delete_file(file_name='20251006_ratecon_tql.pdf')"
     task_3: "Use pdf_extract.delete_file(file_name='20251007_rate_con.pdf')"
     ...one task per file

   *** SCENARIO 2: Files Discovered from Query (NEW!) ***

   User: "get the list of rate con files for October 2025. Delete each of them."
   (Files don't exist yet - will be discovered by the query)

   ❌ WRONG (trace 20251226_145639):
     task_1: "Get the list of rate con files for October 2025"
     task_2: "Delete each rate con file from the business database" ← Can't specify files!

   Problem: PLANNER doesn't know which files exist at planning time!

   ✅ RIGHT (single task with iteration):
     task_1: "Use SHELL_EXECUTOR with Python to: (1) call pdf_extract.lookup_rate_cons_by_month(year=2025, month=10) to get files, (2) loop through results and call pdf_extract.delete_file(file_name=...) for each filename"

   OR EVEN BETTER (if batch delete tool exists):
     task_1: "Use pdf_extract.batch_delete_rate_cons(year=2025, month=10) to delete all October 2025 rate cons in one operation"

   ⚠️  CRITICAL DISTINCTION:
   - User already knows files → Create separate delete tasks per file
   - Files discovered from query → Create SINGLE task that queries AND deletes
   - NEVER create task_2 that says "delete each file" without filenames!
   - For query-based batch delete, use SHELL_EXECUTOR with Python loop

"""

if old_delete_marker in system_prompt:
    # Find the end of the old delete section (before the checklist)
    checklist_marker = "   📋 MANDATORY CHECKLIST BEFORE RETURNING PLAN:"

    # Find where old delete section ends
    start_idx = system_prompt.index(old_delete_marker)
    end_idx = system_prompt.index(checklist_marker, start_idx)

    # Extract the old section
    old_section = system_prompt[start_idx:end_idx]

    # Replace with new enhanced section
    system_prompt = system_prompt.replace(old_section, new_delete_section)

    config["system_prompt"] = system_prompt

    # Write updated config
    with open(planner_file, 'w') as f:
        json.dump(config, f, indent=2)

    print("✓ Updated PLANNER with enhanced DELETE operations guidance")
    print()
    print("Changes:")
    print("  1. Distinguished SCENARIO 1 (explicit files) vs SCENARIO 2 (query-based)")
    print("  2. Added trace_20251226_145639 as example of SCENARIO 2 failure")
    print("  3. Showed correct approach: SINGLE task with Python loop for query-based deletes")
    print("  4. Emphasized: PLANNER can't create per-file tasks for runtime-discovered files")
    print("  5. Suggested using SHELL_EXECUTOR with Python iteration")
    print()
    print(f"Updated: {planner_file}")
else:
    print("⚠ Could not find delete marker - manual update needed")
    print()

print()
print("=" * 80)
print("Next: Also need to fix 'STAY ON TASK' violation (tasks 3 & 4)")
print("=" * 80)
