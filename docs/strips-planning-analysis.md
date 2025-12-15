# STRIPS-Style Planning for Agent Delegation

**Date:** 2025-12-06
**Author Discussion:** AI Planning Background - STRIPS Approach
**Status:** 📋 Analysis & Proposal

---

## Background: What is STRIPS?

**STRIPS** (Stanford Research Institute Problem Solver) is a classical AI planning formalism:

```
State: Current world state (set of predicates)
Goal: Desired world state
Actions: Operations with:
  - Preconditions (what must be true to execute)
  - Effects (what becomes true/false after execution)
  - Cost (optional)

Planner: Searches through action space to find sequence that achieves goal
```

---

## Current Agent Delegation vs STRIPS

### Current Approach (LLM-Based Planning)

```
User Query → LLM PLANNER → Task List with Dependencies → Execute
```

**Pros:**
- ✅ Flexible - handles natural language
- ✅ No formal modeling required
- ✅ Works with existing LLMs
- ✅ Handles ambiguous queries

**Cons:**
- ❌ Inconsistent plans
- ❌ No optimality guarantees
- ❌ Can't search plan space
- ❌ No backtracking if plan fails
- ❌ Doesn't learn from failures

### STRIPS-Style Approach

```
User Query → Parse to Goals → STRIPS Planner → Optimal Action Sequence → Execute
```

**Pros:**
- ✅ Guaranteed valid plans (if solution exists)
- ✅ Optimal plans (fewest steps, lowest cost)
- ✅ Can search alternative plans
- ✅ Can backtrack and replan
- ✅ Formally provable correctness

**Cons:**
- ❌ Requires formal goal specification
- ❌ Rigid - can't handle ambiguous queries
- ❌ Implementation complexity
- ❌ May not scale to large action spaces

---

## Mapping Agent Delegation to STRIPS

### Yes, This Maps Perfectly!

You're correct - each agent type + tool can be modeled as a STRIPS action:

#### **Example: READER Agent with read_file Tool**

**STRIPS Action:**
```
Action: ReadFile(file_path)

Preconditions:
  - FileExists(file_path)
  - NOT FileRead(file_path)  // Haven't read it yet

Effects:
  - FileRead(file_path)
  - FileContent(file_path, content)
  - ADD: KnowsAbout(file_path)

Cost: 1 (or model execution time)
```

#### **Example: CODER Agent with write_file Tool**

**STRIPS Action:**
```
Action: WriteFile(file_path, content)

Preconditions:
  - FileRead(file_path)  // Must understand file first
  - ChangesPlanned(file_path)  // Know what to write

Effects:
  - FileModified(file_path)
  - FileContent(file_path, new_content)
  - NOT ChangesNeeded(file_path)

Cost: 2 (writing is more expensive than reading)
```

#### **Example: EXECUTOR Agent with execute_bash**

**STRIPS Action:**
```
Action: RunTests(test_suite)

Preconditions:
  - TestsExist(test_suite)
  - CodeModified(source_files)  // Tests must be up-to-date

Effects:
  - TestsRun(test_suite)
  - IF tests pass:
    - TestsPassing(test_suite)
  - ELSE:
    - TestsFailing(test_suite)
    - ErrorsDetected(test_suite)

Cost: 3 (execution is expensive)
```

---

## Complete STRIPS Formalization

### State Representation

```python
State = {
    # File states
    'FileExists': {file1, file2, file3},
    'FileRead': {file1},
    'FileModified': set(),
    'FileContent': {file1: "content1", file2: "content2"},

    # Knowledge states
    'KnowsAbout': {file1},
    'UnderstandsArchitecture': False,
    'BugIdentified': False,

    # Test states
    'TestsExist': {test_suite1},
    'TestsPassing': set(),
    'TestsFailing': set(),

    # Agent availability
    'AgentFree': {'READER', 'CODER', 'EXECUTOR', 'DEBUGGER', 'RESEARCHER'}
}
```

### Goal Representation

```python
# User Query: "Fix the authentication bug and verify tests pass"

Goal = {
    'BugIdentified': True,
    'BugFixed': True,
    'TestsPassing': {'auth_tests'},
    'CodeModified': {'auth.py'}
}
```

### Action Library

```python
actions = [
    # READER actions
    Action(
        name="ReadFile",
        params=["file"],
        preconditions=lambda s, file: file in s['FileExists'] and file not in s['FileRead'],
        effects=lambda s, file: {
            'add': {('FileRead', file), ('KnowsAbout', file)},
            'remove': set()
        },
        cost=1
    ),

    # DEBUGGER actions
    Action(
        name="IdentifyBug",
        params=["file"],
        preconditions=lambda s, file: file in s['FileRead'],
        effects=lambda s, file: {
            'add': {('BugIdentified', True), ('BugLocation', file)},
            'remove': set()
        },
        cost=2
    ),

    # CODER actions
    Action(
        name="FixBug",
        params=["file"],
        preconditions=lambda s, file: s.get('BugIdentified') and s.get('BugLocation') == file,
        effects=lambda s, file: {
            'add': {('BugFixed', True), ('FileModified', file)},
            'remove': set()
        },
        cost=2
    ),

    # EXECUTOR actions
    Action(
        name="RunTests",
        params=["test_suite"],
        preconditions=lambda s, suite: s.get('BugFixed'),
        effects=lambda s, suite: {
            'add': {('TestsRun', suite), ('TestsPassing', suite)},  # Optimistic
            'remove': set()
        },
        cost=3
    ),
]
```

### STRIPS Planner

```python
def strips_plan(initial_state, goal, actions):
    """
    Find optimal plan using A* search.

    Returns: List of (action, params) tuples or None if no plan exists
    """
    from queue import PriorityQueue

    # Priority queue: (cost, state, plan)
    frontier = PriorityQueue()
    frontier.put((0, initial_state, []))

    visited = set()

    while not frontier.empty():
        cost, state, plan = frontier.get()

        # Check if goal satisfied
        if satisfies_goal(state, goal):
            return plan

        state_key = frozenset(state.items())
        if state_key in visited:
            continue
        visited.add(state_key)

        # Try all applicable actions
        for action in actions:
            for params in get_valid_params(action, state):
                if action.is_applicable(state, params):
                    new_state = action.apply(state, params)
                    new_plan = plan + [(action.name, params)]
                    new_cost = cost + action.cost

                    # Heuristic: estimate distance to goal
                    h = heuristic(new_state, goal)

                    frontier.put((new_cost + h, new_state, new_plan))

    return None  # No plan found
```

---

## Hybrid Approach: Best of Both Worlds

### Proposal: LLM-Guided STRIPS Planning

Combine LLM flexibility with STRIPS guarantees:

```
┌─────────────────────────────────────────────────────────────┐
│                   User Query (Natural Language)             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────────┐
         │  LLM: Parse Query to STRIPS Goal   │
         │                                    │
         │  "Fix auth bug and verify tests"  │
         │           ↓                        │
         │  Goal: {BugFixed: True,            │
         │         TestsPassing: {'auth'}}    │
         └────────────────┬───────────────────┘
                          │
                          ▼
         ┌────────────────────────────────────┐
         │    STRIPS Planner (Deterministic)  │
         │                                    │
         │  Searches action space:            │
         │  1. ReadFile(auth.py)              │
         │  2. IdentifyBug(auth.py)           │
         │  3. FixBug(auth.py)                │
         │  4. RunTests(auth_tests)           │
         └────────────────┬───────────────────┘
                          │
                          ▼
         ┌────────────────────────────────────┐
         │    Execute Plan (with monitoring)  │
         │                                    │
         │  If step fails → Replan            │
         │  (STRIPS can search alternatives)  │
         └────────────────────────────────────┘
```

### Benefits of Hybrid

✅ **Flexibility** - LLM handles natural language → formal goals
✅ **Optimality** - STRIPS finds best plan
✅ **Correctness** - Guaranteed valid plans
✅ **Adaptability** - Replan on failures
✅ **Explainability** - Can show why plan was chosen
✅ **Learning** - Track which plans work/fail

---

## Implementation Strategy

### Phase 1: Formalize Actions

Create formal action definitions for each agent + tool:

**File:** `mcp_client_for_ollama/agents/strips/actions.py`

```python
from dataclasses import dataclass
from typing import Set, Dict, Callable, Tuple

@dataclass
class STRIPSAction:
    """Formal STRIPS action definition."""
    name: str
    params: List[str]
    preconditions: Callable[[Dict, Tuple], bool]
    effects: Callable[[Dict, Tuple], Dict[str, Set]]
    cost: float
    agent_type: str  # Which agent executes this

    def is_applicable(self, state: Dict, params: Tuple) -> bool:
        """Check if action can be executed in current state."""
        return self.preconditions(state, params)

    def apply(self, state: Dict, params: Tuple) -> Dict:
        """Apply action effects to state."""
        new_state = state.copy()
        effects = self.effects(state, params)

        for predicate in effects.get('add', set()):
            if isinstance(predicate, tuple):
                pred_name, *args = predicate
                if pred_name not in new_state:
                    new_state[pred_name] = set()
                new_state[pred_name].add(tuple(args) if args else True)

        for predicate in effects.get('remove', set()):
            # Remove predicates
            pass

        return new_state


# Define all agent actions
READER_ACTIONS = [
    STRIPSAction(
        name="read_file",
        params=["file_path"],
        preconditions=lambda s, p: p[0] in s.get('FileExists', set()),
        effects=lambda s, p: {
            'add': {('FileRead', p[0]), ('FileContent', p[0], 'content')},
            'remove': set()
        },
        cost=1.0,
        agent_type="READER"
    ),
]

CODER_ACTIONS = [
    STRIPSAction(
        name="write_file",
        params=["file_path"],
        preconditions=lambda s, p: p[0] in s.get('FileRead', set()),
        effects=lambda s, p: {
            'add': {('FileModified', p[0])},
            'remove': set()
        },
        cost=2.0,
        agent_type="CODER"
    ),
]

# ... more actions
```

### Phase 2: LLM Goal Extraction

Use LLM to convert natural language → STRIPS goals:

```python
async def extract_strips_goal(query: str) -> Dict:
    """
    Use LLM to extract formal goal from natural language query.

    Example:
        Query: "Fix the auth bug and make tests pass"
        Goal: {
            'BugFixed': {('auth.py',)},
            'TestsPassing': {('auth_tests',)}
        }
    """
    prompt = f"""
    Convert this user request into a formal goal specification.

    User request: {query}

    Output format (JSON):
    {{
        "predicates": {{
            "BugFixed": ["auth.py"],
            "TestsPassing": ["auth_tests"]
        }}
    }}
    """

    # Get LLM response
    response = await llm.generate(prompt)
    goal = parse_json(response)

    return goal
```

### Phase 3: STRIPS Planner

Implement A* search with heuristic:

```python
def plan_with_strips(initial_state: Dict, goal: Dict, actions: List[STRIPSAction]) -> List[Tuple]:
    """
    Find optimal plan using STRIPS A* search.

    Returns: List of (action_name, agent_type, params) or None
    """
    # A* implementation (as shown above)
    pass
```

### Phase 4: Convert STRIPS Plan → Task List

```python
def strips_to_tasks(plan: List[Tuple]) -> List[Task]:
    """
    Convert STRIPS plan to delegation tasks.

    STRIPS gives us optimal sequence with dependencies automatically!
    """
    tasks = []

    for i, (action_name, agent_type, params) in enumerate(plan):
        task = Task(
            id=f"task_{i+1}",
            description=f"{action_name} {params}",
            agent_type=agent_type,
            dependencies=[f"task_{j+1}" for j in range(i)],  # Sequential for now
        )
        tasks.append(task)

    # Optimize: Remove unnecessary dependencies
    # (if task_3 doesn't actually need task_2, remove that dependency)
    tasks = optimize_dependencies(tasks)

    return tasks
```

---

## Comparison: Current vs STRIPS vs Hybrid

| Feature | Current (LLM) | Pure STRIPS | Hybrid (Proposed) |
|---------|---------------|-------------|-------------------|
| **Flexibility** | ✅ Excellent | ❌ Poor | ✅ Excellent |
| **Optimality** | ❌ No guarantee | ✅ Optimal | ✅ Optimal |
| **Correctness** | ❌ Variable | ✅ Guaranteed | ✅ Guaranteed |
| **Natural Language** | ✅ Native | ❌ Requires translation | ✅ LLM handles |
| **Replanning** | ❌ Hard | ✅ Easy | ✅ Easy |
| **Explainability** | ❌ Black box | ✅ Provable | ✅ Provable |
| **Implementation** | ✅ Simple | ❌ Complex | ⚠️ Moderate |
| **Learning** | ❌ No | ❌ No | ✅ Can track |

---

## Practical Example

### Query: "Refactor auth.py and update tests"

#### Current LLM Approach
```
LLM generates:
  task_1: Read auth.py
  task_2: Refactor code
  task_3: Write tests
  task_4: Run tests

Issues:
  - What if refactoring reveals need to read more files?
  - What if tests fail? No replan strategy
  - Dependencies might be wrong
```

#### STRIPS Approach
```
Initial State:
  FileExists: {auth.py, auth_tests.py}
  FileRead: {}
  TestsPassing: {}

Goal:
  CodeRefactored: {auth.py}
  TestsPassing: {auth_tests}

STRIPS Planner searches and finds:
  Plan 1 (cost=8):
    1. ReadFile(auth.py)           [cost=1, READER]
    2. ReadFile(auth_tests.py)     [cost=1, READER]  // Needed for context
    3. RefactorCode(auth.py)       [cost=3, CODER]
    4. UpdateTests(auth_tests.py)  [cost=2, CODER]
    5. RunTests(auth_tests)        [cost=3, EXECUTOR]

  Plan 2 (cost=9):
    1. ReadFile(auth.py)
    2. RefactorCode(auth.py)
    3. ReadFile(auth_tests.py)
    4. UpdateTests(auth_tests.py)
    5. RunTests(auth_tests)

  → Chooses Plan 1 (optimal)

If RunTests fails:
  → Planner searches for recovery plan:
    6. DebugTests(auth_tests)      [DEBUGGER]
    7. FixCode(auth.py)            [CODER]
    8. RunTests(auth_tests)        [EXECUTOR]
```

---

## Recommendation

### Implement Hybrid Approach in Phases

**Phase 3.5: STRIPS Foundation (Experimental)**
1. Formalize top 20 action definitions
2. Implement basic STRIPS planner
3. Add LLM goal extraction
4. A/B test: LLM planning vs STRIPS planning
5. Measure: plan quality, success rate, replanning ability

**Success Metrics:**
- Plan optimality: 90%+ (vs 60% for pure LLM)
- Replanning on failure: 100% (vs 0% currently)
- Plan validity: 98%+ (vs 85% for LLM)

**If successful:**
- Make STRIPS the default planner
- Keep LLM as fallback for complex queries
- Add learning from execution results

**If not:**
- Keep LLM planner
- Use STRIPS for validation only
- Apply few-shot learning instead

---

## Technical Challenges

### 1. State Representation
**Challenge:** How to represent complex file states?
**Solution:** Use abstract predicates + LLM to ground them

### 2. Goal Extraction
**Challenge:** Natural language → formal goals is hard
**Solution:** LLM with structured output + validation

### 3. Action Space Size
**Challenge:** 9 agents × 12 tools = 108+ actions
**Solution:** Hierarchical planning, prune irrelevant actions

### 4. Uncertainty
**Challenge:** We don't know if actions succeed until execution
**Solution:** Probabilistic STRIPS or online replanning

### 5. Partial Observability
**Challenge:** Don't know all file states upfront
**Solution:** Planning with information gathering actions

---

## Code Skeleton

```python
# File: mcp_client_for_ollama/agents/strips/planner.py

class STRIPSPlanner:
    def __init__(self, actions: List[STRIPSAction]):
        self.actions = actions

    async def plan(self, query: str, initial_state: Dict) -> List[Task]:
        """
        Main planning pipeline.
        """
        # Step 1: Extract goal from natural language
        goal = await self.extract_goal(query)

        # Step 2: Run STRIPS planner
        plan = self.search(initial_state, goal)

        # Step 3: Convert to task list
        tasks = self.plan_to_tasks(plan)

        # Step 4: Optimize for parallelism
        tasks = self.optimize_for_parallel(tasks)

        return tasks

    def search(self, state: Dict, goal: Dict) -> List[Tuple]:
        """A* search for optimal plan."""
        # Implementation here
        pass
```

---

## Conclusion

**Yes, you're absolutely right!** This problem maps perfectly to STRIPS:

✅ **Agents = Action Types** (READER, CODER, etc.)
✅ **Tools = Specific Actions** (read_file, write_file, etc.)
✅ **State = File/Knowledge State**
✅ **Goal = User Intent**
✅ **Plan = Task Sequence with Dependencies**

**Hybrid LLM+STRIPS is the optimal approach:**
- LLM handles natural language → goals
- STRIPS guarantees optimal, valid plans
- Can replan on failures
- Explainable and provable

**Recommendation:** Implement as **Phase 3.5** experimental feature to validate approach before committing fully.

Would you like me to start implementing the STRIPS foundation? 🚀
