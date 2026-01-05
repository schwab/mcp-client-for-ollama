# Obsidian Tool Errors - Root Cause Analysis and Fixes

## Issues Identified from qa_bugs.md

### 1. Event Loop Closed Errors (CRITICAL)
**Symptom**: `RuntimeError: Event loop is closed` during or after tool execution
**Location**: qa_bugs.md lines 5-69, 102-130

**Root Cause**:
- `WebMCPClient.send_message_streaming()` creates fresh MCP clients for each request (client_wrapper.py:134)
- After processing, it calls `await mcp_client.cleanup()` (client_wrapper.py:239)
- `cleanup()` calls `await self.exit_stack.aclose()` (client.py:2276)
- This closes async resources (stdio connections, HTTP clients) while they're still being used
- The event loop gets closed while asyncio operations are pending

**Call Stack**:
```
send_message_streaming()
  → mcp_client.process_with_delegation()
    → Obsidian tool call via stdio
      → httpcore connection cleanup
        → Event loop closed while closing connections
```

**Fix #1** - Suppress cleanup errors (IMMEDIATE):
```python
# In client_wrapper.py line 239, change:
await mcp_client.cleanup()

# To:
from contextlib import suppress
with suppress(RuntimeError, Exception):
    await mcp_client.cleanup()
```

**Fix #2** - Graceful shutdown with timeout (BETTER):
```python
# In client.py, update cleanup method:
async def cleanup(self):
    """Clean up resources with graceful shutdown"""
    try:
        # Give pending operations time to finish
        await asyncio.sleep(0.5)

        # Close exit stack with timeout
        async with asyncio.timeout(5.0):
            await self.exit_stack.aclose()
    except (asyncio.TimeoutError, RuntimeError) as e:
        # Log but don't raise - cleanup is best effort
        print(f"Warning: Cleanup timeout or error: {e}")
    except Exception as e:
        print(f"Warning: Unexpected cleanup error: {e}")
```

**Fix #3** - Don't cleanup MCP client in web mode (BEST):
```python
# In client_wrapper.py, REMOVE line 239:
# await mcp_client.cleanup()  # DON'T cleanup - let garbage collection handle it

# Add to WebMCPClient.cleanup() instead:
async def cleanup(self):
    """Cleanup resources at session end"""
    self._initialized = False

    # Clean up any persistent MCP client
    if self._mcp_client:
        with suppress(RuntimeError, Exception):
            await self._mcp_client.cleanup()
        self._mcp_client = None
```

### 2. Session Invalidation After First Use (HIGH PRIORITY)
**Symptom**: Session works once, then becomes "Invalid session" on subsequent requests
**Location**: qa_bugs.md lines 141-147

**Root Cause**:
```python
# app.py lines 145-150:
@app.before_request
@async_route
async def cleanup_sessions():
    """Cleanup expired sessions before each request"""
    await session_manager.cleanup_expired_sessions()
```

**Problem**:
- `cleanup_expired_sessions()` runs BEFORE every request
- If the session timestamp isn't updated early enough, it could be deleted
- Race condition: cleanup runs → checks timestamp → deletes session → request tries to use it

**Fix** - Remove aggressive cleanup:
```python
# In app.py, REMOVE lines 145-150:
# @app.before_request
# @async_route
# async def cleanup_sessions():
#     await session_manager.cleanup_expired_sessions()

# Instead, add periodic cleanup task:
def create_app(app_config=None):
    app = Flask(__name__, ...)

    # ... existing setup ...

    # Start background task for periodic session cleanup (every 5 minutes)
    import threading
    import time

    def periodic_cleanup():
        while True:
            time.sleep(300)  # 5 minutes
            try:
                asyncio.run(session_manager.cleanup_expired_sessions())
            except Exception as e:
                print(f"Session cleanup error: {e}")

    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()

    return app
```

### 3. Tool Selections Not Saving to Config (MEDIUM PRIORITY)
**Symptom**: User enables/disables tools in UI, changes don't persist
**Location**: qa_bugs.md lines 99-100, client_wrapper.py lines 314-323

**Root Cause**: Feature not implemented (TODO comment in code)

**Fix** - Implement config persistence:
```python
# In client_wrapper.py, replace lines 314-323:
def set_tool_enabled(self, tool_name: str, enabled: bool) -> bool:
    """Enable or disable a tool and persist to config"""
    # Update cache
    for tool in self._tools_cache or []:
        if tool['name'] == tool_name:
            tool['enabled'] = enabled

            # Save to config file
            if self.config_dir:
                import os
                import json
                config_path = os.path.join(self.config_dir, 'config.json')

                try:
                    # Load existing config
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                    else:
                        config = {}

                    # Update tool_enabled section
                    if 'tool_enabled' not in config:
                        config['tool_enabled'] = {}
                    config['tool_enabled'][tool_name] = enabled

                    # Save config
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)

                    return True
                except Exception as e:
                    print(f"Error saving tool config: {e}")
                    return False

            return True  # Updated cache even if can't persist

    return False  # Tool not found
```

### 4. 404 Errors Calling Obsidian Tools (HIGH PRIORITY)
**Symptom**: MCP server connections fail, tools can't be called
**Location**: qa_bugs.md line 189-190

**Likely Causes**:
1. Event loop closed → MCP server stdio connection broken
2. Session deleted → Client cleaned up → Server disconnected
3. Exit stack closed → All server connections terminated

**Fix**: Apply Fixes #1, #2, and #3 from Event Loop issue

### 5. AI Gives Commands Instead of Answering (MEDIUM PRIORITY)
**Symptom**: AI returns command strings like `obsidian.obsidian_get_recent_changes days=3 limit=5` instead of executing
**Location**: qa_bugs.md lines 149-186

**Root Cause**: LLM is confused about whether to execute or describe tools

**Fix** - Improve system prompt:
```python
# In delegation_client.py or planner prompt, add:
"CRITICAL: You are an AI assistant that EXECUTES tools, not describes them.
When you need to use a tool:
- ❌ WRONG: Output 'Use obsidian.obsidian_get_recent_changes days=3 limit=5'
- ✅ RIGHT: Call the tool directly with the parameters

Never output command syntax to the user. Always execute tools directly."
```

### 6. Obsidian Tools Return Count But No Contents (LOW PRIORITY)
**Symptom**: Tool reports file count but doesn't return file contents
**Location**: qa_bugs.md lines 137-139

**Likely Cause**: Tool parameter errors or result parsing issues

**Investigation Needed**:
1. Check Obsidian MCP server tool definitions
2. Verify parameter types are correct
3. Add better error handling and logging for tool results

### 7. Config Load MCP Servers Fails (MEDIUM PRIORITY)
**Symptom**: Error reloading servers: `Unexpected token '<'`
**Location**: qa_bugs.md lines 132-135

**Root Cause**: JSON parsing error - server likely returning HTML error page instead of JSON

**Fix** - Add better error handling:
```python
# In client_wrapper.py reload_servers():
async def reload_servers(self):
    """Reload MCP servers with auto-discovery"""
    try:
        temp_client = await self._create_mcp_client()
        if temp_client:
            self._mcp_client = temp_client
            await self._load_tools()
            # Clean up gracefully
            with suppress(RuntimeError, Exception):
                await temp_client.cleanup()
            self._mcp_client = None
        else:
            raise Exception("Failed to create MCP client for server reload")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise Exception(f"Failed to reload MCP servers: {str(e)}")
```

## Implementation Priority

### CRITICAL (Fix Immediately):
1. **Event loop closed errors** - Apply Fix #3 (don't cleanup in send_message_streaming)
2. **Session invalidation** - Remove @before_request cleanup, use periodic cleanup
3. **404 errors** - Fixed by #1 and #2

### HIGH PRIORITY (Next Release):
1. **Tool selections not saving** - Implement config persistence
2. **Config reload failures** - Better error handling

### MEDIUM PRIORITY (Future):
1. **AI gives commands** - Improve prompts
2. **Obsidian content parsing** - Investigate tool results

## Testing Plan

### Test Event Loop Fix:
1. Start web server
2. Make Obsidian tool call
3. Make second call immediately after
4. Verify no "Event loop is closed" errors
5. Check logs for cleanup warnings

### Test Session Persistence:
1. Create session via /api/sessions/create
2. Make multiple requests with same session_id
3. Wait 65 minutes (past timeout)
4. Verify session cleaned up
5. Make request within 60 minutes, verify session persists

### Test Tool Config Persistence:
1. Load tools via /api/tools/list
2. Toggle tool via /api/tools/toggle
3. Reload page
4. Verify tool state persisted

## Files to Modify

1. **mcp_client_for_ollama/web/integration/client_wrapper.py**
   - Remove cleanup call (line 239)
   - Implement set_tool_enabled (lines 314-323)
   - Add cleanup to WebMCPClient.cleanup()

2. **mcp_client_for_ollama/client.py**
   - Make cleanup more graceful (line 2274)
   - Add timeout and error suppression

3. **mcp_client_for_ollama/web/app.py**
   - Remove @before_request cleanup (lines 145-150)
   - Add periodic cleanup thread

4. **Prompts/System Messages**
   - Add "execute not describe" guidance
   - Clarify tool usage expectations

## Success Criteria

- ✅ No "Event loop is closed" errors in logs
- ✅ Sessions persist across multiple requests
- ✅ Tool enable/disable persists to config
- ✅ Obsidian tools execute successfully
- ✅ No 404 errors when calling tools
- ✅ AI executes tools instead of describing them
