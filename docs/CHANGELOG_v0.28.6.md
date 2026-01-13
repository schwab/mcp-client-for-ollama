## ✅ FIXED (v0.28.6) - Made Python Batch Detection MORE EMPHATIC
**Status**: COMPLETED
**Version**: 0.28.6
**Date**: 2025-12-26

### Summary
v0.28.5 implemented Python batch operations, but **PLANNER wasn't recognizing the pattern**! Trace 20251226_162725 showed PLANNER still creating the old broken pattern despite having the guidance.

**Problem**: Guidance was too specific - only matched exact phrases like "get the list of rate con files for October 2025"

**Solution**: Made pattern detection MORE GENERAL and MORE EMPHATIC with pattern matching rules.

### The Failure (trace 20251226_162725)

**User query**: "Get the rate con pdf files from the local directory Daily/October and process each document into the business database."

**PLANNER created** (WRONG):
```
task_1: "List all .pdf files in Daily/October directory" ✅
task_2: "Process each rate con PDF file" ❌ NO FILES SPECIFIED!
task_3: "Update feature status" ❌ STAY ON TASK violation!
task_4: "Log progress" ❌ STAY ON TASK violation!
```

**Result**:
- task_2 hallucinated `/path/to/rate_con_directory`
- Nothing was processed
- Two unwanted memory tasks created

### Root Cause

The v0.28.5 SCENARIO 2 guidance was:
- Too specific (only showed one example query)
- Not emphatic enough (said "PREFERRED" instead of "MANDATORY")
- No pattern detection rules

PLANNER didn't recognize the query pattern as SCENARIO 2 because it was phrased differently.

### Solution Implemented

#### 1. Added Pattern Detection Rules

**NEW - Detection patterns**:
```
🚨 DETECTION: If user query contains ANY of these patterns, use Python batch:
- "get files" + "process each"
- "list files" + "do X to each"
- "find files" + "process"
- Files in directory + process/import/delete each
- Query returns list + operate on each item

🚨 KEY INDICATOR: If you DON'T know the exact filenames at planning time → Python batch!
```

#### 2. Made It MANDATORY (Not Just Preferred)

Changed from:
```
✅ RIGHT (PREFERRED - Python batch operation):
```

To:
```
✅ RIGHT (MANDATORY - Python batch operation):
```

And added:
```
🚨 CRITICAL RULE:
If user says "get/list/find files" THEN "process/delete/import each"
→ Create ONE task with Python code that does BOTH steps!
→ DO NOT create task_1: list, task_2: process
→ DO NOT create task_3, task_4 for memory (STAY ON TASK!)
```

#### 3. Added Directory Listing Example

**NEW - Example with os.listdir**:
```python
# Example 1: List directory and process each file
import os
files = os.listdir('/home/mcstar/Nextcloud/VTCLLC/Daily/October')
pdf_files = [f for f in files if f.endswith('.pdf') and 'ratecon' in f]

for filename in pdf_files:
    full_path = os.path.join('/home/mcstar/Nextcloud/VTCLLC/Daily/October', filename)
    result = tools.call('pdf_extract.process_document',
                       file_path=full_path,
                       save_to_db=True)
    print(f'Processed {filename}: {result}')

print(f'Total processed: {len(pdf_files)} files')
```

This covers both cases:
- Files from directory listing (os.listdir)
- Files from MCP tool query (tools.call)

#### 4. Strengthened STAY ON TASK Rule

**Added task counting rule**:
```
🚨 ABSOLUTE RULE - COUNT YOUR TASKS:
- User asks for 1 thing → Create 1 task
- User asks for 2 things → Create 2 tasks MAX
- User says "get files and process them" → Create 1 Python batch task
- User does NOT say "update memory" → DO NOT create memory tasks!
- User does NOT say "log progress" → DO NOT create log_progress tasks!

If unsure, count: How many things did user EXPLICITLY ask for? Create ONLY that many tasks!
```

**Added second violation example**:
```
Example 2:
User: "Get the rate con pdf files from Daily/October and process each document"

❌ PLANNER Created (WRONG - added unwanted tasks):
  task_1: List files ✅
  task_2: Process each ✅
  task_3: Update feature status ❌ NOT REQUESTED!
  task_4: Log progress ❌ NOT REQUESTED!
```

### Expected Behavior After Fix

**Same query as trace 162725**:
```
User: "Get the rate con pdf files from Daily/October and process each document"

PLANNER detects pattern: "get files" + "process each" → Python batch!

Creates ONE task:
  task_1: "Use SHELL_EXECUTOR with builtin.execute_python_code to:
          ```python
          import os
          files = os.listdir('/home/mcstar/Nextcloud/VTCLLC/Daily/October')
          pdf_files = [f for f in files if 'ratecon' in f.lower() and f.endswith('.pdf')]

          for filename in pdf_files:
              full_path = os.path.join('/home/mcstar/Nextcloud/VTCLLC/Daily/October', filename)
              result = tools.call('pdf_extract.process_document',
                                 file_path=full_path,
                                 save_to_db=True)
              print(f'Processed {filename}')

          print(f'Total: {len(pdf_files)} files processed')
          ```"

Result: ✅ All files found and processed in ONE task!
        ✅ No task_2, task_3, task_4
        ✅ No hallucinated paths
        ✅ Fast and reliable
```

### Files Modified

**Agent Definitions**:
- `mcp_client_for_ollama/agents/definitions/planner.json`
  - Added pattern detection rules for SCENARIO 2
  - Changed PREFERRED → MANDATORY
  - Added directory listing example (os.listdir)
  - Added trace 20251226_162725 to failure examples
  - Strengthened STAY ON TASK with task counting rule
  - Added second STAY ON TASK violation example

**Version**:
- `pyproject.toml` → 0.28.6
- `mcp_client_for_ollama/__init__.py` → 0.28.6

**Documentation**:
- `CHANGELOG_v0.28.6.md` (this file)

### Key Improvements

1. **Broader Pattern Recognition**:
   - v0.28.5: Only matched specific example phrases
   - v0.28.6: Matches ANY "get files + process each" pattern

2. **More Emphatic**:
   - v0.28.5: "PREFERRED" approach
   - v0.28.6: "MANDATORY" approach with CRITICAL RULE

3. **Better Examples**:
   - v0.28.5: Only MCP tool example
   - v0.28.6: Both directory listing AND MCP tool examples

4. **Stronger STAY ON TASK**:
   - v0.28.5: One violation example
   - v0.28.6: Two violation examples + task counting rule

### Impact

**Prevents**:
- ❌ PLANNER missing Python batch opportunities
- ❌ Creating "process each" tasks without filenames
- ❌ Creating unwanted task_3, task_4 memory tasks
- ❌ Path hallucination from under-specified tasks

**Ensures**:
- ✅ ANY "get + process each" query uses Python batch
- ✅ Only tasks user asked for are created
- ✅ One task does everything (no data passing)
- ✅ Fast, reliable execution

### Backward Compatibility

- Fully backward compatible
- No breaking changes
- Existing patterns still work
- Python batch is now MORE reliably detected

### Testing Recommendations

1. Test: "Get PDF files from directory X and process each" → should create 1 Python batch task
2. Test: "List rate cons for October, delete each" → should create 1 Python batch task
3. Test: "Find unprocessed files and import them" → should create 1 Python batch task
4. Verify: NO task_3, task_4 created unless explicitly requested
5. Verify: No more "/path/to/" hallucinations

---

**Version**: 0.28.6
**Date**: 2025-12-26
**Category**: Critical Bug Fix
**Breaking Changes**: None
**Fixes**: trace_20251226_162725 (PLANNER not using Python batch)
**Related**: v0.28.5 (introduced Python batch operations)
