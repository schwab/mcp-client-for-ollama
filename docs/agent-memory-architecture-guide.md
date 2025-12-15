# Agent Memory Architecture Guide
## Building Effective AI Agents with Domain-Specific Memory

Based on Anthropic's research and patterns for building production-ready AI agents.

---

## Table of Contents

1. [The Problem with Generalized Agents](#the-problem-with-generalized-agents)
2. [The Solution: Domain Memory](#the-solution-domain-memory)
3. [The Two-Agent Pattern](#the-two-agent-pattern)
4. [Core Components of Domain Memory](#core-components-of-domain-memory)
5. [Design Principles](#design-principles)
6. [Domain-Specific Memory Schemas](#domain-specific-memory-schemas)
7. [Strategic Implications](#strategic-implications)
8. [Implementation Checklist](#implementation-checklist)

---

## The Problem with Generalized Agents

Traditional generalized agents suffer from a fundamental flaw: **they are amnesiacs with tool belts**.

### Key Issues:
- **No persistent memory** across sessions
- **No grounded sense** of where they are in a task
- **Every session starts fresh** with no context
- Results in:
  - One manic burst that fails
  - Partial progress with false success claims
  - Infinite sequence of disconnected attempts
  - Inconsistent definitions of "done"

### Why Context Windows Aren't Enough:
- Context compaction alone doesn't solve memory
- Tool sets and planning harnesses aren't sufficient
- **Long-running memory doesn't work** without structure
- LLMs need a "stage to play their part"

---

## The Solution: Domain Memory

**Domain memory** is a persistent, structured representation of work that transforms agents from amnesiacs into disciplined engineers.

### What Domain Memory Is NOT:
- ❌ Just a vector database for RAG
- ❌ Simple chat history
- ❌ Unstructured notes

### What Domain Memory IS:
- ✅ **Stateful representation** of work
- ✅ **Persistent structured data** that survives sessions
- ✅ **Machine-readable artifacts** with pass/fail criteria
- ✅ **The scaffolding** that grounds agent behavior

> **Key Insight**: The agent is just a policy that transforms one consistent memory state into another. The magic is in the memory, not the model.

---

## The Two-Agent Pattern

Anthropic's recommended pattern splits responsibilities between two specialized agents:

### 1. Initializer Agent (Stage Manager)

**Purpose**: Bootstrap domain memory from user input

**Responsibilities**:
- Expands user prompt into detailed feature list
- Creates structured JSON with features (initially marked "failing")
- Sets up progress logs and tracking artifacts
- Establishes best practice rules of engagement
- Defines test harnesses and success criteria

**Key Characteristic**: **No memory needed** - just transforms prompt into scaffolding

**Example Outputs**:
```json
{
  "features": [
    {"id": "F1", "description": "User authentication", "status": "failing", "tests": []},
    {"id": "F2", "description": "Data persistence", "status": "failing", "tests": []}
  ],
  "progress_log": [],
  "constraints": [],
  "test_harness": "pytest"
}
```

### 2. Coding Agent (Actor)

**Purpose**: Make incremental, testable progress

**Workflow** (every run):
1. **Read** progress from logs
2. **Read** commit history from git
3. **Read** feature list
4. **Pick** ONE failing feature to work on
5. **Implement** the feature
6. **Test** end-to-end
7. **Update** feature status (passing/failing)
8. **Write** progress note
9. **Commit** to git
10. **Disappear** (no retained memory)

**Key Characteristic**: **Stateless execution** - all context from domain memory

---

## Core Components of Domain Memory

Every domain memory system needs these elements:

### 1. Goals & Features
- **Explicit feature list** with requirements
- **Constraints** and acceptance criteria
- **Pass/fail criteria** (machine-readable)
- **Priority ordering**

### 2. State Tracking
- **What's passing** vs failing
- **What's been tried** before
- **What broke** and was reverted
- **Current status** of each component

### 3. Scaffolding
- **How to run** the system
- **How to test** (unit, integration, e2e)
- **How to extend** and add features
- **Dependencies** and setup requirements

### 4. Progress History
- **Commit logs** from version control
- **Progress notes** from each run
- **Decision journal** (why choices were made)
- **Error logs** and debugging notes

---

## Design Principles

Follow these principles when building agent systems:

### 1. Externalize Goals
**Transform**: "Do X" → Machine-readable backlog with pass/fail criteria

**Example**:
```
❌ "Build a login system"
✅ {
    "feature": "login",
    "criteria": ["password_hash_secure", "session_token_generated", "test_login_passes"],
    "status": "failing"
  }
```

### 2. Make Progress Atomic & Observable
- **Force agents** to pick ONE item at a time
- **Test after each change**
- **Update shared state** immediately
- **Progress must be** incrementally verifiable

### 3. Enforce Clean State
**"Leave the campsite cleaner than you found it"**
- End every run with **passing tests**
- Update **human-readable documentation**
- Update **machine-readable state**
- **Commit clean** code only

### 4. Standardize Boot-Up Ritual
**Every run must**:
1. **Read** the memory (feature list, progress log, tests)
2. **Run** basic health checks
3. **Orient** to current state
4. **Then and only then**, take action

### 5. Keep Tests Close to Memory
- **Test results** are source of truth
- **Tie test status** directly to feature status
- **No feature is "done"** without passing tests
- **Memory reflects** test reality

---

## Domain-Specific Memory Schemas

The harness pattern is general, but **memory schemas must be domain-specific**.

### For Software Development:
```
- features.json (feature list with pass/fail status)
- progress.log (what each run accomplished)
- .git/ (commit history)
- tests/ (unit, integration tests)
- README.md (current state documentation)
```

### For Research:
```
- hypothesis_backlog.json (research questions)
- experiment_registry.json (experiments run)
- evidence_log.md (findings and data)
- decision_journal.md (why we chose X over Y)
- literature_review.md (related work)
```

### For Operations:
```
- runbook.json (procedures and steps)
- incident_timeline.log (what happened when)
- ticket_queue.json (outstanding issues)
- sla_status.json (service level metrics)
- postmortem_log.md (lessons learned)
```

### For Content Creation:
```
- content_calendar.json (planned pieces)
- drafts/ (work in progress)
- style_guide.md (voice and tone rules)
- publication_log.json (what's been published)
- audience_feedback.json (engagement metrics)
```

---

## Strategic Implications

### The Moat Isn't the Model

**What will commoditize**:
- AI models (getting better and cheaper)
- Basic tool-calling capabilities
- Generic agent harnesses

**What won't commoditize** (your competitive advantage):
- ✅ **Domain-specific memory schemas** you design
- ✅ **Testing loops** that keep agents honest
- ✅ **Harnesses** that turn LLM calls into durable progress
- ✅ **Rituals and processes** that define quality

### Why "Universal Agents" Won't Work

**Claims to dismiss**:
- ❌ "Universal agent for your enterprise" with no domain schemas
- ❌ "Just plug it into Slack and it works"
- ❌ "One agent to rule them all"

**Reality**:
- Agents need **opinionated schemas** about work
- Agents need **testing frameworks** for their domain
- Agents need **structured memory** to function long-term
- **The hard work** is designing the right artifacts

---

## Implementation Checklist

### Phase 1: Define Domain Memory
- [ ] Identify the domain (coding, research, ops, etc.)
- [ ] Define what "done" means (pass/fail criteria)
- [ ] Design memory artifacts (JSON schemas, logs, etc.)
- [ ] Create test framework for the domain

### Phase 2: Build Initializer Agent
- [ ] Prompt engineering to expand user goals
- [ ] Generate structured feature lists
- [ ] Create progress tracking artifacts
- [ ] Set up scaffolding (tests, docs, etc.)
- [ ] Establish best practices and constraints

### Phase 3: Build Worker Agent
- [ ] Implement boot-up ritual (read memory first)
- [ ] Add feature selection logic (pick ONE item)
- [ ] Implement → Test → Update loop
- [ ] Progress logging after each run
- [ ] Clean state enforcement

### Phase 4: Harness Integration
- [ ] Version control integration (git commits)
- [ ] Test automation (run tests every change)
- [ ] State validation (ensure consistency)
- [ ] Error recovery (revert on failure)
- [ ] Human oversight hooks

### Phase 5: Iteration & Refinement
- [ ] Monitor agent behavior over multiple runs
- [ ] Refine memory schemas based on failures
- [ ] Improve test coverage
- [ ] Add domain-specific validation
- [ ] Document learnings

---

## Key Takeaways

1. **Agents without memory are amnesiacs** - they can't maintain long-running context
2. **Domain memory is the solution** - persistent, structured, testable state
3. **Separate concerns**: Initializer sets the stage, Worker acts on it
4. **The magic is in the memory**, not the model or personality
5. **General harness + Domain-specific schema** = Effective agent
6. **Tests are truth** - tie all progress to verifiable outcomes
7. **Your moat is your schema**, not the underlying AI model
8. **Prompting is stage-setting** - give agents context to succeed

---

## Connections to Prompting

**Prompting is like being an initializer agent**:
- You set context so the LLM knows where it is
- You structure the task so success is clear
- You provide scaffolding (examples, format, constraints)
- **Good prompting = Good stage-setting**

When you hit enter on a chat, the LLM should:
- Know where it is
- Know what the task is
- Have criteria for success
- Have tools/context to succeed

---

## Further Reading

- Anthropic's blog post on agent patterns
- Claude Agent SDK documentation
- Research on stateful vs stateless agents
- Domain-driven design principles

---

**Remember**: The mystery of agents is memory. This is how you solve it.
