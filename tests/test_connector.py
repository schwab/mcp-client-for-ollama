"""Test server connector functionality."""

from mcp_client_for_ollama.server.connector import ServerConnector
from mcp_client_for_ollama.utils.constants import MCP_PROTOCOL_VERSION
from contextlib import AsyncExitStack
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


def test_get_headers_from_server_sse():
    """Test that headers are correctly extracted and formatted for SSE servers."""
    connector = ServerConnector(AsyncExitStack())

    # Test SSE server with no custom headers
    server = {
        "name": "test-sse",
        "type": "sse",
        "url": "http://localhost:8000/sse"
    }

    headers = connector._get_headers_from_server(server)

    # Verify MCP Protocol Version header is added with lowercase key
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION

    # Verify no uppercase version exists
    assert "MCP-Protocol-Version" not in headers


def test_get_headers_from_server_streamable_http():
    """Test that headers are correctly extracted and formatted for Streamable HTTP servers."""
    connector = ServerConnector(AsyncExitStack())

    # Test Streamable HTTP server with no custom headers
    server = {
        "name": "test-http",
        "type": "streamable_http",
        "url": "http://localhost:8000/mcp"
    }

    headers = connector._get_headers_from_server(server)

    # Verify MCP Protocol Version header is added with lowercase key
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION

    # Verify no uppercase version exists
    assert "MCP-Protocol-Version" not in headers


def test_get_headers_from_server_with_custom_headers():
    """Test that custom headers are normalized to lowercase and protocol header is added."""
    connector = ServerConnector(AsyncExitStack())

    # Test server with custom headers (mixed case)
    server = {
        "name": "test-server",
        "type": "sse",
        "url": "http://localhost:8000/sse",
        "headers": {
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value"
        }
    }

    headers = connector._get_headers_from_server(server)

    # Verify custom headers are normalized to lowercase
    assert headers["authorization"] == "Bearer token123"
    assert headers["x-custom-header"] == "custom-value"

    # Verify uppercase keys don't exist
    assert "Authorization" not in headers
    assert "X-Custom-Header" not in headers

    # Verify MCP Protocol Version header is added with lowercase key
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION

    # Verify no uppercase version exists
    assert "MCP-Protocol-Version" not in headers


def test_get_headers_from_server_with_config():
    """Test that headers are extracted from config subdict and normalized to lowercase."""
    connector = ServerConnector(AsyncExitStack())

    # Test server with headers in config subdict
    server = {
        "name": "test-server",
        "type": "streamable_http",
        "config": {
            "url": "http://localhost:8000/mcp",
            "headers": {
                "X-API-Key": "secret-key"
            }
        }
    }

    headers = connector._get_headers_from_server(server)

    # Verify headers from config are normalized to lowercase
    assert headers["x-api-key"] == "secret-key"
    assert "X-API-Key" not in headers

    # Verify MCP Protocol Version header is added with lowercase key
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION


def test_get_headers_from_server_script_type():
    """Test that script-type servers don't get the MCP protocol header."""
    connector = ServerConnector(AsyncExitStack())

    # Test script server (should not add protocol header)
    server = {
        "name": "test-script",
        "type": "script",
        "path": "/path/to/server.py"
    }

    headers = connector._get_headers_from_server(server)

    # Verify MCP Protocol Version header is NOT added for script type
    assert "mcp-protocol-version" not in headers
    assert "MCP-Protocol-Version" not in headers


def test_get_headers_no_duplicate_protocol_version():
    """Test that we don't create duplicate protocol version headers and normalize to lowercase."""
    connector = ServerConnector(AsyncExitStack())

    # Test server with uppercase protocol header in custom headers
    server = {
        "name": "test-server",
        "type": "sse",
        "url": "http://localhost:8000/sse",
        "headers": {
            "MCP-Protocol-Version": "old-version",
            "Authorization": "Bearer token"
        }
    }

    headers = connector._get_headers_from_server(server)

    # All headers should be lowercase
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION
    assert headers["authorization"] == "Bearer token"

    # No uppercase headers should exist
    assert "MCP-Protocol-Version" not in headers
    assert "Authorization" not in headers


def test_header_case_normalization():
    """Test that headers with different cases get normalized and don't create duplicates."""
    connector = ServerConnector(AsyncExitStack())

    # Test server with headers in various cases
    server = {
        "name": "test-server",
        "type": "sse",
        "url": "http://localhost:8000/sse",
        "headers": {
            "Content-Type": "application/json",
            "content-type": "text/plain",  # This should overwrite the above
            "Authorization": "Bearer token1",
            "AUTHORIZATION": "Bearer token2",  # This should overwrite the above
        }
    }

    headers = connector._get_headers_from_server(server)

    # All headers should be lowercase and only one value per header name
    assert "content-type" in headers
    assert "Content-Type" not in headers
    assert "authorization" in headers
    assert "Authorization" not in headers
    assert "AUTHORIZATION" not in headers

    # Should have exactly 3 headers: content-type, authorization, mcp-protocol-version
    assert len(headers) == 3
    assert "mcp-protocol-version" in headers


def test_get_url_from_server():
    """Test URL extraction from server configuration."""
    connector = ServerConnector(AsyncExitStack())

    # Test URL directly in server dict
    server = {
        "name": "test-server",
        "url": "http://localhost:8000/sse"
    }
    assert connector._get_url_from_server(server) == "http://localhost:8000/sse"

    # Test URL in config subdict
    server = {
        "name": "test-server",
        "config": {
            "url": "http://localhost:9000/mcp"
        }
    }
    assert connector._get_url_from_server(server) == "http://localhost:9000/mcp"

    # Test no URL
    server = {
        "name": "test-server"
    }
    assert connector._get_url_from_server(server) is None


@pytest.mark.asyncio
async def test_connect_to_servers_with_system_prompt_from_config(tmp_path):
    """Test that connect_to_servers correctly extracts and stores system_prompt from config."""
    connector = ServerConnector(AsyncExitStack())

    # Create a dummy config file
    config_content = {
        "systemPrompt": "You are a helpful AI from config.",
        "mcpServers": {
            "test_server": {
                "type": "script",
                "command": "python",
                "args": ["server.py"]
            }
        }
    }
    config_path = tmp_path / "test_servers.json"
    with open(config_path, 'w') as f:
        json.dump(config_content, f)

    # Mock parse_server_configs to return our dummy data
    with patch('mcp_client_for_ollama.server.connector.parse_server_configs') as mock_parse_server_configs:
        mock_parse_server_configs.return_value = (
            [
                {
                    "type": "script",
                    "name": "test_server",
                    "config": {
                        "command": "python",
                        "args": ["server.py"]
                    }
                }
            ],
            "You are a helpful AI from config."
        )
        
        # Mock _connect_to_server to prevent actual connection attempts and simulate session addition
        with patch.object(connector, '_connect_to_server', new_callable=AsyncMock) as mock_connect_to_server:
            # Configure the mock to add a dummy session to connector.sessions
            def side_effect_connect_to_server(server_config):
                connector.sessions[server_config["name"]] = {"session": MagicMock(), "tools": []}
                connector.available_tools.append(MagicMock(name=f"{server_config['name']}.dummy_tool"))
                connector.enabled_tools[f"{server_config['name']}.dummy_tool"] = True
                return True
            mock_connect_to_server.side_effect = side_effect_connect_to_server

            sessions, available_tools, enabled_tools, system_prompt = await connector.connect_to_servers(
                config_path=str(config_path)
            )

            assert system_prompt == "You are a helpful AI from config."
            assert connector.system_prompt_from_config == "You are a helpful AI from config."
            assert len(sessions) == 1
            assert "test_server" in sessions
            assert len(available_tools) == 1
            assert "test_server.dummy_tool" in enabled_tools
            mock_parse_server_configs.assert_called_once_with(str(config_path))
            mock_connect_to_server.assert_called_once()

@pytest.mark.asyncio
async def test_connect_to_servers_without_system_prompt_from_config(tmp_path):
    """Test that connect_to_servers handles missing system_prompt from config."""
    connector = ServerConnector(AsyncExitStack())

    # Create a dummy config file without systemPrompt
    config_content = {
        "mcpServers": {
            "test_server": {
                "type": "script",
                "command": "python",
                "args": ["server.py"]
            }
        }
    }
    config_path = tmp_path / "test_servers_no_sp.json"
    with open(config_path, 'w') as f:
        json.dump(config_content, f)

    # Mock parse_server_configs to return our dummy data without system_prompt
    with patch('mcp_client_for_ollama.server.connector.parse_server_configs') as mock_parse_server_configs:
        mock_parse_server_configs.return_value = (
            [
                {
                    "type": "script",
                    "name": "test_server",
                    "config": {
                        "command": "python",
                        "args": ["server.py"]
                    }
                }
            ],
            None  # No system prompt
        )

        # Mock _connect_to_server to prevent actual connection attempts and simulate session addition
        with patch.object(connector, '_connect_to_server', new_callable=AsyncMock) as mock_connect_to_server:
            # Configure the mock to add a dummy session to connector.sessions
            def side_effect_connect_to_server(server_config):
                connector.sessions[server_config["name"]] = {"session": MagicMock(), "tools": []}
                connector.available_tools.append(MagicMock(name=f"{server_config['name']}.dummy_tool"))
                connector.enabled_tools[f"{server_config['name']}.dummy_tool"] = True
                return True
            mock_connect_to_server.side_effect = side_effect_connect_to_server

            sessions, available_tools, enabled_tools, system_prompt = await connector.connect_to_servers(
                config_path=str(config_path)
            )

            assert system_prompt is None
            assert connector.system_prompt_from_config is None
            assert len(sessions) == 1
            assert "test_server" in sessions
            assert len(available_tools) == 1
            assert "test_server.dummy_tool" in enabled_tools
            mock_parse_server_configs.assert_called_once_with(str(config_path))
            mock_connect_to_server.assert_called_once()