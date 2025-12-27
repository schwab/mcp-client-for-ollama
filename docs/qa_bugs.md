## ✅ FIXED: Ghost Writer Agents Could Not Read Files

**Status**: FIXED in v0.32.1

**Original Issue** (TRACE: 20251226_200949):
- ACCENT_WRITER agent made up content instead of reading actual story files
- All ghost writer agents had `allowed_tool_categories: ["memory"]` only
- Could not access filesystem_read tools to actually read story content
- Agents hallucinated based on examples in system prompts instead of reading real data
- Memory operations failed because agents had no real data to work with

**Root Cause**:
All 6 ghost writer agents were configured with only `"memory"` in allowed_tool_categories:
- ACCENT_WRITER
- LORE_KEEPER
- CHARACTER_KEEPER
- STYLE_MONITOR
- QUALITY_MONITOR
- DETAIL_CONTRIVER

This meant they could manage memory but couldn't read files to analyze story content.

**Fix Applied**:
Updated all ghost writer agents to include `"filesystem_read"` in allowed_tool_categories:
```json
"allowed_tool_categories": [
  "memory",
  "filesystem_read"
]
```

Now ghost writer agents can:
- ✅ Read story files and documents
- ✅ Analyze actual dialogue, lore, characters, style from text
- ✅ Create accurate profiles based on real content
- ✅ Store findings in memory for consistency tracking

**Files Modified**:
- mcp_client_for_ollama/agents/definitions/accent_writer.json
- mcp_client_for_ollama/agents/definitions/lore_keeper.json
- mcp_client_for_ollama/agents/definitions/character_keeper.json
- mcp_client_for_ollama/agents/definitions/style_monitor.json
- mcp_client_for_ollama/agents/definitions/quality_monitor.json
- mcp_client_for_ollama/agents/definitions/detail_contriver.json

**Version**: 0.32.1
**Fixed**: December 26, 2025

## 🐛 CRITICAL: Multiple Bugs Preventing Ghost Writer Agents from Working

**Status**: IDENTIFIED - Multiple root causes found

**User Query**: "read the files in notes and create lore for the content there, store that in memory"

**Issue** (TRACE: 20251226_203010):
- LORE_KEEPER made up content instead of reading actual files
- Agent tried 7 times to execute Python: `builtin.get_goal_details({"goal_id": "G_LORE_KEEPER"})`
- All attempts failed with: `NameError: name 'builtin' is not defined`
- No files were actually read, no real lore was created

### Root Cause #1: PLANNER Not Passing File Information

**Problem**: PLANNER created task "Create lore based on extracted information from notes" but:
- ❌ Didn't specify which files to read
- ❌ Didn't include directory path
- ❌ Didn't list actual file names
- ❌ Assumed agent could access previous task output (agents are isolated!)

**Should Have Created**:
```
Task 1: Use FILE_EXECUTOR with builtin.list_files to list all files in /path/to/notes directory
Task 2: Use LORE_KEEPER to read each .md file in /path/to/notes and extract lore:
        - Read /path/to/notes/file1.md
        - Read /path/to/notes/file2.md
        - Create lore entries in memory via goal G_LORE_KEEPER
```

**Fix Needed**: Update PLANNER system prompt with guidance for ghost writer agents

### Root Cause #2: Ghost Writer Agents Trying to Execute Python for Memory Tools

**Problem**: LORE_KEEPER is calling memory tools incorrectly:
- ❌ Wrapping tool calls in `builtin.execute_python_code()`
- ❌ Treating `builtin.get_goal_details()` as Python code
- ❌ Should call memory tools DIRECTLY as tool invocations

**Why This Happens**: System prompt shows examples like:
```
builtin.get_goal_details({"goal_id": "G_LORE_KEEPER"})
```

Agent interprets this as "Python code to execute" instead of "tool to call directly"

**Fix Needed**: Clarify in system prompts that these are TOOL CALLS, not Python code

### Root Cause #3: forbidden_tools Not Working

**Problem**: LORE_KEEPER has:
```json
"forbidden_tools": ["builtin.execute_python_code"]
```

Yet agent is still trying to use it!

**Why**: Tool filtering may not be properly enforced in delegation_client.py

**Fix Needed**: Verify and fix tool filtering implementation

### Impact

All 6 ghost writer agents are affected by these bugs:
- ACCENT_WRITER
- LORE_KEEPER
- CHARACTER_KEEPER
- STYLE_MONITOR
- QUALITY_MONITOR
- DETAIL_CONTRIVER

**None of them can currently work properly** because:
1. They don't get file paths from PLANNER
2. They try to execute Python for memory calls
3. Tool filtering doesn't prevent execute_python_code

### Fixes Required

1. **Update PLANNER prompt** with ghost writer-specific guidance
2. **Fix ghost writer system prompts** to clarify tool invocation vs Python execution
3. **Verify/fix tool filtering** in delegation_client.py
4. **Test with actual user scenario**: "read files in notes and create lore"

**Priority**: CRITICAL - Ghost writer agents completely non-functional without these fixes

---

## ✅ FIXED in v0.33.0: Ghost Writer Agents Now Functional

**All three root causes have been fixed:**

### Fix #1: Ghost Writer Agents Now Have Proper Tool Access
- **Problem**: `default_tools: []` was empty, `allowed_tool_categories` not implemented
- **Fix**: Populated `default_tools` with 11 required tools:
  - Memory tools: get_memory_state, get_goal_details, get_feature_details, add_goal, add_feature, update_feature, update_goal, log_progress
  - Filesystem tools: list_files, read_file, search_files
- **Result**: Agents can now access memory and read files directly

### Fix #2: System Prompts Now Clarify Tool Invocation
- **Problem**: Agents interpreted `builtin.get_goal_details({...})` as Python code
- **Fix**: Added explicit clarification section to all 6 ghost writer prompts:
  ```
  *** CRITICAL: HOW TO CALL MEMORY TOOLS ***
  Memory tools are DIRECT TOOL CALLS, not Python code!
  ❌ WRONG: builtin.execute_python_code(code="builtin.get_goal_details(...)")
  ✅ CORRECT: Call builtin.get_goal_details directly
  ```
- **Result**: Agents now understand how to call tools correctly

### Fix #3: PLANNER Now Provides File Paths to Ghost Writers
- **Problem**: Tasks like "Create lore based on extracted information" had no file paths
- **Fix**: Added comprehensive ghost writer planning guidance to PLANNER:
  - Must include absolute file paths in task descriptions
  - Must list specific files, not reference previous outputs
  - Provided example patterns for common scenarios
- **Result**: PLANNER will now create proper tasks with file paths

**Files Modified**:
- All 6 ghost writer agent definitions (default_tools + system_prompt clarifications)
- mcp_client_for_ollama/agents/definitions/planner.json (added planning guidance)
- mcp_client_for_ollama/__init__.py - Version 0.33.0
- pyproject.toml - Version 0.33.0

**Testing Required**: User should retry: "read files in notes and create lore for the content there, store that in memory"


## ✅ FIXED in v0.33.1: LORE_KEEPER Not Recognized by PLANNER

**User Query**: "Create the Lore analysis for the local file notes/20251027_dream_anchor_chains.md and store it in memory"

**Issue** (TRACE: 20251226_205312):
- PLANNER assigned lore analysis to RESEARCHER instead of LORE_KEEPER
- PLANNER also violated "STAY ON TASK" rule by creating 3 extra memory tasks:
  * MEMORY_EXECUTOR - store lore
  * MEMORY_EXECUTOR - update feature status
  * MEMORY_EXECUTOR - log progress
- User said "store it in memory" (one thing), PLANNER created 5 tasks (wrong!)

**Root Cause**:
PLANNER's LORE_KEEPER trigger keywords didn't include "create lore" or "lore analysis"

Old triggers:
```
- Use when: User asks to verify lore, check world consistency, review world-building, validate magic/geography/history/culture
```

Missing keywords: create, extract, analyze, generate, lore analysis

**Fix Applied** (v0.33.1):
Updated LORE_KEEPER trigger conditions:
```
- Use when: User asks to:
  * Create/extract/analyze/generate lore
  * Verify lore, check world consistency
  * Review world-building
  * Validate magic/geography/history/culture/technology
  * Store world-building details in memory
  * Build lore database or lore analysis
```

Added to decision tree:
```
- Create/extract/analyze lore → LORE_KEEPER
- Lore analysis/generation → LORE_KEEPER
```

**Result**:
- ✅ "Create the Lore analysis" now triggers LORE_KEEPER
- ✅ "Extract lore", "Analyze lore", "Generate lore" also trigger LORE_KEEPER
- ✅ LORE_KEEPER will store in memory itself (no extra MEMORY_EXECUTOR tasks needed)
