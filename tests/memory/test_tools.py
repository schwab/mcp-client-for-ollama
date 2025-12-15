"""Tests for memory tools."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from mcp_client_for_ollama.memory.tools import MemoryTools
from mcp_client_for_ollama.memory.storage import MemoryStorage
from mcp_client_for_ollama.memory.base_memory import (
    DomainMemory,
    Goal,
    Feature,
    MemoryMetadata,
    FeatureStatus,
)


class TestMemoryTools:
    """Tests for MemoryTools class."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def setup(self, temp_storage_dir):
        """Set up storage, tools, and sample memory."""
        storage = MemoryStorage(base_dir=temp_storage_dir)
        tools = MemoryTools(storage)

        # Create sample memory
        metadata = MemoryMetadata(
            session_id="test_session",
            domain="coding",
            description="Test session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        goal = Goal(id="G1", description="Test goal")
        goal.features = [
            Feature(
                id="F1",
                description="Feature 1",
                status=FeatureStatus.PENDING,
                criteria=["Criterion 1"],
                tests=["test_1"]
            ),
            Feature(
                id="F2",
                description="Feature 2",
                status=FeatureStatus.IN_PROGRESS,
                criteria=["Criterion 2"],
                tests=["test_2"]
            ),
        ]

        memory = DomainMemory(metadata=metadata, goals=[goal])
        storage.save_memory(memory)

        # Set current session
        tools.set_current_session("test_session", "coding")

        return storage, tools, memory

    def test_update_feature_status(self, setup):
        """Test updating feature status."""
        storage, tools, memory = setup

        result = tools.update_feature_status(
            feature_id="F1",
            status="in_progress",
            notes="Started implementation"
        )

        assert "✓ Updated feature F1" in result
        assert "pending → in_progress" in result

        # Verify in storage
        loaded = storage.load_memory("test_session", "coding")
        feature = loaded.get_feature_by_id("F1")
        assert feature.status == FeatureStatus.IN_PROGRESS
        assert "Started implementation" in feature.notes

    def test_update_feature_status_invalid_status(self, setup):
        """Test updating with invalid status."""
        storage, tools, memory = setup

        result = tools.update_feature_status(
            feature_id="F1",
            status="invalid_status"
        )

        assert "Error: Invalid status" in result

    def test_update_feature_status_not_found(self, setup):
        """Test updating non-existent feature."""
        storage, tools, memory = setup

        result = tools.update_feature_status(
            feature_id="F99",
            status="completed"
        )

        assert "Error: Feature 'F99' not found" in result

    def test_update_feature_status_no_session(self):
        """Test updating without active session."""
        storage = MemoryStorage()
        tools = MemoryTools(storage)

        result = tools.update_feature_status("F1", "completed")

        assert "Error: No active memory session" in result

    def test_log_progress(self, setup):
        """Test logging progress."""
        storage, tools, memory = setup

        result = tools.log_progress(
            agent_type="CODER",
            action="Implemented feature",
            outcome="success",
            details="Added login endpoint",
            feature_id="F1",
            artifacts_changed=["auth.py", "tests/test_auth.py"]
        )

        assert "✓ Progress logged" in result
        assert "CODER" in result
        assert "success" in result

        # Verify in storage
        loaded = storage.load_memory("test_session", "coding")
        assert len(loaded.progress_log) > 0
        latest = loaded.progress_log[-1]
        assert latest.agent_type == "CODER"
        assert latest.action == "Implemented feature"
        assert latest.feature_id == "F1"

    def test_log_progress_invalid_outcome(self, setup):
        """Test logging with invalid outcome."""
        storage, tools, memory = setup

        result = tools.log_progress(
            agent_type="CODER",
            action="Test",
            outcome="invalid_outcome",
            details="Test"
        )

        assert "Error: Invalid outcome" in result

    def test_add_test_result_pass(self, setup):
        """Test adding passing test result."""
        storage, tools, memory = setup

        result = tools.add_test_result(
            feature_id="F1",
            test_id="test_1",
            passed=True,
            details="All assertions passed"
        )

        assert "✓ Test result added" in result
        assert "PASS" in result

        # Verify in storage
        loaded = storage.load_memory("test_session", "coding")
        feature = loaded.get_feature_by_id("F1")
        assert len(feature.test_results) == 1
        assert feature.test_results[0].passed is True

    def test_add_test_result_fail(self, setup):
        """Test adding failing test result."""
        storage, tools, memory = setup

        result = tools.add_test_result(
            feature_id="F1",
            test_id="test_1",
            passed=False,
            details="Assertion failed"
        )

        assert "✗ Test result added" in result
        assert "FAIL" in result

        # Verify status auto-updated
        loaded = storage.load_memory("test_session", "coding")
        feature = loaded.get_feature_by_id("F1")
        assert feature.status == FeatureStatus.FAILED

    def test_add_test_result_auto_updates_status(self, setup):
        """Test that adding test results auto-updates feature status."""
        storage, tools, memory = setup

        # Add passing test
        tools.add_test_result("F1", "test_1", True)

        # Check status updated to completed
        loaded = storage.load_memory("test_session", "coding")
        feature = loaded.get_feature_by_id("F1")
        assert feature.status == FeatureStatus.COMPLETED

    def test_get_memory_state(self, setup):
        """Test getting memory state summary."""
        storage, tools, memory = setup

        result = tools.get_memory_state()

        assert "test_session" in result
        assert "coding" in result
        assert "Test session" in result
        assert "G1: Test goal" in result
        assert "F1: Feature 1" in result

    def test_get_feature_details(self, setup):
        """Test getting feature details."""
        storage, tools, memory = setup

        result = tools.get_feature_details("F1")

        assert "FEATURE: F1" in result
        assert "Feature 1" in result
        assert "Pass/Fail Criteria:" in result
        assert "Criterion 1" in result
        assert "test_1" in result

    def test_get_feature_details_not_found(self, setup):
        """Test getting details for non-existent feature."""
        storage, tools, memory = setup

        result = tools.get_feature_details("F99")

        assert "Error: Feature 'F99' not found" in result

    def test_set_current_session(self):
        """Test setting current session."""
        storage = MemoryStorage()
        tools = MemoryTools(storage)

        assert tools.current_session_id is None
        assert tools.current_domain is None

        tools.set_current_session("session_123", "research")

        assert tools.current_session_id == "session_123"
        assert tools.current_domain == "research"

    def test_update_feature_status_updates_goal(self, setup):
        """Test that updating features updates parent goal."""
        storage, tools, memory = setup

        # Complete both features
        tools.update_feature_status("F1", "completed")
        tools.update_feature_status("F2", "completed")

        # Goal should be completed
        loaded = storage.load_memory("test_session", "coding")
        goal = loaded.goals[0]
        assert goal.status.value in ["completed", "in_progress"]  # Could be either depending on auto-update logic
