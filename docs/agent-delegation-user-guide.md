# Agent Delegation System - User Guide

**Version:** 1.0 (Phase 1 - MVP)
**Date:** December 2025
**Status:** Production Ready

---

## Table of Contents

- [Overview](#overview)
- [Why Agent Delegation?](#why-agent-delegation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Available Agents](#available-agents)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Overview

The **Agent Delegation System** enables small language models (7B-14B parameters) to handle complex multi-file tasks by breaking them down into focused subtasks executed by specialized agents.

### Key Benefits

✅ **Small Model Performance** - 7B-14B models achieve results comparable to 32B+ models
✅ **Context Window Optimization** - Each agent operates within 8-16K token limits
✅ **Task Success Rate** - Significantly fewer errors on complex multi-file operations
✅ **Speed & Efficiency** - Parallel-capable execution (future phases)
✅ **Extensibility** - Easy to add new agent types via JSON files

---

## Why Agent Delegation?

### The Problem

Small models with limited context windows (32K tokens or less) struggle with complex tasks:

```
❌ User: "Refactor authentication across 5 files and update tests"

   Small Model (32K context):
   - Tries to load all 5 files into context
   - Runs out of tokens
   - Makes mistakes
   - Forgets earlier changes
   - Fails or produces incorrect results
```

### The Solution

The delegation system breaks the task into focused subtasks:

```
✅ User: "delegate Refactor authentication across 5 files and update tests"

   PLANNER: Creates 7 focused tasks
   READER: Reads auth.py (8K context) ✓
   READER: Reads config.py (8K context) ✓
   CODER: Refactor auth.py (16K context) ✓
   CODER: Update config.py (16K context) ✓
   EXECUTOR: Run tests (8K context) ✓
   DEBUGGER: Fix test failures (16K context) ✓
   RESEARCHER: Summarize changes (16K context) ✓

   Result: Task completed successfully!
```

---

## Quick Start

### Basic Usage

```bash
# Start the MCP client
ollmcp

# Use delegation for complex tasks
delegate scan all Python files in src/, identify bugs, and create a report

# Short form
d read all .md files in docs/ and create a summary
```

### Your First Delegation

Try this example:

```bash
delegate scan the md files in docs/ directory, read each one,
summarize their contents, and produce an executive-level summary
```

You'll see:
1. **Planning Phase** - Task breakdown displayed
2. **Execution Phase** - Each agent executes its task
3. **Aggregation Phase** - Results synthesized
4. **Final Response** - Comprehensive answer

---

## How It Works

### The Delegation Flow

```
┌─────────────────────────────────────────┐
│  User Query (Complex Multi-File Task)  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ PLANNER Agent  │
         │ Analyzes Query │
         └────────┬───────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │ Task Breakdown (JSON Plan)  │
    │  • Task 1: EXECUTOR         │
    │  • Task 2: READER (dep: 1)  │
    │  • Task 3: CODER (dep: 2)   │
    └──────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ Sequential Execution     │
    │ (Parallel in future)     │
    └──────┬────────┬──────────┘
           │        │
           ▼        ▼
    ┌─────────┐  ┌─────────┐
    │ Agent 1 │  │ Agent 2 │
    │ 8K ctx  │  │ 16K ctx │
    └────┬────┘  └────┬────┘
         │            │
         └─────┬──────┘
               ▼
       ┌───────────────┐
       │  Aggregation  │
       │ Synthesize    │
       │ Results       │
       └───────┬───────┘
               │
               ▼
       ┌───────────────┐
       │ Final Answer  │
       └───────────────┘
```

### Task Dependencies

Agents can depend on previous tasks:

```json
{
  "tasks": [
    {
      "id": "task_1",
      "description": "List all Python files in src/",
      "agent_type": "EXECUTOR",
      "dependencies": []
    },
    {
      "id": "task_2",
      "description": "Read the Python files listed by task_1",
      "agent_type": "READER",
      "dependencies": ["task_1"]  // ← Waits for task_1
    }
  ]
}
```

### Context Sharing Strategy

The system uses **Shared Read** - agents receive:
- Their task description
- Results from dependency tasks
- Task descriptions from dependencies (for context)

```
Task 2 receives:
┌────────────────────────────────────────────────────┐
│ [Result from task_1: List all Python files in src/]│
│ ["auth.py", "config.py", "utils.py"]               │
│                                                     │
│ Your task:                                          │
│ Read the Python files listed by task_1             │
└────────────────────────────────────────────────────┘
```

---

## Available Agents

### PLANNER
- **Purpose:** Decomposes complex queries into subtasks
- **Tools:** `list_files`, `file_exists` (exploration only)
- **Context:** 32K tokens
- **When Used:** Automatically for all delegation queries

### READER
- **Purpose:** Reads and analyzes files without modifications
- **Tools:** `read_file`, `list_files`, `file_exists`, `get_file_info`
- **Context:** 8K tokens
- **Constraints:** Read-only, cannot execute code
- **Best For:**
  - Analyzing code structure
  - Extracting information from files
  - Understanding implementations

### CODER
- **Purpose:** Writes and modifies code files
- **Tools:** `read_file`, `write_file`, `list_files`, `create_directory`
- **Context:** 16K tokens
- **Constraints:** Cannot execute code or delete files
- **Best For:**
  - Creating new files
  - Modifying existing code
  - Refactoring
  - Adding features

### EXECUTOR
- **Purpose:** Runs bash commands and Python scripts
- **Tools:** `execute_bash`, `execute_python`, `read_file`, `list_files`
- **Context:** 8K tokens
- **Constraints:** Cannot write or delete files
- **Best For:**
  - Listing files/directories
  - Running tests
  - Executing scripts
  - Gathering system information

### RESEARCHER
- **Purpose:** Analyzes and summarizes information
- **Tools:** `read_file`, `list_files`, `file_exists`, `get_file_info`
- **Context:** 16K tokens
- **Constraints:** Read-only, emphasizes using task context
- **Best For:**
  - Creating summaries
  - Identifying patterns
  - Synthesizing information from multiple sources
  - Comparative analysis

### DEBUGGER
- **Purpose:** Diagnoses and fixes errors
- **Tools:** `read_file`, `write_file`, `execute_bash`, `execute_python`
- **Context:** 16K tokens
- **Loop Limit:** 5 iterations (for retries)
- **Best For:**
  - Fixing runtime errors
  - Debugging failing tests
  - Resolving compilation errors
  - Investigating unexpected behavior

---

## Usage Examples

### Example 1: Documentation Analysis

**Query:**
```bash
delegate read all markdown files in docs/ and create a user guide summary
```

**Execution:**
```
PLANNER creates:
  task_1: EXECUTOR - List .md files in docs/
  task_2: READER - Read each file (depends on task_1)
  task_3: RESEARCHER - Create summary (depends on task_2)

Result: Comprehensive user guide summary
```

### Example 2: Multi-File Refactoring

**Query:**
```bash
d refactor the database connection logic across src/db/, src/models/,
  and tests/ to use connection pooling
```

**Execution:**
```
PLANNER creates:
  task_1: READER - Analyze current DB connection in src/db/
  task_2: READER - Check usage in src/models/
  task_3: READER - Review tests in tests/
  task_4: CODER - Implement connection pooling in src/db/
  task_5: CODER - Update src/models/ to use pool
  task_6: CODER - Update tests
  task_7: EXECUTOR - Run tests to verify

Result: Refactored codebase with passing tests
```

### Example 3: Bug Investigation

**Query:**
```bash
delegate find and fix the authentication timeout bug in the login flow
```

**Execution:**
```
PLANNER creates:
  task_1: READER - Analyze login flow in auth.py
  task_2: READER - Check timeout configuration
  task_3: EXECUTOR - Run auth tests to reproduce bug
  task_4: DEBUGGER - Fix timeout issue (depends on task_1-3)
  task_5: EXECUTOR - Verify fix with tests

Result: Bug identified and fixed
```

### Example 4: Codebase Analysis

**Query:**
```bash
d analyze the API endpoints, document their parameters,
  and create an API reference
```

**Execution:**
```
PLANNER creates:
  task_1: EXECUTOR - Find all route files
  task_2: READER - Extract endpoint definitions
  task_3: READER - Document parameters and responses
  task_4: RESEARCHER - Create structured API reference
  task_5: CODER - Write reference to api-docs.md

Result: Complete API documentation
```

---

## Best Practices

### When to Use Delegation

✅ **Good Use Cases:**
- Multi-file operations (3+ files)
- Complex refactoring across codebase
- Analysis tasks requiring multiple steps
- Tasks that naturally decompose (read → analyze → modify)
- Operations that would exceed context window

❌ **Not Ideal For:**
- Single-file simple edits
- Quick one-off queries
- Tasks requiring holistic understanding of entire architecture
- Time-sensitive operations (delegation has slight overhead)

### Writing Effective Delegation Queries

**✅ Good Queries:**
```bash
# Clear, specific, multi-step
delegate scan all Python files in src/, identify security vulnerabilities,
  and create a report with recommendations

# Explicit about scope
d read all config files in config/, validate settings,
  and update with production values

# Natural decomposition
delegate analyze the test coverage, identify untested modules,
  and create tests for critical paths
```

**❌ Avoid:**
```bash
# Too vague
delegate fix the codebase

# Single simple operation
delegate read main.py

# Better done directly
delegate add a comment to function foo()
```

### Model Selection

**Recommended Models:**

| Model Size | Type | Use Case |
|------------|------|----------|
| qwen2.5:7b | General | Fast, efficient for most tasks |
| qwen2.5-coder:14b | Code-focused | Best for coding tasks |
| deepseek-coder:6.7b | Code-focused | Alternative coding model |
| llama3.2:8b | General | Good all-rounder |

**Note:** Even 7B models work remarkably well with delegation!

---

## Configuration

### Default Configuration

The delegation system works out-of-the-box with defaults:
- **Planner Model:** Uses your currently selected model
- **Execution:** Sequential (one task at a time)
- **Model Pool:** Single endpoint (your local Ollama)
- **Timeout:** 300 seconds per task

### Future Configuration Options

(Phase 2+)

```json
{
  "delegation": {
    "planner_model": "qwen2.5:14b",
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
    "execution_mode": "parallel",
    "max_parallel_tasks": 4
  }
}
```

### Adding Custom Agent Types

Create a new JSON file in `mcp_client_for_ollama/agents/definitions/`:

```json
{
  "agent_type": "TESTER",
  "display_name": "Test Specialist",
  "description": "Writes and runs tests",
  "system_prompt": "You are a test specialist...",
  "default_tools": ["read_file", "write_file", "execute_bash"],
  "max_context_tokens": 16384,
  "loop_limit": 3,
  "temperature": 0.5,
  "planning_hints": "Assign TESTER when you need to write or run tests"
}
```

The agent will be automatically available!

---

## Troubleshooting

### Issue: "Unknown agent type: XXXX"

**Problem:** Planner requested an agent type that doesn't exist

**Solution:**
1. Check available agents: The system has PLANNER, READER, CODER, EXECUTOR, RESEARCHER, DEBUGGER
2. If you need a new agent type, create a definition file (see Configuration)

### Issue: Agents not using tools

**Problem:** Agents respond with text like "I cannot access files"

**Solution:**
- Ensure tools are enabled: Type `tools` and verify tools are enabled
- Check model compatibility: Use models that support tool calling (qwen2.5, llama3, etc.)
- Try a different model: Some models have better tool support

### Issue: Tasks fail with path errors

**Problem:** "File not found" errors with correct filenames

**Solution:**
- This was fixed in v1.0 - ensure you're on latest version
- Check that dependency context is being passed correctly
- Verify the planner included directory paths in task descriptions

### Issue: Tasks take too long

**Problem:** Delegation times out or is very slow

**Solution:**
- Reduce scope: Break query into smaller pieces
- Check model performance: Switch to faster model
- Adjust timeout: Future config option
- Use direct execution for simple tasks: Don't use `delegate` for single-file operations

---

## Advanced Topics

### Task Dependency Resolution

Tasks are executed in dependency order using topological sort:

```
task_1 (no deps) ───┐
                    ├──> task_3 (deps: 1,2)
task_2 (no deps) ───┘

Execution order: task_1 → task_2 → task_3
```

Circular dependencies are detected and rejected.

### Agent Context Isolation

Each agent receives:
- System prompt defining its role
- Task description
- Results from dependency tasks
- **NOT** the full conversation history

This keeps context minimal and focused.

### Tool Access Control

Agents have:
- **Default tools:** Core tools for their role
- **Forbidden tools:** Tools they can never use (safety)
- **Allowed categories:** Flexible tool groups

Example:
```json
{
  "default_tools": ["read_file", "list_files"],
  "forbidden_tools": ["delete_file", "execute_bash"],
  "allowed_tool_categories": ["filesystem_read"]
}
```

### Performance Metrics

**Typical Performance (qwen2.5:7b):**
- Planning: 2-5 seconds
- Per-task execution: 5-15 seconds
- 3-task delegation: ~25-40 seconds total

**Vs. Direct execution:**
- Direct (failing): 30s then error
- Delegation (succeeding): 35s with correct result

**Winner:** Delegation (when task complexity warrants it)

---

## Roadmap

### Phase 2: Parallelism (Planned)
- Parallel task execution for independent tasks
- Multi-endpoint model pool with load balancing
- Dependency-aware scheduling

### Phase 3: Polish (Planned)
- Improved planner with few-shot examples
- Better result aggregation using dedicated agent
- UI progress indicators
- Error recovery and task retry

### Phase 4: Automation (Planned)
- Auto-detect when to use delegation
- Complexity heuristics
- Seamless fallback to direct execution

---

## FAQ

**Q: Will delegation work with any model?**
A: Best results with models that support tool calling: qwen2.5, llama3, deepseek-coder, mistral. Very small models (<3B) may struggle with planning.

**Q: How much slower is delegation vs direct execution?**
A: Planning adds ~5 seconds overhead. But for complex tasks, delegation often succeeds where direct execution fails, making it effectively faster.

**Q: Can I disable delegation?**
A: Yes! Just don't use the `delegate` command. Normal queries work as before.

**Q: Does delegation work with MCP server tools?**
A: Yes! Agents can use both builtin tools and MCP server tools.

**Q: Can I use delegation with Ollama Cloud models?**
A: Yes, delegation works with any Ollama-compatible model endpoint.

**Q: How do I know if delegation is working?**
A: You'll see clear phases: Planning → Execution → Aggregation, with task progress displayed.

---

## Getting Help

- **Issues:** Found a bug? [Report it](https://github.com/jonigl/mcp-client-for-ollama/issues)
- **Design Docs:** See `docs/agent-delegation-design.md` for technical details
- **Examples:** Check `tests/user_test_result_delegation_1.md` for real execution traces

---

**Happy delegating! 🎯**

*The agent delegation system enables small models to punch above their weight. Give your 7B model the power of focused, specialized agents!*
