"""Tests for base memory dataclasses."""

import pytest
from datetime import datetime
from mcp_client_for_ollama.memory.base_memory import (
    DomainMemory,
    Goal,
    Feature,
    ProgressEntry,
    TestResult,
    MemoryMetadata,
    FeatureStatus,
    GoalStatus,
    OutcomeType,
)


class TestFeature:
    """Tests for Feature class."""

    def test_create_feature(self):
        """Test creating a feature."""
        feature = Feature(
            id="F1",
            description="Test feature",
            status=FeatureStatus.PENDING,
        )
        assert feature.id == "F1"
        assert feature.description == "Test feature"
        assert feature.status == FeatureStatus.PENDING
        assert feature.criteria == []
        assert feature.tests == []

    def test_feature_to_dict(self):
        """Test converting feature to dict."""
        feature = Feature(
            id="F1",
            description="Test feature",
            criteria=["Must work", "Must be fast"],
            tests=["test_1", "test_2"],
        )
        data = feature.to_dict()

        assert data["id"] == "F1"
        assert data["description"] == "Test feature"
        assert data["status"] == "pending"
        assert len(data["criteria"]) == 2
        assert len(data["tests"]) == 2

    def test_feature_from_dict(self):
        """Test creating feature from dict."""
        data = {
            "id": "F1",
            "description": "Test feature",
            "status": "pending",
            "criteria": ["Must work"],
            "tests": ["test_1"],
            "test_results": [],
            "notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "assigned_to": None,
        }
        feature = Feature.from_dict(data)

        assert feature.id == "F1"
        assert feature.description == "Test feature"
        assert feature.status == FeatureStatus.PENDING

    def test_update_status_from_tests_all_pass(self):
        """Test status update when all tests pass."""
        feature = Feature(id="F1", description="Test")
        feature.test_results = [
            TestResult("test_1", "F1", True, datetime.now()),
            TestResult("test_2", "F1", True, datetime.now()),
        ]
        feature.update_status_from_tests()

        assert feature.status == FeatureStatus.COMPLETED

    def test_update_status_from_tests_all_fail(self):
        """Test status update when all tests fail."""
        feature = Feature(id="F1", description="Test")
        feature.test_results = [
            TestResult("test_1", "F1", False, datetime.now()),
            TestResult("test_2", "F1", False, datetime.now()),
        ]
        feature.update_status_from_tests()

        assert feature.status == FeatureStatus.FAILED

    def test_update_status_from_tests_partial(self):
        """Test status update when some tests pass."""
        feature = Feature(id="F1", description="Test")
        feature.test_results = [
            TestResult("test_1", "F1", True, datetime.now()),
            TestResult("test_2", "F1", False, datetime.now()),
        ]
        feature.update_status_from_tests()

        assert feature.status == FeatureStatus.IN_PROGRESS


class TestGoal:
    """Tests for Goal class."""

    def test_create_goal(self):
        """Test creating a goal."""
        goal = Goal(
            id="G1",
            description="Test goal",
        )
        assert goal.id == "G1"
        assert goal.description == "Test goal"
        assert goal.status == GoalStatus.PENDING
        assert goal.features == []

    def test_goal_to_dict(self):
        """Test converting goal to dict."""
        feature = Feature(id="F1", description="Feature 1")
        goal = Goal(
            id="G1",
            description="Test goal",
            features=[feature],
        )
        data = goal.to_dict()

        assert data["id"] == "G1"
        assert len(data["features"]) == 1
        assert data["status"] == "pending"

    def test_goal_from_dict(self):
        """Test creating goal from dict."""
        data = {
            "id": "G1",
            "description": "Test goal",
            "features": [],
            "status": "pending",
            "constraints": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        goal = Goal.from_dict(data)

        assert goal.id == "G1"
        assert goal.status == GoalStatus.PENDING

    def test_update_status_all_completed(self):
        """Test goal status when all features completed."""
        goal = Goal(id="G1", description="Test")
        goal.features = [
            Feature(id="F1", description="F1", status=FeatureStatus.COMPLETED),
            Feature(id="F2", description="F2", status=FeatureStatus.COMPLETED),
        ]
        goal.update_status_from_features()

        assert goal.status == GoalStatus.COMPLETED

    def test_update_status_all_failed(self):
        """Test goal status when all features failed."""
        goal = Goal(id="G1", description="Test")
        goal.features = [
            Feature(id="F1", description="F1", status=FeatureStatus.FAILED),
            Feature(id="F2", description="F2", status=FeatureStatus.FAILED),
        ]
        goal.update_status_from_features()

        assert goal.status == GoalStatus.FAILED

    def test_update_status_in_progress(self):
        """Test goal status when some features in progress."""
        goal = Goal(id="G1", description="Test")
        goal.features = [
            Feature(id="F1", description="F1", status=FeatureStatus.COMPLETED),
            Feature(id="F2", description="F2", status=FeatureStatus.IN_PROGRESS),
        ]
        goal.update_status_from_features()

        assert goal.status == GoalStatus.IN_PROGRESS

    def test_get_next_feature(self):
        """Test getting next feature to work on."""
        goal = Goal(id="G1", description="Test")
        goal.features = [
            Feature(id="F1", description="F1", status=FeatureStatus.COMPLETED),
            Feature(id="F2", description="F2", status=FeatureStatus.PENDING),
            Feature(id="F3", description="F3", status=FeatureStatus.PENDING),
        ]

        next_feature = goal.get_next_feature()
        assert next_feature is not None
        assert next_feature.id == "F2"


class TestProgressEntry:
    """Tests for ProgressEntry class."""

    def test_create_progress_entry(self):
        """Test creating a progress entry."""
        entry = ProgressEntry(
            timestamp=datetime.now(),
            agent_type="CODER",
            action="Implemented feature",
            outcome=OutcomeType.SUCCESS,
            details="Added new function",
        )
        assert entry.agent_type == "CODER"
        assert entry.outcome == OutcomeType.SUCCESS

    def test_progress_entry_to_log_line(self):
        """Test formatting as log line."""
        entry = ProgressEntry(
            timestamp=datetime.now(),
            agent_type="CODER",
            action="Implemented feature",
            outcome=OutcomeType.SUCCESS,
            details="Added new function",
            feature_id="F1",
        )
        log_line = entry.to_log_line()

        assert "CODER" in log_line
        assert "[F1]" in log_line
        assert "Added new function" in log_line


class TestDomainMemory:
    """Tests for DomainMemory class."""

    def test_create_domain_memory(self):
        """Test creating domain memory."""
        metadata = MemoryMetadata(
            session_id="test_session",
            domain="coding",
            description="Test session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        assert memory.metadata.session_id == "test_session"
        assert memory.metadata.domain == "coding"
        assert memory.goals == []
        assert memory.progress_log == []

    def test_add_progress_entry(self):
        """Test adding progress entry."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        memory.add_progress_entry(
            agent_type="CODER",
            action="Test action",
            outcome=OutcomeType.SUCCESS,
            details="Test details",
        )

        assert len(memory.progress_log) == 1
        assert memory.progress_log[0].agent_type == "CODER"

    def test_get_recent_progress(self):
        """Test getting recent progress."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        # Add multiple entries
        for i in range(15):
            memory.add_progress_entry(
                agent_type="CODER",
                action=f"Action {i}",
                outcome=OutcomeType.SUCCESS,
                details=f"Details {i}",
            )

        recent = memory.get_recent_progress(limit=5)
        assert len(recent) == 5
        # Should be most recent first
        assert "14" in recent[0].action

    def test_get_all_features(self):
        """Test getting all features from all goals."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        goal1 = Goal(id="G1", description="Goal 1")
        goal1.features = [
            Feature(id="F1", description="F1"),
            Feature(id="F2", description="F2"),
        ]

        goal2 = Goal(id="G2", description="Goal 2")
        goal2.features = [
            Feature(id="F3", description="F3"),
        ]

        memory.goals = [goal1, goal2]

        all_features = memory.get_all_features()
        assert len(all_features) == 3

    def test_get_feature_by_id(self):
        """Test finding feature by ID."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        goal = Goal(id="G1", description="Goal 1")
        goal.features = [
            Feature(id="F1", description="F1"),
            Feature(id="F2", description="F2"),
        ]
        memory.goals = [goal]

        feature = memory.get_feature_by_id("F2")
        assert feature is not None
        assert feature.id == "F2"

        not_found = memory.get_feature_by_id("F99")
        assert not_found is None

    def test_get_goal_by_id(self):
        """Test finding goal by ID."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        goal1 = Goal(id="G1", description="Goal 1")
        goal2 = Goal(id="G2", description="Goal 2")
        memory.goals = [goal1, goal2]

        goal = memory.get_goal_by_id("G2")
        assert goal is not None
        assert goal.id == "G2"
        assert goal.description == "Goal 2"

        not_found = memory.get_goal_by_id("G99")
        assert not_found is None

    def test_get_pending_features(self):
        """Test getting pending/failed features."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        goal = Goal(id="G1", description="Goal 1")
        goal.features = [
            Feature(id="F1", description="F1", status=FeatureStatus.COMPLETED),
            Feature(id="F2", description="F2", status=FeatureStatus.PENDING),
            Feature(id="F3", description="F3", status=FeatureStatus.FAILED),
        ]
        memory.goals = [goal]

        pending = memory.get_pending_features()
        assert len(pending) == 2
        assert all(f.status in [FeatureStatus.PENDING, FeatureStatus.FAILED] for f in pending)

    def test_get_completion_percentage(self):
        """Test calculating completion percentage."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        goal = Goal(id="G1", description="Goal 1")
        goal.features = [
            Feature(id="F1", description="F1", status=FeatureStatus.COMPLETED),
            Feature(id="F2", description="F2", status=FeatureStatus.COMPLETED),
            Feature(id="F3", description="F3", status=FeatureStatus.PENDING),
            Feature(id="F4", description="F4", status=FeatureStatus.PENDING),
        ]
        memory.goals = [goal]

        percentage = memory.get_completion_percentage()
        assert percentage == 50.0

    def test_memory_serialization(self):
        """Test full serialization/deserialization cycle."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        goal = Goal(id="G1", description="Test goal")
        goal.features = [Feature(id="F1", description="Test feature")]
        memory.goals = [goal]

        memory.add_progress_entry(
            agent_type="CODER",
            action="Test",
            outcome=OutcomeType.SUCCESS,
            details="Test",
        )

        # Convert to dict and back
        data = memory.to_dict()
        restored = DomainMemory.from_dict(data)

        assert restored.metadata.session_id == memory.metadata.session_id
        assert len(restored.goals) == 1
        assert len(restored.progress_log) == 1
