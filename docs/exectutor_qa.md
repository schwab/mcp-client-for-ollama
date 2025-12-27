## ✅ IMPLEMENTED (v0.28.0) - EXECUTOR complexity, partitioning
**Status**: COMPLETED
**Version**: 0.28.0
**Date**: 2025-12-26

**Original Issue**:
- EXECUTOR system prompt exceeded 100 lines (was 212 lines!)
- Becoming untenable to maintain
- Mixed too many responsibilities

**Solution Implemented**:
Partitioned into 5 specialized executors:

1. **FILE_EXECUTOR** (44 lines) - File operations with path validation
2. **TEST_EXECUTOR** (35 lines) - Test execution and reporting
3. **CONFIG_EXECUTOR** (38 lines) - Configuration management
4. **MEMORY_EXECUTOR** (46 lines) - Memory and feature tracking
5. **SHELL_EXECUTOR** (54 lines) - Shell, Python, and MCP tools

**Results**:
- Average 45 lines per executor (down from 212)
- ~80% reduction in prompt size per executor
- Clear single responsibility per executor
- Better model performance with focused prompts
- Easier maintenance and future enhancements

**See**: CHANGELOG_v0.28.0.md for complete details

## ✅ FIXED (v0.28.1) - Partitioned Agents failed to pass file names around correctly
**Status**: COMPLETED
**Version**: 0.28.1
**Date**: 2025-12-26

**Original Issue**:
Trace Session ID: 20251226_122303
- PLANNER was putting file paths in `expected_output` field instead of `description`
- Agents can only see `description` during execution
- FILE_EXECUTOR received "Validate and lock the file path" with NO actual path
- Caused agents to hallucinate placeholder paths

**Solution Implemented**:
Enhanced PLANNER guideline #3c with critical clarification:
- ALL data must be in `description` field (not `expected_output`)
- Agents CANNOT see `expected_output` during execution
- Added real failure example from trace
- Explicitly documented correct vs incorrect patterns

**See**: CHANGELOG_v0.28.1.md for complete details

## ✅ FIXED (v0.28.1) - more issues with missing full path
**Status**: COMPLETED
**Version**: 0.28.1
**Date**: 2025-12-26

**Original Issue**:
Trace Session ID: 20251226_140217
- PLANNER included filename in task_1 but NOT in task_2
- task_2 description: "If the file exists, delete it from the business database"
- No filename specified → EXECUTOR said "you haven't provided a specific filename"

**Solution Implemented**:
Added explicit rule to guideline #3c:
- File paths must be included in EVERY task that uses them
- Each task is STANDALONE - include complete data
- If task needs a file path, put the COMPLETE path in its description

**See**: CHANGELOG_v0.28.1.md for complete details

## ✅ FIXED (v0.28.1) - make Task Plan and task_x notifications use the new emojis
**Status**: COMPLETED
**Version**: 0.28.1
**Date**: 2025-12-26

**Original Issue**:
- Agent JSON files had emoji field
- Emojis not showing in task plans or execution logs

**Solution Implemented**:
1. Added `emoji` field to AgentConfig dataclass
2. Updated `_display_plan()` to show emojis in task plans
3. Updated `_execute_task()` to show emojis in execution logs

**Result**:
```
Task Plan:
1. [📂🔒 FILE_EXECUTOR] Validate file path...
2. [🐚💻 SHELL_EXECUTOR] Check if file exists...

Executing task_1 (📂🔒 FILE_EXECUTOR) <qwen2.5:32b>
```

**See**: CHANGELOG_v0.28.1.md for complete details 

## ✅ FIXED (v0.28.2) - Path locked, but next executor still fails with path issues
**Status**: COMPLETED
**Version**: 0.28.2
**Date**: 2025-12-26

**Original Issue**:
Trace Session ID: 20251226_141922
- Despite v0.28.1 fix, PLANNER still not including file paths in dependent tasks
- task_1: FILE_EXECUTOR validated path ✅
- task_2: EXECUTOR description had NO filename ❌
- task_3: EXECUTOR description had NO filename ❌
- Result: EXECUTOR hallucinated "example.pdf" instead of using correct file

**Solution Implemented**:
Completely rewrote FILE PATHS section of PLANNER guideline #3c:
- Added REAL FAILURE example from this trace showing hallucination
- Added MANDATORY CHECKLIST for PLANNER to follow
- Stronger emphasis (🚨, ⚠️, ABSOLUTE RULE)
- Made crystal clear: "dependencies" = execution order, NOT data access

**New Rule**:
```
⚠️  ABSOLUTE RULE: If a file path appears ANYWHERE in the user query,
that EXACT path must appear in EVERY task that operates on that file!

📋 MANDATORY CHECKLIST BEFORE RETURNING PLAN:
1. Does user query mention a file path? If YES →
2. Extract the COMPLETE file path
3. For EACH task that operates on that file:
   ✓ Does the task description include the COMPLETE file path?
   ✓ If NO - FIX IT NOW!
```

**See**: CHANGELOG_v0.28.2.md for complete details