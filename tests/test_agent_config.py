"""Unit tests for AgentConfig class."""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from mcp_client_for_ollama.agents.agent_config import AgentConfig


class TestAgentConfig:
    """Tests for AgentConfig class."""

    @pytest.fixture
    def basic_config_data(self):
        """Basic valid agent configuration data."""
        return {
            "agent_type": "READER",
            "display_name": "File Reader",
            "description": "Reads and analyzes file contents",
            "system_prompt": "You are a file reader agent.",
            "default_tools": ["builtin.read_file", "builtin.list_files"]
        }

    @pytest.fixture
    def full_config_data(self):
        """Complete agent configuration data with all fields."""
        return {
            "agent_type": "CODER",
            "display_name": "Code Writer",
            "description": "Writes and modifies code files",
            "system_prompt": "You are a code writer agent.",
            "default_tools": ["builtin.read_file", "builtin.write_file"],
            "allowed_tool_categories": ["file_operations"],
            "forbidden_tools": ["builtin.execute_bash_command"],
            "max_context_tokens": 16384,
            "loop_limit": 3,
            "temperature": 0.7,
            "planning_hints": "Use CODER for writing code",
            "output_format": {"type": "code", "language": "python"}
        }

    @pytest.fixture
    def temp_definitions_dir(self, basic_config_data, full_config_data):
        """Create a temporary definitions directory with test agent files."""
        temp_dir = tempfile.mkdtemp()

        # Create basic config file
        reader_path = Path(temp_dir) / "reader.json"
        with open(reader_path, 'w') as f:
            json.dump(basic_config_data, f)

        # Create full config file
        coder_path = Path(temp_dir) / "coder.json"
        with open(coder_path, 'w') as f:
            json.dump(full_config_data, f)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_agent_config_creation_with_defaults(self):
        """Test creating AgentConfig with minimal required fields."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test Agent",
            description="Test description",
            system_prompt="Test prompt",
            default_tools=["tool1", "tool2"]
        )

        assert config.agent_type == "TEST"
        assert config.display_name == "Test Agent"
        assert config.description == "Test description"
        assert config.system_prompt == "Test prompt"
        assert config.default_tools == ["tool1", "tool2"]
        assert config.allowed_tool_categories == []
        assert config.forbidden_tools == []
        assert config.max_context_tokens == 8192
        assert config.loop_limit == 2
        assert config.temperature == 0.5
        assert config.planning_hints is None
        assert config.output_format is None

    def test_agent_config_creation_with_all_fields(self):
        """Test creating AgentConfig with all fields specified."""
        config = AgentConfig(
            agent_type="CUSTOM",
            display_name="Custom Agent",
            description="Custom description",
            system_prompt="Custom prompt",
            default_tools=["tool1"],
            allowed_tool_categories=["category1"],
            forbidden_tools=["bad_tool"],
            max_context_tokens=32000,
            loop_limit=5,
            temperature=0.9,
            planning_hints="Use for custom tasks",
            output_format={"type": "json"}
        )

        assert config.agent_type == "CUSTOM"
        assert config.allowed_tool_categories == ["category1"]
        assert config.forbidden_tools == ["bad_tool"]
        assert config.max_context_tokens == 32000
        assert config.loop_limit == 5
        assert config.temperature == 0.9
        assert config.planning_hints == "Use for custom tasks"
        assert config.output_format == {"type": "json"}

    def test_from_json_file_basic(self, basic_config_data):
        """Test loading agent config from JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(basic_config_data, f)
            temp_path = f.name

        try:
            config = AgentConfig.from_json_file(temp_path)

            assert config.agent_type == "READER"
            assert config.display_name == "File Reader"
            assert config.description == "Reads and analyzes file contents"
            assert config.system_prompt == "You are a file reader agent."
            assert config.default_tools == ["builtin.read_file", "builtin.list_files"]
            # Check defaults
            assert config.max_context_tokens == 8192
            assert config.loop_limit == 2
            assert config.temperature == 0.5
        finally:
            Path(temp_path).unlink()

    def test_from_json_file_full(self, full_config_data):
        """Test loading complete agent config from JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(full_config_data, f)
            temp_path = f.name

        try:
            config = AgentConfig.from_json_file(temp_path)

            assert config.agent_type == "CODER"
            assert config.display_name == "Code Writer"
            assert config.allowed_tool_categories == ["file_operations"]
            assert config.forbidden_tools == ["builtin.execute_bash_command"]
            assert config.max_context_tokens == 16384
            assert config.loop_limit == 3
            assert config.temperature == 0.7
            assert config.planning_hints == "Use CODER for writing code"
            assert config.output_format == {"type": "code", "language": "python"}
        finally:
            Path(temp_path).unlink()

    def test_from_json_file_missing_required_field(self):
        """Test that loading JSON with missing required fields raises KeyError."""
        incomplete_data = {
            "agent_type": "INCOMPLETE",
            "display_name": "Incomplete Agent"
            # Missing required fields
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(incomplete_data, f)
            temp_path = f.name

        try:
            with pytest.raises(KeyError):
                AgentConfig.from_json_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_from_json_file_invalid_json(self):
        """Test that loading invalid JSON raises JSONDecodeError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("This is not valid JSON{]")
            temp_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                AgentConfig.from_json_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_from_json_file_not_found(self):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            AgentConfig.from_json_file("/nonexistent/path/to/config.json")

    def test_load_all_definitions(self, temp_definitions_dir):
        """Test loading all agent definitions from directory."""
        configs = AgentConfig.load_all_definitions(temp_definitions_dir)

        assert len(configs) == 2
        assert "READER" in configs
        assert "CODER" in configs

        reader = configs["READER"]
        assert reader.display_name == "File Reader"
        assert reader.default_tools == ["builtin.read_file", "builtin.list_files"]

        coder = configs["CODER"]
        assert coder.display_name == "Code Writer"
        assert coder.max_context_tokens == 16384

    def test_load_all_definitions_default_path(self):
        """Test loading from default definitions directory."""
        # This should load actual agent definitions from the project
        configs = AgentConfig.load_all_definitions()

        # Should have at least the basic agent types
        assert len(configs) > 0
        # Check for known agent types (adjust based on actual definitions)
        assert "PLANNER" in configs or "READER" in configs

    def test_load_all_definitions_nonexistent_dir(self):
        """Test that loading from nonexistent directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            AgentConfig.load_all_definitions("/nonexistent/definitions")

    def test_load_all_definitions_with_invalid_file(self, temp_definitions_dir):
        """Test that invalid files are skipped with a warning."""
        # Create an invalid JSON file
        invalid_path = Path(temp_definitions_dir) / "invalid.json"
        with open(invalid_path, 'w') as f:
            f.write("Not valid JSON{]")

        # Should still load valid files and skip invalid one
        configs = AgentConfig.load_all_definitions(temp_definitions_dir)

        # Should have the 2 valid configs, invalid one skipped
        assert len(configs) == 2
        assert "READER" in configs
        assert "CODER" in configs

    def test_get_effective_tools_basic(self):
        """Test get_effective_tools with simple case."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test",
            description="Test",
            system_prompt="Test",
            default_tools=["tool1", "tool2", "tool3"]
        )

        available_tools = ["tool1", "tool2", "tool3", "tool4"]
        effective = config.get_effective_tools(available_tools)

        assert set(effective) == {"tool1", "tool2", "tool3"}

    def test_get_effective_tools_with_forbidden(self):
        """Test that forbidden tools are excluded."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test",
            description="Test",
            system_prompt="Test",
            default_tools=["tool1", "tool2", "tool3"],
            forbidden_tools=["tool2"]
        )

        available_tools = ["tool1", "tool2", "tool3", "tool4"]
        effective = config.get_effective_tools(available_tools)

        assert set(effective) == {"tool1", "tool3"}
        assert "tool2" not in effective

    def test_get_effective_tools_unavailable_filtered(self):
        """Test that unavailable tools are filtered out."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test",
            description="Test",
            system_prompt="Test",
            default_tools=["tool1", "tool2", "tool3"]
        )

        # Only tool1 and tool3 are available
        available_tools = ["tool1", "tool3"]
        effective = config.get_effective_tools(available_tools)

        assert set(effective) == {"tool1", "tool3"}
        assert "tool2" not in effective

    def test_get_effective_tools_empty_available(self):
        """Test get_effective_tools when no tools are available."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test",
            description="Test",
            system_prompt="Test",
            default_tools=["tool1", "tool2"]
        )

        effective = config.get_effective_tools([])
        assert effective == []

    def test_get_effective_tools_empty_default(self):
        """Test get_effective_tools when agent has no default tools."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test",
            description="Test",
            system_prompt="Test",
            default_tools=[]
        )

        available_tools = ["tool1", "tool2"]
        effective = config.get_effective_tools(available_tools)
        assert effective == []

    def test_matches_tool_category_no_restrictions(self):
        """Test that agents with no category restrictions match all tools."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test",
            description="Test",
            system_prompt="Test",
            default_tools=[],
            allowed_tool_categories=[]
        )

        tool_categories = {
            "file_ops": ["read", "write"],
            "execution": ["bash", "python"]
        }

        assert config.matches_tool_category("read", tool_categories) is True
        assert config.matches_tool_category("bash", tool_categories) is True
        assert config.matches_tool_category("unknown", tool_categories) is True

    def test_matches_tool_category_with_restrictions(self):
        """Test tool category matching with restrictions."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test",
            description="Test",
            system_prompt="Test",
            default_tools=[],
            allowed_tool_categories=["file_ops"]
        )

        tool_categories = {
            "file_ops": ["read", "write"],
            "execution": ["bash", "python"]
        }

        # Should match tools in allowed category
        assert config.matches_tool_category("read", tool_categories) is True
        assert config.matches_tool_category("write", tool_categories) is True

        # Should not match tools in other categories
        assert config.matches_tool_category("bash", tool_categories) is False
        assert config.matches_tool_category("python", tool_categories) is False

    def test_matches_tool_category_multiple_allowed(self):
        """Test tool category matching with multiple allowed categories."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test",
            description="Test",
            system_prompt="Test",
            default_tools=[],
            allowed_tool_categories=["file_ops", "execution"]
        )

        tool_categories = {
            "file_ops": ["read", "write"],
            "execution": ["bash", "python"],
            "network": ["fetch", "post"]
        }

        # Should match tools in any allowed category
        assert config.matches_tool_category("read", tool_categories) is True
        assert config.matches_tool_category("bash", tool_categories) is True

        # Should not match tools in disallowed categories
        assert config.matches_tool_category("fetch", tool_categories) is False

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = AgentConfig(
            agent_type="TEST",
            display_name="Test Agent",
            description="Test description",
            system_prompt="Test prompt",
            default_tools=["tool1", "tool2"],
            allowed_tool_categories=["cat1"],
            forbidden_tools=["bad_tool"],
            max_context_tokens=16000,
            loop_limit=3,
            temperature=0.8,
            planning_hints="Test hints",
            output_format={"type": "test"}
        )

        config_dict = config.to_dict()

        assert config_dict["agent_type"] == "TEST"
        assert config_dict["display_name"] == "Test Agent"
        assert config_dict["description"] == "Test description"
        assert config_dict["system_prompt"] == "Test prompt"
        assert config_dict["default_tools"] == ["tool1", "tool2"]
        assert config_dict["allowed_tool_categories"] == ["cat1"]
        assert config_dict["forbidden_tools"] == ["bad_tool"]
        assert config_dict["max_context_tokens"] == 16000
        assert config_dict["loop_limit"] == 3
        assert config_dict["temperature"] == 0.8
        assert config_dict["planning_hints"] == "Test hints"
        assert config_dict["output_format"] == {"type": "test"}

    def test_repr(self):
        """Test string representation."""
        config = AgentConfig(
            agent_type="READER",
            display_name="File Reader",
            description="Reads files",
            system_prompt="You read files",
            default_tools=["read", "list"],
            max_context_tokens=16384
        )

        repr_str = repr(config)

        assert "AgentConfig(" in repr_str
        assert "agent_type=READER" in repr_str
        assert "display_name=File Reader" in repr_str
        assert "tools=2" in repr_str
        assert "max_tokens=16384" in repr_str
