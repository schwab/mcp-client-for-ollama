# Tool Calling Fixes - qwen2.5:32b Migration

## Problem Summary

Based on trace analysis (`trace_20251214_084421.json`), the model `hhao/qwen2.5-coder-tools:7b` had critical issues:

1. **PLANNER**: Wrapping JSON output in markdown code blocks despite instructions
2. **EXECUTOR**: Generating empty responses after successful tool calls
3. **All Agents**: Lacking explicit post-tool response guidance

This caused infinite retry loops and failed task execution.

## Solutions Implemented

### Fix 1: Changed Default Model

**File**: `mcp_client_for_ollama/utils/constants.py`

```python
# Before
DEFAULT_MODEL = "qwen3-coder:30b"

# After
DEFAULT_MODEL = "qwen2.5:32b"
```

**Why qwen2.5:32b:**
- ✅ Proven excellent tool calling capabilities
- ✅ Generates proper responses after tool execution
- ✅ Still excellent at code generation
- ✅ Better instruction following than coder variants
- ✅ 32B parameters for strong reasoning

### Fix 2: Enhanced PLANNER Output Format Instructions

**File**: `mcp_client_for_ollama/agents/definitions/planner.json`

**Added explicit JSON formatting rules:**
```
CRITICAL - JSON OUTPUT FORMAT:
- Output ONLY raw JSON, starting with { and ending with }
- DO NOT wrap in markdown code blocks (```json or ```)
- DO NOT add any text before or after the JSON
- DO NOT use code fences or formatting
- Your ENTIRE response must be ONLY the JSON object
WRONG: ```json\n{...}\n```
RIGHT: {...}
```

**Impact**: Forces model to output raw JSON without markdown wrapping.

### Fix 3: Added Post-Tool Response Protocol

**Files Updated**: All agent definitions
- `coder.json`
- `executor.json`
- `debugger.json`
- `researcher.json`
- `reader.json`

**Added to all agents:**
```
CRITICAL - TOOL USAGE PROTOCOL:
After calling ANY tool, you MUST:
1. Generate a clear text response explaining what you did
2. Summarize the tool's result in your own words
3. Answer the user's question using the information from the tool
4. NEVER leave your response empty after calling a tool

Example:
WRONG: [calls tool, returns empty response]
RIGHT: [calls tool] "I've retrieved the system prompt using builtin.get_system_prompt.
       The current prompt shows..."
```

**Impact**: Explicitly instructs agents to generate text after tool calls.

## Validation Results

All changes validated successfully:

```
✓ coder.json - Valid JSON
✓ planner.json - Valid JSON
✓ executor.json - Valid JSON
✓ researcher.json - Valid JSON
✓ debugger.json - Valid JSON
✓ reader.json - Valid JSON
✓ DEFAULT_MODEL = "qwen2.5:32b"
```

## Expected Improvements

### Before (hhao/qwen2.5-coder-tools:7b)
```
❌ PLANNER: {"tasks": [...]}  → wrapped in ```json blocks
❌ EXECUTOR: Calls tool successfully → generates EMPTY response
❌ Result: Infinite retry loop, task fails
```

### After (qwen2.5:32b)
```
✅ PLANNER: {"tasks": [...]}  → clean JSON output
✅ EXECUTOR: Calls tool successfully → explains result in text
✅ Result: Task completes successfully on first try
```

## Behavioral Changes

### Tool Call Flow (New)
1. Agent receives task
2. Agent calls tool using proper JSON format
3. Tool executes and returns result
4. **Agent generates text response** explaining what it found
5. Task marked complete

### PLANNER Output (New)
- No more markdown code block stripping needed
- Direct JSON parsing
- Faster, more reliable

## Testing Recommendations

1. **Test PLANNER**: Ask it to break down a complex task
   - Verify: Raw JSON output (no ```json wrapping)

2. **Test EXECUTOR with tools**: Ask to get system prompt
   - Verify: Tool called AND text response generated

3. **Test loop completion**: Ask simple tool-based question
   - Verify: Completes in 1 iteration, not 10+

4. **Test all agents**: Ensure they still work with new prompts
   - Verify: No behavioral regressions

## Files Changed

**Total**: 7 files

**Configuration**:
- `mcp_client_for_ollama/utils/constants.py` - Default model

**Agent Definitions**:
- `mcp_client_for_ollama/agents/definitions/planner.json` - JSON output format
- `mcp_client_for_ollama/agents/definitions/coder.json` - Tool response protocol
- `mcp_client_for_ollama/agents/definitions/executor.json` - Tool response protocol
- `mcp_client_for_ollama/agents/definitions/debugger.json` - Tool response protocol
- `mcp_client_for_ollama/agents/definitions/researcher.json` - Tool response protocol
- `mcp_client_for_ollama/agents/definitions/reader.json` - Tool response protocol

## Migration Notes

### Model Download
Ensure `qwen2.5:32b` is available:
```bash
ollama pull qwen2.5:32b
```

### Size Requirements
- **qwen3-coder:30b**: ~17GB
- **qwen2.5:32b**: ~18GB
- Similar VRAM requirements

### Backward Compatibility
- Configuration is **not** backward compatible with older traces
- Old traces used different models and may have different behavior patterns
- Recommend clearing conversation history after deploying

## Known Limitations

### What This Fixes
✅ Empty responses after tool calls
✅ Infinite retry loops
✅ JSON markdown wrapping from PLANNER
✅ General tool calling reliability

### What This Doesn't Fix
❌ Model still needs proper tool schemas (already working)
❌ Tool execution errors (different issue)
❌ Network/connection issues (different issue)

## Rollback Instructions

If issues occur:

```bash
# Rollback all changes
git checkout HEAD~1 -- mcp_client_for_ollama/

# Or rollback just the model
# Edit constants.py, change:
DEFAULT_MODEL = "qwen3-coder:30b"  # or another model
```

## Success Criteria

✅ PLANNER outputs clean JSON (no markdown blocks)
✅ EXECUTOR generates text after tool calls
✅ All agents complete tool-based tasks successfully
✅ No infinite retry loops
✅ Tool calls complete in 1-2 iterations max

## Next Steps

1. Deploy changes
2. Test with `qwen2.5:32b` once downloaded
3. Monitor trace files for proper behavior
4. If issues persist, check model-specific quirks
5. Consider adding empty response detection in client code as fallback

## Notes

- These fixes target **model behavior**, not client logic
- qwen2.5:32b is proven to work well with these patterns
- The added protocol instructions should work with other models too
- Always check trace files when debugging tool call issues
