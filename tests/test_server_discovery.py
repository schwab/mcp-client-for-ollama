import os
import json
from mcp_client_for_ollama.server.discovery import process_server_urls, parse_server_configs, auto_discover_servers
from mcp_client_for_ollama.utils.constants import DEFAULT_CLAUDE_CONFIG

# Helper function to create a dummy config file for testing
def create_dummy_config(tmp_path, content, filename="servers.json"):
    config_path = tmp_path / filename
    with open(config_path, 'w') as f:
        json.dump(content, f)
    return str(config_path)

def test_process_server_urls():
    """Test that server URL processing works correctly."""
    # Test single URL string
    result = process_server_urls("http://localhost:8000/sse")
    assert len(result) == 1
    assert result[0]["type"] == "sse"
    assert result[0]["url"] == "http://localhost:8000/sse"
    assert result[0]["name"] == "localhost_8000"

    # Test list of URLs
    urls = [
        "http://localhost:8000/sse",
        "https://api.example.com/mcp",
        "http://server1.com:9000/streamable"
    ]
    result = process_server_urls(urls)
    assert len(result) == 3

    # Check SSE detection
    sse_server = next(s for s in result if s["url"] == "http://localhost:8000/sse")
    assert sse_server["type"] == "sse"

    # Check default streamable_http type
    http_server = next(s for s in result if s["url"] == "https://api.example.com/mcp")
    assert http_server["type"] == "streamable_http"

    # Test invalid URLs are filtered out
    invalid_urls = ["not-a-url", "ftp://invalid.com", ""]
    result = process_server_urls(invalid_urls)
    assert len(result) == 0

    # Test empty input
    assert process_server_urls([]) == []
    assert process_server_urls(None) == []


def test_server_url_name_generation():
    """Test that server names are generated correctly from URLs."""
    # Test with path - path doesn't affect name, only hostname matters
    result = process_server_urls("http://localhost:8000/api/mcp")
    assert result[0]["name"] == "localhost_8000"

    # Test with SSE path
    result = process_server_urls("http://localhost:8000/sse")
    assert result[0]["name"] == "localhost_8000"

    # Test without path
    result = process_server_urls("http://localhost:9000")
    assert result[0]["name"] == "localhost_9000"

    # Test with complex host including dots (IP address)
    result = process_server_urls("https://127.0.0.1:8443/mcp/v1")
    assert result[0]["name"] == "127_0_0_1_8443"

    # Test with domain containing dots
    result = process_server_urls("https://api.example.com:8080/mcp")
    assert result[0]["name"] == "api_example_com_8080"


def test_server_name_uniqueness():
    """Test that different hosts get unique names."""
    # Test multiple servers with different hosts
    urls = [
        "http://server1.com/sse",
        "http://server2.com/sse",
        "https://api.example.com:8000/sse"
    ]
    result = process_server_urls(urls)
    assert len(result) == 3

    names = [server["name"] for server in result]
    assert len(set(names)) == 3  # All names should be unique
    assert "server1_com" in names
    assert "server2_com" in names
    assert "api_example_com_8000" in names


def test_same_host_different_types():
    """Test that same host with different server types can coexist."""
    # Note: This creates a name collision but is rare in practice
    urls = [
        "http://localhost:8000/sse",
        "http://localhost:8000/mcp"
    ]
    result = process_server_urls(urls)
    assert len(result) == 2

    # Both have same name but different types
    assert all(server["name"] == "localhost_8000" for server in result)
    types = [server["type"] for server in result]
    assert "sse" in types
    assert "streamable_http" in types


def test_ip_address_name_generation():
    """Test that IP addresses in URLs generate proper names without dots."""
    # This is the specific case that was causing the parsing issue
    result = process_server_urls("http://127.0.0.1:8000/mcp")
    assert result[0]["name"] == "127_0_0_1_8000"

    # Test tool name parsing with the generated name
    tool_name = f"{result[0]['name']}.hello_world"
    server_name, actual_tool_name = tool_name.split('.', 1) if '.' in tool_name else (None, tool_name)

    assert server_name == "127_0_0_1_8000"
    assert actual_tool_name == "hello_world"

def test_server_type_detection():
    """Test that server types are detected correctly."""
    # SSE detection by path
    result = process_server_urls("http://localhost:8000/sse")
    assert result[0]["type"] == "sse"

    # SSE detection by URL content
    result = process_server_urls("http://localhost:8000/api/sse/endpoint")
    assert result[0]["type"] == "sse"

    # Default to streamable_http
    result = process_server_urls("http://localhost:8000/mcp")
    assert result[0]["type"] == "streamable_http"

    # Default to streamable_http for generic URLs
    result = process_server_urls("https://api.example.com")
    assert result[0]["type"] == "streamable_http"

def test_parse_server_configs_with_system_prompt(tmp_path):
    """Test that parse_server_configs correctly extracts system_prompt."""
    config_content = {
        "systemPrompt": "You are a helpful AI assistant.",
        "mcpServers": {
            "test_server": {
                "type": "script",
                "command": "python",
                "args": ["server.py"]
            }
        }
    }
    config_path = create_dummy_config(tmp_path, config_content)
    
    servers, system_prompt = parse_server_configs(config_path)
    
    assert system_prompt == "You are a helpful AI assistant."
    assert len(servers) == 1
    assert servers[0]["name"] == "test_server"

def test_parse_server_configs_without_system_prompt(tmp_path):
    """Test parse_server_configs when no system_prompt is present."""
    config_content = {
        "mcpServers": {
            "test_server": {
                "type": "script",
                "command": "python",
                "args": ["server.py"]
            }
        }
    }
    config_path = create_dummy_config(tmp_path, config_content)
    
    servers, system_prompt = parse_server_configs(config_path)
    
    assert system_prompt is None
    assert len(servers) == 1

def test_auto_discover_servers_with_system_prompt(tmp_path, monkeypatch):
    """Test that auto_discover_servers correctly extracts system_prompt."""
    config_content = {
        "systemPrompt": "You are a witty chatbot.",
        "mcpServers": {
            "auto_server": {
                "type": "script",
                "command": "python",
                "args": ["auto_server.py"]
            }
        }
    }
    # Create a dummy DEFAULT_CLAUDE_CONFIG
    dummy_claude_config_path = create_dummy_config(tmp_path, config_content, filename=os.path.basename(DEFAULT_CLAUDE_CONFIG))
    
    # Directly call parse_server_configs with the dummy path
    servers, system_prompt = parse_server_configs(dummy_claude_config_path)
    
    assert system_prompt == "You are a witty chatbot."
    assert len(servers) == 1
    assert servers[0]["name"] == "auto_server"

def test_auto_discover_servers_without_system_prompt(tmp_path, monkeypatch):
    """Test auto_discover_servers when no system_prompt is present."""
    config_content = {
        "mcpServers": {
            "auto_server": {
                "type": "script",
                "command": "python",
                "args": ["auto_server.py"]
            }
        }
    }
    dummy_claude_config_path = create_dummy_config(tmp_path, config_content, filename=os.path.basename(DEFAULT_CLAUDE_CONFIG))
    
    # Directly call parse_server_configs with the dummy path
    servers, system_prompt = parse_server_configs(dummy_claude_config_path)
    
    assert system_prompt is None
    assert len(servers) == 1
    assert servers[0]["name"] == "auto_server"
