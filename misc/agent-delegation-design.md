# Agent Delegation System Design

**Date:** 2025-12-05
**Status:** Phase 1 - MVP Implementation
**Purpose:** Enable small models with limited context windows to handle complex multi-file tasks through task decomposition and specialized agents

---

## Problem Statement

Small language models (e.g., Qwen2.5-7B with 32K context) excel at focused tasks but struggle with complex multi-file operations due to:
- **Context window limitations** - Can't keep track of many files simultaneously
- **Task complexity** - Multi-step operations cause errors and mistakes
- **Information overload** - Too much context leads to degraded performance

## Solution: Agent Delegation System

Break down complex tasks into smaller, focused subtasks handled by specialized agents with minimal context requirements.

```
User Query (Complex)
    ↓
Planner Agent → Task Breakdown
    ↓
┌─────────┬─────────┬─────────┐
│ Agent 1 │ Agent 2 │ Agent 3 │
│ Reader  │ Coder   │ Executor│
└─────────┴─────────┴─────────┘
    ↓           ↓           ↓
Aggregate Results → Final Answer
```

---

## Design Decisions

### 1. Planner Model Configuration
- **Configurable** via `config.json` field: `delegation.planner_model`
- **Fallback** to currently selected model if not configured
- **Rationale:** Allow upgrading to smarter planner without forcing it

### 2. Execution Model
- **Parallel execution** of independent tasks via `asyncio.gather()`
- **Model pool** support for distributed execution across multiple Ollama servers
- **Dependency resolution** to ensure tasks execute in correct order
- **Rationale:** Maximize throughput when multiple model servers available

### 3. Context Sharing Strategy
- **Shared Read:** Agents can read results from completed sibling tasks
- Agents do NOT see full conversation history (prevents context explosion)
- **Rationale:** Balance between information sharing and context limits

### 4. Tool Access Control
- **Hybrid approach:**
  - Default toolsets defined in agent definition files
  - Tool categories/tags for flexible extension
  - Forbidden tools list for safety
- **Rationale:** Safety with flexibility, no planner micromanagement needed

### 5. Integration Approach
- **Option B:** Separate `DelegationClient` that wraps `MCPClient`
- **Rationale:** Clean separation, easier testing, optional feature

### 6. Agent Definition Format
- **File-driven:** JSON files in `agents/definitions/`
- **Extensible:** Add new agent types by creating new definition files
- Base agent types included: planner, reader, coder, executor, debugger, researcher

### 7. Activation Mode
- **Phase 1:** User-triggered via `/delegate` command
- **Future:** Automatic detection based on query complexity heuristics

### 8. Development Philosophy
- **Start simple, iterate:** MVP first, add complexity incrementally
- **Results over complexity:** Pragmatic solutions, avoid over-engineering

---

## Architecture

### Component Overview

```
DelegationClient (new)
├── PlannerAgent
│   └── Task decomposition logic
├── TaskExecutor
│   ├── Dependency resolution
│   ├── Parallel execution
│   └── Model pool management
├── ModelPool
│   └── Load balancing across multiple Ollama servers
└── ResultAggregator
    └── Synthesis of task results
```

### Core Classes

#### Task
```python
@dataclass
class Task:
    id: str
    description: str
    agent_type: str
    status: TaskStatus  # PENDING/RUNNING/COMPLETED/FAILED/BLOCKED
    dependencies: List[str]
    context: List[Dict[str, str]]
    tools: List[str]
    result: Optional[str]
    error: Optional[str]
```

#### AgentConfig
```python
@dataclass
class AgentConfig:
    agent_type: str
    display_name: str
    system_prompt: str
    default_tools: List[str]
    forbidden_tools: List[str]
    max_context_tokens: int
    loop_limit: int
    temperature: float
```

#### ModelPool
```python
class ModelPool:
    endpoints: List[ModelEndpoint]

    async def acquire() -> ModelEndpoint
    async def release(endpoint)
    async def wait_for_available(timeout) -> ModelEndpoint
```

#### DelegationClient
```python
class DelegationClient:
    mcp_client: MCPClient
    agent_configs: Dict[str, AgentConfig]
    model_pool: ModelPool
    tasks: Dict[str, Task]

    async def process_with_delegation(query) -> str
    async def create_plan(query) -> List[Task]
    async def execute_tasks_parallel(tasks) -> List[Task]
    async def aggregate_results(results) -> str
```

---

## File Structure

```
mcp_client_for_ollama/
├── agents/                      # NEW MODULE
│   ├── __init__.py
│   ├── task.py                 # Task, TaskStatus classes
│   ├── agent_config.py         # AgentConfig loader
│   ├── model_pool.py           # ModelPool for distributed execution
│   ├── delegation_client.py    # Main orchestrator
│   ├── planner.py              # Planning logic
│   ├── executor.py             # Task execution engine
│   ├── aggregator.py           # Result synthesis
│   └── definitions/            # Agent type definitions (JSON)
│       ├── planner.json
│       ├── reader.json
│       ├── coder.json
│       ├── executor.json
│       ├── debugger.json
│       └── researcher.json
├── client.py                   # Existing - no changes needed
├── cli.py                      # MODIFY: add /delegate command
└── config/
    └── defaults.py             # ADD: delegation config defaults
```

---

## Agent Type Definitions

### Planner
- **Purpose:** Decompose complex queries into focused subtasks
- **Tools:** `list_files`, `file_exists` (read-only exploration)
- **Context:** 32K tokens (needs to see full request)
- **Output:** JSON array of tasks with dependencies

### Reader
- **Purpose:** Read and analyze code without modifications
- **Tools:** `read_file`, `list_files`, `file_exists`, `get_file_info`
- **Context:** 8K tokens
- **Loop limit:** 2

### Coder
- **Purpose:** Write and modify code files
- **Tools:** `read_file`, `write_file`, `list_files`, `create_directory`
- **Context:** 16K tokens
- **Loop limit:** 3
- **Forbidden:** `execute_bash`, `delete_file`

### Executor
- **Purpose:** Run tests, scripts, and commands
- **Tools:** `execute_bash`, `execute_python_code`, `read_file`
- **Context:** 8K tokens
- **Loop limit:** 3

### Debugger
- **Purpose:** Fix errors and debug issues
- **Tools:** `read_file`, `write_file`, `execute_bash`, `execute_python_code`
- **Context:** 16K tokens
- **Loop limit:** 5 (may need multiple attempts)

### Researcher
- **Purpose:** Search codebase, find patterns, understand architecture
- **Tools:** `list_files`, `file_exists`, `read_file`, `get_file_info`
- **Context:** 8K tokens
- **Loop limit:** 2

---

## Configuration Schema

### config.json
```json
{
  "delegation": {
    "enabled": false,
    "planner_model": "qwen2.5:14b",  // Optional, falls back to current model
    "model_pool": [
      {
        "url": "http://localhost:11434",
        "model": "qwen2.5:7b",
        "max_concurrent": 2
      },
      {
        "url": "http://192.168.1.100:11434",
        "model": "qwen2.5:7b",
        "max_concurrent": 2
      }
    ],
    "execution_mode": "parallel",  // or "sequential"
    "max_parallel_tasks": 4,
    "task_timeout": 300
  }
}
```

---

## Implementation Phases

### Phase 1: Foundation (MVP) ← CURRENT
**Goal:** Basic delegation with sequential execution

- [x] Document design
- [ ] Create `agents/` module structure
- [ ] Implement `Task`, `TaskStatus` classes
- [ ] Implement `AgentConfig` class
- [ ] Implement `ModelPool` class
- [ ] Create 3 agent definitions: planner, reader, coder
- [ ] Implement `DelegationClient` with sequential execution
- [ ] Add `/delegate` command to CLI
- [ ] Test with simple multi-file query

**Success Criteria:**
- Can decompose "read file A and write file B" into 2 tasks
- Tasks execute sequentially
- Results aggregated correctly

---

### Phase 2: Parallelism
**Goal:** Parallel execution with dependency resolution

- [ ] Implement parallel task execution
- [ ] Add dependency resolution algorithm
- [ ] Implement model pool with load balancing
- [ ] Add task status UI (progress display)
- [ ] Add configuration options for parallel execution

**Success Criteria:**
- Independent tasks execute in parallel
- Dependent tasks wait for predecessors
- Model pool distributes load across endpoints

---

### Phase 3: Polish
**Goal:** Production-ready delegation system

- [ ] Add executor, debugger, researcher agent types
- [ ] Improve planner prompts (few-shot examples)
- [ ] Implement result aggregation with summarization
- [ ] Add delegation settings to config UI
- [ ] Add error recovery and retry logic
- [ ] Add task cancellation support

**Success Criteria:**
- All 6 agent types working
- Handles errors gracefully
- User can configure delegation settings

---

### Phase 4: Automation
**Goal:** Automatic delegation for complex queries

- [ ] Implement complexity heuristics
  - Query length > 500 chars
  - Keywords: "multiple files", "refactor", "across", "all"
  - File count estimation > 3
- [ ] Add auto-delegation toggle in config
- [ ] Add fallback to direct execution if delegation fails
- [ ] Add metrics tracking (delegation success rate)

**Success Criteria:**
- 80%+ of complex queries delegated correctly
- Users can disable auto-delegation if needed
- Metrics show improved success rates

---

## Key Technical Challenges

### 1. Planner Output Parsing
**Challenge:** Small models may not output perfect JSON
**Solution:**
- Use structured output hints in prompt
- Implement fuzzy JSON parser
- Fallback to regex extraction of task list

### 2. Context Budget Management
**Challenge:** Ensure tasks stay within agent context limits
**Solution:**
- Validate task description length before execution
- Truncate dependency results if too large
- Monitor token usage per task

### 3. Dependency Cycles
**Challenge:** Planner might create circular dependencies
**Solution:**
- Topological sort to detect cycles
- Reject plans with cycles, ask planner to revise

### 4. Task Failure Handling
**Challenge:** What if a critical task fails?
**Solution:**
- Mark dependent tasks as BLOCKED
- Allow retry (up to N attempts)
- Report failure to user with partial results

### 5. Model Pool Exhaustion
**Challenge:** More tasks than available model endpoints
**Solution:**
- Task queue with waiting
- Timeout with informative error
- Suggest adding more endpoints in config

---

## Success Metrics

### Phase 1 Success Indicators
- [ ] Can decompose 2-3 step tasks correctly
- [ ] Tasks execute without crashes
- [ ] Results are coherent

### Long-term Success Indicators
- [ ] 50%+ reduction in errors for multi-file tasks
- [ ] Small models (7B) achieve results comparable to larger models (32B+)
- [ ] Users report improved handling of complex requests

---

## Future Enhancements (Post-MVP)

### High Priority
1. **Unit Test Coverage:** Comprehensive tests for delegation system components (DelegationClient, Task, AgentConfig, ModelPool)
2. **Parallel Task Execution:** Execute independent tasks concurrently using model pool
3. **Error Recovery & Retry:** Automatic retry logic for failed tasks, partial recovery mechanisms

### Medium Priority
4. **Multi-modal Agent Support (VISION):** Add image handling capabilities
   - Load images from folders with base64 encoding
   - New VISION agent type for image analysis
   - Support for vision models (llama3.2-vision, llava, bakllava)
   - Builtin tools: `load_image`, `load_images_from_folder`
   - Proper image payload packaging in Ollama API messages
5. **Recursive Agent Delegation:** Allow agents to call other agents during execution
   - New `builtin.delegate` tool for spawning sub-agents
   - Recursion depth limits and safety controls
   - Enables dynamic task discovery and agent collaboration
6. **Better Result Aggregation:** Use dedicated AGGREGATOR agent instead of simple concatenation
7. **Context Window Enforcement:** Validate and truncate large dependency results

### Low Priority
8. **Agent Memory:** Persistent knowledge base per agent type
9. **Agent Learning:** Track successful patterns, improve over time
10. **Human-in-the-loop for Planning:** User approval before task execution
11. **Task Templates:** Pre-defined task patterns for common operations
12. **Streaming Results:** Show task progress in real-time
13. **Multi-turn Delegation:** Planner can revise plan based on results
14. **Agent Specialization:** Fine-tune small models for specific agent roles
15. **Auto-Detection:** Complexity heuristics to automatically trigger delegation

---

## References

- Main discussion: Session 2025-12-05
- Related pattern: AutoGPT, CrewAI, LangGraph agent systems
- Context: Small model optimization for complex tasks
- Target models: Qwen2.5 (7B-14B), DeepSeek, Llama 3.2

---

## Notes

- This is an **experimental feature** - may not work for all query types
- Performance depends heavily on planner quality
- Best suited for tasks that naturally decompose (multi-file edits, testing workflows)
- May struggle with tasks requiring holistic understanding (architecture redesign)

---

**Last Updated:** 2025-12-05
**Next Review:** After Phase 1 completion
