# Changelog v0.28.3

## Critical Fix: Delete Operations Failing Due to Missing File Lists

### Summary
Fixed PLANNER not including file lists in delete/update tasks, causing EXECUTOR to hallucinate filenames and delete wrong files. This is the FOURTH iteration of fixing the persistent "data in task description" issue.

### Issue

**Problem**: PLANNER created delete task without specifying which files to delete, causing EXECUTOR to hallucinate placeholder filenames.

**Real Failure** (trace_20251226_143431):
```
User query: "delete the 6 files above from the business database."

PLANNER created:
  task_1: "List all ratecon files in the business database for October 2025."
    → Result: Found 6 real files ✅
      - 20251003_ratecon_revised.pdf
      - 20251006_ratecon_tql.pdf
      - 20251007_rate_con.pdf
      - 20251007_ratecon_tql.pdf
      - 20251009_ratecon_tql.pdf (appears twice)

  task_2: "Delete each listed ratecon file from the business database." ❌ NO FILE NAMES!

EXECUTOR response to task_2:
  "Since no specific list of files was provided in your request, I'll assume
   you want to proceed with a hypothetical list."

  Hallucinated files: ["ratecon1.pdf", "ratecon2.pdf", "ratecon3.pdf"]

  Tried to delete MADE-UP files instead of the real 6 files!
  Result: COMPLETE FAILURE - wrong files, real files remain
```

### Root Cause

**PLANNER assumed EXECUTOR could access task_1 output**, but each task executes in isolation!

When task_2 said "Delete each listed ratecon file," EXECUTOR had no way to know which files because:
1. EXECUTOR only sees its own task description
2. EXECUTOR cannot access previous task outputs
3. Task description didn't include the file list
4. EXECUTOR hallucinated placeholder filenames to proceed

**Pattern Recognition**: This is the SAME issue fixed in:
- v0.26.30: Initial data dependencies guideline
- v0.28.1: "Data Must Be in 'description' Field"
- v0.28.2: MANDATORY CHECKLIST with file path propagation
- v0.28.3: Now adding DELETE-specific example

The persistence of this issue across 4 versions shows how difficult it is to get LLMs to consistently follow guidelines, even when extremely explicit.

### Solution Implemented

Added **DELETE OPERATIONS** failure example to PLANNER guideline #3c, positioned prominently before the MANDATORY CHECKLIST:

**New Section Added**:
```
🚨 REAL FAILURE - DELETE OPERATIONS (trace 20251226_143431):
User: "delete the 6 files above from the business database."

❌ PLANNER Created (WRONG - caused hallucination):
  task_1: "List all ratecon files in the business database for October 2025"
    → Found: 20251003_ratecon_revised.pdf, 20251006_ratecon_tql.pdf, ...
  task_2: "Delete each listed ratecon file from the business database."  ← NO FILE NAMES!

💥 Result:
  - task_2 EXECUTOR: "Since no specific list of files was provided..."
  - task_2 EXECUTOR hallucinated: "ratecon1.pdf", "ratecon2.pdf", "ratecon3.pdf"
  - Tried to delete MADE-UP files instead of the real 6 files!

✅ CORRECT PLAN (what should have been created):
  task_1: "Use pdf_extract.lookup_rate_cons_by_month(year=2025, month=10)"
  task_2: "Use pdf_extract.delete_file(file_name='20251003_ratecon_revised.pdf')"
  task_3: "Use pdf_extract.delete_file(file_name='20251006_ratecon_tql.pdf')"
  task_4: "Use pdf_extract.delete_file(file_name='20251007_rate_con.pdf')"
  task_5: "Use pdf_extract.delete_file(file_name='20251007_ratecon_tql.pdf')"
  task_6: "Use pdf_extract.delete_file(file_name='20251009_ratecon_tql.pdf')"

⚠️  CRITICAL FOR DELETE/UPDATE/BATCH OPERATIONS:
When user says "delete the files" or "update each file" after listing them:
- DO NOT create single task: "Delete each listed file" ❌
- CREATE SEPARATE TASKS: One task per file with explicit filename ✅
- INCLUDE the complete file list from the query context
- Each delete/update task must be STANDALONE with explicit data
```

### Expected Behavior After Fix

When user says: "delete the 6 files above"

PLANNER should now create:
```json
{
  "tasks": [
    {
      "id": "task_1",
      "description": "Use pdf_extract.delete_file(file_name='20251003_ratecon_revised.pdf') to delete from database"
    },
    {
      "id": "task_2",
      "description": "Use pdf_extract.delete_file(file_name='20251006_ratecon_tql.pdf') to delete from database"
    },
    ...one task per file
  ]
}
```

Every task has explicit filename - no references to "the files" or "each listed file"!

### Files Modified

**Agent Definitions**:
- `mcp_client_for_ollama/agents/definitions/planner.json` - Added DELETE operations failure example in guideline #3c

**Version**:
- `pyproject.toml` → 0.28.3
- `mcp_client_for_ollama/__init__.py` → 0.28.3

**Documentation**:
- `CHANGELOG_v0.28.3.md` (this file)

### Impact

**Critical Fix**:
- PLANNER has explicit DELETE operations example showing exact hallucination
- Positioned before MANDATORY CHECKLIST for maximum visibility
- Shows correct approach: ONE TASK PER FILE for delete operations
- Clarifies that batch operations need separate tasks with explicit data

**Backward Compatibility**:
- Fully backward compatible
- No breaking changes

### Historical Context

This is the **FOURTH iteration** of fixing the "include data in task description" issue:

| Version | Fix | Result |
|---------|-----|--------|
| v0.26.30 | Added guideline #3c for data dependencies | PLANNER still referenced "from task_2" |
| v0.28.1 | "Data Must Be in 'description' Field" | PLANNER still omitted file paths |
| v0.28.2 | MANDATORY CHECKLIST + file path propagation | PLANNER still created "delete each listed file" |
| v0.28.3 | DELETE operations example + "one task per file" | Testing needed |

**Why so many iterations?**
- LLMs don't always follow general rules consistently
- Need specific, concrete examples for each pattern (file paths, delete operations, etc.)
- Each real failure becomes a training example in the prompt
- Guidelines must be EXTREMELY explicit with exact failure/success patterns

### Testing Recommendations

1. Test delete operations with multiple files
2. Test update operations with file lists
3. Test batch processing scenarios
4. Verify PLANNER creates separate tasks per file
5. Verify each task has explicit filenames

---

**Version**: 0.28.3
**Date**: 2025-12-26
**Category**: Critical Bug Fix
**Breaking Changes**: None
