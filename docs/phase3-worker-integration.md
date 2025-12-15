# Phase 3: Worker Agent Memory Integration

**Status**: ✅ COMPLETED
**Timeline**: Weeks 5-6
**Goal**: Enable worker agents to read and update memory state during execution

## Overview

Phase 3 completes the memory integration by implementing the "boot ritual" pattern and providing memory update tools. Worker agents now receive memory context before execution and can update memory state as they work.

This phase transforms worker agents from stateless task executors into memory-aware collaborators that maintain persistent state across sessions.

## What Was Implemented

### 1. Boot Ritual Module (`memory/boot_ritual.py`)

The boot ritual builds comprehensive memory context that gets injected into worker agent messages before task execution.

**Key Functions**:

```python
@staticmethod
def build_memory_context(
    memory: DomainMemory,
    agent_type: str,
    task_description: Optional[str] = None,
    max_recent_progress: int = 5
) -> str:
    """Build memory context for a worker agent."""
```

**Context Includes**:
- Session metadata (ID, domain, description)
- Progress summary (total features, completion %, status breakdown)
- All goals with their features and pass/fail criteria
- Required tests for each feature
- Test results (if any)
- Domain-specific state (test framework, language, git status, etc.)
- Recent progress log entries
- Protocol for memory-aware work
- Current task description

**Example Output**:
```
================================================================================
MEMORY CONTEXT - READ THIS BEFORE TAKING ACTION
================================================================================

SESSION: auth-system-123
DOMAIN: coding
DESCRIPTION: Build authentication system with JWT tokens

PROGRESS SUMMARY:
  Total Features: 5
  Completed: 2 (40.0%)
  In Progress: 1
  Pending: 1
  Failed: 1
  Completion: 40.0%

GOALS AND FEATURES:
────────────────────────────────────────────────────────────────────────────────
GOAL: G1 - User authentication
  ● F1: Login endpoint [COMPLETED] ✓
    Pass/Fail Criteria:
      • Returns JWT on success
      • Returns 401 on failure
    Required Tests: test_login_success, test_login_failure
    Test Status: [2/2 passing] ✓

  ● F2: Password hashing [COMPLETED] ✓
    ...

DOMAIN STATE:
  Test Framework: pytest
  Run Command: pytest -v
  Language: python
  Git Enabled: True

RECENT PROGRESS:
  [INITIALIZER] Created session → SUCCESS
    Initialized memory
  [CODER] Implemented F1 → SUCCESS
    Added login endpoint with JWT
  [EXECUTOR] Ran tests for F1 → SUCCESS
    All tests passing

PROTOCOL:
  1. Review the memory state above
  2. Pick ONE feature to work on (preferably pending or failed)
  3. Implement your changes
  4. Test your changes (if applicable)
  5. Update the feature status using memory update tools
  6. Log your progress for future sessions

YOUR TASK:
Implement token validation middleware
```

**Helper Functions**:

```python
@staticmethod
def get_next_feature_suggestion(memory: DomainMemory, agent_type: str) -> Optional[Feature]:
    """Suggest the next feature to work on based on priority."""
    # Priority order: failed → high priority pending → pending → in_progress

@staticmethod
def format_feature_context(feature: Feature) -> str:
    """Format detailed context for a specific feature."""

@staticmethod
def build_tool_update_message(feature_id: str, new_status: str, details: str) -> str:
    """Build instruction message for updating memory."""
```

### 2. Memory Update Tools (`memory/tools.py`)

Provides builtin tools that agents can call to update memory state.

**MemoryTools Class**:

```python
class MemoryTools:
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
        self.current_session_id: Optional[str] = None
        self.current_domain: Optional[str] = None

    def set_current_session(self, session_id: str, domain: str) -> None:
        """Set the current session context."""

    def update_feature_status(
        self,
        feature_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> str:
        """Update the status of a feature."""

    def log_progress(
        self,
        agent_type: str,
        action: str,
        outcome: str,
        details: str,
        feature_id: Optional[str] = None,
        artifacts_changed: Optional[list] = None
    ) -> str:
        """Log progress entry to memory."""

    def add_test_result(
        self,
        feature_id: str,
        test_id: str,
        passed: bool,
        details: Optional[str] = None
    ) -> str:
        """Add test result and auto-update feature status."""

    def get_memory_state(self) -> str:
        """Get formatted summary of current memory state."""

    def get_feature_details(self, feature_id: str) -> str:
        """Get detailed information about a specific feature."""
```

**Tool Behaviors**:

1. **update_feature_status**:
   - Validates status value (pending/in_progress/completed/failed)
   - Updates feature status and timestamp
   - Adds notes to feature
   - Triggers goal status update
   - Returns formatted confirmation

2. **log_progress**:
   - Validates outcome type (success/failure/partial/blocked)
   - Creates ProgressEntry with timestamp
   - Links to feature_id if provided
   - Tracks artifacts changed
   - Returns formatted summary

3. **add_test_result**:
   - Creates TestResult entry
   - **Auto-updates feature status** based on test outcomes:
     - All tests pass → COMPLETED
     - Some tests pass → IN_PROGRESS
     - All tests fail → FAILED
   - Returns formatted result with auto-update notification

4. **get_memory_state**:
   - Returns full memory context (same as boot ritual)
   - Useful for agents to refresh their understanding

5. **get_feature_details**:
   - Returns focused view of single feature
   - Includes criteria, tests, test results, notes

### 3. DelegationClient Integration

**Initialization** (`__init__`):

```python
# Memory components (Phase 2+3)
if self.memory_enabled:
    memory_dir = os.path.expanduser(self.config.get("memory", {}).get("storage_dir", "~/.mcp-memory"))
    self.memory_storage = MemoryStorage(base_dir=Path(memory_dir))
    self.memory_initializer = MemoryInitializer(self.memory_storage)
    self.memory_tools = MemoryTools(self.memory_storage)  # Phase 3
    self.current_memory: Optional[DomainMemory] = None
```

**Boot Ritual Injection** (`_build_task_context`):

```python
# Phase 3: Inject memory context for worker agents (boot ritual)
if self.memory_enabled and self.current_memory and task.agent_type not in ["PLANNER", "INITIALIZER"]:
    memory_context = BootRitual.build_memory_context(
        memory=self.current_memory,
        agent_type=task.agent_type,
        task_description=task.description
    )
    messages.append({
        "role": "system",
        "content": memory_context
    })
```

**Key Points**:
- Boot ritual runs for ALL worker agents (CODER, EXECUTOR, RESEARCHER, etc.)
- PLANNER and INITIALIZER are excluded (they don't need memory context)
- Memory context inserted as system message BEFORE task description
- Ensures agents always see current state before acting

**Session Management** (`process_with_memory`):

```python
def process_with_memory(self, user_request: str, session_id: Optional[str] = None) -> str:
    # 1. Run INITIALIZER if new session
    # 2. Bootstrap memory from INITIALIZER output
    # 3. Set current session for memory tools
    self.memory_tools.set_current_session(memory.metadata.session_id, memory.metadata.domain)
    # 4. Execute with memory context
    self.current_memory = memory
    result = self.process(task_description)
```

### 4. CODER Agent Update

Added memory-aware workflow section to `agents/definitions/coder.json`:

```
**MEMORY-AWARE WORKFLOW** (when memory context is provided):
If you see a MEMORY CONTEXT section above, you are working within a persistent session:
1. Review the memory context to understand current goals and features
2. Focus on ONE feature from the memory at a time
3. After implementing changes, the test/validation will happen separately
4. The memory system will track your progress across sessions
```

**Rationale**:
- Guides CODER to work in memory-aware mode
- Emphasizes single-feature focus (avoiding scope creep)
- Sets expectation that testing is separate (handled by EXECUTOR)
- Clarifies that progress persists across sessions

## Integration Points

### 1. Task Execution Flow

```
User Request
    ↓
PLANNER (if multi-step) - no memory context
    ↓
INITIALIZER (if new session) - creates memory
    ↓
Memory Bootstrapped
    ↓
Worker Agent Task
    ↓
Boot Ritual Injects Memory Context ← Phase 3
    ↓
Agent Executes with Memory Awareness
    ↓
Agent Updates Memory via Tools ← Phase 3
    ↓
Memory Persisted
    ↓
Next Task (memory carries forward)
```

### 2. Memory Context in Messages

```python
messages = [
    {"role": "system", "content": agent_system_prompt},
    {"role": "system", "content": memory_context},  # ← Boot ritual
    {"role": "user", "content": task_description}
]
```

### 3. Memory Tool Access

Memory tools are **not yet exposed as builtin tools** to agents. This is intentional for Phase 3:
- Tools exist in Python layer
- Can be called programmatically by orchestrator
- Phase 4+ will expose as builtin tools for agents to call directly

**Future Integration**:
```python
# Phase 4+: Register memory tools as builtins
builtin_tools.register("memory.update_feature_status", memory_tools.update_feature_status)
builtin_tools.register("memory.log_progress", memory_tools.log_progress)
builtin_tools.register("memory.add_test_result", memory_tools.add_test_result)
```

## Usage Examples

### Example 1: CODER Working on Feature

**Memory Context Injected**:
```
SESSION: auth-123
GOAL: G1 - User authentication
  ● F1: Login endpoint [PENDING]
    Criteria: Returns JWT on success, Returns 401 on failure
    Tests: test_login_success, test_login_failure

YOUR TASK: Implement login endpoint
```

**CODER Sees**:
1. System prompt (standard CODER instructions)
2. Memory context (above)
3. Task description ("Implement login endpoint")

**CODER Actions**:
1. Reviews memory context
2. Sees F1 is pending
3. Reads existing code
4. Implements login endpoint
5. (In future phases) Calls `memory.update_feature_status("F1", "in_progress")`

### Example 2: EXECUTOR Running Tests

**Memory Context Injected**:
```
SESSION: auth-123
GOAL: G1 - User authentication
  ● F1: Login endpoint [IN_PROGRESS]
    Tests: test_login_success, test_login_failure
    Test Status: [0/2 passing]

YOUR TASK: Run tests for F1
```

**EXECUTOR Actions**:
1. Reviews memory context
2. Sees F1 needs test_login_success and test_login_failure
3. Runs pytest for those tests
4. (In future phases) Calls `memory.add_test_result("F1", "test_login_success", True)`
5. Feature auto-updates to COMPLETED when all tests pass

### Example 3: Multi-Session Work

**Session 1**:
- INITIALIZER creates memory with F1, F2, F3
- CODER implements F1 (status → completed)
- Memory persisted

**Session 2** (different day):
- User returns: "Continue building auth system"
- DelegationClient loads existing memory (session-id from user or auto-resume)
- Boot ritual shows F1 completed, F2 pending, F3 pending
- CODER picks up where it left off
- No context lost between sessions ✅

## Testing Summary

**Total Tests**: 24 (all passing ✅)

### test_boot_ritual.py (10 tests)

1. `test_build_memory_context` - Comprehensive context building
2. `test_build_memory_context_with_test_results` - Test status display
3. `test_get_next_feature_suggestion_pending` - Feature prioritization
4. `test_get_next_feature_suggestion_no_work` - No pending features
5. `test_get_next_feature_suggestion_priority` - Priority-based selection
6. `test_format_feature_context` - Detailed feature formatting
7. `test_build_tool_update_message` - Tool instruction generation
8. `test_memory_context_includes_domain_state` - State inclusion
9. `test_memory_context_includes_recent_progress` - Progress log display
10. `test_memory_context_completion_percentage` - Progress metrics

### test_tools.py (14 tests)

1. `test_update_feature_status` - Status update workflow
2. `test_update_feature_status_invalid_status` - Validation
3. `test_update_feature_status_not_found` - Error handling
4. `test_update_feature_status_no_session` - Session requirement
5. `test_log_progress` - Progress logging
6. `test_log_progress_invalid_outcome` - Outcome validation
7. `test_add_test_result_pass` - Passing test result
8. `test_add_test_result_fail` - Failing test result
9. `test_add_test_result_auto_updates_status` - Auto-status update
10. `test_get_memory_state` - State summary
11. `test_get_feature_details` - Feature details
12. `test_get_feature_details_not_found` - Error handling
13. `test_set_current_session` - Session context
14. `test_update_feature_status_updates_goal` - Goal status propagation

**Coverage**: Boot ritual context building, memory update tools, error handling, auto-status updates

## What's Next: Phase 4

**Phase 4: Test Integration & State Validation (Weeks 7-8)**

Now that workers can read/update memory, the next phase will:

1. **Test Harness Integration**
   - EXECUTOR agent automatically logs test results to memory
   - Test execution tied to feature verification
   - Auto-status updates from test outcomes (already implemented in tools, needs orchestration)

2. **State Validation**
   - Consistency checks (e.g., completed feature must have passing tests)
   - State repair utilities
   - Memory health checks

3. **Builtin Tool Exposure**
   - Register memory tools as builtin tools
   - Agents can directly call `memory.update_feature_status()` etc.
   - Remove manual orchestration layer

4. **Enhanced Workflows**
   - "Continue from last session" command
   - "Show project status" command
   - Feature-driven task routing

## Key Achievements

✅ **Boot Ritual Pattern Implemented**
- Memory context injected before every worker task
- Agents always see current state before acting
- Consistent protocol across all agent types

✅ **Memory Update Infrastructure**
- Complete CRUD operations for features
- Progress logging with timestamps
- Test result tracking with auto-status updates

✅ **Seamless Integration**
- Minimal changes to existing DelegationClient
- Feature-flagged for gradual rollout
- Backward compatible (memory_enabled=False works)

✅ **Comprehensive Testing**
- 86 total memory tests (Phases 1-3 combined)
- 100% passing rate
- Coverage of happy paths and error cases

✅ **Memory-Aware Agents**
- CODER updated with memory workflow
- Foundation for other agents (EXECUTOR, RESEARCHER, etc.)
- Consistent experience across agent types

## Files Modified/Created

### Created:
- `mcp_client_for_ollama/memory/boot_ritual.py` (220 lines)
- `mcp_client_for_ollama/memory/tools.py` (280 lines)
- `tests/memory/test_boot_ritual.py` (265 lines)
- `tests/memory/test_tools.py` (267 lines)
- `docs/phase3-worker-integration.md` (this file)

### Modified:
- `mcp_client_for_ollama/memory/__init__.py` - Exported BootRitual, MemoryTools
- `mcp_client_for_ollama/agents/delegation_client.py` - Integrated boot ritual
- `mcp_client_for_ollama/agents/definitions/coder.json` - Added memory workflow

## Summary

Phase 3 successfully implements the "Agents read memory before acting" principle from the Anthropic pattern. Worker agents now receive rich memory context before every task and have tools to update memory as they work.

The memory system is now functional end-to-end:
1. **Phase 1**: Memory infrastructure (dataclasses, storage, schemas)
2. **Phase 2**: Session initialization (INITIALIZER agent creates memory)
3. **Phase 3**: Worker integration (boot ritual + update tools) ← **COMPLETED**

Next: Phase 4 will automate test-driven state updates and expose memory tools as builtins for direct agent access.
