"""Tests for tool state persistence."""
import pytest
import json
import tempfile
from pathlib import Path

from mcp_client_for_ollama.config.tool_persistence import ToolStatePersistence


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def persistence(temp_config_dir):
    """Create ToolStatePersistence instance with temp directory"""
    return ToolStatePersistence(config_dir=temp_config_dir)


class TestToolStatePersistence:
    """Tests for ToolStatePersistence class"""

    def test_init_creates_config_dir(self, temp_config_dir):
        """Test that init creates config directory if it doesn't exist"""
        config_dir = Path(temp_config_dir) / 'subdir'
        persistence = ToolStatePersistence(config_dir=str(config_dir))

        # Config dir should be created when we access config
        persistence._ensure_config_exists()
        assert config_dir.exists()
        assert (config_dir / 'config.json').exists()

    def test_get_disabled_tools_empty(self, persistence):
        """Test getting disabled tools from empty config"""
        disabled = persistence.get_disabled_tools()
        assert disabled == set()

    def test_get_disabled_servers_empty(self, persistence):
        """Test getting disabled servers from empty config"""
        disabled = persistence.get_disabled_servers()
        assert disabled == set()

    def test_set_tool_enabled_disable(self, persistence):
        """Test disabling a tool"""
        success = persistence.set_tool_enabled('filesystem.write', False)
        assert success is True

        disabled = persistence.get_disabled_tools()
        assert 'filesystem.write' in disabled

    def test_set_tool_enabled_enable(self, persistence):
        """Test enabling a previously disabled tool"""
        # First disable
        persistence.set_tool_enabled('filesystem.write', False)
        assert 'filesystem.write' in persistence.get_disabled_tools()

        # Then enable
        success = persistence.set_tool_enabled('filesystem.write', True)
        assert success is True

        disabled = persistence.get_disabled_tools()
        assert 'filesystem.write' not in disabled

    def test_set_multiple_tools(self, persistence):
        """Test disabling multiple tools"""
        persistence.set_tool_enabled('filesystem.write', False)
        persistence.set_tool_enabled('obsidian.create', False)
        persistence.set_tool_enabled('git.commit', False)

        disabled = persistence.get_disabled_tools()
        assert disabled == {'filesystem.write', 'obsidian.create', 'git.commit'}

    def test_set_server_enabled_disable(self, persistence):
        """Test disabling a server"""
        success = persistence.set_server_enabled('obsidian', False)
        assert success is True

        disabled = persistence.get_disabled_servers()
        assert 'obsidian' in disabled

    def test_set_server_enabled_enable(self, persistence):
        """Test enabling a previously disabled server"""
        # First disable
        persistence.set_server_enabled('obsidian', False)
        assert 'obsidian' in persistence.get_disabled_servers()

        # Then enable
        success = persistence.set_server_enabled('obsidian', True)
        assert success is True

        disabled = persistence.get_disabled_servers()
        assert 'obsidian' not in disabled

    def test_set_multiple_servers(self, persistence):
        """Test disabling multiple servers"""
        persistence.set_server_enabled('git', False)
        persistence.set_server_enabled('slack', False)

        disabled = persistence.get_disabled_servers()
        assert disabled == {'git', 'slack'}

    def test_set_multiple_tools_enabled_bulk(self, persistence):
        """Test bulk enable/disable of tools"""
        tools = ['filesystem.read', 'filesystem.write', 'filesystem.delete']

        # Bulk disable
        success = persistence.set_multiple_tools_enabled(tools, False)
        assert success is True

        disabled = persistence.get_disabled_tools()
        assert all(tool in disabled for tool in tools)

        # Bulk enable
        success = persistence.set_multiple_tools_enabled(tools, True)
        assert success is True

        disabled = persistence.get_disabled_tools()
        assert all(tool not in disabled for tool in tools)

    def test_is_tool_enabled(self, persistence):
        """Test checking if tool is enabled"""
        # Initially enabled (not in disabled list)
        assert persistence.is_tool_enabled('filesystem.write') is True

        # Disable it
        persistence.set_tool_enabled('filesystem.write', False)
        assert persistence.is_tool_enabled('filesystem.write') is False

        # Enable it
        persistence.set_tool_enabled('filesystem.write', True)
        assert persistence.is_tool_enabled('filesystem.write') is True

    def test_is_server_enabled(self, persistence):
        """Test checking if server is enabled"""
        # Initially enabled (not in disabled list)
        assert persistence.is_server_enabled('obsidian') is True

        # Disable it
        persistence.set_server_enabled('obsidian', False)
        assert persistence.is_server_enabled('obsidian') is False

        # Enable it
        persistence.set_server_enabled('obsidian', True)
        assert persistence.is_server_enabled('obsidian') is True

    def test_clear_all_disabled_tools(self, persistence):
        """Test clearing all disabled tools"""
        # Disable some tools
        persistence.set_tool_enabled('filesystem.write', False)
        persistence.set_tool_enabled('obsidian.create', False)

        assert len(persistence.get_disabled_tools()) == 2

        # Clear all
        success = persistence.clear_all_disabled_tools()
        assert success is True

        assert len(persistence.get_disabled_tools()) == 0

    def test_clear_all_disabled_servers(self, persistence):
        """Test clearing all disabled servers"""
        # Disable some servers
        persistence.set_server_enabled('git', False)
        persistence.set_server_enabled('slack', False)

        assert len(persistence.get_disabled_servers()) == 2

        # Clear all
        success = persistence.clear_all_disabled_servers()
        assert success is True

        assert len(persistence.get_disabled_servers()) == 0

    def test_persistence_across_instances(self, temp_config_dir):
        """Test that settings persist across different instances"""
        # Create first instance and disable a tool
        persistence1 = ToolStatePersistence(config_dir=temp_config_dir)
        persistence1.set_tool_enabled('filesystem.write', False)

        # Create second instance and verify setting is persisted
        persistence2 = ToolStatePersistence(config_dir=temp_config_dir)
        disabled = persistence2.get_disabled_tools()
        assert 'filesystem.write' in disabled

    def test_config_file_format(self, persistence):
        """Test that config file has correct JSON format"""
        persistence.set_tool_enabled('filesystem.write', False)
        persistence.set_server_enabled('obsidian', False)

        # Read config file directly
        with open(persistence.config_file, 'r') as f:
            config = json.load(f)

        assert 'disabledTools' in config
        assert 'disabledServers' in config
        assert 'filesystem.write' in config['disabledTools']
        assert 'obsidian' in config['disabledServers']

        # Lists should be sorted
        assert config['disabledTools'] == sorted(config['disabledTools'])
        assert config['disabledServers'] == sorted(config['disabledServers'])

    def test_get_config_path(self, persistence):
        """Test getting config file path"""
        path = persistence.get_config_path()
        assert path.endswith('config.json')
        assert Path(path).parent.exists()

    def test_preserves_other_config_fields(self, persistence, temp_config_dir):
        """Test that tool persistence doesn't overwrite other config fields"""
        # Manually create config with other fields
        config_file = Path(temp_config_dir) / 'config.json'
        initial_config = {
            'mcpServers': {
                'filesystem': {'command': 'mcp-filesystem'}
            },
            'delegation': {
                'enabled': True
            }
        }
        with open(config_file, 'w') as f:
            json.dump(initial_config, f)

        # Use persistence to disable a tool
        persistence.set_tool_enabled('filesystem.write', False)

        # Read config and verify other fields are preserved
        with open(config_file, 'r') as f:
            config = json.load(f)

        assert config['mcpServers'] == initial_config['mcpServers']
        assert config['delegation'] == initial_config['delegation']
        assert 'disabledTools' in config
        assert 'filesystem.write' in config['disabledTools']

    def test_thread_safety(self, persistence):
        """Test that multiple concurrent operations don't corrupt config"""
        import threading

        def disable_tool(tool_name):
            persistence.set_tool_enabled(tool_name, False)

        # Create multiple threads disabling different tools
        tools = [f'tool{i}' for i in range(10)]
        threads = [threading.Thread(target=disable_tool, args=(tool,)) for tool in tools]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Verify all tools were disabled
        disabled = persistence.get_disabled_tools()
        assert len(disabled) == 10
        assert all(f'tool{i}' in disabled for i in range(10))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
