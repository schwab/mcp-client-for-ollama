"""Tests for boot ritual."""

import pytest
from datetime import datetime

from mcp_client_for_ollama.memory.boot_ritual import BootRitual
from mcp_client_for_ollama.memory.base_memory import (
    DomainMemory,
    Goal,
    Feature,
    MemoryMetadata,
    FeatureStatus,
    ProgressEntry,
    OutcomeType,
)


class TestBootRitual:
    """Tests for BootRitual class."""

    @pytest.fixture
    def sample_memory(self):
        """Create sample memory for testing."""
        metadata = MemoryMetadata(
            session_id="test_session",
            domain="coding",
            description="Build authentication system",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        goal = Goal(id="G1", description="User authentication")
        goal.features = [
            Feature(
                id="F1",
                description="Login endpoint",
                status=FeatureStatus.PENDING,
                criteria=["Returns JWT on success", "Returns 401 on failure"],
                tests=["test_login_success", "test_login_failure"]
            ),
            Feature(
                id="F2",
                description="Password hashing",
                status=FeatureStatus.COMPLETED,
                criteria=["Uses bcrypt", "Hash verification works"],
                tests=["test_password_hashing"]
            ),
            Feature(
                id="F3",
                description="Token validation",
                status=FeatureStatus.FAILED,
                criteria=["Validates signature", "Checks expiration"],
                tests=["test_token_validation"]
            ),
        ]

        memory = DomainMemory(metadata=metadata, goals=[goal])

        # Add some progress entries
        memory.add_progress_entry(
            agent_type="INITIALIZER",
            action="Created session",
            outcome=OutcomeType.SUCCESS,
            details="Initialized memory",
        )
        memory.add_progress_entry(
            agent_type="CODER",
            action="Implemented F2",
            outcome=OutcomeType.SUCCESS,
            details="Added password hashing with bcrypt",
            feature_id="F2",
        )

        return memory

    def test_build_memory_context(self, sample_memory):
        """Test building memory context for an agent."""
        context = BootRitual.build_memory_context(
            memory=sample_memory,
            agent_type="CODER",
            task_description="Implement login endpoint",
        )

        # Check that context includes key information
        assert "test_session" in context
        assert "coding" in context
        assert "Build authentication system" in context

        # Check progress summary
        assert "Total Features: 3" in context
        assert "Completed:" in context
        assert "Pending:" in context

        # Check goals and features
        assert "G1: User authentication" in context
        assert "F1: Login endpoint" in context
        assert "F2: Password hashing" in context
        assert "F3: Token validation" in context

        # Check criteria are included
        assert "Returns JWT on success" in context
        assert "Uses bcrypt" in context

        # Check protocol
        assert "PROTOCOL:" in context
        assert "ONE feature at a time" in context

        # Check task description is included
        assert "Implement login endpoint" in context

    def test_build_memory_context_with_test_results(self):
        """Test context includes test result information."""
        from mcp_client_for_ollama.memory.base_memory import TestResult

        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        feature = Feature(
            id="F1",
            description="Test feature",
            tests=["test_1", "test_2"]
        )
        feature.test_results = [
            TestResult("test_1", "F1", True, datetime.now()),
            TestResult("test_2", "F1", False, datetime.now()),
        ]

        goal = Goal(id="G1", description="Test", features=[feature])
        memory = DomainMemory(metadata=metadata, goals=[goal])

        context = BootRitual.build_memory_context(memory, "CODER")

        # Should show test status
        assert "[1/2 passing]" in context

    def test_get_next_feature_suggestion_pending(self, sample_memory):
        """Test getting next feature suggestion prioritizes pending."""
        next_feature = BootRitual.get_next_feature_suggestion(
            sample_memory,
            "CODER"
        )

        # Should suggest failed feature first (F3)
        assert next_feature is not None
        assert next_feature.id == "F3"  # Failed has higher priority

    def test_get_next_feature_suggestion_no_work(self):
        """Test when no features need work."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        goal = Goal(id="G1", description="Test")
        goal.features = [
            Feature(id="F1", description="Done", status=FeatureStatus.COMPLETED),
        ]

        memory = DomainMemory(metadata=metadata, goals=[goal])

        next_feature = BootRitual.get_next_feature_suggestion(memory, "CODER")
        assert next_feature is None

    def test_get_next_feature_suggestion_priority(self):
        """Test priority-based feature selection."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        goal = Goal(id="G1", description="Test")
        goal.features = [
            Feature(id="F1", description="Low", notes="Priority: low", status=FeatureStatus.PENDING),
            Feature(id="F2", description="High", notes="Priority: high", status=FeatureStatus.PENDING),
            Feature(id="F3", description="Medium", notes="Priority: medium", status=FeatureStatus.PENDING),
        ]

        memory = DomainMemory(metadata=metadata, goals=[goal])

        next_feature = BootRitual.get_next_feature_suggestion(memory, "CODER")

        # Should suggest high priority feature
        assert next_feature.id == "F2"

    def test_format_feature_context(self, sample_memory):
        """Test formatting detailed feature context."""
        feature = sample_memory.goals[0].features[0]  # F1

        context = BootRitual.format_feature_context(feature)

        assert "FEATURE: F1" in context
        assert "Login endpoint" in context
        assert "Pass/Fail Criteria:" in context
        assert "Returns JWT on success" in context
        assert "Required Tests:" in context
        assert "test_login_success" in context

    def test_build_tool_update_message(self):
        """Test building tool update instruction."""
        message = BootRitual.build_tool_update_message(
            feature_id="F1",
            new_status="completed",
            details="Implemented and tested",
        )

        assert "F1" in message
        assert "completed" in message
        assert "update_feature_status" in message
        assert "log_progress" in message

    def test_memory_context_includes_domain_state(self):
        """Test that domain state is included in context."""
        metadata = MemoryMetadata(
            session_id="test",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        memory = DomainMemory(metadata=metadata)
        memory.state = {
            "test_harness": {
                "framework": "pytest",
                "run_command": "pytest -v"
            },
            "scaffolding": {
                "language": "python",
                "git_enabled": True
            }
        }

        context = BootRitual.build_memory_context(memory, "CODER")

        assert "Test Framework: pytest" in context
        assert "Language: python" in context
        assert "Git Enabled: True" in context

    def test_memory_context_includes_recent_progress(self, sample_memory):
        """Test that recent progress is included."""
        context = BootRitual.build_memory_context(sample_memory, "CODER")

        assert "RECENT PROGRESS:" in context
        assert "INITIALIZER" in context
        assert "CODER" in context
        assert "Implemented F2" in context

    def test_memory_context_completion_percentage(self, sample_memory):
        """Test completion percentage is shown."""
        context = BootRitual.build_memory_context(sample_memory, "CODER")

        # 1 completed out of 3 = 33.3%
        assert "Completion: 33.3%" in context
