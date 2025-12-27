# Changelog v0.28.1

## Critical Bug Fixes and Visual Enhancements

### Summary
Fixed critical PLANNER bug causing file path hallucination and added emoji support for visual agent identification in task plans and execution logs.

### Issues Fixed

---

## Issue 1: PLANNER Putting Data in Wrong Field (CRITICAL)

**Problem**: PLANNER was putting file paths in `expected_output` instead of `description` field, causing agents to hallucinate paths.

**Root Cause Analysis** (trace_20251226_122303):
```json
// User query: "import this pdf file: Daily/October/20251007_rate_con.pdf"

// PLANNER created task_1:
{
  "description": "Validate and lock the file path for processing.",
  "expected_output": "Validated file path: /home/mcstar/Nextcloud/VTCLLC/Daily/October/20251007_rate_con.pdf"
}

// FILE_EXECUTOR response:
"I need the exact path... no specific path was provided"
```

**Why This Failed**:
- Agents can ONLY see the `description` field during execution
- Agents CANNOT see `expected_output` (it's for humans/logging only)
- File path was in expected_output → Agent saw no path → Hallucinated placeholder paths

**Solution Implemented**:
Enhanced PLANNER guideline #3c with critical clarification:

```
*** CRITICAL: Data Must Be in 'description' Field ***
- Agents can ONLY see the 'description' field during execution
- Agents CANNOT see 'expected_output' during execution
- 'expected_output' is for humans/logging ONLY
- ALL file paths, IDs, parameters MUST be in 'description'
```

Added real failure example and correct pattern:
```
❌ WRONG (data in wrong field):
  {
    "description": "Validate and lock the file path for processing.",
    "expected_output": "Validated file path: /home/.../file.pdf"
  }

✅ RIGHT (data in description):
  {
    "description": "Use builtin.validate_file_path(path='/home/.../file.pdf', ...) to validate",
    "expected_output": "Confirmation that path is locked"
  }
```

**Files Modified**:
- `mcp_client_for_ollama/agents/definitions/planner.json` - Enhanced guideline #3c

---

## Issue 2: File Paths Not Propagated to Dependent Tasks

**Problem**: PLANNER included file path in task_1 but not in task_2, even though task_2 needed the same file.

**Root Cause Analysis** (trace_20251226_140217):
```json
// User query: "delete this file: Daily/October/20251003_ratecon_revised.pdf"

// task_1 - HAS filename ✅
{
  "description": "Validate that the file Daily/October/20251003_ratecon_revised.pdf exists..."
}

// task_2 - NO filename ❌
{
  "description": "If the file exists, delete it from the business database using appropriate database operations.",
  "dependencies": ["task_1"]
}

// EXECUTOR response:
"you haven't provided a specific filename"
```

**Solution Implemented**:
Added explicit rule in guideline #3c:

```
*** FILE PATHS - Include in EVERY Task That Uses Them ***

❌ WRONG (path only in first task):
  task_1: "Validate path for processing" (no path!)
  task_2: "Check if document exists" (no path!)
  task_3: "Import the document" (no path!)

✅ RIGHT (path in every task):
  task_1: "Use builtin.validate_file_path(path='/abs/path/file.pdf', ...) to validate"
  task_2: "Use pdf_extract.check_file_exists(file_name='file.pdf') for /abs/path/file.pdf"
  task_3: "Use pdf_extract.process_document(file_path='/abs/path/file.pdf') to import"
```

**Key Principle**: Each task is STANDALONE - if it needs a file path, include the COMPLETE path in its description!

---

## Issue 3: Emojis Not Showing in Task Plans and Execution Logs

**Problem**: Agent JSON files had emoji field, but UI wasn't displaying them.

**Solution Implemented**:

1. **Added emoji field to AgentConfig dataclass**:
   - `mcp_client_for_ollama/agents/agent_config.py`
   - Added `emoji: Optional[str] = None` field
   - Updated `from_json_file()` to load emoji
   - Updated `to_dict()` to serialize emoji

2. **Updated task plan display** (`delegation_client.py:_display_plan`):
   ```python
   # Before:
   plan_text += f"{i}. [{agent_type}] {description}\n"

   # After:
   agent_emoji = config.emoji + " " if config.emoji else ""
   plan_text += f"{i}. [{agent_emoji}{agent_type}] {description}\n"
   ```

3. **Updated task execution display** (`delegation_client.py:_execute_task`):
   ```python
   # Before:
   print(f"Executing {task.id} ({agent_type})")

   # After:
   agent_emoji = config.emoji if config.emoji else ""
   agent_display = f"{agent_emoji} {agent_type}" if agent_emoji else agent_type
   print(f"Executing {task.id} ({agent_display})")
   ```

**Result**:
Task plans and execution logs now display agent emojis:
```
Task Plan:
1. [📂🔒 FILE_EXECUTOR] Validate file path...
2. [🐚💻 SHELL_EXECUTOR] Check if file exists...
3. [🧠💾 MEMORY_EXECUTOR] Update feature status...

Executing task_1 (📂🔒 FILE_EXECUTOR) <qwen2.5:32b>
```

---

## Files Modified

**Agent Definitions**:
- `mcp_client_for_ollama/agents/definitions/planner.json` - Enhanced guideline #3c with critical data field clarifications

**Core Code**:
- `mcp_client_for_ollama/agents/agent_config.py` - Added emoji field support
- `mcp_client_for_ollama/agents/delegation_client.py` - Display emojis in task plans and execution

**Version**:
- `pyproject.toml` → 0.28.1
- `mcp_client_for_ollama/__init__.py` → 0.28.1

**Documentation**:
- `CHANGELOG_v0.28.1.md` (this file)

---

## Impact

**Critical Fix**:
- PLANNER will now put ALL data (file paths, IDs, parameters) in `description` field
- Agents will receive complete data and stop hallucinating paths
- File paths will propagate to ALL tasks that need them

**Visual Enhancement**:
- Emojis now visible in task plans and execution logs
- Easier to identify which agent is handling each task
- Improved readability and user experience

**Backward Compatibility**:
- Fully backward compatible
- Agents without emoji field still work correctly
- No breaking changes

---

**Version**: 0.28.1
**Date**: 2025-12-26
**Category**: Critical Bug Fix + Visual Enhancement
**Breaking Changes**: None
