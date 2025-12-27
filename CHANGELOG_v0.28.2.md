# Changelog v0.28.2

## Critical Fix: PLANNER Still Not Propagating File Paths

### Summary
Strengthened PLANNER guideline #3c even further after trace_20251226_141922 showed that despite the v0.28.1 fix, PLANNER was STILL not including file paths in dependent tasks, causing EXECUTOR to hallucinate filenames.

### Issue

**Problem**: v0.28.1 added the rule "Include in EVERY Task That Uses Them" but the model was ignoring it.

**Real Failure** (trace_20251226_141922):
```
User query: "check for this file ... Daily/October/20251003_ratecon_tdr26003.pdf"

PLANNER created:
  task_1: "Validate the file path for Daily/October/20251003_ratecon_tdr26003.pdf" ✅ Has filename
  task_2: "Check if the file exists in the Business database using pdf_extract.check_file_exists" ❌ NO filename!
  task_3: "Remove the file from the Business database if it exists" ❌ NO filename!

Result:
  - task_2 EXECUTOR: "you haven't provided the name of the file"
  - task_2 EXECUTOR hallucinated: checked "example.pdf" instead!
  - task_3 EXECUTOR: "Which file name should we use?"
  - COMPLETE FAILURE - wrong file checked, no file deleted!
```

### Root Cause

The v0.28.1 guideline said "Include in EVERY Task" but:
1. Wasn't prominent enough
2. Didn't have a real failure example showing hallucination
3. Didn't include a mandatory checklist
4. Model was ignoring the rule

### Solution Implemented

Completely rewrote the FILE PATHS section of guideline #3c with:

**1. Stronger Emphasis**:
```
*** FILE PATHS - REPEAT IN EVERY SINGLE TASK (CRITICAL!) ***

⚠️  ABSOLUTE RULE: If a file path appears ANYWHERE in the user query,
that EXACT path must appear in EVERY task that operates on that file!
```

**2. Real Failure Example**:
Added the EXACT failure from trace_20251226_141922 showing:
- What PLANNER created (wrong)
- What happened (EXECUTOR hallucinated "example.pdf")
- What should have been created (correct)

**3. Mandatory Checklist**:
```
📋 MANDATORY CHECKLIST BEFORE RETURNING PLAN:
1. Does user query mention a file path? If YES →
2. Extract the COMPLETE file path (convert to absolute if needed)
3. For EACH task in your plan that operates on that file:
   ✓ Does the task description include the COMPLETE file path or filename?
   ✓ If NO - FIX IT NOW by adding the path to the description!
4. NEVER assume agents can "figure it out" from dependencies
5. NEVER assume agents can access previous task outputs
6. Each task is COMPLETELY ISOLATED - include all data it needs!
```

**4. Critical Clarification**:
```
REMEMBER: "dependencies" = execution order, NOT data access!
If task_2 needs the file path, PUT THE FILE PATH IN task_2's description!
```

### Expected Behavior After Fix

When user says: "check for this file ... Daily/October/20251003_ratecon_tdr26003.pdf"

PLANNER should now create:
```json
{
  "tasks": [
    {
      "id": "task_1",
      "description": "Use builtin.validate_file_path(path='/home/mcstar/Nextcloud/VTCLLC/Daily/October/20251003_ratecon_tdr26003.pdf', ...) to validate"
    },
    {
      "id": "task_2",
      "description": "Use pdf_extract.check_file_exists(file_name='20251003_ratecon_tdr26003.pdf') to check if /home/mcstar/Nextcloud/VTCLLC/Daily/October/20251003_ratecon_tdr26003.pdf exists"
    },
    {
      "id": "task_3",
      "description": "Use pdf_extract.delete_file(file_name='20251003_ratecon_tdr26003.pdf') to remove /home/mcstar/Nextcloud/VTCLLC/Daily/October/20251003_ratecon_tdr26003.pdf if it exists"
    }
  ]
}
```

Every task has the complete file path/filename!

### Files Modified

**Agent Definitions**:
- `mcp_client_for_ollama/agents/definitions/planner.json` - Completely rewrote FILE PATHS section in guideline #3c

**Version**:
- `pyproject.toml` → 0.28.2
- `mcp_client_for_ollama/__init__.py` → 0.28.2

**Documentation**:
- `CHANGELOG_v0.28.2.md` (this file)

### Impact

**Critical Fix**:
- PLANNER should now consistently include file paths in EVERY task
- Added mandatory checklist for PLANNER to follow before returning plan
- Real failure example shows exact consequences of not following rule
- Stronger emphasis and emojis to grab model's attention

**Backward Compatibility**:
- Fully backward compatible
- No breaking changes

### Notes

This is the THIRD iteration of fixing this issue:
- v0.26.30: Enhanced data dependencies in general
- v0.28.1: Added "Data Must Be in 'description' Field" + "Include in EVERY Task"
- v0.28.2: Made rule MUCH more forceful with real failure, checklist, and stronger emphasis

The persistence of this issue shows how difficult it can be to get LLMs to follow specific rules consistently, even when explicitly stated. Multiple iterations with increasingly forceful guidelines may be necessary.

---

**Version**: 0.28.2
**Date**: 2025-12-26
**Category**: Critical Bug Fix
**Breaking Changes**: None
