# Changelog - Version 0.42.1

**Release Date**: 2026-01-04
**Release Type**: Bug Fix Release

## Overview
Critical bug fixes for Obsidian MCP tool errors, event loop issues, and session management problems identified in QA testing.

## Critical Fixes

### 🔴 Fix #1: Event Loop Closed Errors
**Issue**: `RuntimeError: Event loop is closed` when using Obsidian tools or any MCP server tools
- **Root Cause**: Premature cleanup of MCP client while async operations still pending
- **Files Modified**:
  - `mcp_client_for_ollama/web/integration/client_wrapper.py`
  - `mcp_client_for_ollama/client.py`
- **Changes**:
  - Removed premature `mcp_client.cleanup()` call in `send_message_streaming()` (line 239)
  - Added graceful cleanup with error suppression to `WebMCPClient.cleanup()`
  - Added graceful cleanup with timeout (5s) and error handling to `MCPClient.cleanup()`
  - MCP clients now cleaned up only when sessions are deleted, not after each request
- **Impact**: Eliminates "Event loop is closed" errors, 404 tool call errors, and stdio connection failures

### 🔴 Fix #2: Session Invalidation After First Use
**Issue**: Sessions marked as "Invalid session" after first successful request
- **Root Cause**: Aggressive session cleanup running on EVERY request via `@app.before_request`
- **File Modified**: `mcp_client_for_ollama/web/app.py`
- **Changes**:
  - Removed `@app.before_request` cleanup hook that ran on every request
  - Added background daemon thread for periodic cleanup (every 5 minutes)
  - Eliminated race condition where sessions were deleted while being used
- **Impact**: Sessions now persist correctly across multiple requests

### 🔴 Fix #3: Graceful MCP Client Cleanup
**Issue**: Cleanup operations causing cascading failures in async operations
- **File Modified**: `mcp_client_for_ollama/client.py`
- **Changes**:
  - Added 500ms grace period for pending operations before cleanup
  - Added 5-second timeout for cleanup operations
  - Catch and log `RuntimeError`, `TimeoutError`, and generic exceptions
  - Never raise exceptions during cleanup (best-effort approach)
- **Impact**: Cleanup failures no longer propagate and break the application

## Bug Fixes

### Obsidian MCP Tools
- ✅ Fixed event loop closed errors when calling Obsidian tools
- ✅ Fixed 404 errors when MCP server connections fail
- ✅ Fixed stdio connection failures during tool execution
- ✅ Fixed session invalidation preventing subsequent tool calls
- ✅ Fixed cleanup errors causing GeneratorExit exceptions

### Web Interface
- ✅ Fixed sessions becoming invalid after first use
- ✅ Fixed race conditions in session cleanup
- ✅ Improved session lifetime (now uses periodic cleanup vs per-request)
- ✅ Better error messages for cleanup warnings

### Compatibility
- ✅ Fixed Python 3.10 compatibility issue with `asyncio.timeout` (replaced with `asyncio.wait_for`)

## Technical Details

### Cleanup Strategy Changes

**Before (v0.42.0)**:
```python
# Every request cleaned up immediately after use
await mcp_client.cleanup()  # ❌ Causes event loop errors

# Sessions cleaned up on EVERY request
@app.before_request
async def cleanup_sessions():
    await session_manager.cleanup_expired_sessions()  # ❌ Race condition
```

**After (v0.42.1)**:
```python
# No cleanup after each request - let garbage collection handle it
# Only cleanup when session is deleted

# Sessions cleaned up periodically in background thread
def periodic_session_cleanup():  # ✅ No race conditions
    while True:
        time.sleep(300)  # Every 5 minutes
        loop = asyncio.new_event_loop()
        loop.run_until_complete(session_manager.cleanup_expired_sessions())
        loop.close()
```

### Error Handling Improvements

**Graceful Cleanup Pattern**:
```python
async def cleanup(self):
    try:
        await asyncio.sleep(0.5)  # Grace period
        async with asyncio.timeout(5.0):  # Timeout protection
            await self.exit_stack.aclose()
    except asyncio.TimeoutError:
        print("[Cleanup] Warning: Timed out (expected)")
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            print("[Cleanup] Warning: Event loop closed (expected in web context)")
        else:
            print(f"[Cleanup] Warning: {e}")
    except Exception as e:
        print(f"[Cleanup] Warning: {e}")
```

## Testing

### Verified Fixes
- ✅ Web server starts without errors
- ✅ Multiple requests to same session work correctly
- ✅ No "Event loop closed" errors in logs
- ✅ No "Invalid session" errors on second request
- ✅ Cleanup warnings logged but don't break functionality
- ✅ Background cleanup thread starts correctly

### Test Commands
```bash
# Start web server
python -m mcp_client_for_ollama.web.app

# Expected output:
[Session Manager] Initializing in standalone mode
[Standalone Mode] CORS allows all origins
[Session Cleanup] Started background cleanup thread (5 minute interval)
Starting MCP Client Web Server on http://0.0.0.0:5222
```

## Known Issues

### Still Open (Non-Critical)
1. **Tool selections not saving to config** - Feature not yet implemented (tracked in qa_bugs.md)
2. **AI gives commands instead of executing** - Prompt engineering needed
3. **Obsidian content parsing** - Requires investigation of tool definitions

These issues are documented in `docs/obsidian_tool_fixes.md` for future releases.

## Upgrade Instructions

### From v0.42.0
```bash
# Pull latest changes
git pull

# Rebuild package
python -m build

# Install/upgrade
pip install dist/mcp_client_for_ollama-0.42.1-py3-none-any.whl --force-reinstall

# Verify version
python -c "from mcp_client_for_ollama import __version__; print(__version__)"
# Should output: 0.42.1
```

## Files Changed

### Modified Files
1. `mcp_client_for_ollama/__init__.py` - Version bump to 0.42.1
2. `pyproject.toml` - Version bump to 0.42.1
3. `mcp_client_for_ollama/web/app.py` - API version + periodic cleanup thread
4. `mcp_client_for_ollama/web/integration/client_wrapper.py` - Removed premature cleanup, added error suppression
5. `mcp_client_for_ollama/client.py` - Graceful cleanup with timeout and error handling

### New Files
1. `docs/obsidian_tool_fixes.md` - Comprehensive analysis and fix documentation
2. `docs/CHANGELOG_v0.42.1.md` - This changelog

## References
- QA Bug Report: `docs/qa_bugs.md`
- Fix Documentation: `docs/obsidian_tool_fixes.md`
- Version 0.42.0 Release: Nextcloud integration features
