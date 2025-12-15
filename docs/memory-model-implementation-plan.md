# Memory Model Implementation Plan
## Phased Approach to Domain Memory Architecture

This document outlines a phased plan to transform the current MCP client agent framework towards the Anthropic-recommended domain memory architecture.

---

## Current State Analysis

### Strengths
✅ **Well-defined agent types** (PLANNER, EXECUTOR, CODER, READER, DEBUGGER, RESEARCHER)
✅ **Strong tool integration** (builtin tools + MCP server tools)
✅ **Task dependency resolution** (topological sort, parallel execution)
✅ **Stateless worker agents** (good foundation - agents don't retain memory)
✅ **Trace logging system** (observability of agent actions)
✅ **Flexible configuration** (JSON-based agent definitions)

### Gaps vs. Anthropic Pattern

❌ **No persistent domain memory** across sessions
❌ **No Initializer Agent** pattern (PLANNER is close but doesn't bootstrap memory)
❌ **No memory artifacts** (feature lists, progress logs, test results)
❌ **No test integration** (no pass/fail tracking tied to state)
❌ **No git integration** (no commit-based progress tracking)
❌ **No boot-up ritual** (agents don't read persistent state before acting)
❌ **No domain-specific schemas** (all agents use generic context)

---

## Implementation Phases

### Phase 1: Foundation - Memory Infrastructure (Weeks 1-2)

**Goal**: Create the basic infrastructure for persistent domain memory without disrupting current functionality.

#### 1.1 Create Memory Schema System

**Files to Create**:
- `mcp_client_for_ollama/memory/` (new package)
  - `__init__.py`
  - `base_memory.py` - Abstract base class for domain memory
  - `schemas.py` - JSON schema definitions
  - `storage.py` - Persistence layer (filesystem-based initially)

**Base Memory Schema**:
```python
@dataclass
class DomainMemory:
    """Base class for domain-specific memory"""
    session_id: str
    domain: str  # e.g., "coding", "research", "operations"
    created_at: datetime
    updated_at: datetime
    goals: List[Goal]  # User objectives
    state: Dict[str, Any]  # Current state
    progress_log: List[ProgressEntry]  # History of actions
    artifacts: Dict[str, str]  # Paths to domain-specific files

@dataclass
class Goal:
    id: str
    description: str
    status: str  # "pending", "in_progress", "completed", "failed"
    criteria: List[str]  # Pass/fail criteria
    tests: List[str]  # Associated test identifiers

@dataclass
class ProgressEntry:
    timestamp: datetime
    agent_type: str
    action: str
    outcome: str  # "success", "failure", "partial"
    details: str
    artifacts_changed: List[str]
```

#### 1.2 Storage Layer

**Implementation**:
```python
class MemoryStorage:
    def __init__(self, base_dir: Path = Path("~/.mcp-memory")):
        self.base_dir = base_dir.expanduser()

    def save_memory(self, memory: DomainMemory) -> None:
        """Persist memory to disk"""

    def load_memory(self, session_id: str, domain: str) -> Optional[DomainMemory]:
        """Load memory from disk"""

    def list_sessions(self, domain: Optional[str] = None) -> List[str]:
        """List all available sessions"""
```

**Directory Structure**:
```
~/.mcp-memory/
├── coding/
│   ├── session_abc123/
│   │   ├── memory.json (main memory state)
│   │   ├── features.json (feature list)
│   │   ├── progress.log (human-readable log)
│   │   └── artifacts/ (domain-specific files)
│   └── session_def456/
├── research/
└── operations/
```

#### 1.3 Configuration Integration

**Update `config/defaults.py`**:
```python
"memory": {
    "enabled": False,  # Feature flag for gradual rollout
    "storage_dir": "~/.mcp-memory",
    "auto_persist": True,
    "max_sessions": 50,
    "session_ttl_days": 30
}
```

**Deliverables**:
- [ ] Memory schema dataclasses
- [ ] Storage layer with save/load
- [ ] Unit tests for memory persistence
- [ ] Configuration integration
- [ ] Documentation in `docs/memory-system.md`

---

### Phase 2: Initializer Pattern (Weeks 3-4)

**Goal**: Implement the Initializer Agent pattern to bootstrap domain memory from user queries.

#### 2.1 Create INITIALIZER Agent Type

**New File**: `mcp_client_for_ollama/agents/definitions/initializer.json`

```json
{
  "agent_type": "INITIALIZER",
  "display_name": "Initializer",
  "description": "Bootstraps domain memory by expanding user goals into structured artifacts",
  "system_prompt": "You are an Initializer Agent. Your job is to transform user requests into structured domain memory...",
  "default_tools": [
    "builtin.create_directory",
    "builtin.write"
  ],
  "allowed_tool_categories": ["file_operations"],
  "forbidden_tools": ["builtin.bash", "builtin.python"],
  "max_context_tokens": 131072,
  "loop_limit": 5,
  "temperature": 0.3,
  "output_format": "json",
  "planning_hints": "Use for bootstrapping new sessions or when user starts a new project/task"
}
```

**System Prompt Focus**:
- Parse user intent into explicit goals
- Generate feature list with pass/fail criteria
- Create domain-specific scaffolding (tests, docs, etc.)
- Set up progress tracking artifacts
- Define success criteria
- NO execution - only planning and artifact creation

#### 2.2 Domain-Specific Initializers

**Coding Domain Schema**:
```json
{
  "domain": "coding",
  "goals": [
    {
      "id": "G1",
      "description": "User's goal here",
      "features": [
        {
          "id": "F1",
          "description": "Specific feature",
          "status": "pending",
          "tests": ["test_feature_1"],
          "criteria": ["Code compiles", "Tests pass", "Documentation updated"]
        }
      ]
    }
  ],
  "test_harness": {
    "framework": "pytest",
    "test_dirs": ["tests/"],
    "run_command": "pytest -v"
  },
  "scaffolding": {
    "git_enabled": true,
    "auto_commit": false,
    "required_files": ["README.md", "requirements.txt"]
  }
}
```

**Research Domain Schema**:
```json
{
  "domain": "research",
  "hypotheses": [
    {
      "id": "H1",
      "question": "Research question",
      "status": "pending",
      "experiments": [],
      "evidence": []
    }
  ],
  "experiment_registry": [],
  "evidence_log": [],
  "decision_journal": []
}
```

#### 2.3 Integration with DelegationClient

**Modify `delegation_client.py`**:
```python
class DelegationClient:
    def __init__(self, ...):
        self.memory_enabled = config.get("memory", {}).get("enabled", False)
        self.memory_storage = MemoryStorage() if self.memory_enabled else None
        self.current_memory: Optional[DomainMemory] = None

    async def process_with_memory(self, query: str, domain: str = "coding"):
        """Process query with domain memory"""
        # 1. Check if session exists
        if not self.current_memory:
            # 2. Run INITIALIZER agent to bootstrap
            init_result = await self.initialize_domain_memory(query, domain)

        # 3. Pass memory context to subsequent agents
        # 4. Update memory after execution
        # 5. Persist to disk
```

**Deliverables**:
- [ ] INITIALIZER agent definition
- [ ] Domain-specific schema templates
- [ ] Memory bootstrapping logic
- [ ] Integration with DelegationClient
- [ ] Unit tests for initialization
- [ ] Documentation updates

---

### Phase 3: Worker Agent Memory Integration (Weeks 5-6)

**Goal**: Modify existing worker agents (CODER, EXECUTOR, etc.) to read from and update domain memory.

#### 3.1 Boot-Up Ritual Implementation

**New File**: `mcp_client_for_ollama/agents/boot_ritual.py`

```python
class BootRitual:
    """Standardized boot-up sequence for all worker agents"""

    @staticmethod
    def build_context(memory: DomainMemory, task_description: str) -> List[Dict]:
        """
        Build agent context from domain memory:
        1. Read memory state
        2. Read progress log
        3. Read test results (if applicable)
        4. Orient to current state
        5. Add task description
        """
        context = []

        # System message with memory context
        context.append({
            "role": "system",
            "content": f"""
            Current Session: {memory.session_id}
            Domain: {memory.domain}

            GOALS:
            {format_goals(memory.goals)}

            CURRENT STATE:
            {format_state(memory.state)}

            RECENT PROGRESS:
            {format_progress_log(memory.progress_log[-5:])}

            YOUR TASK:
            {task_description}

            PROTOCOL:
            1. Review the current state and progress
            2. Pick ONE specific item to work on
            3. Implement and test your changes
            4. Update the memory state
            5. Log your progress
            """
        })

        return context
```

#### 3.2 Update Worker Agents

**Modify CODER agent** (`definitions/coder.json`):
- Add system prompt section about reading memory first
- Add memory update tools
- Enforce single-feature focus

**Modify EXECUTOR agent**:
- Add test execution and result tracking
- Update memory state based on test results

**Example Enhanced System Prompt**:
```
You are a CODER agent. Before making any changes:

1. READ the feature list from memory
2. IDENTIFY features marked "pending" or "failing"
3. PICK exactly ONE feature to work on this run
4. IMPLEMENT the feature
5. UPDATE the feature status in memory
6. LOG your progress

NEVER work on multiple features simultaneously.
NEVER mark a feature as "completed" unless tests pass.
ALWAYS leave the code in a clean, working state.
```

#### 3.3 Memory Update Tools

**New Builtin Tools** (add to `BuiltinToolManager`):
```python
def update_feature_status(
    session_id: str,
    feature_id: str,
    status: str,
    notes: str
) -> Dict:
    """Update feature status in domain memory"""

def log_progress(
    session_id: str,
    agent_type: str,
    action: str,
    outcome: str,
    details: str
) -> Dict:
    """Add entry to progress log"""

def read_memory_state(session_id: str) -> Dict:
    """Read current memory state"""
```

**Deliverables**:
- [ ] Boot ritual implementation
- [ ] Updated worker agent system prompts
- [ ] Memory update tools
- [ ] Integration tests
- [ ] Documentation on agent protocols

---

### Phase 4: Test Integration & State Validation (Weeks 7-8)

**Goal**: Tie test results to memory state, making tests the source of truth.

#### 4.1 Test Harness Integration

**New File**: `mcp_client_for_ollama/memory/test_integration.py`

```python
class TestHarness:
    """Manages test execution and result tracking"""

    def __init__(self, memory: DomainMemory):
        self.memory = memory
        self.framework = memory.state.get("test_harness", {}).get("framework", "pytest")

    async def run_tests(
        self,
        test_filter: Optional[str] = None
    ) -> TestResults:
        """Execute tests and return results"""

    def update_memory_from_tests(self, results: TestResults) -> None:
        """Update feature status based on test results"""
        # Auto-update features.json based on which tests passed/failed

    def get_failing_features(self) -> List[Feature]:
        """Get features with failing tests"""
```

#### 4.2 Auto-Status Updates

**Logic**:
```python
# After test run
test_results = await test_harness.run_tests()

for feature in memory.goals.features:
    feature_tests = [t for t in test_results if t.feature_id == feature.id]

    if all(t.passed for t in feature_tests):
        feature.status = "completed"
    elif any(t.failed for t in feature_tests):
        feature.status = "failing"
    else:
        feature.status = "pending"  # No tests run yet

memory_storage.save_memory(memory)
```

#### 4.3 State Validation

**New File**: `mcp_client_for_ollama/memory/validators.py`

```python
class MemoryValidator:
    """Validates memory state consistency"""

    @staticmethod
    def validate_memory(memory: DomainMemory) -> List[ValidationError]:
        """Check for inconsistencies in memory state"""
        errors = []

        # Check: Features marked "completed" have passing tests
        # Check: Progress log entries reference valid features
        # Check: No circular dependencies
        # Check: All artifacts exist on disk

        return errors
```

**Deliverables**:
- [ ] Test harness abstraction
- [ ] Auto-status update logic
- [ ] Memory validators
- [ ] Integration with EXECUTOR agent
- [ ] Test coverage for test integration
- [ ] Documentation on test protocols

---

### Phase 5: Git Integration & Progress Tracking (Weeks 9-10)

**Goal**: Use git commits as additional memory layer for coding domain.

#### 5.1 Git Memory Layer

**New File**: `mcp_client_for_ollama/memory/git_integration.py`

```python
class GitMemory:
    """Git-based memory augmentation for coding domain"""

    def __init__(self, repo_path: Path, memory: DomainMemory):
        self.repo_path = repo_path
        self.memory = memory
        self.repo = git.Repo(repo_path) if repo_path.exists() else None

    def get_commit_history(self, limit: int = 10) -> List[Commit]:
        """Get recent commits"""

    def auto_commit(self, message: str, feature_id: str) -> str:
        """Auto-commit with structured message"""
        # Message format:
        # [feature_id] Brief description
        #
        # - Details
        # - Test status: passing/failing
        #
        # Agent: CODER
        # Session: abc123

    def read_commit_context(self) -> str:
        """Generate context from recent commits"""
        # Used in boot ritual to show agent what's been done
```

#### 5.2 Enhanced CODER Workflow

**Updated CODER Protocol**:
1. Read memory (features, progress, state)
2. Read git history (last 5-10 commits)
3. Pick ONE failing/pending feature
4. Implement feature
5. Run tests
6. If tests pass:
   - Update feature status to "completed"
   - Auto-commit with structured message
   - Log progress
7. If tests fail:
   - Update feature status to "failing"
   - Log error details
   - DO NOT commit

#### 5.3 Commit-Based Artifacts

**Auto-Generated Files** (in git):
```
.mcp-memory/
├── session-state.json  (current memory state - committed)
├── features.json       (feature list - committed)
├── progress.log        (append-only log - committed)
└── .gitignore          (ignore temp files)
```

**Benefits**:
- Version control on memory state
- Human-readable progress in git log
- Easy rollback to previous states
- Shareable across team members

**Deliverables**:
- [ ] Git integration module
- [ ] Auto-commit functionality
- [ ] Commit message formatting
- [ ] Integration with CODER agent
- [ ] Documentation on git workflows

---

### Phase 6: Multi-Session & Context Resumption (Weeks 11-12)

**Goal**: Enable resuming work across multiple sessions with preserved context.

#### 6.1 Session Management

**New File**: `mcp_client_for_ollama/memory/session_manager.py`

```python
class SessionManager:
    """Manages multiple memory sessions"""

    def create_session(self, domain: str, description: str) -> str:
        """Create new session, return session_id"""

    def list_sessions(
        self,
        domain: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[SessionInfo]:
        """List available sessions"""

    def resume_session(self, session_id: str) -> DomainMemory:
        """Load and resume existing session"""

    def archive_session(self, session_id: str) -> None:
        """Archive completed session"""
```

#### 6.2 CLI Commands for Session Management

**New Commands** (add to CLI):
```bash
# List sessions
mcp-client sessions list [--domain coding]

# Resume session
mcp-client sessions resume abc123

# Create new session
mcp-client sessions new --domain coding --description "Build auth system"

# Show session status
mcp-client sessions status abc123
```

#### 6.3 Automatic Session Detection

**Logic** (in `delegation_client.py`):
```python
async def process_query_with_memory(self, query: str, chat_history: List[Dict]):
    """
    Intelligent session handling:
    1. Check if user references existing session
    2. Extract context clues (file paths, feature names)
    3. Attempt to resume relevant session
    4. Fall back to creating new session
    """

    # Extract session hints from query
    session_hints = extract_session_context(query, chat_history)

    # Try to match existing session
    if session_hints:
        matching_sessions = session_manager.find_matching_sessions(session_hints)
        if matching_sessions:
            memory = session_manager.resume_session(matching_sessions[0].id)
            # Continue with existing memory
```

**Deliverables**:
- [ ] Session manager implementation
- [ ] CLI commands for sessions
- [ ] Session auto-detection
- [ ] Documentation on multi-session workflows
- [ ] Examples and tutorials

---

### Phase 7: Domain-Specific Extensions (Weeks 13-14)

**Goal**: Implement specialized memory schemas for non-coding domains.

#### 7.1 Research Domain

**Memory Schema**:
```python
@dataclass
class ResearchMemory(DomainMemory):
    hypotheses: List[Hypothesis]
    experiments: List[Experiment]
    evidence_log: List[Evidence]
    decision_journal: List[Decision]
    literature_review: List[Paper]

@dataclass
class Hypothesis:
    id: str
    question: str
    status: str  # "pending", "testing", "confirmed", "rejected"
    experiments: List[str]  # experiment IDs

@dataclass
class Experiment:
    id: str
    hypothesis_id: str
    methodology: str
    status: str
    results: Optional[Dict]
```

**RESEARCHER Agent Updates**:
- Read hypothesis backlog
- Pick ONE hypothesis to test
- Design and run experiment
- Log evidence
- Update hypothesis status
- Document decision rationale

#### 7.2 Operations Domain

**Memory Schema**:
```python
@dataclass
class OperationsMemory(DomainMemory):
    runbooks: List[Runbook]
    incidents: List[Incident]
    tickets: List[Ticket]
    sla_metrics: Dict[str, float]

@dataclass
class Incident:
    id: str
    severity: str
    status: str
    timeline: List[TimelineEntry]
    root_cause: Optional[str]
    resolution: Optional[str]
```

**Operations Agent**:
- Monitor system state
- Execute runbook procedures
- Track incident timeline
- Update SLA metrics
- Generate postmortems

#### 7.3 Content Creation Domain

**Memory Schema**:
```python
@dataclass
class ContentMemory(DomainMemory):
    content_calendar: List[ContentPiece]
    drafts: Dict[str, Draft]
    style_guide: StyleGuide
    publication_log: List[Publication]
    audience_feedback: List[Feedback]
```

**Deliverables**:
- [ ] Research domain memory schema
- [ ] Operations domain memory schema
- [ ] Content domain memory schema
- [ ] Domain-specific initializers
- [ ] Domain-specific worker protocols
- [ ] Documentation and examples

---

### Phase 8: Advanced Features & Optimization (Weeks 15-16)

**Goal**: Add advanced capabilities and optimize performance.

#### 8.1 Memory Compression & Summarization

**Problem**: Memory grows unbounded over long sessions

**Solution**:
```python
class MemoryCompactor:
    """Compress old memory while preserving important context"""

    async def compact_progress_log(
        self,
        memory: DomainMemory,
        keep_recent: int = 20
    ) -> None:
        """
        Summarize old progress entries using LLM:
        - Keep last 20 entries verbatim
        - Summarize older entries into key milestones
        """

    async def archive_completed_goals(self, memory: DomainMemory) -> None:
        """Move completed goals to archive while keeping summary"""
```

#### 8.2 Memory Branching

**Use Case**: Try different approaches without losing context

```python
class MemoryBranch:
    """Git-like branching for memory"""

    def create_branch(
        self,
        memory: DomainMemory,
        branch_name: str
    ) -> str:
        """Create a branch from current memory state"""

    def merge_branch(
        self,
        target: DomainMemory,
        source: DomainMemory,
        strategy: str = "auto"
    ) -> DomainMemory:
        """Merge branches with conflict resolution"""
```

#### 8.3 Shared Memory Across Agents

**Use Case**: Multiple agents collaborating on same project

```python
class SharedMemory:
    """Multi-agent coordination via shared memory"""

    def acquire_lock(self, feature_id: str, agent_type: str) -> bool:
        """Lock feature to prevent concurrent edits"""

    def release_lock(self, feature_id: str) -> None:
        """Release feature lock"""

    def get_available_features(self, agent_type: str) -> List[Feature]:
        """Get features this agent can work on (not locked)"""
```

#### 8.4 Memory Analytics

**Observability**:
```python
class MemoryAnalytics:
    """Analytics and insights from memory"""

    def get_completion_rate(self, memory: DomainMemory) -> float:
        """% of features completed"""

    def get_velocity(self, memory: DomainMemory, days: int = 7) -> float:
        """Features completed per day"""

    def get_failure_patterns(self, memory: DomainMemory) -> List[Pattern]:
        """Common failure modes"""

    def generate_report(self, memory: DomainMemory) -> str:
        """Human-readable progress report"""
```

**Deliverables**:
- [ ] Memory compaction
- [ ] Memory branching
- [ ] Shared memory coordination
- [ ] Analytics dashboard
- [ ] Performance optimizations
- [ ] Documentation

---

## Success Metrics

### Phase 1-2 (Foundation + Initializer)
- Memory can be persisted and loaded
- INITIALIZER agent creates valid domain memory
- Sessions are isolated

### Phase 3-4 (Workers + Tests)
- Worker agents read from memory before acting
- Feature status auto-updates based on tests
- Agents pick ONE feature at a time

### Phase 5-6 (Git + Multi-Session)
- Git commits track progress
- Sessions can be resumed across restarts
- Memory state is consistent with git state

### Phase 7-8 (Domains + Advanced)
- Multiple domains supported (coding, research, ops)
- Memory compaction prevents unbounded growth
- Analytics provide visibility into progress

---

## Migration Strategy

### Backward Compatibility

**Feature Flag Approach**:
```python
if config.get("memory", {}).get("enabled"):
    # Use new memory-based flow
    result = await delegation_client.process_with_memory(query)
else:
    # Use existing flow
    result = await delegation_client.create_and_execute_plan(query)
```

### Gradual Rollout

1. **Week 1-4**: Memory disabled by default, opt-in via config
2. **Week 5-8**: Memory enabled for "coding" domain only
3. **Week 9-12**: Memory enabled for all domains
4. **Week 13+**: Memory becomes default, old flow deprecated

### Testing Strategy

- Unit tests for each memory component
- Integration tests for end-to-end flows
- Regression tests to ensure existing functionality preserved
- Performance tests (memory overhead, latency)

---

## Risk Mitigation

### Risk 1: Memory Corruption
**Mitigation**:
- Validation on every save/load
- Automatic backups
- Schema versioning for migrations

### Risk 2: Performance Degradation
**Mitigation**:
- Lazy loading of memory components
- Memory compaction
- Caching frequently accessed data

### Risk 3: User Confusion
**Mitigation**:
- Clear documentation
- Helpful error messages
- Optional CLI commands for debugging memory state

### Risk 4: Scope Creep
**Mitigation**:
- Strict adherence to phased plan
- Each phase has clear deliverables
- User feedback loops after each phase

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize phases** based on user needs
3. **Assign ownership** of each phase
4. **Set up tracking** (GitHub issues, project board)
5. **Start with Phase 1** - memory infrastructure

---

## References

- [Agent Memory Architecture Guide](./agent-memory-architecture-guide.md)
- Anthropic's blog post on agent patterns
- Current codebase: `/mcp_client_for_ollama/agents/`
- Configuration: `/config/defaults.py`

---

**Last Updated**: 2025-12-14
**Status**: Draft - Awaiting Review
