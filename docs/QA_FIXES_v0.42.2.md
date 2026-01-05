# QA Fixes - Version 0.42.2

**Release Date**: 2026-01-04
**Release Type**: Bug Fix Release (QA-driven)

## Critical Fixes

### ✅ Fix #1: Server Reload Crash Regression
**QA Bug**: "application now crashes when calling server reload"

**Root Cause**: The `reload_servers()` method was calling `cleanup()` on a temporary MCP client within a Flask async request context. This caused a RuntimeError: "Attempted to exit cancel scope in a different task than it was entered in" because anyio cancel scopes cannot be exited in different tasks than they were entered.

**Fix**: Removed the `cleanup()` call from `reload_servers()` method in `client_wrapper.py`. The temporary client is now automatically garbage collected, and cleanup happens when the WebMCPClient session is destroyed.

**File Modified**: `mcp_client_for_ollama/web/integration/client_wrapper.py:338-351`

**Before**:
```python
async def reload_servers(self):
    temp_client = await self._create_mcp_client()
    if temp_client:
        self._mcp_client = temp_client
        await self._load_tools()
        try:
            await temp_client.cleanup()  # ❌ Causes cancel scope error
        except (RuntimeError, Exception) as e:
            print(f"Warning: Server reload cleanup error (expected): {e}")
        finally:
            self._mcp_client = None
```

**After**:
```python
async def reload_servers(self):
    temp_client = await self._create_mcp_client()
    if temp_client:
        self._mcp_client = temp_client
        await self._load_tools()
        # Don't call cleanup() - causes cancel scope errors
        # Cleanup happens when WebMCPClient session is destroyed
        self._mcp_client = None  # ✅ Automatic garbage collection
```

**Testing**:
- ✅ Server reload button works without crashes
- ✅ Tools list refreshes correctly
- ✅ No RuntimeError about cancel scopes

---

## Status of Other QA Bugs

### ✅ FIXED in v0.42.1 (Already Deployed)

1. **Event loop closed errors** - Fixed with `asyncio.wait_for()` instead of `asyncio.timeout()`
2. **Session invalidation after first use** - Fixed with background cleanup thread
3. **Obsidian tool GeneratorExit exceptions** - Fixed with graceful cleanup
4. **404 errors calling Obsidian tools** - Fixed by removing premature cleanup

### ⚠️ KNOWN ISSUES (Not Regressions - Pre-existing)

1. **Memory UI not fully functional**
   - **Status**: Partial implementation
   - **Issue**: Backend methods in `client_wrapper.py` are stubs (lines 398-447)
   - **Impact**: UI shows prompts but goals/features don't persist
   - **Root Cause**: Memory system integration incomplete
   - **Fix Required**: Full implementation of memory API methods to parse builtin tool results
   - **Tracked In**: Issue #TBD

2. **Tool selections not saving to config**
   - **Status**: Feature not implemented
   - **Issue**: `set_tool_enabled()` raises NotImplementedError (line 324)
   - **Impact**: Tool enable/disable changes don't persist
   - **Fix Required**: Implement config.json persistence for tool states
   - **Tracked In**: Original QA bug report

3. **Config load MCP servers fails**
   - **Status**: Needs investigation
   - **Issue**: "Unexpected token '<'" error when loading config
   - **Impact**: Cannot reload servers from config
   - **Fix Required**: Debug config parsing logic
   - **Tracked In**: Needs reproduction steps

4. **Planner validation errors**
   - **Status**: Agent configuration issue
   - **Issue**: "Task 1 has invalid agent_type: builtin.get_system_prompt"
   - **Impact**: Planner tries to delegate to tool names instead of agents
   - **Root Cause**: Planner agent definition needs update
   - **Fix Required**: Update planner.json agent definitions
   - **Tracked In**: Agent system refactor

5. **AI gives commands instead of executing**
   - **Status**: Prompt engineering issue
   - **Issue**: AI returns tool syntax instead of calling tools
   - **Impact**: User gets `obsidian.tool_name args` instead of results
   - **Root Cause**: Model behavior / system prompt
   - **Fix Required**: Improve system prompts and model fine-tuning
   - **Tracked In**: Prompt engineering backlog

6. **Hallucination of search results**
   - **Status**: AI/Model behavior
   - **Issue**: AI makes up file names instead of using real results
   - **Impact**: Incorrect responses to search queries
   - **Root Cause**: Model limitations
   - **Fix Required**: Better prompting, result validation
   - **Tracked In**: AI quality improvements

7. **Obsidian tools return count but no contents**
   - **Status**: Needs investigation
   - **Issue**: Tools report finding files but don't return content
   - **Impact**: Incomplete tool responses
   - **Fix Required**: Debug Obsidian MCP server integration
   - **Tracked In**: Needs reproduction steps

## Files Modified

### v0.42.2 Changes:
1. `mcp_client_for_ollama/web/integration/client_wrapper.py` - Removed premature cleanup in reload_servers()
2. `docs/QA_FIXES_v0.42.2.md` - This documentation

## Upgrade Instructions

### From v0.42.1:
```bash
cd /path/to/mcp-client-for-ollama

# Pull latest changes
git pull

# Update version
# (Already done in this commit)

# Restart web server
# If running as service:
systemctl restart mcp-web

# If running manually:
# Kill existing process and restart
ollmcp web
```

## Testing Checklist

- [x] Server reload works without crashes
- [x] Tools list refreshes after reload
- [x] No cancel scope errors in logs
- [ ] Memory UI integration (deferred - see Known Issues #1)
- [ ] Tool enable/disable persistence (deferred - see Known Issues #2)

## Next Release (v0.43.0)

**Planned Fixes**:
1. Complete memory UI backend implementation
2. Implement tool selection persistence
3. Fix config loading errors
4. Update planner agent definitions

**Target Date**: TBD

## Notes

- The Memory Control Panel UI (Phase 3) was completed but backend integration is incomplete
- The UI is functional for display but doesn't persist data to the memory system
- This is a known limitation and will be addressed in v0.43.0
- Users can still use memory features via CLI (`memory-new`, `add-goal`, etc.)
