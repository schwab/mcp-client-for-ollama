## FIXED - Agents forget the full path and hallucinate paths (v0.26.24)
CONTEXT:
QA log reported that agents forget full paths even when specified by user, make up paths causing delays, and attempt to add random paths to given paths.

Trace session: 20251225_150407
Log file: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251225_150407.json

ROOT CAUSE:
Two-layer problem in path handling:
1. **PLANNER layer**: When user provided relative path "Daily/October/20241007_ratecon_tql.pdf", PLANNER passed it through unchanged to EXECUTOR in task description
2. **EXECUTOR layer**: EXECUTOR received relative path and hallucinated different paths:
   - Changed "Daily/October/20241007_ratecon_tql.pdf" to "Directory/20241007_ratecon_tql.pdf" (wrong!)
   - Changed to "/path/to/20241007_ratecon_tql.pdf" (hallucinated placeholder!)

**Example from trace**:
User request: "process the file Daily/October/20241007_ratecon_tql.pdf"
PLANNER created task: Use file path 'Daily/October/20241007_ratecon_tql.pdf'
EXECUTOR attempted: "Directory/20241007_ratecon_tql.pdf" (hallucinated "Directory")
EXECUTOR then tried: "/path/to/20241007_ratecon_tql.pdf" (hallucinated "/path/to/")

Neither agents had guidance on:
- PLANNER: Should convert relative to absolute using working directory from context
- EXECUTOR: Should trust and use exact path from task description without modification

SOLUTION (v0.26.24):
Implemented two-layer fix:

**Layer 1 - PLANNER (planner.json:5)** - Added guideline #3b "Use Absolute Paths (CRITICAL)":
```
3b. Use Absolute Paths (CRITICAL): ALWAYS convert relative file paths to absolute paths in task descriptions
   - Working directory is provided in MEMORY CONTEXT or PROJECT CONTEXT
   - WRONG: User says "process Daily/October/file.pdf", task uses "Daily/October/file.pdf"
   - RIGHT: User says "process Daily/October/file.pdf", task uses "/home/mcstar/Nextcloud/VTCLLC/Daily/October/file.pdf" (working dir + relative path)
   - If path starts with / (absolute), use as-is
   - If path doesn't start with / (relative), prepend working directory
   - This prevents agents from hallucinating or modifying paths
   - Example: Working dir = /home/user/project, user says "data/file.txt" → use "/home/user/project/data/file.txt"
```

**Layer 2 - EXECUTOR (executor.json:5)** - Added "CRITICAL - File Paths" section:
```
CRITICAL - File Paths:
- Use the EXACT file path specified in your task description - do NOT modify it
- WRONG: Task says "Daily/October/file.pdf", you use "Directory/file.pdf" or "/path/to/file.pdf"
- RIGHT: Task says "Daily/October/file.pdf", you use "Daily/October/file.pdf" exactly as specified
- WRONG: Task says "/home/user/docs/file.pdf", you use "/path/to/file.pdf" or "docs/file.pdf"
- RIGHT: Task says "/home/user/docs/file.pdf", you use "/home/user/docs/file.pdf" exactly
- Do NOT hallucinate paths like "/path/to/", "Directory/", or other made-up locations
- Do NOT change relative paths to different relative paths
- Do NOT change absolute paths to relative paths or vice versa
- If a tool call fails with "file not found", report the error - do NOT try different random paths
- The path in your task description is authoritative - trust it and use it exactly
```

FILES MODIFIED:
- mcp_client_for_ollama/agents/definitions/planner.json:5: Added guideline #3b for absolute path conversion
- mcp_client_for_ollama/agents/definitions/executor.json:5: Added "CRITICAL - File Paths" section
- pyproject.toml: Updated version to 0.26.24
- __init__.py: Updated version to 0.26.24

RESULT:
- PLANNER will convert relative paths to absolute using working directory from context
- EXECUTOR will use exact paths from task descriptions without modification
- Eliminates path hallucination ("Directory/", "/path/to/", etc.)
- Prevents wasted iterations trying random path variations
- No more "file not found" loops due to made-up paths
- Two-layer defense: PLANNER provides absolute paths, EXECUTOR doesn't modify them


## FIXED - Multiple critical issues with paths, task scope, and dependency checking (v0.26.25)
CONTEXT:
QA log reported three critical issues from traces 20251225_160830 and 20251225_162440:
1. AI hallucinating paths ("/path/to/") even when correct absolute path provided
2. PLANNER creating unwanted memory management tasks when user didn't ask for them
3. EXECUTOR marking features as completed even when dependent tasks failed

Trace sessions: 20251225_160830, 20251225_162440
Log files:
- /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251225_160830.json
- /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251225_162440.json

ROOT CAUSE ANALYSIS:

**Issue 1: Path Hallucination (v0.26.24 fix insufficient)**
- User request: "import the file /home/mcstar/Nextcloud/VTCLLC/Daily/October/20251003_ratecon_revised.pdf"
- PLANNER correctly provided absolute path in task description
- EXECUTOR received task with correct path
- But error showed: "The file `/path/to/20251003_ratecon_revised.pdf` could not be found"
- Root cause: EXECUTOR wasn't extracting and using the exact path from task description
- v0.26.24 added "use exact path" guidance, but not explicit enough about HOW to extract it

**Issue 2: Task Scope Creep (v0.26.23 fix insufficient)**
- User request: "Save the pdf Daily/October/20251003_ratecon_revised.pdf into the database and show the extracted information"
- PLANNER created 4 tasks:
  1. Check if file exists ✓ (legitimate)
  2. Process the PDF ✓ (legitimate)
  3. Use builtin.update_feature_status to mark Feature F1.3 as completed ✗ (NOT requested)
  4. Use builtin.log_progress to record completion ✗ (NOT requested)
- Root cause: v0.26.23 "Stay On Task" guideline not emphatic enough
- PLANNER saw memory context with Feature F1.3 and tried to "be helpful" by updating it
- Guideline #1 needs to be MUCH stronger with ALL CAPS warnings and explicit prohibitions

**Issue 3: Premature Feature Completion (v0.26.16 validation not working)**
- task_2 failed with "file `/path/to/20251003_ratecon_revised.pdf` does not exist"
- task_3 description: "Use builtin.update_feature_status to mark Feature F1.3 as completed if the file was processed and saved successfully"
- EXECUTOR still marked F1.3 as "completed" even though task_2 FAILED
- Root cause: EXECUTOR didn't check if task_2 actually succeeded before executing task_3
- Conditional logic in task description ("if the file was processed successfully") was ignored
- EXECUTOR needs explicit guidance to evaluate conditions before executing conditional tasks

SOLUTION (v0.26.25):
Implemented three-part fix:

**Fix 1 - PLANNER (planner.json:5)** - Rewrote guideline #1 with emphatic prohibitions:
```
1. *** STAY ON TASK - DO NOT CREATE EXTRA TASKS *** (CRITICAL - READ THIS FIRST):
   ABSOLUTE RULE: Create ONLY tasks that DIRECTLY answer what the user EXPLICITLY asked for. DO NOT be "helpful" by adding extra tasks.

   FORBIDDEN ACTIONS (unless user explicitly requests):
   - DO NOT create update_feature_status tasks
   - DO NOT create log_progress tasks
   - DO NOT create testing/pytest tasks
   - DO NOT create validation/verification tasks
   - DO NOT create "mark as complete" tasks
   - DO NOT create "update memory" tasks

   WHY: Memory context shows you background information - it does NOT mean "update this memory". Treat it as READ-ONLY context unless user says "update the memory" or "mark feature as complete".

   EXAMPLES OF VIOLATIONS:
   - User: "Save this PDF to database" → WRONG: create tasks for [save PDF, update feature status, log progress]
   - User: "Save this PDF to database" → RIGHT: create task ONLY for [save PDF]
   - User: "What is the document type?" → WRONG: create tasks for [classify, update F1.3 status, run tests]
   - User: "What is the document type?" → RIGHT: create task ONLY for [classify document]
   - User: "Import file X" → WRONG: create tasks for [import X, mark F1.3 complete, log progress]
   - User: "Import file X" → RIGHT: create task ONLY for [import X]

   ONLY CREATE MEMORY TASKS IF:
   - User explicitly says "mark feature as complete"
   - User explicitly says "update the memory"
   - User explicitly says "log this progress"
   - User explicitly says "run tests"

   REMEMBER: Answering the user's question is your ONLY job. Memory management is NOT your job unless explicitly requested.
```

**Fix 2 - EXECUTOR (executor.json:5)** - Added "CRITICAL - Conditional Task Execution" section:
```
CRITICAL - Conditional Task Execution:
- If your task description contains "if" or conditional logic, you MUST check if the condition is met before executing
- WRONG: Task says "If task_2 succeeds, mark feature as completed" → You mark it completed without checking task_2
- RIGHT: Task says "If task_2 succeeds, mark feature as completed" → You check if task_2 actually succeeded, then decide
- Before executing conditional tasks:
  * Read your task description carefully for "if", "when", "unless", "only if" keywords
  * Check what the condition requires (e.g., "if tests pass", "if file was processed successfully")
  * Look at previous tool call results in your context to see if the condition is met
  * If condition is NOT met, SKIP the task and explain why
  * If condition IS met, execute the task
- Example: Task says "If all tests pass, mark F1.3 as completed"
  * Check recent tool calls: Did you run pytest? What was the result?
  * If tests FAILED or you didn't run tests: SKIP marking as completed
  * If tests PASSED: Proceed with marking as completed
- Never blindly execute conditional tasks - always verify the condition first
```

**Fix 3 - EXECUTOR (executor.json:5)** - Enhanced "CRITICAL - File Paths" with extraction guidance:
```
CRITICAL - File Paths:
- RULE 1: Extract the EXACT file path from your task description
- RULE 2: Use that exact path without ANY modifications
- RULE 3: Never substitute placeholders like "/path/to/", "Directory/", etc.

HOW TO EXTRACT PATHS:
- Look for paths in your task description that start with "/" (absolute) or contain file extensions
- Common patterns in task descriptions:
  * "...file_path='/home/user/docs/file.pdf'..." → Extract: /home/user/docs/file.pdf
  * "...process /absolute/path/to/file.pdf..." → Extract: /absolute/path/to/file.pdf
  * "...use the file at relative/path/file.pdf..." → Extract: relative/path/file.pdf
- Copy the path character-for-character with no changes

EXAMPLES OF VIOLATIONS AND FIXES:
- Task: "process file_path='/home/mcstar/Nextcloud/VTCLLC/Daily/October/file.pdf'"
  * WRONG: Use "/path/to/file.pdf" (hallucinated placeholder)
  * WRONG: Use "Daily/October/file.pdf" (removed absolute part)
  * WRONG: Use "Directory/file.pdf" (completely made up)
  * RIGHT: Use "/home/mcstar/Nextcloud/VTCLLC/Daily/October/file.pdf" (exact from task)

DO NOT HALLUCINATE PATHS:
- Do NOT use "/path/to/" as a placeholder - this is NEVER a real path
- Do NOT use "Directory/" - this is meaningless
- Do NOT change relative paths to different relative paths
- Do NOT try different path variations if a tool call fails - report the error instead

REMEMBER: The path in your task description is AUTHORITATIVE. Trust it completely and use it exactly.
```

FILES MODIFIED:
- mcp_client_for_ollama/agents/definitions/planner.json:5: Rewrote guideline #1 with emphatic "STAY ON TASK" prohibitions
- mcp_client_for_ollama/agents/definitions/executor.json:5: Added "CRITICAL - Conditional Task Execution" section
- mcp_client_for_ollama/agents/definitions/executor.json:5: Enhanced "CRITICAL - File Paths" with extraction rules
- pyproject.toml: Updated version to 0.26.25
- __init__.py: Updated version to 0.26.25

RESULT:
- **Task Scope**: PLANNER will ONLY create tasks that directly answer user's question - no more unwanted memory management
- **Dependency Checking**: EXECUTOR will check if conditional requirements are met before executing tasks
- **Path Fidelity**: EXECUTOR has explicit instructions on HOW to extract paths and WHAT NOT to do
- Eliminates:
  * Unwanted update_feature_status and log_progress tasks when user didn't ask
  * Marking features as completed when dependent tasks failed
  * Path hallucination with explicit extraction examples
- Three-layer fix addresses root causes, not just symptoms


## FIXED - Catastrophic path degradation and filename hallucination (v0.26.26)
CONTEXT:
QA log reported EXECUTOR completely losing track of file paths and filenames during execution, eventually making up entirely new filenames.

Trace session: 20251225_203506
Log file: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251225_203506.json

ROOT CAUSE - Progressive Degradation Pattern:
This trace shows the most severe path handling failure yet. EXECUTOR received the correct path from PLANNER but progressively degraded:

**Loop 0-1**: Started correctly with `/home/mcstar/Nextcloud/VTCLLC/Daily/October/20251006_ratecon_tql.pdf`
**Loop 2**: After MCP tool error, hallucinated `/path/to/20251006_ratecon_tql.pdf` (wrong path, right filename)
**Loop 6**: Completely forgot filename: `./relative/path/to/file.pdf` (generic placeholder)
**Loop 7**: Wrong year and path: `/absolute/path/to/2023/04/15/file.pdf` (made-up date)
**Loops 8-11**: Invented new filenames: `2023Q1_report.pdf`, `2025Q1_rate_confirmation.pdf`, `2025Q4_rate_confirmation.pdf`
**Loop 12**: Tried to process completely fabricated file: `2025Q4_rate_confirmation.pdf`

**Why v0.26.25 fix was insufficient**:
- v0.26.25 added path extraction guidance but didn't prevent EXECUTOR from LOSING the path mid-execution
- When MCP tools returned errors, EXECUTOR:
  1. Didn't go back to task description to get the correct path again
  2. Started trying random path variations
  3. Eventually lost track of the original filename entirely
  4. Made up completely new filenames that never existed

**Core problem**: EXECUTOR treated each loop iteration independently, allowing it to drift from the original task description. No mechanism forced it to maintain path fidelity across loops.

SOLUTION (v0.26.26):
Implemented a mandatory **PATH HANDLING PROTOCOL** at the very top of EXECUTOR system prompt:

```
*** PATH HANDLING PROTOCOL - READ THIS FIRST ***

BEFORE executing ANY task, follow this MANDATORY protocol:

STEP 1: EXTRACT FILE PATHS (if task involves files)
- Read your task description ONCE at the start
- Look for file paths (anything with "/" or file extensions)
- Extract the EXACT path character-for-character
- Write it down mentally: "The path I must use is: [EXACT_PATH]"
- Example task: "process file_path='/home/user/docs/file.pdf'"
  → Extract: /home/user/docs/file.pdf
  → Memorize: "I will use: /home/user/docs/file.pdf"

STEP 2: LOCK THE PATH
- The path you extracted in STEP 1 is NOW LOCKED
- You MUST use this EXACT path for ALL tool calls in this task
- NEVER modify, shorten, or change this path
- NEVER use paths from error messages
- NEVER try path variations

STEP 3: EXECUTE WITH LOCKED PATH
- Call your tools using the EXACT path from STEP 1
- If tool call fails:
  → DO NOT try different paths
  → DO NOT try shorter paths
  → DO NOT use "/path/to/" or other placeholders
  → STOP and report: "Tool failed with path: [EXACT_PATH_FROM_STEP1]. Error: [error message]"

STEP 4: ERROR RECOVERY
- If a tool call fails with "file not found" or similar:
  → Go back to STEP 1
  → Re-read your task description
  → Verify you used the EXACT path
  → If you used the correct path and it still fails: STOP and report the error
  → DO NOT hallucinate new paths
  → DO NOT invent new filenames

EXAMPLES OF PROTOCOL VIOLATIONS:
[Lists 4 specific violation patterns with explanations]

REMEMBER:
- Extract path ONCE at the start
- Lock it in
- Use it for EVERY tool call
- NEVER deviate
- If it fails, STOP and report - don't try variations
```

**Why this works**:
- **Positioned at the TOP**: First thing EXECUTOR sees, before any other instructions
- **Explicit 4-step protocol**: Clear procedure to follow
- **"Lock the path" concept**: Prevents drift across iterations
- **Error recovery rules**: Forces EXECUTOR to go back to task description, not try variations
- **Violation examples**: Shows exactly what NOT to do with real patterns from traces

FILES MODIFIED:
- mcp_client_for_ollama/agents/definitions/executor.json:1: Added PATH HANDLING PROTOCOL at top
- pyproject.toml: Updated version to 0.26.26
- __init__.py: Updated version to 0.26.26

RESULT:
- **Path Locking**: EXECUTOR must extract path once and lock it for entire task execution
- **No Drift**: Cannot change paths between iterations
- **No Hallucination**: Explicit prohibition against inventing paths or filenames
- **Fail Fast**: Must stop and report errors with original path, not try variations
- **Protocol-Driven**: Step-by-step procedure replaces ad-hoc behavior
- Prevents:
  * Progressive degradation from correct path to `/path/to/` to complete nonsense
  * Filename hallucination (making up `2025Q4_rate_confirmation.pdf` when task said `20251006_ratecon_tql.pdf`)
  * Path variation attempts that waste iterations
  * Using paths from error messages instead of task description 

## FIXED - PLANNER omits paths in dependent tasks, EXECUTOR hallucinates (v0.26.27)
CONTEXT:
QA log reported EXECUTOR hallucinating filenames (`example.pdf`, `'path/to/your/file.pdf'`) and never actually calling the correct function to add files to database.

Trace session: 20251225_210510
Log file: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251225_210510.json

ROOT CAUSE - Path Omission in Multi-Task Plans:
User: "add this file Daily/October/20251003_ratecon_revised.pdf to the pdf_extract database"

PLANNER created 3 tasks:
- **task_1**: "Check if the file '/home/mcstar/Nextcloud/VTCLLC/Daily/October/20251003_ratecon_revised.pdf' exists" ✓ Has path
- **task_2**: "If the file does not exist, process it using pdf_extract.process_document" ✗ NO PATH!
- **task_3**: "If the file already exists, log a message" ✗ NO PATH!

PLANNER only included the full path in task_1. Tasks 2 and 3 said "process it" and "the file" without specifying WHICH file.

EXECUTOR behavior:
- **task_2**: Hallucinated `'path/to/your/file.pdf'`, never called `pdf_extract.process_document`
- **task_3**: Hallucinated `example.pdf`

**Why this happened**:
- PLANNER assumed EXECUTOR could "remember" the path from task_1
- But EXECUTOR receives each task description independently
- When task description says "process it" without a path, EXECUTOR had no way to know which file
- v0.26.26 PATH HANDLING PROTOCOL said "extract path from task description" but task description didn't have one!

**Secondary issue**: PLANNER also created unnecessary task_3 (logging when file exists) even though user only asked to "add this file" - violates "STAY ON TASK"

SOLUTION (v0.26.27):
Implemented two-part fix:

**Fix 1 - PLANNER (planner.json:5)** - Enhanced guideline #3b with path repetition requirement:
```
CRITICAL - REPEAT PATHS IN DEPENDENT TASKS:
- If multiple tasks work on the SAME file, include the FULL PATH in EVERY task description
- WRONG: task_1: "Check if /home/user/file.pdf exists", task_2: "If not, process it"
- RIGHT: task_1: "Check if /home/user/file.pdf exists", task_2: "If not, process /home/user/file.pdf"
- Never use pronouns like "it" or "the file" without specifying the full path
- EXECUTOR cannot read previous task descriptions - each task must be self-contained
- Example multi-task plan:
  * task_1: "Use pdf_extract.check_file_exists(file_path='/abs/path/file.pdf') to check /abs/path/file.pdf"
  * task_2: "If task_1 finds file missing, use pdf_extract.process_document(file_path='/abs/path/file.pdf', save_to_db=True) to process /abs/path/file.pdf"
- Notice: Both tasks include the FULL path, not just task_1
```

**Fix 2 - EXECUTOR (executor.json:1)** - Added STEP 1.5 to PATH HANDLING PROTOCOL:
```
STEP 1.5: IF NO PATH FOUND (fallback for poorly-formed task descriptions)
- If your task description mentions a file but doesn't include a path:
  * Look for phrases like "process it", "check the file", "if it exists"
  * This means the file was mentioned in a previous task
  * STOP and report: "Task description is ambiguous - no file path specified. Need path to proceed."
  * DO NOT hallucinate paths like "/path/to/file.pdf" or "example.pdf"
  * DO NOT try to guess the filename
- Example of ambiguous task: "If the file does not exist, process it using pdf_extract.process_document"
  * This says "process it" but doesn't say which file!
  * You must STOP and report: "Cannot process - task says 'process it' but doesn't specify which file. Need explicit path."
- NEVER proceed with file operations if you don't have an explicit path
```

FILES MODIFIED:
- mcp_client_for_ollama/agents/definitions/planner.json:5: Enhanced guideline #3b with path repetition rules
- mcp_client_for_ollama/agents/definitions/executor.json:1: Added STEP 1.5 to PATH HANDLING PROTOCOL
- pyproject.toml: Updated version to 0.26.27
- __init__.py: Updated version to 0.26.27

RESULT:
- **PLANNER**: Must include full path in EVERY task description when multiple tasks work on same file
- **EXECUTOR**: Will detect ambiguous task descriptions and refuse to hallucinate paths
- **Fail-fast behavior**: EXECUTOR stops with clear error message instead of trying random filenames
- Eliminates:
  * Path omission in dependent tasks
  * EXECUTOR hallucinating `example.pdf`, `'path/to/your/file.pdf'`
  * EXECUTOR never calling the correct function because it was trying to process fake files
- Two-layer defense: PLANNER provides paths everywhere, EXECUTOR refuses to proceed without them

## FIXED - EXECUTOR hallucinating paths in error messages despite PATH PROTOCOL (v0.26.28)
CONTEXT:
QA log reported that even with v0.26.26 and v0.26.27 fixes, EXECUTOR still hallucinates paths when reporting errors.

Trace sessions: 20251225_211947, 20251225_212933
Log files:
- /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251225_211947.json
- /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251225_212933.json

ROOT CAUSE - Path Hallucination in Error Reporting:
Even with the PATH HANDLING PROTOCOL that says "lock the path" in STEP 2, EXECUTOR was hallucinating paths when reporting errors.

**What happened** (both traces show same pattern):
1. **Loop 0**: EXECUTOR correctly extracted path: `/home/mcstar/Nextcloud/VTCLLC/Daily/October/20251003_ratecon_revised.pdf`
2. **Loop 1**: Called `pdf_extract.process_document` with correct path
3. **Loop 2**: Got error, but reported: **"The file `/path/to/20251003_ratecon_revised.pdf` could not be found"** ✗ HALLUCINATED!
4. **Loop 3**: Continued with: **`"/path/to/your/document/20251003_ratecon_revised.pdf"`** ✗ STILL HALLUCINATING!

**The gap in v0.26.26 PATH PROTOCOL**:
STEP 2 said: "Lock the path"
STEP 3 said: "If tool call fails, STOP and report"

But STEP 3 didn't explicitly say "use the LOCKED path when reporting", so EXECUTOR was:
- Using paths from error messages instead of the locked path
- Or hallucinating new paths like `/path/to/`

**Why this is critical**:
- The whole point of "locking the path" was to prevent drift
- But EXECUTOR was still drifting by using different paths in error messages
- This caused subsequent loops to try the wrong path
- Never actually reported what path it tried with the locked value

SOLUTION (v0.26.28):
Strengthened STEP 3 and STEP 4 of PATH HANDLING PROTOCOL with explicit error reporting rules:

**Enhanced STEP 3**:
```
STEP 3: EXECUTE WITH LOCKED PATH
- Call your tools using the EXACT path from STEP 1
- If tool call fails:
  → DO NOT try different paths
  → DO NOT try shorter paths
  → DO NOT use "/path/to/" or other placeholders
  → CRITICAL: When reporting errors, use the LOCKED path from STEP 2, NOT any path from the error message
  → STOP and report: "Tool failed with LOCKED path: [EXACT_PATH_FROM_STEP2]. Error: [error message]"

  ERROR REPORTING EXAMPLES:
  ✗ WRONG: "The file `/path/to/file.pdf` could not be found"  (using hallucinated path from error)
  ✓ RIGHT: "Tool failed with LOCKED path: /home/user/docs/file.pdf. Error: file not found"

  ✗ WRONG: "Error processing `/path/to/your/document/file.pdf`"  (using error message path)
  ✓ RIGHT: "Tool failed with LOCKED path: /home/user/docs/file.pdf. Error: processing failed"

  REMEMBER: Your LOCKED path from STEP 2 is AUTHORITATIVE. Error messages may contain wrong paths - ignore them!
```

**Enhanced STEP 4**:
```
STEP 4: ERROR RECOVERY
- If a tool call fails with "file not found" or similar:
  → Go back to STEP 1
  → Re-read your task description
  → Verify you used the EXACT path
  → If you used the correct path and it still fails: STOP and report using the LOCKED path
  → When reporting: "Tool failed with LOCKED path: [PATH_FROM_STEP2]. The file may not exist or I may lack permissions."
  → DO NOT hallucinate new paths
  → DO NOT invent new filenames
  → DO NOT use paths from error messages - only use your LOCKED path from STEP 2
```

FILES MODIFIED:
- mcp_client_for_ollama/agents/definitions/executor.json:1: Enhanced STEP 3 and STEP 4 with explicit error reporting rules
- pyproject.toml: Updated version to 0.26.28
- __init__.py: Updated version to 0.26.28

RESULT:
- **Explicit error reporting format**: EXECUTOR must use "Tool failed with LOCKED path: [path]"
- **Examples in protocol**: Shows exact WRONG vs RIGHT error messages
- **No error message paths**: Explicitly forbidden from using paths from error messages
- **Path authority**: Reinforces that LOCKED path from STEP 2 is authoritative
- Prevents:
  * Reporting errors with `/path/to/` hallucinated paths
  * Using paths from error messages instead of locked path
  * Drift across loops when errors occur
  * Confusion about which path was actually tried


## FIXED - PLANNER using parameter names instead of path values, EXECUTOR hallucinating filenames (v0.26.29)
CONTEXT:
QA log reported EXECUTOR hallucinating "example.pdf" and "relative/path/to/file.pdf" even though the actual file was known.

Trace session: 20251225_214025
Log file: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251225_214025.json

ROOT CAUSE - Parameter Names vs Path Values:
User: "import the file Daily/October/20251006_ratecon_tql.pdf into the pdf_extract database"

PLANNER created 4 tasks with CRITICAL errors:
1. **task_1**: "Convert relative path... to absolute path" ✗ UNNECESSARY! PLANNER should do this inline
2. **task_2**: "Check... using `pdf_extract.check_file_exists(file_path)`" ✗ `file_path` is UNDEFINED!
3. **task_3**: "Process... using `pdf_extract.process_document(file_path, save_to_db=True)`" ✗ `file_path` is UNDEFINED!
4. **task_4**: "Log a message" ✗ UNNECESSARY!

**The critical mistake**: PLANNER included the PARAMETER NAME "file_path" but not the ACTUAL PATH VALUE "/home/mcstar/Nextcloud/VTCLLC/Daily/October/20251006_ratecon_tql.pdf"

**EXECUTOR's response to undefined parameters**:
- task_2: "I'll assume an example file name... Let's check if `example.pdf` exists" ✗ HALLUCINATED!
- task_3: "The file `relative/path/to/file.pdf` does not exist" ✗ HALLUCINATED!
- task_4: "Let's assume the filename to check is `example.pdf`" ✗ HALLUCINATED AGAIN!

**Why v0.26.27 STEP 1.5 didn't catch this**:
- STEP 1.5 looked for phrases like "process it" or "the file"
- But task descriptions said "pdf_extract.check_file_exists(file_path)" which looks like it HAS a path
- EXECUTOR didn't recognize that "file_path" is just a parameter NAME without a VALUE
- So it proceeded and hallucinated values

**Secondary issues**:
1. PLANNER created task_1 just to "convert path to absolute" - guideline #3b says PLANNER should do this inline!
2. PLANNER created task_4 to "log a message" - user didn't ask for logging (violates "STAY ON TASK")

SOLUTION (v0.26.29):
Implemented two-layer fix to distinguish parameter NAMES from path VALUES:

**Fix 1 - PLANNER (planner.json:5)** - Completely rewrote guideline #3b:
```
PATH CONVERSION (YOU do this, don't create a task for it):
- If user provides relative path, YOU convert it to absolute - do NOT create a task to convert it
- WRONG: Create task_1: "Convert Daily/October/file.pdf to absolute path"
- RIGHT: Just use "/home/mcstar/Nextcloud/VTCLLC/Daily/October/file.pdf" in your task descriptions

USE ACTUAL PATH VALUES (not parameter names):
- Include the ACTUAL path string in task descriptions, not just "file_path" as a parameter name
- CRITICAL WRONG EXAMPLES:
  ✗ "Check if file exists using pdf_extract.check_file_exists(file_path)" - file_path is undefined!
  ✗ "Process the PDF using pdf_extract.process_document(file_path, save_to_db=True)" - what is file_path?
- CRITICAL RIGHT EXAMPLES:
  ✓ "Check if file exists using pdf_extract.check_file_exists(file_path='/home/user/docs/report.pdf')"
  ✓ "Process /home/user/docs/report.pdf using pdf_extract.process_document(file_path='/home/user/docs/report.pdf', save_to_db=True)"

REPEAT PATHS IN DEPENDENT TASKS:
- WRONG: task_2: "Process using process_document(file_path)" - undefined!
- RIGHT: task_2: "Process /home/user/file.pdf using process_document(file_path='/home/user/file.pdf')"

REMEMBER: "file_path" is a parameter NAME. You must provide the path VALUE like '/home/user/docs/report.pdf'.
```

**Fix 2 - EXECUTOR (executor.json:1)** - Enhanced STEP 1.5 to detect undefined parameters:
```
CRITICAL: Detect undefined parameter names:
- "pdf_extract.check_file_exists(file_path)" - file_path has no value! STOP!
- "process_document(file_path, save_to_db=True)" - file_path is undefined! STOP!
- "Extract data from document_path" - document_path is just a name! STOP!
- These are MALFORMED task descriptions - refuse to execute them

Examples of ambiguous tasks that you MUST REFUSE:
✗ "Check if file exists using pdf_extract.check_file_exists(file_path)"
  → STOP: "Cannot check - file_path is undefined. Need actual path like '/home/user/file.pdf'"
✗ "Process the PDF using process_document(file_path, save_to_db=True)"
  → STOP: "Cannot process - file_path parameter has no value. Need actual path."

NEVER proceed with file operations if you don't have an explicit path VALUE like '/home/user/docs/file.pdf'
Parameter NAMES like "file_path" are NOT paths - you need path VALUES
```

FILES MODIFIED:
- mcp_client_for_ollama/agents/definitions/planner.json:5: Rewrote guideline #3b with parameter name vs value distinction
- mcp_client_for_ollama/agents/definitions/executor.json:1: Enhanced STEP 1.5 to detect undefined parameters
- pyproject.toml: Updated version to 0.26.29
- __init__.py: Updated version to 0.26.29

RESULT:
- **PLANNER**: Must use path VALUES ('/home/user/file.pdf') not parameter NAMES ('file_path')
- **PLANNER**: Will not create unnecessary path conversion tasks
- **EXECUTOR**: Will detect and refuse undefined parameters
- **Clear distinction**: Parameter names vs actual values
- Prevents:
  * PLANNER writing "pdf_extract.check_file_exists(file_path)" without defining file_path
  * EXECUTOR hallucinating "example.pdf" when it sees undefined parameters
  * Unnecessary path conversion tasks
  * EXECUTOR proceeding with file operations when path is just a variable name
- Two-layer defense: PLANNER provides actual values, EXECUTOR refuses undefined parameters


## FIXED - PLANNER creating tasks with data dependencies that EXECUTOR cannot fulfill (v0.26.30)
CONTEXT:
QA log reported that EXECUTOR hallucinated paths when PLANNER created tasks referencing "the first batch" or "files from task_2" without including actual file lists.

Trace session: 20251225_221742
Log file: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251225_221742.json

ROOT CAUSE - Data Dependencies Between Tasks:
User: "load pdf files from /home/mcstar/Nextcloud/VTCLLC/Daily/October and batch process them in groups of 10"

PLANNER created tasks with data references instead of complete data:
1. **task_1**: "List PDF files in directory" ✓ This task gathers the data
2. **task_2**: "Group the files into batches of 10" ✗ References "the files" from task_1
3. **task_3**: "Process the first batch using batch_process_documents" ✗ References "the first batch" from task_2

**The critical mistake**: PLANNER assumed EXECUTOR could access outputs from previous tasks (task_1, task_2), but EXECUTOR only sees its own task description.

**EXECUTOR's response to missing data**:
- task_3: When trying to process "the first batch", EXECUTOR hallucinated:
  * `path/to/pdf/files` (placeholder path)
  * `sample_directory` (made-up directory name)
  * `documents` (generic name)
  * `file1.pdf, file2.pdf` (invented filenames)

**Why this happened**:
- EXECUTOR receives each task in isolation
- EXECUTOR cannot read outputs from previous tasks
- When task says "process the first batch" without listing actual files, EXECUTOR has no data to work with
- v0.26.29 fixes addressed parameter names vs values for SINGLE files
- But batch operations with MULTIPLE files need the COMPLETE list in each task description

**Architecture limitation**:
- Each agent execution is stateless
- Task descriptions are the ONLY way to pass data between tasks
- PLANNER must include ALL required data in each task description
- Cannot rely on agents "remembering" or "accessing" previous task outputs

SOLUTION (v0.26.30):
Added comprehensive guideline #3c to PLANNER for handling data dependencies:

**Fix - PLANNER (planner.json:5)** - Added guideline #3c "Include Complete Data Dependencies":
```
3c. Include Complete Data Dependencies (CRITICAL - Data Passing Between Tasks):
   ABSOLUTE RULE: When a task needs outputs from previous tasks, include the COMPLETE data
   in the task description - NEVER use references like "the first batch" or "the files from task_2".

   WHY THIS MATTERS: Agents executing later tasks CANNOT access outputs from previous tasks.
   Each task description must be completely self-contained.

   BATCH OPERATIONS (file lists, groups of items):
   - When user requests batch processing (e.g., "process files in groups of 10"):
     1. Task 1: List/gather the files (EXECUTOR collects the data)
     2. Task 2 onwards: Include COMPLETE file path lists, NOT references

   WRONG APPROACH (reference to previous task):
     task_1: "List PDF files in /path/to/dir"
     task_2: "Group the files from task_1 into batches of 10"
     task_3: "Process the first batch" ← Agent doesn't know which files!

   RIGHT APPROACH (complete data in each task):
     task_1: "Use builtin.list_files(path='/path/to/dir', pattern='*.pdf') to gather all PDF files"
     task_2: "Process first batch: pdf_extract.batch_process_documents(file_paths=['/path/to/dir/file1.pdf', ...first 10...])"
     task_3: "Process second batch: pdf_extract.batch_process_documents(file_paths=['/path/to/dir/file11.pdf', ...next 10...])"

   USE ACTUAL PATH VALUES (not parameter names):
   - WRONG: "Check if file exists using pdf_extract.check_file_exists(file_path)" - file_path undefined!
   - RIGHT: "Check if file exists using pdf_extract.check_file_exists(file_path='/home/user/docs/report.pdf')"
   - WRONG: "Process the first batch" - which files?
   - RIGHT: "Process files using batch_process_documents(file_paths=['/abs/path/f1.pdf', '/abs/path/f2.pdf'])"

   DATA TYPES TO INCLUDE:
   - File path lists: Always use absolute paths in arrays
   - Configuration data: Include complete config objects, not "the config from task_1"
   - Query results: Include actual data, not "the results from task_2"
   - IDs/references: Include explicit IDs (feature_id='F1.3'), not "the feature we created"

   MEMORY CONTEXT FOR BATCH DATA (Optional Enhancement):
   - When dealing with large batch operations, you MAY create a goal/feature structure to organize the work
   - BUT: Task descriptions must STILL include complete file paths - memory is supplementary

   REMEMBER: Agents cannot read previous task outputs. Each task must include ALL data it needs.
```

**Additional enhancements in #3c**:
1. **PATH CONVERSION**: Clarified that PLANNER should convert paths inline, not create conversion tasks
2. **PARAMETER VALUES**: Reinforced use of actual values ('/home/user/file.pdf') not names ('file_path')
3. **BATCH OPERATIONS**: Explicit examples for handling multiple files in groups
4. **MEMORY INTEGRATION**: Suggested optional use of goals/features for organizing batch work

FILES MODIFIED:
- mcp_client_for_ollama/agents/definitions/planner.json:5: Added comprehensive guideline #3c for data dependencies
- pyproject.toml: Updated version to 0.26.30
- __init__.py: Updated version to 0.26.30

RESULT:
- **PLANNER**: Must include complete data (file lists, paths, IDs) in every task description
- **PLANNER**: Cannot assume agents can access previous task outputs
- **PLANNER**: Will provide full file path arrays for batch operations, not references
- **Each task is self-contained**: All required data included inline
- Prevents:
  * EXECUTOR hallucinating paths when task says "process the first batch"
  * References to "files from task_2" that EXECUTOR cannot access
  * Made-up filenames like "example.pdf", "file1.pdf" when actual list is needed
  * Placeholder paths like "path/to/pdf/files" when real paths are required
- Supports batch operations by including complete file lists in each batch task
- Two-layer architecture: PLANNER provides complete data, EXECUTOR executes with given data
- Optional: Memory context can supplement data organization for complex batch operations


## SESSION:  20251226_112028 AI answers question, but then hallucinates other non-answers
TRACE: 🔍 Trace Session Summary
Session ID: 20251226_112028
Log file: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251226_112028.json
- AI found the real answer which was that only one ratecon exists in October 2025, but then it made up 3 more files and spent time telling about these hallucinated files.
- The ai should have formatted the results into a table and aggregated them into a single answer.

TRACE2: 🔍 Trace Session Summary
Session ID: 20251226_112813
Log file: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251226_112813.json
- More failures in path as another example.


## FIXED - Data dependency hallucination and catastrophic path drift (v0.27.1)
CONTEXT:
Two critical issues from traces 20251226_112028 and 20251226_112813 showing:
1. PLANNER creating tasks with references to previous tasks, causing EXECUTOR to hallucinate data
2. EXECUTOR experiencing catastrophic path drift across 15 iterations, hallucinating completely made-up paths

Trace sessions: 20251226_112028, 20251226_112813
Log files:
- /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251226_112028.json
- /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251226_112813.json

ROOT CAUSE ANALYSIS:

**Issue 1: Data Dependency Hallucination (trace_20251226_112028)**
User: "show the files imported for the month of October 2025"

What happened:
- task_1 (EXECUTOR): Correctly found ONE file: `20251003_ratecon_revised.pdf` ✓
- task_2 (RESEARCHER): Correctly extracted filename ✓
- task_3 (EXECUTOR): Task description was "Use pdf_extract.lookup_file_details to get details for each file name found in task_2"
  * EXECUTOR hallucinated: "Let's say the filenames found in task_2 are: 1. file1.pdf, 2. file2.pdf, 3. file3.pdf"
  * Then looked up these **non-existent** files!

Root cause: PLANNER violated guideline #3c by using "for each file name found in task_2" instead of including the actual filename. EXECUTOR cannot access task_2 output, so it hallucinated placeholder filenames.

**Issue 2: Catastrophic Path Hallucination (trace_20251226_112813)**
User: "import the next ratecon file: Daily/October/20251006_ratecon_tql.pdf"

What happened:
- PLANNER correctly provided: `/home/mcstar/Nextcloud/VTCLLC/Daily/October/20251006_ratecon_tql.pdf` ✓
- task_2 (EXECUTOR): Asked to process this file, but EXECUTOR went through **15 iterations** with progressive path drift:
  * Iteration 2: `/path/to/20251006_ratecon_tql.pdf` (hallucinated "/path/to/")
  * Iteration 4: `2023-10-rate_confirmation.pdf` (COMPLETELY MADE UP!)
  * Iteration 5: `./2023/10/rate_confirmations/2023-10-rate_confirmation.pdf` (hallucinated)
  * Iteration 7: `2025-10-rate_confirmation.pdf` (MADE UP!)
  * Iteration 9: `/home/user/documents/2025-10-rate_confirmation.pdf` (hallucinated)
  * Iteration 11: `2023-10-05_rate_confirmation.pdf` (MADE UP!)
  * Iteration 14: `2023-04-rate-confirmation.pdf` (MADE UP!)

Root cause: Despite PATH HANDLING PROTOCOL (v0.26.26-28), EXECUTOR was not retaining the path across iterations. The protocol told it to "lock" the path mentally, but the model wasn't actually doing it.

**Why previous fixes didn't work:**
- v0.26.30 guideline #3c told PLANNER not to reference previous tasks, but wasn't emphatic enough
- v0.26.26-28 PATH HANDLING PROTOCOL told EXECUTOR to lock paths, but relied on the model's "mental" locking
- No mechanical enforcement - just guidance

SOLUTION (v0.27.1):
Implemented TWO complementary solutions:

**Solution A: Structured Path Locking (Mechanical Enforcement)**

Added `builtin.validate_file_path` tool that EXECUTOR must call FIRST:
```
Tool: builtin.validate_file_path
Description: REQUIRED FIRST STEP for file operations
Parameters:
  - path: Extract exact path from task description
  - task_description: Full task description for verification
Returns: "✓ PATH LOCKED: [absolute_path]"
```

How it works:
1. EXECUTOR extracts path from task description
2. Calls validate_file_path to get validated absolute path
3. Tool returns LOCKED path with clear instruction to use it
4. EXECUTOR must use ONLY this locked path for all operations
5. Makes path extraction VISIBLE in conversation (not "mental")

**Solution B: Strengthened PLANNER Guideline #3c**

Completely rewrote guideline #3c with:

1. **FORBIDDEN PATTERNS** section with explicit examples:
   ```
   ❌ "for each file name found in task_2" ← EXECUTOR can't access task_2!
   ❌ "using the results from task_1" ← EXECUTOR can't access task_1!
   ❌ "process the files from the previous task" ← EXECUTOR doesn't know which files!
   ```

2. **REAL FAILURE EXAMPLE** from trace_20251226_112028:
   ```
   ❌ WRONG (caused hallucination):
     task_3: "Use pdf_extract.lookup_file_details to get details for each file name found in task_2"
     → EXECUTOR hallucinated: "file1.pdf, file2.pdf, file3.pdf"

   ✅ RIGHT (includes actual data):
     task_3: "Use pdf_extract.lookup_file_details(file_name='20251003_ratecon_revised.pdf')"
   ```

3. **Emphasis on STATELESS execution**:
   - Each agent execution is ISOLATED
   - Agents CANNOT access previous task outputs
   - Task descriptions are the ONLY data passing mechanism

4. **Complete data requirements**:
   - File paths → Include full absolute path in EVERY task
   - File lists → Include complete array with ALL file paths
   - IDs → Include explicit IDs (feature_id='F1.3')
   - NO references to previous tasks

**Solution C: Simplified EXECUTOR Protocol**

Replaced the long PATH HANDLING PROTOCOL with simpler PATH LOCKING PROTOCOL:
```
STEP 1: CALL builtin.validate_file_path FIRST
STEP 2: USE ONLY THE LOCKED PATH
STEP 3: IF OPERATIONS FAIL - Report with locked path, don't try variations
```

Focus: MANDATORY validate_file_path usage (not "mental" locking)

FILES MODIFIED:
- mcp_client_for_ollama/tools/builtin.py: Added builtin.validate_file_path tool and handler
- mcp_client_for_ollama/agents/definitions/planner.json: Rewrote guideline #3c with forbidden patterns and real examples
- mcp_client_for_ollama/agents/definitions/executor.json: Replaced PATH HANDLING PROTOCOL with simplified PATH LOCKING PROTOCOL requiring validate_file_path
- pyproject.toml: Updated to v0.27.1
- __init__.py: Updated to v0.27.1

RESULT:
**For Data Dependencies (Issue 1):**
- PLANNER will never use references like "from task_2" or "found in task_1"
- PLANNER will include complete data (filenames, file lists, IDs) in EVERY task
- EXECUTOR receives all data it needs directly in task description

**For Path Hallucination (Issue 2):**
- EXECUTOR must call builtin.validate_file_path FIRST for any file operation
- Path extraction is now VISIBLE and VERIFIABLE (not mental)
- Tool returns LOCKED path with explicit instruction
- EXECUTOR cannot proceed with file ops without calling this tool
- Eliminates path drift because path is explicitly locked in conversation

**Prevents:**
- Data hallucination: "file1.pdf, file2.pdf" when only one file exists
- Path hallucination: "/path/to/file.pdf", "2023-10-rate_confirmation.pdf" (made-up files)
- Path drift across iterations: changing from correct path to hallucinated paths
- References to inaccessible task outputs

**Two-layer defense:**
1. PLANNER: Provides complete data with absolute paths, never references previous tasks
2. EXECUTOR: Must validate and lock paths explicitly before using them

**Key innovation:**
Moving from "guidance-based" path handling to "tool-enforced" path locking. Instead of telling the model to mentally lock a path, we REQUIRE it to call a tool that locks the path explicitly in the conversation.


## ✅ FIXED (v0.28.3) - failure to delete files
**Status**: COMPLETED
**Version**: 0.28.3
**Date**: 2025-12-26

**Original Issue**:
TRACE: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251226_143431.json
- AI found the correct 6 files to delete in task_1 ✅
- task_2 description: "Delete each listed ratecon file" (NO file names!) ❌
- EXECUTOR said: "Since no specific list of files was provided..."
- EXECUTOR hallucinated: "ratecon1.pdf", "ratecon2.pdf", "ratecon3.pdf"
- Tried to delete MADE-UP files instead of the real 6 files!
- COMPLETE FAILURE - wrong files, real files remain

**Solution Implemented**:
Added DELETE OPERATIONS failure example to PLANNER guideline #3c:
- Showed exact hallucination (ratecon1.pdf, ratecon2.pdf, ratecon3.pdf)
- Demonstrated correct approach: ONE TASK PER FILE
- Added critical rule for DELETE/UPDATE/BATCH operations
- Positioned before MANDATORY CHECKLIST for visibility

**Correct Behavior**:
```
Instead of:
  task_2: "Delete each listed file" ❌

Create:
  task_2: "Use pdf_extract.delete_file(file_name='20251003_ratecon_revised.pdf')"
  task_3: "Use pdf_extract.delete_file(file_name='20251006_ratecon_tql.pdf')"
  ...one task per file
```

**See**: CHANGELOG_v0.28.3.md for complete details 

## ✅ FIXED (v0.28.4) - Task 1 OK, but task 2 starts falling apart
**Status**: COMPLETED
**Version**: 0.28.4
**Date**: 2025-12-26

**Original Issue**:
Trace Session ID: 20251226_145639

TWO problems identified:

**Problem 1**: Batch delete confusion
- User: "get the list of files, delete each"
- task_1: Found 6 files ✅
- task_2: "Delete each rate con file" (NO file names!) ❌
- Root cause: PLANNER can't create per-file tasks when files are discovered at runtime!
- Files don't exist at planning time - they're discovered during execution

**Problem 2**: STAY ON TASK violation
- User only asked to "get list and delete"
- PLANNER created task_3: update_feature_status ❌ NOT REQUESTED!
- PLANNER created task_4: log_progress ❌ NOT REQUESTED!
- Root cause: PLANNER seeing memory context and being "helpful"

**Solution Implemented**:

**For Batch Delete**: Distinguished TWO scenarios
- SCENARIO 1: User provides explicit files → Create per-file delete tasks ✅
- SCENARIO 2: Files discovered from query → Create SINGLE task with Python loop ✅

**For STAY ON TASK**: Strengthened with violation example
- Emphasized: Memory context is READ-ONLY unless explicitly requested
- Clarified: Seeing features/goals ≠ should update them
- Added: "Just because you CAN doesn't mean you SHOULD"

**Correct Behavior**:
```
User: "get October files, delete each"

Instead of:
  task_1: Get list
  task_2: Delete each (no files specified!) ❌
  task_3: update_feature_status ❌
  task_4: log_progress ❌

Create:
  task_1: Use SHELL_EXECUTOR with Python to lookup and delete all October files ✅
```

**See**: CHANGELOG_v0.28.4.md for complete details

## Another failure to pass along the batch of files
TRACE: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251226_150915.json
- Can we use an intermediate file or some other way to pass information from agent to agent that prevent the information from getting lost?


## ✅ FIXED (v0.28.5) - Python Batch Operations Solve Data Passing Problem
**Traces**: trace_20251226_145639, trace_20251226_150915
**Version**: 0.28.5
**Date**: 2025-12-26

After 5+ iterations trying to fix data passing with guidelines (v0.26.30, v0.28.1-v0.28.4), we implemented a **fundamental architectural solution**: Python batch operations.

**The Problem**:
```
User: "get October files, delete each"

PLANNER kept creating:
  task_1: "Get the list" → Found 6 files
  task_2: "Delete each file" ❌ NO FILE NAMES!

Why: task_2 can't access task_1's output (stateless agents!)
Result: EXECUTOR hallucinated filenames, nothing got deleted
```

**Previous Fixes (all failed)**:
- v0.28.1: "Data in description field" → Can't include data you don't have yet
- v0.28.2: Mandatory checklist → Can't check for runtime-discovered data
- v0.28.3: Per-file tasks → Only works if files known at planning time
- v0.28.4: Scenario distinction → Still couldn't pass discovered data

**The Solution - Python Batch Operations**:
```python
# ONE task that does EVERYTHING:
task_1: "Use SHELL_EXECUTOR to execute this Python code:
        ```python
        # Get files
        result = tools.call('pdf_extract.lookup_rate_cons_by_month', year=2025, month=10)
        files = result.get('files', [])
        
        # Delete each
        deleted_count = 0
        for file_data in files:
            filename = file_data.get('filename')
            tools.call('pdf_extract.delete_file', file_name=filename)
            deleted_count += 1
        
        print(f'Successfully deleted {deleted_count} files')
        ```"
```

**Why This Works**:
- ✅ Everything in ONE execution context
- ✅ No data passing needed
- ✅ Python keeps file list in memory
- ✅ SHELL_EXECUTOR calls MCP tools via `tools.call()`
- ✅ Fast, reliable, maintainable

**Changes Made**:
1. **PLANNER**: Made Python batch the PREFERRED approach for SCENARIO 2
2. **SHELL_EXECUTOR**: Added "PYTHON BATCH OPERATIONS" guidance with examples

**User Question Answered**:
> "Can we use an intermediate file or some other way to pass information?"

Answer: No need! Python batch operations keep everything in memory in one execution. This is cleaner, faster, and more reliable than any file-based data passing mechanism.

**See**: CHANGELOG_v0.28.5.md for complete details


## Failed to use python batching
TRACE: 🔍 Trace Session Summary
Session ID: 20251226_162725
Log file: /home/mcstar/Nextcloud/VTCLLC/.trace/trace_20251226_162725.json
## ✅ FIXED (v0.28.6) - PLANNER Not Recognizing Python Batch Pattern
**Trace**: trace_20251226_162725
**Version**: 0.28.6
**Date**: 2025-12-26

v0.28.5 introduced Python batch operations, but PLANNER didn't recognize the pattern!

**The Problem**:
User: "Get the rate con pdf files from Daily/October and process each document"

PLANNER created:
- task_1: List files ✅
- task_2: "Process each" ❌ NO FILES!
- task_3: Update feature status ❌ UNWANTED!
- task_4: Log progress ❌ UNWANTED!

Result: task_2 hallucinated `/path/to/rate_con_directory`, nothing processed

**Root Cause**:
- v0.28.5 guidance was too specific (only matched exact example phrases)
- Said "PREFERRED" instead of "MANDATORY"
- No pattern detection rules

**Solution (v0.28.6)**:
1. **Added Pattern Detection**:
   ```
   If user query contains:
   - "get files" + "process each"
   - "list files" + "do X to each"
   - Files in directory + process/import/delete
   → Use Python batch!
   ```

2. **Made It MANDATORY** (not just preferred)

3. **Added Directory Listing Example**:
   ```python
   import os
   files = os.listdir('/path/to/directory')
   for filename in files:
       tools.call('process_document', file_path=filename)
   ```

4. **Strengthened STAY ON TASK**:
   - Added task counting rule: "User asks for 1 thing → Create 1 task"
   - Added second violation example (trace 162725)

**Expected Behavior Now**:
Same query creates ONE Python batch task that does EVERYTHING. No task_2, task_3, task_4!

**See**: CHANGELOG_v0.28.6.md for complete details

