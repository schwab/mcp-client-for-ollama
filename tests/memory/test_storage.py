"""Tests for memory storage layer."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from mcp_client_for_ollama.memory.storage import MemoryStorage
from mcp_client_for_ollama.memory.base_memory import (
    DomainMemory,
    Goal,
    Feature,
    MemoryMetadata,
    OutcomeType,
)
from mcp_client_for_ollama.memory.schemas import DomainType


class TestMemoryStorage:
    """Tests for MemoryStorage class."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for storage tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def storage(self, temp_storage_dir):
        """Create a MemoryStorage instance with temp directory."""
        return MemoryStorage(base_dir=temp_storage_dir)

    @pytest.fixture
    def sample_memory(self):
        """Create a sample memory for testing."""
        metadata = MemoryMetadata(
            session_id="test_session_123",
            domain="coding",
            description="Test session for unit testing",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        goal = Goal(id="G1", description="Implement authentication")
        goal.features = [
            Feature(id="F1", description="User login"),
            Feature(id="F2", description="Password hashing"),
        ]
        memory.goals = [goal]

        memory.add_progress_entry(
            agent_type="INITIALIZER",
            action="Created session",
            outcome=OutcomeType.SUCCESS,
            details="Initialized domain memory",
        )

        return memory

    def test_storage_initialization(self, temp_storage_dir):
        """Test storage initialization creates base directory."""
        storage = MemoryStorage(base_dir=temp_storage_dir)
        assert storage.base_dir.exists()
        assert storage.base_dir.is_dir()

    def test_save_memory(self, storage, sample_memory):
        """Test saving memory to disk."""
        storage.save_memory(sample_memory)

        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain

        # Check memory.json exists
        memory_path = storage._get_memory_path(session_id, domain)
        assert memory_path.exists()

        # Check progress.log exists
        progress_path = storage._get_progress_log_path(session_id, domain)
        assert progress_path.exists()

    def test_load_memory(self, storage, sample_memory):
        """Test loading memory from disk."""
        # Save first
        storage.save_memory(sample_memory)

        # Load
        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain
        loaded = storage.load_memory(session_id, domain)

        assert loaded is not None
        assert loaded.metadata.session_id == session_id
        assert loaded.metadata.domain == domain
        assert len(loaded.goals) == 1
        assert len(loaded.progress_log) == 1

    def test_load_nonexistent_memory(self, storage):
        """Test loading memory that doesn't exist."""
        loaded = storage.load_memory("nonexistent", "coding")
        assert loaded is None

    def test_session_exists(self, storage, sample_memory):
        """Test checking if session exists."""
        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain

        assert not storage.session_exists(session_id, domain)

        storage.save_memory(sample_memory)

        assert storage.session_exists(session_id, domain)

    def test_list_sessions_empty(self, storage):
        """Test listing sessions when none exist."""
        sessions = storage.list_sessions()
        assert sessions == []

    def test_list_sessions(self, storage, sample_memory):
        """Test listing sessions."""
        # Create multiple sessions
        storage.save_memory(sample_memory)

        # Create second session
        metadata2 = MemoryMetadata(
            session_id="test_session_456",
            domain="research",
            description="Research session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory2 = DomainMemory(metadata=metadata2)
        storage.save_memory(memory2)

        # List all sessions
        sessions = storage.list_sessions()
        assert len(sessions) == 2

        # Check structure
        assert all("session_id" in s for s in sessions)
        assert all("domain" in s for s in sessions)
        assert all("completion_percentage" in s for s in sessions)

    def test_list_sessions_filtered_by_domain(self, storage, sample_memory):
        """Test listing sessions filtered by domain."""
        storage.save_memory(sample_memory)

        metadata2 = MemoryMetadata(
            session_id="test_session_456",
            domain="research",
            description="Research session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory2 = DomainMemory(metadata=metadata2)
        storage.save_memory(memory2)

        # List only coding sessions
        coding_sessions = storage.list_sessions(domain="coding")
        assert len(coding_sessions) == 1
        assert coding_sessions[0]["domain"] == "coding"

    def test_delete_session(self, storage, sample_memory):
        """Test deleting a session."""
        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain

        storage.save_memory(sample_memory)
        assert storage.session_exists(session_id, domain)

        result = storage.delete_session(session_id, domain)
        assert result is True
        assert not storage.session_exists(session_id, domain)

    def test_delete_nonexistent_session(self, storage):
        """Test deleting a session that doesn't exist."""
        result = storage.delete_session("nonexistent", "coding")
        assert result is False

    def test_archive_session(self, storage, sample_memory):
        """Test archiving a session."""
        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain

        storage.save_memory(sample_memory)

        result = storage.archive_session(session_id, domain)
        assert result is True

        # Session should no longer exist in normal location
        assert not storage.session_exists(session_id, domain)

        # Should exist in archive
        archive_path = storage.base_dir / "_archived" / domain / session_id
        assert archive_path.exists()

    def test_backup_creation(self, storage, sample_memory):
        """Test that backups are created on save."""
        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain

        # Save once
        storage.save_memory(sample_memory, create_backup=False)

        # Modify and save again with backup
        sample_memory.add_progress_entry(
            agent_type="CODER",
            action="Updated code",
            outcome=OutcomeType.SUCCESS,
            details="Made changes",
        )
        storage.save_memory(sample_memory, create_backup=True)

        # Check backup exists
        backups_dir = storage._get_backups_dir(session_id, domain)
        backups = list(backups_dir.glob("memory_*.json"))
        assert len(backups) == 1

    def test_get_artifacts_path(self, storage, sample_memory):
        """Test getting artifacts directory path."""
        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain

        storage.save_memory(sample_memory)

        artifacts_path = storage.get_artifacts_path(session_id, domain)
        assert artifacts_path.exists()
        assert artifacts_path.is_dir()

    def test_memory_persistence_cycle(self, storage, sample_memory):
        """Test full save/load cycle preserves data."""
        # Save
        storage.save_memory(sample_memory)

        # Load
        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain
        loaded = storage.load_memory(session_id, domain)

        # Verify all data preserved
        assert loaded.metadata.session_id == sample_memory.metadata.session_id
        assert loaded.metadata.description == sample_memory.metadata.description
        assert len(loaded.goals) == len(sample_memory.goals)
        assert len(loaded.progress_log) == len(sample_memory.progress_log)

        # Verify goal details
        assert loaded.goals[0].id == sample_memory.goals[0].id
        assert len(loaded.goals[0].features) == len(sample_memory.goals[0].features)

    def test_progress_log_file_format(self, storage, sample_memory):
        """Test that progress.log is human-readable."""
        storage.save_memory(sample_memory)

        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain
        progress_path = storage._get_progress_log_path(session_id, domain)

        # Read progress log
        content = progress_path.read_text()

        # Should contain session info
        assert session_id in content
        assert domain in content

        # Should contain progress entries
        assert "INITIALIZER" in content
        assert "Created session" in content

    def test_cleanup_old_backups(self, storage, sample_memory, temp_storage_dir):
        """Test that old backups are cleaned up."""
        session_id = sample_memory.metadata.session_id
        domain = sample_memory.metadata.domain

        # Create multiple backups manually
        storage.save_memory(sample_memory, create_backup=False)
        backups_dir = storage._get_backups_dir(session_id, domain)

        # Create 15 fake backups
        for i in range(15):
            backup_file = backups_dir / f"memory_2024010{i:02d}_120000.json"
            backup_file.write_text('{"test": "backup"}')

        # Run cleanup (keep 10)
        storage._cleanup_old_backups(backups_dir, keep=10)

        # Should only have 10 remaining
        remaining = list(backups_dir.glob("memory_*.json"))
        assert len(remaining) == 10

    def test_completion_percentage_in_session_list(self, storage):
        """Test that session list includes completion percentage."""
        metadata = MemoryMetadata(
            session_id="test_completion",
            domain="coding",
            description="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)

        goal = Goal(id="G1", description="Test")
        from mcp_client_for_ollama.memory.base_memory import FeatureStatus
        goal.features = [
            Feature(id="F1", description="F1", status=FeatureStatus.COMPLETED),
            Feature(id="F2", description="F2", status=FeatureStatus.PENDING),
        ]
        memory.goals = [goal]

        storage.save_memory(memory)

        sessions = storage.list_sessions(domain="coding")
        assert len(sessions) == 1
        assert sessions[0]["completion_percentage"] == 50.0
        assert sessions[0]["total_features"] == 2
        assert sessions[0]["completed_features"] == 1
