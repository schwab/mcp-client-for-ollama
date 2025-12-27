#!/usr/bin/env python3
"""
Strengthen PLANNER guideline #3c even MORE forcefully after trace_20251226_141922 showed
PLANNER is STILL not including filenames in dependent tasks.

The model is ignoring the rule "Include in EVERY Task That Uses Them". Need to make it
even more explicit and prominent.
"""

import json
from pathlib import Path

planner_file = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/planner.json"

print("=" * 80)
print("Strengthening PLANNER File Path Propagation (v2)")
print("=" * 80)
print()
print("Issue: trace_20251226_141922 showed PLANNER still not following the rule!")
print("  - task_1: Had filename ✅")
print("  - task_2: NO filename ❌ → EXECUTOR hallucinated 'example.pdf'")
print("  - task_3: NO filename ❌ → EXECUTOR asked for filename")
print()

# Read current planner config
with open(planner_file, 'r') as f:
    config = json.load(f)

system_prompt = config["system_prompt"]

# Find guideline #3c and replace the FILE PATHS section with a much stronger version
old_marker = """   *** FILE PATHS - Include in EVERY Task That Uses Them ***
   If user says: \"import this file: Daily/October/file.pdf\"

   ❌ WRONG (path only in first task):
     task_1: \"Validate path for processing\" (no path!)
     task_2: \"Check if document exists\" (no path!)
     task_3: \"Import the document\" (no path!)

   ✅ RIGHT (path in every task):
     task_1: \"Use builtin.validate_file_path(path='/abs/path/Daily/October/file.pdf', ...) to validate\"
     task_2: \"Use pdf_extract.check_file_exists(file_name='file.pdf') to check if /abs/path/Daily/October/file.pdf exists in database\"
     task_3: \"Use pdf_extract.process_document(file_path='/abs/path/Daily/October/file.pdf') to import\"

   Each task is STANDALONE - if it needs a file path, include the COMPLETE path in its description!"""

new_file_paths_section = """   *** FILE PATHS - REPEAT IN EVERY SINGLE TASK (CRITICAL!) ***

   ⚠️  ABSOLUTE RULE: If a file path appears ANYWHERE in the user query, that EXACT path must appear in EVERY task that operates on that file!

   🚨 REAL FAILURE (trace 20251226_141922):
   User: "check for this file ... Daily/October/20251003_ratecon_tdr26003.pdf"

   ❌ PLANNER Created (WRONG - caused hallucination):
     task_1: "Validate the file path for Daily/October/20251003_ratecon_tdr26003.pdf"
     task_2: "Check if the file exists in the Business database using pdf_extract.check_file_exists"  ← NO FILENAME!
     task_3: "Remove the file from the Business database if it exists"  ← NO FILENAME!

   💥 Result:
     - task_2 EXECUTOR: "you haven't provided the name of the file"
     - task_2 EXECUTOR hallucinated: checked "example.pdf" instead!
     - task_3 EXECUTOR: "Which file name should we use?"
     - COMPLETE FAILURE - wrong file checked, no file deleted!

   ✅ CORRECT PLAN (what should have been created):
     task_1: "Use builtin.validate_file_path(path='/home/mcstar/Nextcloud/VTCLLC/Daily/October/20251003_ratecon_tdr26003.pdf', task_description='...') to validate the file path"
     task_2: "Use pdf_extract.check_file_exists(file_name='20251003_ratecon_tdr26003.pdf') to check if /home/mcstar/Nextcloud/VTCLLC/Daily/October/20251003_ratecon_tdr26003.pdf exists in the Business database"
     task_3: "Use pdf_extract.delete_file(file_name='20251003_ratecon_tdr26003.pdf') to remove /home/mcstar/Nextcloud/VTCLLC/Daily/October/20251003_ratecon_tdr26003.pdf from the Business database if it exists"

   ✅ Result: Each task has complete filename - agents execute correctly!

   📋 MANDATORY CHECKLIST BEFORE RETURNING PLAN:
   1. Does user query mention a file path? If YES →
   2. Extract the COMPLETE file path (convert to absolute if needed)
   3. For EACH task in your plan that operates on that file:
      ✓ Does the task description include the COMPLETE file path or filename?
      ✓ If NO - FIX IT NOW by adding the path to the description!
   4. NEVER assume agents can "figure it out" from dependencies
   5. NEVER assume agents can access previous task outputs
   6. Each task is COMPLETELY ISOLATED - include all data it needs!

   REMEMBER: "dependencies" = execution order, NOT data access!
   If task_2 needs the file path, PUT THE FILE PATH IN task_2's description!"""

if old_marker in system_prompt:
    system_prompt = system_prompt.replace(old_marker, new_file_paths_section)
    config["system_prompt"] = system_prompt

    # Write updated config
    with open(planner_file, 'w') as f:
        json.dump(config, f, indent=2)

    print("✓ Updated PLANNER with MUCH stronger file path propagation rule")
    print()
    print("Changes:")
    print("  1. Added REAL FAILURE example from trace_20251226_141922")
    print("  2. Showed exact hallucination ('example.pdf')")
    print("  3. Added MANDATORY CHECKLIST for PLANNER to follow")
    print("  4. Used stronger emphasis (🚨, ⚠️, ABSOLUTE RULE)")
    print("  5. Made it crystal clear: dependencies ≠ data access")
    print()
    print(f"Updated: {planner_file}")
else:
    print("⚠ Could not find file paths marker - manual update needed")
    print()

print()
print("=" * 80)
print("Next: Bump version to 0.28.2 and rebuild")
print("=" * 80)
