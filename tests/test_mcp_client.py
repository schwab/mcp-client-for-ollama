import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import AsyncExitStack

from mcp_client_for_ollama.client import MCPClient
from mcp_client_for_ollama.server.connector import ServerConnector
from mcp_client_for_ollama.models.config_manager import ModelConfigManager

@pytest.mark.asyncio
async def test_system_prompt_loaded_from_servers_json():
    """
    Test that the system prompt is correctly loaded from servers-json
    via ServerConnector and set in ModelConfigManager.
    """
    # Mock ServerConnector.connect_to_servers to return a system_prompt
    with patch.object(ServerConnector, 'connect_to_servers', new_callable=AsyncMock) as mock_connect_to_servers:
        mock_connect_to_servers.return_value = (
            {},  # sessions
            [],  # available_tools
            {},  # enabled_tools
            "You are a test AI from config." # system_prompt_from_config
        )

        # Instantiate MCPClient
        client = MCPClient()
        
        # Ensure initial system prompt is empty
        assert client.model_config_manager.get_system_prompt() == ""

        # Call connect_to_servers, which should trigger the system prompt loading
        await client.connect_to_servers(config_path="dummy_path.json")

        # Assert that the system prompt in ModelConfigManager is updated
        assert client.model_config_manager.get_system_prompt() == "You are a test AI from config."
        
        # Verify connect_to_servers was called
        mock_connect_to_servers.assert_called_once_with(
            server_paths=None,
            server_urls=None,
            config_path="dummy_path.json",
            auto_discovery=False
        )

@pytest.mark.asyncio
async def test_system_prompt_not_loaded_if_none_in_servers_json():
    """
    Test that the system prompt remains empty if no system_prompt is provided in servers-json.
    """
    # Mock ServerConnector.connect_to_servers to return None for system_prompt
    with patch.object(ServerConnector, 'connect_to_servers', new_callable=AsyncMock) as mock_connect_to_servers:
        mock_connect_to_servers.return_value = (
            {},  # sessions
            [],  # available_tools
            {},  # enabled_tools
            None # system_prompt_from_config
        )

        # Instantiate MCPClient
        client = MCPClient()
        
        # Ensure initial system prompt is empty
        assert client.model_config_manager.get_system_prompt() == ""

        # Call connect_to_servers
        await client.connect_to_servers(config_path="dummy_path.json")

        # Assert that the system prompt in ModelConfigManager is still empty
        assert client.model_config_manager.get_system_prompt() == ""
        
        # Verify connect_to_servers was called
        mock_connect_to_servers.assert_called_once_with(
            server_paths=None,
            server_urls=None,
            config_path="dummy_path.json",
            auto_discovery=False
        )
