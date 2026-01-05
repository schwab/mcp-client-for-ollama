# QA Fixes - Version 0.42.4

**Release Date**: 2026-01-04
**Release Type**: Critical Bug Fix
**Previous Version**: 0.42.3

## Critical Fix

### ✅ Fix: Domain Mismatch Causing "Memory file not found" Error

**QA Bug**: "Error while creating goal (in a memory session)" (lines 381-416 in qa_bugs.md)

**Symptoms**:
- User creates memory session with custom domain (e.g., "Book ghost writer")
- User creates goal successfully (gets confirmation)
- Goal doesn't show up in UI
- Error in logs: `Memory file not found for session ... in domain web`

**Root Cause**:

When users created memory sessions with custom domains (e.g., "Book ghost writer"), the domain was stored in the memory file but not tracked by the `WebMCPClient` instance. Subsequent operations (`list_goals()`, `create_goal()`, `create_feature()`) were hardcoded to use domain "web", causing a domain mismatch:

1. Memory session created with domain "Book ghost writer" → saves to `/tmp/mcp_web_sessions/{session_id}/memory/Book ghost writer/{session_id}/memory.json`
2. User creates goal → code looks in domain "web" instead of "Book ghost writer"
3. Memory file not found → goal creation appears to succeed but isn't actually saved
4. List goals → looks in domain "web", finds nothing

**Solution**:

Added `memory_domain` tracking to `WebMCPClient`:

1. **Store domain when memory session is created** (`create_memory_session()`)
2. **Use stored domain for all subsequent operations** (`list_goals()`, `create_goal()`, `create_feature()`)
3. **Fall back to "web" if no domain is stored** (for backward compatibility)

**Implementation**:

```python
class WebMCPClient:
    def __init__(self, session_id: str, config: Optional[Dict] = None):
        # ... existing code ...
        self.memory_domain = None  # Track memory domain for this session
```

```python
async def create_memory_session(self, domain: str, description: str) -> Dict:
    # ... create memory ...
    delegation_client.memory_tools.storage.save_memory(memory)

    # Store the domain for future operations
    self.memory_domain = domain  # ✅ Remember which domain was used

    return {'status': 'created', ...}
```

```python
async def list_goals(self) -> List[Dict]:
    # Use stored domain if available, otherwise fall back to "web"
    domain = self.memory_domain if self.memory_domain else "web"

    # Load memory from correct domain
    memory = delegation_client.memory_tools.storage.load_memory(
        self.session_id,
        domain  # ✅ Use correct domain
    )
```

Same pattern applied to `create_goal()` and `create_feature()`.

**Testing**:

```bash
# Create session
POST /api/sessions/create
→ {"session_id": "f2402de2..."}

# Create memory with custom domain
POST /api/memory/new
{
  "session_id": "f2402de2...",
  "domain": "Book ghost writer",  # Custom domain
  "description": "Ghost writing project"
}
→ {"status": "created", "domain": "Book ghost writer"}

# Create goal (now uses correct domain)
POST /api/memory/goals
{
  "session_id": "f2402de2...",
  "goal_id": "G1",
  "description": "Write chapter 1",
  "constraints": ["10000 words"]
}
→ {"status": "created", "message": "Added new goal G1..."}

# List goals (finds goal in correct domain!)
GET /api/memory/goals?session_id=f2402de2...
→ {
    "goals": [{
      "goal_id": "G1",
      "description": "Write chapter 1",
      "constraints": ["10000 words"],
      "features": [],
      "status": "pending"
    }]
  }  ✅ Goal shows up!
```

**Logs**: No errors! All operations return HTTP 200/201.

---

## Files Modified

### v0.42.4 Changes:

1. **mcp_client_for_ollama/web/integration/client_wrapper.py**
   - Line 18: Added `self.memory_domain = None` to track domain
   - Line 464: Store domain in `create_memory_session()`
   - Lines 513-518: Use stored domain in `list_goals()`
   - Lines 605-618: Use stored domain in `create_goal()`
   - Lines 722-735: Use stored domain in `create_feature()`

2. **mcp_client_for_ollama/__init__.py** - Version bump to 0.42.4

3. **pyproject.toml** - Version bump to 0.42.4

4. **mcp_client_for_ollama/web/app.py** - API version bump to 0.42.4

5. **docs/QA_FIXES_v0.42.4.md** - This documentation

---

## Status of QA Bugs

### ✅ FIXED in v0.42.4

1. **Error while creating goal - domain mismatch** (Lines 381-416 in qa_bugs.md)
   - Goals now work with custom domains
   - No more "Memory file not found" errors
   - Goals show up correctly in UI

### ✅ FIXED in v0.42.3

1. **Memory session creation crash** - Removed cleanup() calls
2. **Session manager cleanup error** - Sessions now persist correctly
3. **Goal creation errors** - All CRUD operations working

### ✅ FIXED in v0.42.2

1. **Server reload crash** - Removed cleanup() call
2. **Event loop closed errors** - Fixed with asyncio.wait_for()
3. **Session invalidation** - Background cleanup thread
4. **Obsidian tool errors** - Graceful cleanup

---

## Upgrade Instructions

### From v0.42.3:

```bash
cd /path/to/mcp-client-for-ollama

# Pull latest changes
git pull

# Restart web server
pkill -f "mcp_client_for_ollama.web.app"
python3 -m mcp_client_for_ollama.web.app

# Or if running as service:
systemctl restart mcp-web
```

**No breaking changes** - Existing sessions with domain "web" continue to work. Custom domains are now properly supported.

---

## Testing Checklist

- [x] Memory session creation with custom domain
- [x] Goal creation in custom domain
- [x] Goal listing from custom domain
- [x] Feature creation in custom domain
- [x] Backward compatibility with domain "web"
- [x] No "Memory file not found" errors
- [x] All operations return 200/201
- [x] No errors in server logs

---

## Summary

**Impact**: This was a critical bug that made custom domains completely non-functional. Users could create memory sessions with custom domains, but couldn't actually use them because all subsequent operations defaulted to domain "web".

**Fix**: Simple but important - track the domain used when creating a memory session, and use that same domain for all subsequent operations.

**Result**: Memory system now fully supports custom domains while maintaining backward compatibility with the default "web" domain.

---

## Next Steps

The memory system is now fully functional with:
- ✅ Persistent sessions
- ✅ No cancel scope errors
- ✅ Custom domain support
- ✅ Complete CRUD operations
- ✅ Goals and features tracking

All critical QA bugs related to memory have been resolved! 🎉
