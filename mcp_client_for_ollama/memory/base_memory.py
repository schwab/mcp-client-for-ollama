"""
Base memory schema dataclasses for domain-specific agent memory.

These dataclasses define the core structure for persistent agent memory,
following the Anthropic pattern of stateful, structured representation of work.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class FeatureStatus(str, Enum):
    """Status of a feature in the domain memory."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class GoalStatus(str, Enum):
    """Status of a goal in the domain memory."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutcomeType(str, Enum):
    """Outcome of an agent action."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass
class TestResult:
    """Result of a test execution."""
    test_id: str
    feature_id: str
    passed: bool
    timestamp: datetime
    details: str = ""
    output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_id": self.test_id,
            "feature_id": self.feature_id,
            "passed": self.passed,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "output": self.output,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestResult":
        """Create from dictionary."""
        return cls(
            test_id=data["test_id"],
            feature_id=data["feature_id"],
            passed=data["passed"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            details=data.get("details", ""),
            output=data.get("output", ""),
        )


@dataclass
class Feature:
    """
    A single feature or work item within a goal.

    Features are the atomic units of work that agents can complete.
    Each feature has clear pass/fail criteria and associated tests.
    """
    id: str
    description: str
    status: FeatureStatus = FeatureStatus.PENDING
    criteria: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None  # Agent type

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "criteria": self.criteria,
            "tests": self.tests,
            "test_results": [tr.to_dict() for tr in self.test_results],
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "assigned_to": self.assigned_to,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feature":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            status=FeatureStatus(data["status"]),
            criteria=data.get("criteria", []),
            tests=data.get("tests", []),
            test_results=[TestResult.from_dict(tr) for tr in data.get("test_results", [])],
            notes=data.get("notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            assigned_to=data.get("assigned_to"),
        )

    def update_status_from_tests(self) -> None:
        """Update feature status based on test results."""
        if not self.test_results:
            if self.status == FeatureStatus.IN_PROGRESS:
                return  # Keep current status if no tests yet
            self.status = FeatureStatus.PENDING
            return

        latest_results = sorted(self.test_results, key=lambda x: x.timestamp, reverse=True)

        # Group by test_id to get latest result for each test
        latest_by_test: Dict[str, TestResult] = {}
        for result in latest_results:
            if result.test_id not in latest_by_test:
                latest_by_test[result.test_id] = result

        # Check if all tests pass
        if all(r.passed for r in latest_by_test.values()):
            self.status = FeatureStatus.COMPLETED
        elif any(r.passed for r in latest_by_test.values()):
            self.status = FeatureStatus.IN_PROGRESS  # Partial progress
        else:
            self.status = FeatureStatus.FAILED

        self.updated_at = datetime.now()


@dataclass
class Goal:
    """
    A high-level goal that contains multiple features.

    Goals represent user objectives and are broken down into
    specific, testable features that agents can work on.
    """
    id: str
    description: str
    features: List[Feature] = field(default_factory=list)
    status: GoalStatus = GoalStatus.PENDING
    constraints: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "features": [f.to_dict() for f in self.features],
            "status": self.status.value,
            "constraints": self.constraints,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            features=[Feature.from_dict(f) for f in data.get("features", [])],
            status=GoalStatus(data.get("status", "pending")),
            constraints=data.get("constraints", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def update_status_from_features(self) -> None:
        """Update goal status based on feature statuses."""
        if not self.features:
            return

        completed = sum(1 for f in self.features if f.status == FeatureStatus.COMPLETED)
        failed = sum(1 for f in self.features if f.status == FeatureStatus.FAILED)
        in_progress = sum(1 for f in self.features if f.status == FeatureStatus.IN_PROGRESS)

        total = len(self.features)

        if completed == total:
            self.status = GoalStatus.COMPLETED
        elif failed == total:
            self.status = GoalStatus.FAILED
        elif completed > 0 or in_progress > 0:
            self.status = GoalStatus.IN_PROGRESS
        else:
            self.status = GoalStatus.PENDING

        self.updated_at = datetime.now()

    def get_next_feature(self) -> Optional[Feature]:
        """Get the next feature to work on (first pending or failed)."""
        for feature in self.features:
            if feature.status in [FeatureStatus.PENDING, FeatureStatus.FAILED]:
                return feature
        return None


@dataclass
class ProgressEntry:
    """
    A single entry in the progress log.

    Progress entries track what agents did, when, and with what outcome.
    This provides a human-readable audit trail of agent actions.
    """
    timestamp: datetime
    agent_type: str
    action: str
    outcome: OutcomeType
    details: str
    feature_id: Optional[str] = None
    artifacts_changed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_type": self.agent_type,
            "action": self.action,
            "outcome": self.outcome.value,
            "details": self.details,
            "feature_id": self.feature_id,
            "artifacts_changed": self.artifacts_changed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressEntry":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            agent_type=data["agent_type"],
            action=data["action"],
            outcome=OutcomeType(data["outcome"]),
            details=data["details"],
            feature_id=data.get("feature_id"),
            artifacts_changed=data.get("artifacts_changed", []),
        )

    def to_log_line(self) -> str:
        """Format as human-readable log line."""
        emoji = {
            OutcomeType.SUCCESS: "✓",
            OutcomeType.FAILURE: "✗",
            OutcomeType.PARTIAL: "~",
            OutcomeType.BLOCKED: "⊘",
        }

        feature_str = f" [{self.feature_id}]" if self.feature_id else ""
        return (
            f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
            f"{emoji[self.outcome]} {self.agent_type}{feature_str}: "
            f"{self.action} - {self.details}"
        )


@dataclass
class MemoryMetadata:
    """Metadata about the memory session."""
    session_id: str
    domain: str  # e.g., "coding", "research", "operations"
    description: str
    created_at: datetime
    updated_at: datetime
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "domain": self.domain,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryMetadata":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            domain=data["domain"],
            description=data["description"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", "1.0"),
        )


@dataclass
class DomainMemory:
    """
    Domain-specific persistent memory for AI agents.

    This is the core memory structure that maintains state across sessions.
    It contains goals, features, progress history, and domain-specific artifacts.

    Following the Anthropic pattern: The agent is just a policy that transforms
    one consistent memory state into another. The magic is in the memory.
    """
    metadata: MemoryMetadata
    goals: List[Goal] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    progress_log: List[ProgressEntry] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)  # name -> path

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": self.metadata.to_dict(),
            "goals": [g.to_dict() for g in self.goals],
            "state": self.state,
            "progress_log": [p.to_dict() for p in self.progress_log],
            "artifacts": self.artifacts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainMemory":
        """Create from dictionary."""
        return cls(
            metadata=MemoryMetadata.from_dict(data["metadata"]),
            goals=[Goal.from_dict(g) for g in data.get("goals", [])],
            state=data.get("state", {}),
            progress_log=[ProgressEntry.from_dict(p) for p in data.get("progress_log", [])],
            artifacts=data.get("artifacts", {}),
        )

    def add_progress_entry(
        self,
        agent_type: str,
        action: str,
        outcome: OutcomeType,
        details: str,
        feature_id: Optional[str] = None,
        artifacts_changed: Optional[List[str]] = None,
    ) -> None:
        """Add a new entry to the progress log."""
        entry = ProgressEntry(
            timestamp=datetime.now(),
            agent_type=agent_type,
            action=action,
            outcome=outcome,
            details=details,
            feature_id=feature_id,
            artifacts_changed=artifacts_changed or [],
        )
        self.progress_log.append(entry)
        self.metadata.updated_at = datetime.now()

    def get_recent_progress(self, limit: int = 10) -> List[ProgressEntry]:
        """Get the most recent progress entries."""
        return sorted(self.progress_log, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_all_features(self) -> List[Feature]:
        """Get all features from all goals."""
        return [feature for goal in self.goals for feature in goal.features]

    def get_feature_by_id(self, feature_id: str) -> Optional[Feature]:
        """Find a feature by its ID."""
        for goal in self.goals:
            for feature in goal.features:
                if feature.id == feature_id:
                    return feature
        return None

    def get_pending_features(self) -> List[Feature]:
        """Get all features that are pending or failed."""
        return [
            f for f in self.get_all_features()
            if f.status in [FeatureStatus.PENDING, FeatureStatus.FAILED]
        ]

    def update_all_statuses(self) -> None:
        """Update all feature and goal statuses based on test results."""
        # Update features from tests
        for feature in self.get_all_features():
            feature.update_status_from_tests()

        # Update goals from features
        for goal in self.goals:
            goal.update_status_from_features()

        self.metadata.updated_at = datetime.now()

    def get_completion_percentage(self) -> float:
        """Calculate overall completion percentage."""
        all_features = self.get_all_features()
        if not all_features:
            return 0.0

        completed = sum(1 for f in all_features if f.status == FeatureStatus.COMPLETED)
        return (completed / len(all_features)) * 100
