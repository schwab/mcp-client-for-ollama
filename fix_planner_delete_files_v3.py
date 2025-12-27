#!/usr/bin/env python3
"""
Add DELETE FILES failure example to PLANNER guideline #3c after trace_20251226_143431
showed PLANNER STILL not including file lists in delete tasks.

Even with v0.28.1 and v0.28.2 fixes, PLANNER created:
  task_2: "Delete each listed ratecon file from the business database."
Without specifying WHICH files! EXECUTOR hallucinated "ratecon1.pdf, ratecon2.pdf, ratecon3.pdf"
and deleted those instead of the real 6 files from task_1.

This is the THIRD iteration showing this specific pattern persists.
"""

import json
from pathlib import Path

planner_file = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/planner.json"

print("=" * 80)
print("Adding DELETE FILES Failure Example to PLANNER (v3)")
print("=" * 80)
print()
print("Issue: trace_20251226_143431 - PLANNER still not including file lists!")
print("  - task_1: Found 6 real files ✅")
print("  - task_2: 'Delete each listed file' (NO file names!) ❌")
print("  - EXECUTOR hallucinated: ratecon1.pdf, ratecon2.pdf, ratecon3.pdf")
print("  - Deleted WRONG files!")
print()

# Read current planner config
with open(planner_file, 'r') as f:
    config = json.load(f)

system_prompt = config["system_prompt"]

# Find the FILE PATHS section and add DELETE example before the mandatory checklist
checklist_marker = """   📋 MANDATORY CHECKLIST BEFORE RETURNING PLAN:"""

delete_example = """
   🚨 REAL FAILURE - DELETE OPERATIONS (trace 20251226_143431):
   User: "delete the 6 files above from the business database."

   ❌ PLANNER Created (WRONG - caused hallucination):
     task_1: "List all ratecon files in the business database for October 2025"
       → Found: 20251003_ratecon_revised.pdf, 20251006_ratecon_tql.pdf, 20251007_rate_con.pdf,
                20251007_ratecon_tql.pdf, 20251009_ratecon_tql.pdf (6 files total)
     task_2: "Delete each listed ratecon file from the business database."  ← NO FILE NAMES!

   💥 Result:
     - task_2 EXECUTOR: "Since no specific list of files was provided..."
     - task_2 EXECUTOR hallucinated: "ratecon1.pdf", "ratecon2.pdf", "ratecon3.pdf"
     - Tried to delete MADE-UP files instead of the real 6 files!
     - COMPLETE FAILURE - wrong files deleted, real files remain!

   ✅ CORRECT PLAN (what should have been created):
     task_1: "Use pdf_extract.lookup_rate_cons_by_month(year=2025, month=10) to list October 2025 rate cons"
     task_2: "Use pdf_extract.delete_file(file_name='20251003_ratecon_revised.pdf') to delete /abs/path/20251003_ratecon_revised.pdf"
     task_3: "Use pdf_extract.delete_file(file_name='20251006_ratecon_tql.pdf') to delete /abs/path/20251006_ratecon_tql.pdf"
     task_4: "Use pdf_extract.delete_file(file_name='20251007_rate_con.pdf') to delete /abs/path/20251007_rate_con.pdf"
     task_5: "Use pdf_extract.delete_file(file_name='20251007_ratecon_tql.pdf') to delete /abs/path/20251007_ratecon_tql.pdf"
     task_6: "Use pdf_extract.delete_file(file_name='20251009_ratecon_tql.pdf') to delete /abs/path/20251009_ratecon_tql.pdf"

   ✅ Result: Each task has explicit filename - agents execute correctly!

   ⚠️  CRITICAL FOR DELETE/UPDATE/BATCH OPERATIONS:
   When user says "delete the files" or "update each file" after listing them:
   - DO NOT create single task: "Delete each listed file" ❌
   - CREATE SEPARATE TASKS: One task per file with explicit filename ✅
   - INCLUDE the complete file list from the query context
   - Each delete/update task must be STANDALONE with explicit data

""" + checklist_marker

if checklist_marker in system_prompt:
    system_prompt = system_prompt.replace(checklist_marker, delete_example)
    config["system_prompt"] = system_prompt

    # Write updated config
    with open(planner_file, 'w') as f:
        json.dump(config, f, indent=2)

    print("✓ Updated PLANNER with DELETE FILES failure example")
    print()
    print("Changes:")
    print("  1. Added REAL FAILURE from trace_20251226_143431")
    print("  2. Showed exact hallucination ('ratecon1.pdf', 'ratecon2.pdf', 'ratecon3.pdf')")
    print("  3. Showed correct approach: ONE TASK PER FILE for delete operations")
    print("  4. Added critical rule for DELETE/UPDATE/BATCH operations")
    print("  5. Positioned before MANDATORY CHECKLIST for visibility")
    print()
    print(f"Updated: {planner_file}")
else:
    print("⚠ Could not find checklist marker - manual update needed")
    print()

print()
print("=" * 80)
print("Next: Bump version to 0.28.3 and rebuild")
print("=" * 80)
