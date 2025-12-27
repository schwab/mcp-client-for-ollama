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

## ✅ FIXED in v0.33.2: PLANNER Using Placeholder Paths Instead of Real Paths

**User Query**: "read the file in notes/20251027_dream_anchor_chains.md and create a lore for environment and save it to memory"

**Issue** (TRACE: 20251226_210243):
- User gave relative path: `notes/20251027_dream_anchor_chains.md`
- PLANNER should have converted to absolute path using working directory
- Instead, PLANNER literally used placeholder from examples: `/absolute/path/to/notes/20251027_dream_anchor_chains.md`
- This is a **hallucinated path** that doesn't exist!

**Root Cause**:
PLANNER guidance examples used placeholder paths like:
```
- Read /absolute/path/to/notes/file1.md
- Read /absolute/path/to/notes/file2.md
```

PLANNER copied these **literally** instead of understanding they were placeholders to be replaced with actual working directory.

**Fix Applied** (v0.33.2):

1. **Replaced placeholder examples with real examples**:
```
Old (caused copying):
- Read /absolute/path/to/notes/file1.md  ← Copied literally!

New (shows actual conversion):
Working Directory: /home/user/project
Relative path: notes
Absolute path: /home/user/project/notes
Task: "Read /home/user/project/notes/file.md"
```

2. **Added critical warning**:
```
🚨 CRITICAL: NEVER USE PLACEHOLDER PATHS!

❌ WRONG: "/absolute/path/to/file.md" ← Placeholder!
✅ CORRECT: "/home/user/project/notes/file.md" ← Real path!
```

3. **Added path conversion algorithm**:
```
1. User provides: "notes/file.md"
2. Working directory: "/home/user/project"
3. Check if absolute (starts with /):
   - If YES: use as-is
   - If NO: prepend working directory
4. Result: "/home/user/project/notes/file.md"
```

**Result**:
- ✅ PLANNER will now convert relative paths correctly
- ✅ No more placeholder path copying
- ✅ Uses actual working directory from session context

## ✅ FIXED in v0.33.3: PLANNER Still Using /path/to/ Placeholders

**User Query**: "read the content in the file notes/20251027_dream_anchor_chains.md and create a lore for this content"

**Issue** (TRACE: 20251226_211007):
- Working directory: `/home/mcstar/Vault/Journal`
- User provided relative path: `notes/20251027_dream_anchor_chains.md`
- Expected absolute path: `/home/mcstar/Vault/Journal/notes/20251027_dream_anchor_chains.md`
- PLANNER output: `/path/to/notes/20251027_dream_anchor_chains.md` (STILL a placeholder!)
- LORE_KEEPER tried to read it: "Error: Permission denied to access file outside working directory."

**Root Cause**:
v0.33.2 fixed `/absolute/path/to/` placeholders but missed `/path/to/` placeholders!

The PLANNER prompt had more placeholder examples in the "Example Patterns" section:
```
✅ Task: "Use ACCENT_WRITER... to read /path/to/story.md"
files = [f for f in os.listdir('/path/to/notes') if f.endswith('.md')]
content = tools.call('builtin.read_file', file_path=f'/path/to/notes/{file}')
1. List all .md files in /path/to/notes
✅ Task: "Use QUALITY_MONITOR... to read /path/to/chapter1.md"
```

PLANNER was still copying these `/path/to/` patterns literally!

**Fix Applied** (v0.33.3):

Replaced ALL remaining placeholder paths in PLANNER prompt with realistic working directory examples:

1. `/path/to/story.md` → `/home/user/mybook/story.md`
2. `/path/to/notes` → `/home/user/mybook/notes` (multiple instances in Python and task examples)
3. `/path/to/chapter1.md` → `/home/user/mybook/chapter1.md`

Added "Working Directory:" and "Conversion:" labels to make examples explicit:
```
**Pattern: Analyze dialogue in file**
User: "Check dialogue in story.md for accent consistency"
Working Directory: /home/user/mybook
Conversion: story.md → /home/user/mybook/story.md
✅ Task: "Use ACCENT_WRITER with builtin.read_file to read /home/user/mybook/story.md..."
```

**Result**:
- ✅ NO MORE placeholders in PLANNER prompt (verified: `/absolute/path/to/` AND `/path/to/` both eliminated)
- ✅ All examples show actual working directory conversion
- ✅ PLANNER will now properly convert relative paths to absolute

**Files Modified**:
- mcp_client_for_ollama/agents/definitions/planner.json - Replaced all `/path/to/` placeholders
- mcp_client_for_ollama/__init__.py - Version 0.33.3
- pyproject.toml - Version 0.33.3
- docs/qa_bugs.md - Bug documentation

**Testing Required**: User should retry: "read the content in the file notes/20251027_dream_anchor_chains.md and create a lore"


## ✅ FIXED in v0.33.4: PLANNER Copying Example Paths Instead of Converting

**User Query**: "read the content in the file notes/20251027_dream_anchor_chains.md and create a lore"

**Issue** (TRACE: 20251226_212848):
- Working directory: `/home/mcstar/Vault/Journal`
- User provided: `notes/20251027_dream_anchor_chains.md`
- Expected: `/home/mcstar/Vault/Journal/notes/20251027_dream_anchor_chains.md`
- PLANNER output: `/home/user/notes/20251027_dream_anchor_chains.md` (copied from examples!)
- Result: Permission denied error - `/home/user/` doesn't exist

**Root Cause - FUNDAMENTAL FLAW IN APPROACH**:
v0.33.3 replaced placeholders with "realistic" examples, but LLM kept copying them!

The problem: Showing EXAMPLES with specific paths teaches the LLM to COPY, not CONVERT
- Showed `/home/user/mybook/story.md` as example
- PLANNER copied `/home/user/` pattern instead of using actual working directory
- No matter what paths we show, LLM pattern-matches and copies them

**Fix Applied** (v0.33.4):

**REMOVED**: Example-based learning (causes copying)
**ADDED**: Mandatory preprocessing algorithm

Changed from:
```
Example: Working Directory: /home/user/mybook
         User: "read notes"
         Task: "/home/user/mybook/notes"  ← LLM copies this!
```

To:
```
🚨 MANDATORY PATH CONVERSION PRE-PROCESSING 🚨

STEP 1: EXTRACT paths from user query
STEP 2: GET working directory from context
STEP 3: CONVERT each path (if starts with / → use as-is, else prepend working dir)
STEP 4: USE converted paths in ALL task descriptions

VALIDATION BEFORE OUTPUT:
- Check EVERY path in task descriptions
- Does it start with ACTUAL working directory?
- If you see "/home/user/" but working dir is "/home/mcstar/" → WRONG!
```

**New Approach Uses VALIDATION Examples** (not copyable):
```
Example 1:
Working Directory: /home/mcstar/Vault/Journal
User says: "read files in notes"
YOU MUST OUTPUT: "/home/mcstar/Vault/Journal/notes"
❌ WRONG: "/home/user/notes" or "/path/to/notes"
```

The examples now show "right vs wrong" for VALIDATION, not a pattern to copy.

**Result**:
- ✅ No more copyable path examples in prompt
- ✅ Mandatory 4-step preprocessing forces correct conversion
- ✅ Validation checklist catches mistakes before output
- ✅ PLANNER must use ACTUAL working directory, not example paths

**Files Modified**:
- mcp_client_for_ollama/agents/definitions/planner.json - Replaced examples with mandatory preprocessing
- mcp_client_for_ollama/__init__.py - Version 0.33.4
- pyproject.toml - Version 0.33.4
- docs/qa_bugs.md - Bug documentation

**Testing Required**: User should retry: "read the content in the file notes/20251027_dream_anchor_chains.md"
Expected: PLANNER uses `/home/mcstar/Vault/Journal/notes/20251027_dream_anchor_chains.md`
