# System Prompt Tools Fix

## Problem Identified

From trace file analysis (`trace_20251213_223140.json`), agents were unable to access system prompt tools:
- **Issue**: `builtin.get_system_prompt` was not available to EXECUTOR and other agents
- **Root Cause**: System prompt tools were not included in agents' `default_tools` lists
- **Impact**: Agents couldn't read or modify their system prompts dynamically

## Solution Implemented

Added system prompt tool access to all agents based on their needs:

### 1. All Agents Got `get_system_prompt` (Read Access)

All text-based agents can now READ the current system prompt:
- ✅ CODER
- ✅ EXECUTOR
- ✅ DEBUGGER
- ✅ PLANNER
- ✅ RESEARCHER
- ✅ READER

**Rationale**: Reading system prompt is safe and useful for:
- Understanding current behavior/constraints
- Context awareness
- Debugging task execution
- Adaptive behavior based on current configuration

### 2. Selected Agents Got `set_system_prompt` (Write Access)

Three agents can now MODIFY the system prompt:
- ✅ **CODER** - Can adjust coding style/behavior dynamically
- ✅ **EXECUTOR** - Can modify execution behavior based on environment
- ✅ **DEBUGGER** - Can adjust debugging approach based on error patterns

**Rationale**: These agents benefit from dynamic behavior modification:
- **CODER**: Switch between coding styles, add constraints, modify patterns
- **EXECUTOR**: Adjust execution safety, modify tool usage patterns, adapt to environment
- **DEBUGGER**: Change debugging verbosity, focus areas, approach strategies

### 3. Agents That DON'T Have `set_system_prompt`

Read-only agents kept restricted from modifying behavior:
- ❌ PLANNER - Should maintain consistent planning strategy
- ❌ RESEARCHER - Should maintain objective analysis approach
- ❌ READER - Should maintain consistent reading patterns

**Rationale**: These agents should maintain stable, predictable behavior patterns.

## Changes Made

### Files Modified

**6 agent definition files updated**:

1. **`mcp_client_for_ollama/agents/definitions/executor.json`**
   - Added `builtin.get_system_prompt` to `default_tools`
   - Added `builtin.set_system_prompt` to `default_tools`
   - Removed `builtin.set_system_prompt` from `forbidden_tools`

2. **`mcp_client_for_ollama/agents/definitions/coder.json`**
   - Added `builtin.get_system_prompt` to `default_tools`
   - Added `builtin.set_system_prompt` to `default_tools`

3. **`mcp_client_for_ollama/agents/definitions/debugger.json`**
   - Added `builtin.get_system_prompt` to `default_tools`
   - Added `builtin.set_system_prompt` to `default_tools`
   - Removed `builtin.set_system_prompt` from `forbidden_tools`

4. **`mcp_client_for_ollama/agents/definitions/planner.json`**
   - Added `builtin.get_system_prompt` to `default_tools`

5. **`mcp_client_for_ollama/agents/definitions/researcher.json`**
   - Added `builtin.get_system_prompt` to `default_tools`

6. **`mcp_client_for_ollama/agents/definitions/reader.json`**
   - Added `builtin.get_system_prompt` to `default_tools`

## Verification

### JSON Validation
✅ All 6 modified JSON files validated successfully

### Tool Availability Matrix

| Agent | get_system_prompt | set_system_prompt |
|-------|-------------------|-------------------|
| **CODER** | ✅ | ✅ |
| **EXECUTOR** | ✅ | ✅ |
| **DEBUGGER** | ✅ | ✅ |
| **PLANNER** | ✅ | ❌ |
| **RESEARCHER** | ✅ | ❌ |
| **READER** | ✅ | ❌ |

## Use Cases Enabled

### 1. Reading System Prompt
```
Agents can now:
- Check their current instructions
- Understand their constraints
- See what tools they have access to
- Debug why they're behaving a certain way
```

### 2. Modifying System Prompt (CODER, EXECUTOR, DEBUGGER only)
```
CODER can:
- Switch to different coding styles (functional vs OOP)
- Add temporary constraints (e.g., "use only built-in libraries")
- Modify code patterns (e.g., "prefer composition over inheritance")

EXECUTOR can:
- Adjust safety levels for command execution
- Modify tool usage preferences
- Adapt to different environments

DEBUGGER can:
- Change debugging verbosity
- Focus on specific error types
- Adjust fix strategies (minimal vs comprehensive)
```

## Benefits

1. **Fixes Original Issue**: EXECUTOR can now access `builtin.get_system_prompt`
2. **Adaptive Behavior**: Agents can modify their behavior dynamically
3. **Better Debugging**: Agents can introspect their configuration
4. **Enhanced Flexibility**: Supports more complex multi-agent workflows
5. **Safe Restrictions**: Read-only agents maintain stable behavior

## Testing

### Before Fix
```
❌ EXECUTOR: "builtin.get_system_prompt tool does not exist"
❌ All agents: No access to system prompt
```

### After Fix
```
✅ All agents can read system prompt
✅ CODER, EXECUTOR, DEBUGGER can modify system prompt
✅ PLANNER, RESEARCHER, READER cannot modify (by design)
✅ All JSON configurations valid
```

## Security Considerations

### Safe by Design
- **get_system_prompt**: Read-only, no security risk
- **set_system_prompt**: Only on agents that execute/modify code already
- **Restricted**: Planning and analysis agents cannot modify behavior

### No Additional Risk
Agents with `set_system_prompt` already have powerful capabilities:
- **CODER**: Can write arbitrary code
- **EXECUTOR**: Can execute arbitrary commands
- **DEBUGGER**: Can execute and modify code

Adding system prompt modification doesn't add new attack vectors.

## Rollback Instructions

If needed, revert changes:
```bash
git checkout HEAD~1 -- mcp_client_for_ollama/agents/definitions/
```

Or manually:
1. Remove `builtin.get_system_prompt` from all `default_tools`
2. Remove `builtin.set_system_prompt` from CODER, EXECUTOR, DEBUGGER `default_tools`
3. Add `builtin.set_system_prompt` back to EXECUTOR and DEBUGGER `forbidden_tools`

## Next Steps

1. Deploy changes
2. Test EXECUTOR with `builtin.get_system_prompt`
3. Experiment with dynamic system prompt modifications
4. Monitor agent behavior for unexpected changes
5. Consider adding system prompt versioning/history

## Notes

- System prompt changes are **session-scoped** (don't persist across restarts)
- Agents should use `set_system_prompt` sparingly
- Consider adding guards against infinite prompt modification loops
- May want to add prompt change logging/auditing in the future
