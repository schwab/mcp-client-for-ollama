# Two-Phase Planning: Solving Partial Observability

**Date:** 2025-12-06
**Approach:** Information Gathering → Action Execution
**Status:** 📋 Design Proposal

---

## The Partial Observability Problem

### Classic STRIPS Assumes Full Observability

Traditional STRIPS planning assumes we know the complete state:

```python
# STRIPS assumption: We know everything
initial_state = {
    'FileExists': {all_files_in_project},  # ❓ But we don't know this!
    'FileContent': {file: content for file in all_files},  # ❓ Expensive to know upfront
    'BugLocation': 'auth.py:line_42',  # ❓ Don't know until we investigate
    'TestsFailing': {'test_auth'},  # ❓ Don't know until we run tests
}
```

**Problem:** We can't know the full state without executing expensive operations first!

### What We Actually Know Upfront

```python
# Reality: Very limited initial knowledge
initial_state = {
    'WorkingDirectory': '/home/user/project',
    'UserQuery': "Fix the authentication bug",
    'AvailableAgents': {'READER', 'CODER', 'EXECUTOR', 'DEBUGGER', 'RESEARCHER'},
    'AvailableTools': {'read_file', 'write_file', 'execute_bash', ...},
    # Everything else is unknown!
}
```

---

## Your Solution: Two-Phase Planning ✨

### Phase 1: Information Gathering (Read-Only)

**Goal:** Collect necessary information to create accurate action plan

**Allowed Operations:**
- ✅ `list_files` - Discover what files exist
- ✅ `read_file` - Understand file contents
- ✅ `file_exists` - Check file presence
- ✅ `execute_bash` (read-only) - Get system state (e.g., `git status`, `ls`)
- ✅ Search/grep operations
- ✅ Code analysis

**Forbidden Operations:**
- ❌ `write_file` - No modifications
- ❌ `delete_file` - No deletions
- ❌ Destructive bash commands

**Output:** Enriched state with full observability

### Phase 2: Action Execution (Write Operations)

**Goal:** Execute planned modifications based on gathered information

**Allowed Operations:**
- ✅ All write operations
- ✅ Code modifications
- ✅ File creation/deletion
- ✅ Test execution
- ✅ Deployment

**Input:** Complete state from Phase 1

---

## Architecture

### Complete Two-Phase Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Query (Natural Language)                │
│             "Fix the authentication bug and verify"             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────┐
              │   LLM: Extract High-Level Goal   │
              │                                  │
              │   Goal: Fix auth bug + verify    │
              └──────────────┬───────────────────┘
                             │
                             ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    PHASE 1: INFORMATION GATHERING              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                             │
              ┌──────────────────────────────────┐
              │  STRIPS Planner (Read-Only)      │
              │                                  │
              │  Actions allowed:                │
              │    - list_files                  │
              │    - read_file                   │
              │    - search_code                 │
              │    - execute_tests (dry-run)     │
              │                                  │
              │  Goal: Discover state            │
              └──────────────┬───────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────┐
              │   Execute Info Gathering Plan    │
              │                                  │
              │   task_1: List Python files      │
              │   task_2: Read auth.py           │
              │   task_3: Read auth_tests.py     │
              │   task_4: Search for "auth"      │
              │   task_5: Run tests (dry-run)    │
              └──────────────┬───────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────┐
              │    Enriched State (Complete!)    │
              │                                  │
              │  FileExists: {auth.py, ...}      │
              │  FileContent: {auth.py: "..."}   │
              │  BugLocation: auth.py:line_42    │
              │  TestsFailing: {test_login}      │
              │  Dependencies: {auth→db, ...}    │
              └──────────────┬───────────────────┘
                             │
                             ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    PHASE 2: ACTION EXECUTION                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                             │
              ┌──────────────────────────────────┐
              │  STRIPS Planner (Write-Enabled)  │
              │                                  │
              │  Initial State: Enriched State   │
              │  Actions allowed: ALL            │
              │                                  │
              │  Goal: Fix bug + verify          │
              └──────────────┬───────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────┐
              │     Optimal Action Plan          │
              │                                  │
              │   task_1: Fix auth.py:line_42    │
              │   task_2: Update tests           │
              │   task_3: Run tests              │
              │   task_4: Verify success         │
              └──────────────┬───────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────┐
              │   Execute Action Plan            │
              │                                  │
              │   (Parallel waves, monitored)    │
              └──────────────┬───────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────┐
              │         Final Result             │
              │                                  │
              │  ✅ Bug fixed                    │
              │  ✅ Tests passing                │
              └──────────────────────────────────┘
```

---

## Benefits of Two-Phase Approach

### 1. **Solves Partial Observability** ✅

**Before (Single Phase):**
```
STRIPS Planner: "I need to know what files exist to plan"
User: "But we don't know that yet!"
STRIPS Planner: "Then I can't create an optimal plan"
→ Deadlock
```

**After (Two-Phase):**
```
Phase 1: "Discover what files exist, read relevant ones"
Phase 1 completes → Now we know everything
Phase 2: "Given this complete state, create optimal plan"
→ Success!
```

### 2. **Natural Separation of Concerns** ✅

**Read vs Write** is a fundamental distinction:
- Reading is **safe** (no side effects)
- Writing is **dangerous** (can break things)
- Reading is **fast** (can parallelize aggressively)
- Writing needs **careful ordering** (dependencies matter)

### 3. **Better Parallelization** ✅

**Phase 1 (Info Gathering):**
```
All read operations can run in parallel!

Wave 1 (all parallel):
  - list_files(src/)
  - list_files(tests/)
  - read_file(README.md)
  - git status
  - run tests --dry-run

No dependencies needed - safe to run everything at once
```

**Phase 2 (Actions):**
```
Write operations must respect dependencies:

Wave 1: Fix code
Wave 2: Update tests (depends: code fixed)
Wave 3: Run tests (depends: tests updated)
```

### 4. **User Confirmation Point** ✅

Natural place for human approval:

```
Phase 1 completes
↓
Show user:
  "I found these files: [auth.py, db.py, tests/auth_test.py]
   The bug is in auth.py:42
   I will:
     1. Fix the null check in auth.py
     2. Add test case for null input
     3. Run test suite

   Proceed? (y/n)"
↓
If yes → Phase 2
If no → Replan or abort
```

### 5. **Better Error Handling** ✅

**Phase 1 Errors:**
- File not found → Easy to handle (ask user)
- No bug found → Can abort before making changes
- Tests already passing → Skip Phase 2 entirely

**Phase 2 Errors:**
- Code change breaks tests → Revert (we have clean state from Phase 1)
- Can rerun Phase 2 with different plan (same info)

### 6. **State Caching** ✅

Phase 1 output can be **cached**:

```
Query 1: "Fix auth bug"
→ Phase 1: Gather info about auth system
→ Cache results

Query 2: "Add logging to auth"
→ Phase 1: Skip! Use cached auth system state
→ Phase 2: Plan logging additions
```

---

## Implementation

### Phase Detection

```python
def needs_two_phase_planning(query: str, goal: Dict) -> bool:
    """
    Determine if query requires two-phase planning.

    Two-phase needed when:
    - Goal requires unknown file state
    - Goal involves modifications (write operations)
    - Goal is complex (3+ steps)
    """
    # Heuristics
    write_keywords = ['fix', 'add', 'modify', 'update', 'refactor', 'delete']
    unknown_state = ['bug', 'error', 'issue', 'find', 'search']

    has_writes = any(kw in query.lower() for kw in write_keywords)
    has_unknowns = any(kw in query.lower() for kw in unknown_state)

    return has_writes or has_unknowns
```

### Phase 1: Information Gathering Planner

```python
class InformationGatheringPlanner:
    """STRIPS planner restricted to read-only operations."""

    def __init__(self):
        # Only include read-only actions
        self.actions = [
            action for action in ALL_ACTIONS
            if action.is_read_only()
        ]

    def plan(self, query: str, initial_state: Dict) -> List[Task]:
        """
        Create information gathering plan.

        Goal: Maximize state knowledge
        Constraint: No side effects
        """
        # Extract information goals
        info_goal = self.extract_info_goal(query)
        # Example: "Fix auth bug" → Need to know:
        #   - Which files handle auth?
        #   - What is the bug?
        #   - Are tests failing?

        # Plan to gather this information
        plan = self.strips_search(
            initial_state=initial_state,
            goal=info_goal,
            actions=self.actions  # Read-only
        )

        return plan

    def extract_info_goal(self, query: str) -> Dict:
        """
        Convert user query to information-gathering goal.

        "Fix auth bug" →
        {
            'KnowsAuthFiles': True,
            'KnowsBugLocation': True,
            'KnowsTestStatus': True,
            'KnowsDependencies': True
        }
        """
        # LLM prompt to extract what info we need
        prompt = f"""
        For this query: "{query}"

        What information do we need to know before we can execute?

        Output as JSON goal predicates.
        """

        # LLM generates info goal
        info_goal = await llm.generate(prompt)
        return parse_json(info_goal)
```

### Phase 2: Action Planner

```python
class ActionPlanner:
    """STRIPS planner with full action set."""

    def __init__(self):
        self.actions = ALL_ACTIONS  # All actions (read + write)

    def plan(self, query: str, enriched_state: Dict) -> List[Task]:
        """
        Create action plan with complete state knowledge.

        Now we have full observability from Phase 1!
        """
        # Extract action goal
        action_goal = self.extract_action_goal(query)
        # Example: "Fix auth bug" →
        #   {
        #       'BugFixed': True,
        #       'TestsPassing': True
        #   }

        # Plan with complete state
        plan = self.strips_search(
            initial_state=enriched_state,  # Complete!
            goal=action_goal,
            actions=self.actions  # All actions
        )

        return plan
```

### Unified Two-Phase Planner

```python
class TwoPhaseHybridPlanner:
    """Combines LLM flexibility with two-phase STRIPS planning."""

    def __init__(self):
        self.info_planner = InformationGatheringPlanner()
        self.action_planner = ActionPlanner()

    async def plan(self, query: str) -> Tuple[List[Task], List[Task]]:
        """
        Create two-phase plan.

        Returns:
            (phase1_tasks, phase2_tasks)
        """
        # Determine if two-phase needed
        if not needs_two_phase_planning(query):
            # Simple query - direct action plan
            return [], self.action_planner.plan(query, get_initial_state())

        # Phase 1: Information gathering
        phase1_tasks = self.info_planner.plan(
            query=query,
            initial_state=get_initial_state()
        )

        # Execute Phase 1 (not shown here)
        enriched_state = await execute_tasks(phase1_tasks)

        # Phase 2: Actions (based on gathered info)
        phase2_tasks = self.action_planner.plan(
            query=query,
            enriched_state=enriched_state
        )

        return phase1_tasks, phase2_tasks
```

---

## Concrete Example

### Query: "Fix the authentication bug and verify it's fixed"

#### Initial State (Sparse)

```python
initial_state = {
    'WorkingDirectory': '/home/user/myapp',
    'UserQuery': "Fix the authentication bug and verify it's fixed",
    # Everything else unknown!
}
```

#### Phase 1: Information Gathering Plan

**Info Goal:**
```python
info_goal = {
    'KnowsAuthFiles': True,
    'KnowsBugLocation': True,
    'KnowsTestFiles': True,
    'KnowsTestStatus': True
}
```

**STRIPS Plan (Read-Only):**
```python
phase1_plan = [
    ('search_files', 'RESEARCHER', ('pattern=auth',)),
    ('read_file', 'READER', ('src/auth/login.py',)),
    ('read_file', 'READER', ('src/auth/session.py',)),
    ('list_files', 'EXECUTOR', ('tests/',)),
    ('run_tests', 'EXECUTOR', ('tests/test_auth.py', '--dry-run')),
]
```

**Execution (Parallel - all read-only!):**
```
Wave 1 (all parallel):
  ✅ task_1: Search for auth files → Found: login.py, session.py
  ✅ task_2: Read login.py → Found bug at line 42: missing null check
  ✅ task_3: Read session.py → OK
  ✅ task_4: List test files → Found: test_auth.py
  ✅ task_5: Run tests (dry) → test_null_login FAILING
```

#### Enriched State (Complete!)

```python
enriched_state = {
    'WorkingDirectory': '/home/user/myapp',
    'FileExists': {'src/auth/login.py', 'src/auth/session.py', 'tests/test_auth.py'},
    'FileContent': {
        'src/auth/login.py': "def login(user):\n    return user.name  # BUG: no null check",
        'src/auth/session.py': "...",
        'tests/test_auth.py': "def test_null_login(): ..."
    },
    'BugLocation': 'src/auth/login.py:42',
    'BugType': 'missing_null_check',
    'TestsFailing': {'test_null_login'},
    'TestsPassing': {'test_valid_login', 'test_logout'},
}
```

#### Phase 2: Action Plan

**Action Goal:**
```python
action_goal = {
    'BugFixed': True,
    'TestsPassing': {'test_null_login'},  # This specific test must pass
}
```

**STRIPS Plan (With Writes):**
```python
phase2_plan = [
    ('fix_null_check', 'CODER', ('src/auth/login.py', 'line_42')),
    ('run_tests', 'EXECUTOR', ('tests/test_auth.py',)),
]
```

**Execution (Sequential - has dependencies!):**
```
Wave 1:
  task_1: Fix null check in login.py ✅

Wave 2 (depends: task_1):
  task_2: Run tests → All passing ✅
```

**Result:** ✅ Bug fixed, tests passing!

---

## Advantages Over Single-Phase

| Aspect | Single-Phase STRIPS | Two-Phase STRIPS |
|--------|---------------------|------------------|
| **State Knowledge** | Assumes full (unrealistic) | Gathers then acts (realistic) |
| **Planning Quality** | Poor (missing info) | Optimal (complete info) |
| **Safety** | Risky (might write wrong) | Safe (read first, write second) |
| **Parallelization** | Limited | Phase 1 fully parallel |
| **User Approval** | No natural checkpoint | After Phase 1 |
| **Error Recovery** | Hard | Easy (revert to Phase 1 state) |
| **Efficiency** | Wasteful (over-planning) | Focused (know what to do) |

---

## Implementation Priority

### Phase 3.5: Experimental Two-Phase STRIPS

**Step 1:** Classify actions as read-only vs write
```python
# Add to each action definition
action.is_read_only = True/False
```

**Step 2:** Implement information gathering goal extraction
```python
def extract_info_goal(query: str) -> Dict:
    # LLM: "What do we need to know?"
    pass
```

**Step 3:** Create two separate planners
- InformationGatheringPlanner (read-only actions)
- ActionPlanner (all actions)

**Step 4:** Implement two-phase execution flow
```python
phase1_tasks = await info_planner.plan(query)
enriched_state = await execute_tasks(phase1_tasks)
phase2_tasks = await action_planner.plan(query, enriched_state)
await execute_tasks(phase2_tasks)
```

**Step 5:** Add user confirmation between phases (optional)

---

## Potential Issues & Solutions

### Issue 1: Phase 1 Too Expensive

**Problem:** Reading every file is slow
**Solution:** LLM filters relevant files first

```python
# Ask LLM: "Which files are likely relevant for fixing auth bug?"
relevant_files = llm.predict_relevant_files(query)
# Only read those in Phase 1
```

### Issue 2: Circular Dependencies

**Problem:** Need to read file A to know we need file B
**Solution:** Iterative information gathering

```python
# Phase 1.1: Initial scan
# Phase 1.2: Follow-up based on 1.1 results
# Phase 1.3: Final checks
# Then Phase 2
```

### Issue 3: State Too Large

**Problem:** Enriched state has megabytes of data
**Solution:** Abstract state representation

```python
enriched_state = {
    'FileSummaries': {file: summary for file in relevant_files},  # Not full content
    'BugLocation': 'auth.py:42',
    'KeyFindings': ['null check missing', 'test failing'],
}
```

---

## Recommendation

**YES - Implement Two-Phase Planning!** 🚀

**Why:**
✅ Solves partial observability elegantly
✅ Natural separation (read vs write)
✅ Better parallelization (Phase 1 fully parallel)
✅ Safer (understand before modifying)
✅ User confirmation point built-in
✅ Better error handling

**Effort:** ~15-20 hours
**Impact:** High - enables true STRIPS optimality

**Next Steps:**
1. Tag all actions as `read_only: true/false`
2. Implement info goal extraction
3. Split planner into two phases
4. Test on real queries

This is a **brilliant solution** to the partial observability problem! 🎯
