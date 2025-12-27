#!/usr/bin/env python3
"""
Strengthen STAY ON TASK guideline after trace_20251226_145639 showed PLANNER
creating unwanted memory management tasks.

User said: "get list of files, delete each"
PLANNER created:
  task_1: Get list ✅
  task_2: Delete files ✅
  task_3: update_feature_status ❌ NOT REQUESTED!
  task_4: log_progress ❌ NOT REQUESTED!

This keeps happening even though guideline #1 supposedly prevents it.
Need to make it even more emphatic.
"""

import json
from pathlib import Path

planner_file = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions/planner.json"

print("=" * 80)
print("Strengthening STAY ON TASK Guideline (v5)")
print("=" * 80)
print()

# Read current planner config
with open(planner_file, 'r') as f:
    config = json.load(f)

system_prompt = config["system_prompt"]

# Find the ONLY CREATE MEMORY TASKS IF section and enhance it
old_marker = """   ONLY CREATE MEMORY TASKS IF:
   - User explicitly says "mark feature as complete"
   - User explicitly says "update the memory"
   - User explicitly says "log this progress"
   - User explicitly says "run tests"

   REMEMBER: Answering the user's question is your ONLY job. Memory management is NOT your job unless explicitly requested."""

new_section = """   ONLY CREATE MEMORY TASKS IF:
   - User explicitly says "mark feature as complete"
   - User explicitly says "update the memory"
   - User explicitly says "log this progress"
   - User explicitly says "run tests"

   🚨 REAL VIOLATION (trace 20251226_145639):
   User: "get the list of rate con files for October 2025. Delete each of them."

   ❌ PLANNER Created (WRONG - added unwanted tasks):
     task_1: "Get the list of rate con files..." ✅ User asked for this
     task_2: "Delete each rate con file..." ✅ User asked for this
     task_3: "Use builtin.update_feature_status to mark the deletion feature as completed" ❌ NOT REQUESTED!
     task_4: "Use builtin.log_progress to record what was accomplished" ❌ NOT REQUESTED!

   ✅ CORRECT Plan (only what user asked):
     task_1: Delete October 2025 rate cons using SHELL_EXECUTOR with Python loop ✅ DONE!
     (No task_2, task_3, task_4 - user didn't ask for memory management!)

   ⚠️  CRITICAL: Memory context shows you BACKGROUND INFORMATION.
   - Memory context is READ-ONLY unless user says "update the memory"
   - Seeing active features/goals does NOT mean "update them"
   - ONLY create memory tasks if user EXPLICITLY requests it
   - Just because you CAN update memory doesn't mean you SHOULD

   REMEMBER: Answering the user's question is your ONLY job. Memory management is NOT your job unless explicitly requested."""

if old_marker in system_prompt:
    system_prompt = system_prompt.replace(old_marker, new_section)
    config["system_prompt"] = system_prompt

    # Write updated config
    with open(planner_file, 'w') as f:
        json.dump(config, f, indent=2)

    print("✓ Updated PLANNER with strengthened STAY ON TASK rule")
    print()
    print("Changes:")
    print("  1. Added REAL VIOLATION from trace_20251226_145639")
    print("  2. Showed exact unwanted tasks (task_3, task_4)")
    print("  3. Emphasized: Memory context is READ-ONLY unless explicitly requested")
    print("  4. Clarified: Seeing features/goals ≠ should update them")
    print("  5. Added warning: Just because you CAN doesn't mean you SHOULD")
    print()
    print(f"Updated: {planner_file}")
else:
    print("⚠ Could not find marker - manual update needed")
    print()

print()
print("=" * 80)
print("Next: Bump version to 0.28.4 and rebuild")
print("=" * 80)
