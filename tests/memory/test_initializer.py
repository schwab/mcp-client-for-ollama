"""Tests for memory initializer."""

import pytest
import tempfile
import shutil
from pathlib import Path

from mcp_client_for_ollama.memory.initializer import (
    MemoryInitializer,
    InitializerPromptBuilder,
)
from mcp_client_for_ollama.memory.storage import MemoryStorage
from mcp_client_for_ollama.memory.base_memory import FeatureStatus, GoalStatus


class TestMemoryInitializer:
    """Tests for MemoryInitializer class."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for storage tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def storage(self, temp_storage_dir):
        """Create a MemoryStorage instance with temp directory."""
        return MemoryStorage(base_dir=temp_storage_dir)

    @pytest.fixture
    def initializer(self, storage):
        """Create a MemoryInitializer instance."""
        return MemoryInitializer(storage)

    @pytest.fixture
    def sample_initializer_output(self):
        """Sample output from INITIALIZER agent."""
        return {
            "domain": "coding",
            "session_description": "Implement JWT authentication system",
            "goals": [
                {
                    "id": "G1",
                    "description": "Build authentication endpoints",
                    "constraints": [
                        "Use bcrypt for password hashing",
                        "JWT tokens expire in 24 hours"
                    ],
                    "features": [
                        {
                            "id": "F1",
                            "description": "POST /api/login endpoint",
                            "criteria": [
                                "Accepts username and password",
                                "Returns JWT on success",
                                "Returns 401 on failure"
                            ],
                            "tests": [
                                "test_login_success",
                                "test_login_failure"
                            ],
                            "priority": "high"
                        },
                        {
                            "id": "F2",
                            "description": "Password hashing with bcrypt",
                            "criteria": [
                                "Passwords never stored in plaintext",
                                "Hash verification works correctly"
                            ],
                            "tests": [
                                "test_password_hashing",
                                "test_password_verification"
                            ],
                            "priority": "high"
                        }
                    ]
                }
            ],
            "state": {
                "test_harness": {
                    "framework": "pytest",
                    "test_dirs": ["tests/"],
                    "run_command": "pytest -v"
                },
                "scaffolding": {
                    "language": "python",
                    "required_files": ["README.md", "requirements.txt"]
                }
            },
            "initial_artifacts": {
                "README.md": "# Auth System\n\nJWT-based authentication"
            }
        }

    def test_create_session_id(self, initializer):
        """Test session ID generation."""
        session_id = initializer.create_session_id()
        assert session_id.startswith("session_")
        assert len(session_id) > 8

        # With prefix
        session_id_with_prefix = initializer.create_session_id(prefix="coding")
        assert session_id_with_prefix.startswith("coding_")

    def test_bootstrap_from_json(self, initializer, sample_initializer_output):
        """Test creating DomainMemory from INITIALIZER output."""
        memory = initializer.bootstrap_from_json(sample_initializer_output)

        # Check metadata
        assert memory.metadata.domain == "coding"
        assert "authentication" in memory.metadata.description.lower()

        # Check goals and features
        assert len(memory.goals) == 1
        assert memory.goals[0].id == "G1"
        assert len(memory.goals[0].features) == 2

        # Check features
        f1 = memory.goals[0].features[0]
        assert f1.id == "F1"
        assert f1.status == FeatureStatus.PENDING
        assert len(f1.criteria) == 3
        assert len(f1.tests) == 2

        # Check state
        assert "test_harness" in memory.state
        assert memory.state["test_harness"]["framework"] == "pytest"

        # Check progress log
        assert len(memory.progress_log) == 1
        assert memory.progress_log[0].agent_type == "INITIALIZER"

    def test_bootstrap_with_custom_session_id(self, initializer, sample_initializer_output):
        """Test bootstrapping with custom session ID."""
        custom_id = "my_custom_session"
        memory = initializer.bootstrap_from_json(
            sample_initializer_output,
            session_id=custom_id
        )

        assert memory.metadata.session_id == custom_id

    def test_bootstrap_missing_domain(self, initializer):
        """Test bootstrapping with missing domain field."""
        invalid_output = {"goals": []}

        with pytest.raises(ValueError, match="Missing required field: 'domain'"):
            initializer.bootstrap_from_json(invalid_output)

    def test_bootstrap_missing_goals(self, initializer):
        """Test bootstrapping with missing goals field."""
        invalid_output = {"domain": "coding"}

        with pytest.raises(ValueError, match="Missing required field: 'goals'"):
            initializer.bootstrap_from_json(invalid_output)

    def test_initialize_state_coding_domain(self, initializer):
        """Test state initialization for coding domain."""
        state = initializer._initialize_state("coding", {})

        assert "test_harness" in state
        assert "scaffolding" in state
        assert state["test_harness"]["framework"] == "pytest"

    def test_initialize_state_research_domain(self, initializer):
        """Test state initialization for research domain."""
        state = initializer._initialize_state("research", {})

        assert "hypothesis_tracking" in state
        assert "experiment_registry" in state

    def test_initialize_state_custom_merge(self, initializer):
        """Test state initialization with custom overrides."""
        custom_state = {
            "test_harness": {
                "framework": "unittest"  # Override default
            },
            "custom_field": "custom_value"
        }

        state = initializer._initialize_state("coding", custom_state)

        # Should merge, not replace
        assert state["test_harness"]["framework"] == "unittest"
        assert "test_dirs" in state["test_harness"]  # Default preserved
        assert state["custom_field"] == "custom_value"

    def test_create_initial_artifacts(self, initializer, storage, sample_initializer_output):
        """Test creation of initial artifact files."""
        memory = initializer.bootstrap_from_json(sample_initializer_output)

        # Artifacts should be tracked
        assert "README.md" in memory.artifacts

        # Check file exists
        artifacts_dir = storage.get_artifacts_path(
            memory.metadata.session_id,
            memory.metadata.domain
        )
        readme_path = artifacts_dir / "README.md"
        assert readme_path.exists()

        # Check content
        content = readme_path.read_text()
        assert "Auth System" in content

    def test_initialize_and_save(self, initializer, storage, sample_initializer_output):
        """Test full initialization and persistence."""
        memory = initializer.initialize_and_save(sample_initializer_output)

        # Should be saved to disk
        assert storage.session_exists(
            memory.metadata.session_id,
            memory.metadata.domain
        )

        # Should be loadable
        loaded = storage.load_memory(
            memory.metadata.session_id,
            memory.metadata.domain
        )
        assert loaded is not None
        assert loaded.metadata.session_id == memory.metadata.session_id


class TestInitializerPromptBuilder:
    """Tests for InitializerPromptBuilder class."""

    def test_build_basic_prompt(self):
        """Test building a basic prompt."""
        prompt = InitializerPromptBuilder.build_prompt(
            user_query="Build a login system",
            domain="coding"
        )

        assert "Domain: coding" in prompt
        assert "Build a login system" in prompt
        assert "User Request:" in prompt

    def test_build_prompt_with_context(self):
        """Test building prompt with additional context."""
        context = {
            "existing_files": ["main.py", "utils.py"],
            "constraints": ["Must use Python 3.10+"],
            "preferences": {"test_framework": "pytest"}
        }

        prompt = InitializerPromptBuilder.build_prompt(
            user_query="Add authentication",
            domain="coding",
            context=context
        )

        assert "Existing Files:" in prompt
        assert "main.py" in prompt
        assert "Constraints:" in prompt
        assert "Python 3.10+" in prompt
        assert "Preferences:" in prompt
        assert "pytest" in prompt

    def test_get_domain_guidance_coding(self):
        """Test domain guidance for coding."""
        guidance = InitializerPromptBuilder._get_domain_guidance("coding")

        assert "programming language" in guidance.lower()
        assert "test" in guidance.lower()

    def test_get_domain_guidance_research(self):
        """Test domain guidance for research."""
        guidance = InitializerPromptBuilder._get_domain_guidance("research")

        assert "hypothes" in guidance.lower()
        assert "experiment" in guidance.lower()

    def test_get_domain_guidance_unknown(self):
        """Test domain guidance for unknown domain."""
        guidance = InitializerPromptBuilder._get_domain_guidance("unknown_domain")

        assert guidance == ""

    def test_parse_initializer_response_valid_json(self):
        """Test parsing valid JSON response."""
        response = '{"domain": "coding", "goals": []}'
        parsed = InitializerPromptBuilder.parse_initializer_response(response)

        assert parsed["domain"] == "coding"
        assert parsed["goals"] == []

    def test_parse_initializer_response_with_code_fence(self):
        """Test parsing JSON wrapped in code fence."""
        response = '```json\n{"domain": "coding", "goals": []}\n```'
        parsed = InitializerPromptBuilder.parse_initializer_response(response)

        assert parsed["domain"] == "coding"

    def test_parse_initializer_response_invalid_json(self):
        """Test parsing invalid JSON."""
        response = 'not valid json'

        with pytest.raises(ValueError, match="Invalid JSON response"):
            InitializerPromptBuilder.parse_initializer_response(response)

    def test_parse_initializer_response_with_markdown(self):
        """Test parsing JSON with markdown fence (common LLM output)."""
        response = '```\n{"domain": "research", "goals": []}\n```'
        parsed = InitializerPromptBuilder.parse_initializer_response(response)

        assert parsed["domain"] == "research"


class TestEndToEndInitialization:
    """End-to-end tests for memory initialization workflow."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for storage tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def setup(self, temp_storage_dir):
        """Set up storage and initializer."""
        storage = MemoryStorage(base_dir=temp_storage_dir)
        initializer = MemoryInitializer(storage)
        return storage, initializer

    def test_full_initialization_workflow(self, setup):
        """Test complete workflow from INITIALIZER output to persisted memory."""
        storage, initializer = setup

        # Simulate INITIALIZER output
        initializer_output = {
            "domain": "coding",
            "session_description": "Build REST API",
            "goals": [
                {
                    "id": "G1",
                    "description": "Create API endpoints",
                    "constraints": [],
                    "features": [
                        {
                            "id": "F1",
                            "description": "GET /api/users endpoint",
                            "criteria": ["Returns list of users", "Returns 200 status"],
                            "tests": ["test_get_users"],
                            "priority": "high"
                        }
                    ]
                }
            ],
            "state": {},
            "initial_artifacts": {
                "README.md": "# API Project"
            }
        }

        # Initialize and save
        memory = initializer.initialize_and_save(initializer_output)

        # Verify it was saved
        assert storage.session_exists(memory.metadata.session_id, "coding")

        # Load and verify
        loaded = storage.load_memory(memory.metadata.session_id, "coding")
        assert loaded.metadata.description == "Build REST API"
        assert len(loaded.goals) == 1
        assert len(loaded.goals[0].features) == 1

        # Verify artifacts were created
        artifacts_dir = storage.get_artifacts_path(memory.metadata.session_id, "coding")
        assert (artifacts_dir / "README.md").exists()

        # Verify progress log
        assert len(loaded.progress_log) == 1
        assert loaded.progress_log[0].agent_type == "INITIALIZER"

    def test_resume_workflow(self, setup):
        """Test resuming an existing session."""
        storage, initializer = setup

        # Create initial session
        output1 = {
            "domain": "research",
            "session_description": "Study hypothesis X",
            "goals": [],
            "state": {},
            "initial_artifacts": {}
        }
        memory1 = initializer.initialize_and_save(output1, session_id="test_session_123")

        # Verify we can resume
        resumed_memory, is_new = initializer.resume_or_create(
            user_query="Continue research",
            session_id="test_session_123",
            domain="research"
        )

        assert not is_new
        assert resumed_memory.metadata.session_id == "test_session_123"
        assert resumed_memory.metadata.description == "Study hypothesis X"

    def test_new_session_workflow(self, setup):
        """Test creating a new session when none exists."""
        storage, initializer = setup

        # Try to resume non-existent session
        memory, is_new = initializer.resume_or_create(
            user_query="New task",
            session_id="nonexistent",
            domain="coding"
        )

        assert is_new
        assert memory.metadata.session_id is not None
        # Note: Memory is placeholder, not yet initialized by INITIALIZER agent
        assert len(memory.goals) == 0  # No goals yet
