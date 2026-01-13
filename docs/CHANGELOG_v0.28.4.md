## ✅ FIXED (v0.28.4) - Task 1 OK, but task 2 starts falling apart
**Status**: COMPLETED
**Version**: 0.28.4
**Date**: 2025-12-26

### Summary
Fixed TWO critical PLANNER issues from trace_20251226_145639:
1. **Batch delete confusion**: PLANNER trying to create per-file delete tasks when files are discovered at runtime
2. **STAY ON TASK violation**: PLANNER creating unwanted memory management tasks (update_feature_status, log_progress)

### Issue 1: Batch Delete Confusion

**Problem**: Different delete scenarios require different approaches

**Trace 20251226_145639**:
```
User: "get the list of rate con files for October 2025. Delete each of them."

PLANNER created:
  task_1: "Get the list of rate con files..." ✅
  task_2: "Delete each rate con file from the business database" ❌ NO FILE NAMES!

Problem: PLANNER doesn't know which files exist at planning time!
Files are discovered during task_1 execution.
```

**Root Cause Analysis**:

The v0.28.3 fix assumed PLANNER knows which files to delete at planning time. But there are TWO different scenarios:

**SCENARIO 1**: User provides explicit file list
- User: "delete the 6 files above: file1.pdf, file2.pdf, ..."
- PLANNER knows the files → Create separate delete task per file ✅

**SCENARIO 2**: Files discovered from query (THIS trace)
- User: "get October files, delete each"
- PLANNER DOESN'T know files yet → Can't create per-file tasks! ❌

**Solution Implemented**:

Enhanced PLANNER guideline #3c to distinguish between scenarios:

```
*** SCENARIO 1: User Provides Explicit File List ***
✅ Create separate delete task per file

*** SCENARIO 2: Files Discovered from Query (NEW!) ***
User: "get the list ... Delete each of them."

❌ WRONG:
  task_1: "Get the list of rate con files"
  task_2: "Delete each rate con file" ← Can't specify files!

✅ RIGHT (single task with iteration):
  task_1: "Use SHELL_EXECUTOR with Python to:
           (1) call pdf_extract.lookup_rate_cons_by_month(year=2025, month=10)
           (2) loop through results and call pdf_extract.delete_file(file_name=...)
           for each filename"

OR EVEN BETTER (if batch tool exists):
  task_1: "Use pdf_extract.batch_delete_rate_cons(year=2025, month=10)"

⚠️  CRITICAL DISTINCTION:
- User already knows files → Create separate delete tasks per file
- Files discovered from query → Create SINGLE task that queries AND deletes
- For query-based batch operations, use SHELL_EXECUTOR with Python loop
```

### Issue 2: STAY ON TASK Violation

**Problem**: PLANNER creating unwanted memory management tasks

**Trace 20251226_145639**:
```
User: "get the list of rate con files for October 2025. Delete each of them."

PLANNER created:
  task_1: "Get the list..." ✅ User asked for this
  task_2: "Delete each..." ✅ User asked for this
  task_3: "Use builtin.update_feature_status to mark deletion feature as completed" ❌ NOT REQUESTED!
  task_4: "Use builtin.log_progress to record what was accomplished" ❌ NOT REQUESTED!
```

**Root Cause**:

PLANNER saw memory context with active features/goals and thought it should update them, even though user didn't ask. This violates "STAY ON TASK" guideline #1.

**Solution Implemented**:

Strengthened STAY ON TASK rule with real violation example:

```
🚨 REAL VIOLATION (trace 20251226_145639):
User: "get the list ... Delete each of them."

❌ PLANNER Created (added unwanted tasks):
  task_1: Get list ✅
  task_2: Delete ✅
  task_3: update_feature_status ❌ NOT REQUESTED!
  task_4: log_progress ❌ NOT REQUESTED!

✅ CORRECT Plan (only what user asked):
  task_1: Delete October 2025 rate cons using SHELL_EXECUTOR ✅ DONE!
  (No task_2, task_3, task_4)

⚠️  CRITICAL: Memory context shows you BACKGROUND INFORMATION.
- Memory context is READ-ONLY unless user says "update the memory"
- Seeing active features/goals does NOT mean "update them"
- ONLY create memory tasks if user EXPLICITLY requests it
- Just because you CAN update memory doesn't mean you SHOULD
```

### Expected Behavior After Fix

**Scenario 1** (explicit file list):
```
User: "delete these 3 files: file1.pdf, file2.pdf, file3.pdf"

PLANNER creates:
  task_1: "Use pdf_extract.delete_file(file_name='file1.pdf')"
  task_2: "Use pdf_extract.delete_file(file_name='file2.pdf')"
  task_3: "Use pdf_extract.delete_file(file_name='file3.pdf')"
```

**Scenario 2** (query-based):
```
User: "get October files, delete each"

PLANNER creates:
  task_1: "Use SHELL_EXECUTOR with Python to lookup and delete all October files"

OR:
  task_1: "Use pdf_extract.batch_delete_rate_cons(year=2025, month=10)"
```

**No unwanted memory tasks** unless user explicitly requests them!

### Files Modified

**Agent Definitions**:
- `mcp_client_for_ollama/agents/definitions/planner.json`
  - Enhanced DELETE operations with scenario distinction
  - Strengthened STAY ON TASK with real violation example

**Version**:
- `pyproject.toml` → 0.28.4
- `mcp_client_for_ollama/__init__.py` → 0.28.4

**Documentation**:
- `CHANGELOG_v0.28.4.md` (this file)

### Impact

**Critical Fixes**:
1. PLANNER now distinguishes between:
   - Explicit file lists (create per-file tasks)
   - Query-based lists (create single task with loop)
2. PLANNER won't create memory tasks unless explicitly requested
3. Clearer guidance on batch operations

**Prevents**:
- Creating "delete each file" tasks without filenames
- Creating unwanted update_feature_status / log_progress tasks
- Confusion about when to create per-file vs batch tasks

**Backward Compatibility**:
- Fully backward compatible
- No breaking changes

### Testing Recommendations

1. Test "delete these specific files: file1, file2, file3" → should create per-file tasks
2. Test "get files from database, delete each" → should create single batch task
3. Verify no unwanted memory tasks are created unless user explicitly asks
4. Verify SHELL_EXECUTOR can handle batch operations with Python loops

---

**Version**: 0.28.4
**Date**: 2025-12-26
**Category**: Critical Bug Fix
**Breaking Changes**: None
