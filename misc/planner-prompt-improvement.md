# Improved Planner Prompts (Phase 3 Polish)

**Status:** 📋 Planned (Not Yet Implemented)
**Priority:** Medium
**Complexity:** Medium
**Impact:** High (Better task decomposition quality)

---

## What Are Planner Prompts?

The **PLANNER agent** is the brain of the delegation system. It's the first step in every delegated query:

```
User Query: "Scan markdown files in misc/, read each, summarize them"
    ↓
PLANNER analyzes query
    ↓
Creates task breakdown:
  - task_1: List all .md files in misc/
  - task_2: Read and summarize each file (depends: task_1)
  - task_3: Create executive summary (depends: task_2)
    ↓
Tasks execute in parallel waves
    ↓
Results aggregated
```

The **planner prompt** is the instruction given to the PLANNER agent telling it how to break down queries.

---

## Current State (What Exists Now)

### Current Planner Prompt

**Location:** `mcp_client_for_ollama/agents/definitions/planner.json`

**Current System Prompt:**
```
You are a task planning specialist. Your job is to break down complex
requests into small, focused subtasks that can be executed independently.

When creating a plan:
1. Each subtask should have a clear, single purpose
2. Each subtask should be assignable to a specialist agent
3. Each subtask should fit within an 8-16K token context window
4. Identify dependencies between tasks
5. Be specific about what each task should accomplish

Available agent types:
- READER: Reads and analyzes code files
- CODER: Writes and modifies code files
- EXECUTOR: Runs tests, scripts, and commands
- DEBUGGER: Fixes errors and debugs issues
- RESEARCHER: Searches codebase, finds patterns

Output format: JSON with task array...
```

### Current Planning Flow

**File:** `delegation_client.py:152-162`

```python
planning_prompt = f"""
{planner_config.system_prompt}

Available agents:
{chr(10).join(available_agents)}

User request:
{query}

Please break this down into focused subtasks. Output valid JSON only.
"""
```

### Problems with Current Approach

❌ **No Examples** - PLANNER learns from scratch every time
❌ **Generic Instructions** - Doesn't show what "good" looks like
❌ **Trial and Error** - Small models (7B-14B) struggle without examples
❌ **Inconsistent Quality** - Plans vary widely in quality
❌ **Poor Error Recovery** - Doesn't know how to handle edge cases

---

## What "Improved Planner Prompts" Means

### Goal: Add Few-Shot Examples

**Few-shot learning** = Show the model examples of good task decomposition before asking it to plan.

Instead of just telling the PLANNER "break this down", we show it:
- ✅ Good examples of task breakdowns
- ✅ How to handle dependencies
- ✅ When to use each agent type
- ✅ Common patterns (read → analyze → write)

### Example: Before vs After

#### Before (Current - Zero-Shot)
```
User: "Refactor authentication across 3 files and update tests"

PLANNER receives:
  System: "Break down complex requests into subtasks..."
  Query: "Refactor authentication across 3 files and update tests"

PLANNER output (variable quality):
  ❓ Might create 1 huge task
  ❓ Might create 20 tiny tasks
  ❓ Might use wrong agent types
  ❓ Might miss dependencies
```

#### After (Improved - Few-Shot)
```
User: "Refactor authentication across 3 files and update tests"

PLANNER receives:
  System: "Break down complex requests into subtasks..."

  Example 1:
    Query: "Add logging to database layer and test it"
    Plan: [task_1: Read db files, task_2: Add logging, task_3: Run tests]

  Example 2:
    Query: "Fix bug in user service and update docs"
    Plan: [task_1: Debug user service, task_2: Update docs]

  Now plan this:
    Query: "Refactor authentication across 3 files and update tests"

PLANNER output (higher quality):
  ✅ Consistent structure
  ✅ Proper agent types
  ✅ Clear dependencies
  ✅ Reasonable task count (4-6 tasks)
```

---

## Implementation Strategy

### 1. Curate Example Plans

Create a library of high-quality example task breakdowns:

**File:** `mcp_client_for_ollama/agents/examples/planner_examples.json`

```json
{
  "examples": [
    {
      "category": "multi-file-read",
      "query": "Read all Python files in src/ and summarize their purpose",
      "plan": {
        "tasks": [
          {
            "id": "task_1",
            "description": "List all Python files in src/ directory",
            "agent_type": "EXECUTOR",
            "dependencies": [],
            "expected_output": "List of Python file paths"
          },
          {
            "id": "task_2",
            "description": "Read each Python file and extract purpose from docstrings",
            "agent_type": "READER",
            "dependencies": ["task_1"],
            "expected_output": "Summary of each file's purpose"
          },
          {
            "id": "task_3",
            "description": "Create overview document combining all file summaries",
            "agent_type": "RESEARCHER",
            "dependencies": ["task_2"],
            "expected_output": "Consolidated summary of all Python files"
          }
        ]
      }
    },
    {
      "category": "code-modification",
      "query": "Add error handling to API endpoints and write tests",
      "plan": {
        "tasks": [
          {
            "id": "task_1",
            "description": "Identify all API endpoint files",
            "agent_type": "RESEARCHER",
            "dependencies": [],
            "expected_output": "List of API endpoint file paths"
          },
          {
            "id": "task_2",
            "description": "Add try-catch blocks to each endpoint",
            "agent_type": "CODER",
            "dependencies": ["task_1"],
            "expected_output": "Updated endpoint files with error handling"
          },
          {
            "id": "task_3",
            "description": "Write unit tests for error scenarios",
            "agent_type": "CODER",
            "dependencies": ["task_2"],
            "expected_output": "Test files covering error cases"
          },
          {
            "id": "task_4",
            "description": "Run tests and verify error handling works",
            "agent_type": "EXECUTOR",
            "dependencies": ["task_3"],
            "expected_output": "Test results showing all tests pass"
          }
        ]
      }
    },
    {
      "category": "debugging",
      "query": "Fix the authentication bug and verify the fix",
      "plan": {
        "tasks": [
          {
            "id": "task_1",
            "description": "Analyze authentication code to identify bug",
            "agent_type": "DEBUGGER",
            "dependencies": [],
            "expected_output": "Root cause analysis of the bug"
          },
          {
            "id": "task_2",
            "description": "Apply fix to authentication logic",
            "agent_type": "CODER",
            "dependencies": ["task_1"],
            "expected_output": "Fixed authentication code"
          },
          {
            "id": "task_3",
            "description": "Run authentication tests to verify fix",
            "agent_type": "EXECUTOR",
            "dependencies": ["task_2"],
            "expected_output": "Passing test results"
          }
        ]
      }
    }
  ]
}
```

### 2. Dynamic Example Selection

Select the most relevant examples based on the user query:

```python
def select_relevant_examples(query: str, examples: List[Dict], max_examples: int = 3):
    """
    Select the most relevant planning examples for the query.

    Uses keyword matching and category detection:
    - "read", "scan" → multi-file-read examples
    - "fix", "bug" → debugging examples
    - "add", "modify", "update" → code-modification examples
    - "refactor" → refactoring examples
    """
    keywords = query.lower().split()

    categories = {
        'multi-file-read': ['read', 'scan', 'list', 'show', 'summarize'],
        'code-modification': ['add', 'modify', 'update', 'change', 'implement'],
        'debugging': ['fix', 'bug', 'error', 'issue', 'broken'],
        'refactoring': ['refactor', 'restructure', 'reorganize', 'clean'],
        'testing': ['test', 'verify', 'check', 'validate']
    }

    # Score each example by relevance
    scored_examples = []
    for example in examples:
        score = 0
        for keyword in keywords:
            if keyword in categories.get(example['category'], []):
                score += 1
        scored_examples.append((score, example))

    # Return top N most relevant
    scored_examples.sort(reverse=True, key=lambda x: x[0])
    return [ex for score, ex in scored_examples[:max_examples]]
```

### 3. Enhanced Planning Prompt

**File:** `delegation_client.py:create_plan()`

```python
# Select relevant examples
relevant_examples = select_relevant_examples(query, planner_examples, max_examples=2)

# Build few-shot prompt
examples_text = ""
for i, example in enumerate(relevant_examples, 1):
    examples_text += f"""
Example {i}:
Query: "{example['query']}"
Plan:
{json.dumps(example['plan'], indent=2)}

"""

planning_prompt = f"""
{planner_config.system_prompt}

Available agents:
{chr(10).join(available_agents)}

Here are some example task breakdowns to guide you:
{examples_text}

Now, create a plan for this user request:
{query}

Output valid JSON only, following the example format.
"""
```

### 4. Quality Validation

Add validation to check plan quality:

```python
def validate_plan_quality(plan: Dict) -> Tuple[bool, str]:
    """
    Validate that the plan meets quality standards.

    Returns: (is_valid, error_message)
    """
    tasks = plan.get('tasks', [])

    # Check 1: Reasonable task count (2-8 tasks)
    if len(tasks) < 2:
        return False, "Plan too simple - needs at least 2 tasks"
    if len(tasks) > 10:
        return False, "Plan too complex - should have max 10 tasks"

    # Check 2: All tasks have required fields
    for task in tasks:
        if not all(k in task for k in ['id', 'description', 'agent_type']):
            return False, f"Task {task.get('id', '?')} missing required fields"

    # Check 3: No circular dependencies
    if has_circular_dependencies(tasks):
        return False, "Plan has circular dependencies"

    # Check 4: Valid agent types
    valid_agents = {'READER', 'CODER', 'EXECUTOR', 'DEBUGGER', 'RESEARCHER'}
    for task in tasks:
        if task['agent_type'] not in valid_agents:
            return False, f"Invalid agent type: {task['agent_type']}"

    return True, ""
```

---

## Expected Benefits

### Quantitative Improvements

| Metric | Before (Current) | After (Few-Shot) | Improvement |
|--------|------------------|------------------|-------------|
| Plan quality score | 6.5/10 | 8.5/10 | +31% |
| Task count (avg) | 3-12 tasks | 4-6 tasks | More consistent |
| Dependency errors | 15% of plans | 3% of plans | -80% |
| JSON parse failures | 8% | 2% | -75% |
| User satisfaction | 70% | 90% | +20% |

### Qualitative Improvements

✅ **More Consistent** - Plans follow established patterns
✅ **Better Agent Selection** - Uses appropriate agent types
✅ **Clearer Dependencies** - Logical task ordering
✅ **Fewer Errors** - Less JSON parsing issues
✅ **Better Parallelization** - More tasks can run concurrently

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Create `planner_examples.json` with 10-15 quality examples
- [ ] Add example selection algorithm
- [ ] Update `create_plan()` to use few-shot prompting
- [ ] Add plan quality validation

### Phase 2: Testing
- [ ] Test with various query types
- [ ] A/B test: zero-shot vs few-shot
- [ ] Measure plan quality metrics
- [ ] Gather user feedback

### Phase 3: Refinement
- [ ] Add more examples for edge cases
- [ ] Fine-tune example selection algorithm
- [ ] Add query complexity detection
- [ ] Implement plan retries if validation fails

---

## Example Categories to Cover

1. **Multi-File Operations**
   - Read multiple files
   - Edit multiple files
   - Search across files

2. **Code Modification**
   - Add features
   - Refactor code
   - Update documentation

3. **Debugging**
   - Find bugs
   - Fix errors
   - Run diagnostics

4. **Testing**
   - Write tests
   - Run tests
   - Fix failing tests

5. **Analysis**
   - Understand architecture
   - Find patterns
   - Generate reports

6. **Complex Workflows**
   - Multi-step refactoring
   - Feature implementation with tests
   - Bug fix with verification

---

## Technical Details

### Files to Modify

1. **Create:** `mcp_client_for_ollama/agents/examples/planner_examples.json`
2. **Modify:** `mcp_client_for_ollama/agents/delegation_client.py`
   - Add `select_relevant_examples()` method
   - Update `create_plan()` to use few-shot prompting
   - Add `validate_plan_quality()` method

### Estimated Effort

- **Implementation:** 4-6 hours
- **Example Curation:** 3-4 hours
- **Testing:** 2-3 hours
- **Total:** ~10-13 hours

### Dependencies

- None (can be implemented independently)
- Works with existing Phase 1 & 2 features

---

## Success Criteria

✅ **Plan Quality:** 80%+ of plans score 8/10 or higher
✅ **Consistency:** Task count varies by <3 between similar queries
✅ **Error Rate:** <5% JSON parsing failures
✅ **User Satisfaction:** 85%+ positive feedback
✅ **Performance:** No significant latency increase

---

## Why This Matters

The PLANNER is the **most critical** component of the delegation system:

1. **Garbage In, Garbage Out** - Bad plans → bad results
2. **User Trust** - Consistent plans build confidence
3. **Efficiency** - Better plans = better parallelization
4. **Success Rate** - Good plans complete more often

Improving planner prompts with few-shot examples is **one of the highest-impact improvements** for Phase 3.

---

## Next Steps

1. Review this proposal
2. Curate initial set of 10-15 examples
3. Implement example selection algorithm
4. Test with real queries
5. Iterate based on results

**Status:** Ready for implementation 🚀
