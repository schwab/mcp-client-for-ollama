# Memory System Documentation

## Overview

The memory system provides persistent, domain-specific state management for AI agents. It implements the Anthropic-recommended pattern where agents are stateless workers that read from and write to persistent domain memory.

**Key Principle**: The agent is just a policy that transforms one consistent memory state into another. The magic is in the memory, not the model.

---

## Architecture

### Core Components

```
mcp_client_for_ollama/memory/
├── __init__.py          # Public API exports
├── base_memory.py       # Core dataclasses
├── schemas.py           # Domain-specific schemas
└── storage.py           # Persistence layer
```

### Data Model

```
DomainMemory
├── metadata: MemoryMetadata
│   ├── session_id
│   ├── domain (coding, research, operations, etc.)
│   ├── description
│   └── timestamps
├── goals: List[Goal]
│   └── features: List[Feature]
│       ├── id, description, status
│       ├── criteria (pass/fail requirements)
│       ├── tests (test identifiers)
│       └── test_results: List[TestResult]
├── state: Dict (domain-specific state)
├── progress_log: List[ProgressEntry]
└── artifacts: Dict (file paths)
```

---

## Usage

### Basic Memory Operations

```python
from mcp_client_for_ollama.memory import (
    DomainMemory,
    MemoryMetadata,
    Goal,
    Feature,
    MemoryStorage,
    DomainType,
)
from datetime import datetime

# Create storage
storage = MemoryStorage()  # Uses ~/.mcp-memory by default

# Create new memory
metadata = MemoryMetadata(
    session_id="my_session_001",
    domain="coding",
    description="Build authentication system",
    created_at=datetime.now(),
    updated_at=datetime.now(),
)
memory = DomainMemory(metadata=metadata)

# Add goals and features
goal = Goal(
    id="G1",
    description="Implement user authentication"
)
goal.features = [
    Feature(
        id="F1",
        description="User login endpoint",
        criteria=[
            "Endpoint accepts username/password",
            "Returns JWT token on success",
            "Returns 401 on invalid credentials"
        ],
        tests=["test_login_success", "test_login_failure"]
    ),
    Feature(
        id="F2",
        description="Password hashing with bcrypt",
        criteria=[
            "Passwords are hashed before storage",
            "Hash verification works correctly"
        ],
        tests=["test_password_hashing"]
    )
]
memory.goals = [goal]

# Save to disk
storage.save_memory(memory)

# Load from disk
loaded = storage.load_memory("my_session_001", "coding")

# Update feature status
feature = loaded.get_feature_by_id("F1")
if feature:
    feature.status = FeatureStatus.IN_PROGRESS
    loaded.add_progress_entry(
        agent_type="CODER",
        action="Started implementing login endpoint",
        outcome=OutcomeType.SUCCESS,
        details="Created initial endpoint structure",
        feature_id="F1"
    )
    storage.save_memory(loaded)
```

### Session Management

```python
# List all sessions
sessions = storage.list_sessions()
for session in sessions:
    print(f"{session['session_id']}: {session['description']}")
    print(f"  Completion: {session['completion_percentage']:.1f}%")
    print(f"  Features: {session['completed_features']}/{session['total_features']}")

# List sessions by domain
coding_sessions = storage.list_sessions(domain="coding")

# Check if session exists
exists = storage.session_exists("my_session_001", "coding")

# Delete session
storage.delete_session("my_session_001", "coding")

# Archive session
storage.archive_session("my_session_001", "coding")
```

### Working with Features

```python
# Get all pending/failed features
pending = memory.get_pending_features()
for feature in pending:
    print(f"{feature.id}: {feature.description} - {feature.status}")

# Get next feature to work on
goal = memory.goals[0]
next_feature = goal.get_next_feature()
if next_feature:
    print(f"Work on: {next_feature.description}")

# Update feature from test results
from mcp_client_for_ollama.memory.base_memory import TestResult

feature = memory.get_feature_by_id("F1")
feature.test_results.append(
    TestResult(
        test_id="test_login_success",
        feature_id="F1",
        passed=True,
        timestamp=datetime.now(),
        details="All assertions passed"
    )
)
feature.update_status_from_tests()

# Update all statuses from tests
memory.update_all_statuses()
```

### Progress Logging

```python
# Add progress entry
memory.add_progress_entry(
    agent_type="CODER",
    action="Implemented feature F1",
    outcome=OutcomeType.SUCCESS,
    details="Added login endpoint with JWT token generation",
    feature_id="F1",
    artifacts_changed=["src/auth/login.py", "tests/test_auth.py"]
)

# Get recent progress
recent = memory.get_recent_progress(limit=5)
for entry in recent:
    print(entry.to_log_line())
```

---

## Domain-Specific Schemas

The memory system supports different domains with specific state structures.

### Coding Domain

```python
from mcp_client_for_ollama.memory.schemas import MemorySchema, DomainType

# Get default state for coding domain
defaults = MemorySchema.get_domain_defaults(DomainType.CODING)
# Returns:
# {
#     "test_harness": {
#         "framework": "pytest",
#         "test_dirs": ["tests/"],
#         "run_command": "pytest -v"
#     },
#     "scaffolding": {
#         "git_enabled": True,
#         "auto_commit": False,
#         "required_files": ["README.md"]
#     }
# }

# Get artifact templates
artifacts = MemorySchema.get_domain_artifact_templates(DomainType.CODING)
# Returns:
# {
#     "features": "features.json",
#     "progress": "progress.log",
#     "tests": "test_results.json"
# }
```

### Research Domain

```python
defaults = MemorySchema.get_domain_defaults(DomainType.RESEARCH)
# Returns:
# {
#     "hypothesis_tracking": {
#         "active_hypotheses": [],
#         "confirmed_hypotheses": [],
#         "rejected_hypotheses": []
#     },
#     "experiment_registry": [],
#     "evidence_log": []
# }
```

### Operations Domain

```python
defaults = MemorySchema.get_domain_defaults(DomainType.OPERATIONS)
# Returns:
# {
#     "runbooks": [],
#     "incidents": {"active": [], "resolved": []},
#     "tickets": {"open": [], "in_progress": [], "closed": []},
#     "sla_metrics": {...}
# }
```

---

## Storage Structure

Memory is stored in the filesystem with the following structure:

```
~/.mcp-memory/
├── coding/
│   ├── session_abc123/
│   │   ├── memory.json          # Main memory state (JSON)
│   │   ├── progress.log         # Human-readable log
│   │   ├── artifacts/           # Domain-specific files
│   │   └── backups/             # Automatic backups
│   │       ├── memory_20250114_120000.json
│   │       └── memory_20250114_130000.json
│   └── session_def456/
├── research/
│   └── session_xyz789/
├── operations/
└── _archived/                   # Archived sessions
    └── coding/
        └── old_session/
```

### Files

**memory.json**: Complete memory state as JSON
- Goals, features, test results
- State dictionary
- Progress log
- Metadata

**progress.log**: Human-readable progress log
- Session header with metadata
- Timestamped entries with emojis (✓ ✗ ~ ⊘)
- Agent actions and outcomes

**artifacts/**: Domain-specific files
- Coding: test results, build logs
- Research: experiment data, evidence
- Operations: runbooks, incident reports

**backups/**: Automatic backups
- Created on each save (if enabled)
- Timestamped snapshots
- Automatically cleaned (keeps last 10)

---

## Configuration

Memory system settings in `config.json`:

```json
{
  "memory": {
    "enabled": false,
    "storage_dir": "~/.mcp-memory",
    "auto_persist": true,
    "max_sessions": 50,
    "session_ttl_days": 30,
    "auto_cleanup": false,
    "default_domain": "coding"
  }
}
```

### Settings

- **enabled**: Feature flag to enable memory system (default: false)
- **storage_dir**: Base directory for memory storage
- **auto_persist**: Automatically save after updates (default: true)
- **max_sessions**: Maximum number of sessions to keep
- **session_ttl_days**: Delete sessions older than N days
- **auto_cleanup**: Automatically clean old sessions (default: false)
- **default_domain**: Default domain for new sessions

---

## API Reference

### DomainMemory

Main memory container.

**Methods**:
- `add_progress_entry(agent_type, action, outcome, details, feature_id=None, artifacts_changed=None)` - Add progress log entry
- `get_recent_progress(limit=10)` - Get recent progress entries
- `get_all_features()` - Get all features from all goals
- `get_feature_by_id(feature_id)` - Find feature by ID
- `get_pending_features()` - Get features that are pending or failed
- `update_all_statuses()` - Update all statuses from test results
- `get_completion_percentage()` - Calculate completion percentage
- `to_dict()` - Serialize to dictionary
- `from_dict(data)` - Deserialize from dictionary

### Goal

A high-level objective containing features.

**Methods**:
- `update_status_from_features()` - Update goal status from feature statuses
- `get_next_feature()` - Get next pending/failed feature
- `to_dict()` - Serialize to dictionary
- `from_dict(data)` - Deserialize from dictionary

### Feature

An atomic work item with pass/fail criteria.

**Methods**:
- `update_status_from_tests()` - Update status based on test results
- `to_dict()` - Serialize to dictionary
- `from_dict(data)` - Deserialize from dictionary

**Status Values**:
- `PENDING` - Not started
- `IN_PROGRESS` - Being worked on or partially complete
- `COMPLETED` - All tests passing
- `FAILED` - Tests failing
- `BLOCKED` - Cannot proceed

### MemoryStorage

Persistence layer for memory.

**Methods**:
- `save_memory(memory, create_backup=True)` - Save memory to disk
- `load_memory(session_id, domain)` - Load memory from disk
- `session_exists(session_id, domain)` - Check if session exists
- `list_sessions(domain=None)` - List all sessions
- `delete_session(session_id, domain)` - Delete session
- `archive_session(session_id, domain)` - Archive session
- `get_artifacts_path(session_id, domain)` - Get artifacts directory
- `cleanup_old_sessions(days=30)` - Delete old sessions

---

## Best Practices

### 1. Use Feature-Level Granularity

Break goals into small, testable features:

```python
# Good: Specific, testable feature
Feature(
    id="F1",
    description="User login endpoint returns JWT",
    criteria=["Returns 200 on valid credentials", "JWT contains user ID"],
    tests=["test_login_success"]
)

# Bad: Too broad
Feature(
    id="F1",
    description="Build authentication system",
    criteria=["Authentication works"]
)
```

### 2. Always Define Pass/Fail Criteria

```python
feature = Feature(
    id="F1",
    description="Password validation",
    criteria=[
        "Minimum 8 characters",
        "Contains uppercase and lowercase",
        "Contains at least one digit",
        "Rejects common passwords"
    ],
    tests=["test_password_validation"]
)
```

### 3. Log All Agent Actions

```python
# Before implementing
memory.add_progress_entry(
    agent_type="CODER",
    action="Starting work on F1",
    outcome=OutcomeType.SUCCESS,
    details="Reviewed requirements and existing code",
    feature_id="F1"
)

# After implementing
memory.add_progress_entry(
    agent_type="CODER",
    action="Implemented F1",
    outcome=OutcomeType.SUCCESS,
    details="Added login endpoint with JWT generation",
    feature_id="F1",
    artifacts_changed=["src/auth.py", "tests/test_auth.py"]
)
```

### 4. Update Statuses from Tests

```python
# Run tests
test_results = run_tests()

# Add results to feature
for result in test_results:
    feature.test_results.append(
        TestResult(
            test_id=result.name,
            feature_id=feature.id,
            passed=result.passed,
            timestamp=datetime.now(),
            details=result.message
        )
    )

# Auto-update status
feature.update_status_from_tests()
```

### 5. Persist After Every Change

```python
# Update memory
feature.status = FeatureStatus.IN_PROGRESS
memory.add_progress_entry(...)

# Save immediately
storage.save_memory(memory)
```

### 6. Use Domain-Specific State

```python
# For coding domain
memory.state = MemorySchema.get_domain_defaults(DomainType.CODING)
memory.state["test_harness"]["framework"] = "pytest"

# For research domain
memory.state = MemorySchema.get_domain_defaults(DomainType.RESEARCH)
memory.state["hypothesis_tracking"]["active_hypotheses"].append(...)
```

---

## Testing

Run memory system tests:

```bash
# Run all memory tests
pytest tests/memory/ -v

# Run with coverage
pytest tests/memory/ --cov=mcp_client_for_ollama/memory --cov-report=term-missing

# Run specific test file
pytest tests/memory/test_base_memory.py -v
pytest tests/memory/test_storage.py -v
```

---

## Troubleshooting

### Memory file not found

```python
# Check if session exists
if not storage.session_exists(session_id, domain):
    print(f"Session {session_id} not found in domain {domain}")

# List available sessions
sessions = storage.list_sessions(domain=domain)
```

### Invalid JSON in memory file

```python
try:
    memory = storage.load_memory(session_id, domain)
except ValueError as e:
    print(f"Error loading memory: {e}")
    # Restore from backup
    # backups are in: {storage_dir}/{domain}/{session_id}/backups/
```

### Memory state inconsistency

```python
from mcp_client_for_ollama.memory.schemas import MemorySchema

# Validate structure
is_valid, error = MemorySchema.validate_memory_structure(memory.to_dict())
if not is_valid:
    print(f"Invalid memory: {error}")
```

### Storage directory permissions

```python
import os
from pathlib import Path

storage_dir = Path("~/.mcp-memory").expanduser()
if not os.access(storage_dir, os.W_OK):
    print(f"No write permission for {storage_dir}")
```

---

## Next Steps

Phase 1 (Foundation) is complete. Next phases will add:

- **Phase 2**: Initializer agent pattern
- **Phase 3**: Worker agent integration (boot ritual)
- **Phase 4**: Test integration and auto-status updates
- **Phase 5**: Git integration for commit-based tracking

See [Memory Model Implementation Plan](./memory-model-implementation-plan.md) for details.

---

## References

- [Agent Memory Architecture Guide](./agent-memory-architecture-guide.md)
- [Memory Model Implementation Plan](./memory-model-implementation-plan.md)
- Anthropic blog post on agent patterns
- Source code: `mcp_client_for_ollama/memory/`
