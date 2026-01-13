"""Server discovery for MCP Client for Ollama.

This module handles automatic discovery of MCP servers from different sources,
like Claude's configuration files.
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
from ..utils.constants import DEFAULT_CLAUDE_CONFIG

def process_server_paths(server_paths) -> List[Dict[str, Any]]:
    """Process individual server script paths and validate them.

    Args:
        server_paths: A string or list of paths to server scripts

    Returns:
        List of valid server configurations ready to be connected to
    """
    if not server_paths:
        return []

    # Convert single string to list
    if isinstance(server_paths, str):
        server_paths = [server_paths]

    all_servers = []
    for path in server_paths:
        # Check if the path exists and is a file
        if not os.path.exists(path):
            continue

        if not os.path.isfile(path):
            continue

        # Create server entry
        all_servers.append({
            "type": "script",
            "path": path,
            "name": os.path.basename(path).split('.')[0]  # Use filename without extension as name
        })

    return all_servers

def process_server_urls(server_urls) -> List[Dict[str, Any]]:
    """Process individual server URLs and create configurations for SSE/HTTP servers.

    Args:
        server_urls: A string or list of URLs to server endpoints

    Returns:
        List of valid server configurations ready to be connected to
    """
    if not server_urls:
        return []

    # Convert single string to list
    if isinstance(server_urls, str):
        server_urls = [server_urls]

    all_servers = []
    for url in server_urls:
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            continue

        # Extract a meaningful name from the URL
        parsed = urlparse(url)

        # Use hostname but replace dots and colons with underscores to avoid parsing issues
        name = parsed.netloc.replace(':', '_').replace('.', '_')

        # Determine server type based on URL patterns
        server_type = "streamable_http"  # Default to streamable_http
        if "sse" in url.lower() or "/sse" in parsed.path.lower():
            server_type = "sse"

        # Create server entry with clean hostname-based name
        all_servers.append({
            "type": server_type,
            "url": url,
            "name": name
        })

    return all_servers

def parse_server_configs(config_path: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Parse and validate server configurations from a file.

    Args:
        config_path: Path to JSON config file

    Returns:
        Tuple of (List of valid server configurations, Optional system prompt)
    """
    all_servers = []
    system_prompt = None

    if not config_path or not os.path.exists(config_path):
        return all_servers, system_prompt

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        system_prompt = config.get('systemPrompt')
        server_configs = config.get('mcpServers', {})

        for name, server_config_data in server_configs.items():
            # Skip disabled servers (support both 'disabled' and 'enabled' fields)
            # If 'enabled' field exists, use it (skip if enabled=false)
            # Otherwise, check 'disabled' field (skip if disabled=true)
            if 'enabled' in server_config_data:
                if not server_config_data['enabled']:
                    continue
            elif server_config_data.get('disabled', False):
                continue

            # Determine server type
            server_type = "config"  # Default type for STDIO servers

            # Check for URL-based server types (sse or streamable_http)
            # Support both "type" and "transport" fields for compatibility
            if "type" in server_config_data:
                # Type is explicitly specified in config
                server_type = server_config_data["type"]
            elif "transport" in server_config_data:
                # Transport field (alternative to type)
                server_type = server_config_data["transport"]
            elif "url" in server_config_data:
                # URL exists but no type/transport, infer from URL pattern
                url = server_config_data.get("url", "")
                parsed = urlparse(url)

                # Check if URL suggests SSE endpoint
                if "sse" in url.lower() or "/sse" in parsed.path.lower():
                    server_type = "sse"
                else:
                    # Default to streamable_http for other HTTP URLs
                    server_type = "streamable_http"

            # Create server config object
            server = {
                "type": server_type,
                "name": name,
                "config": server_config_data
            }

            # For URL-based servers, add direct access to URL and headers
            if server_type in ["sse", "streamable_http"]:
                server["url"] = server_config_data.get("url")
                if "headers" in server_config_data:
                    server["headers"] = server_config_data.get("headers")

            all_servers.append(server)

        return all_servers, system_prompt

    except Exception as e:
        # Return empty list and None on error
        return all_servers, system_prompt

def auto_discover_servers() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Automatically discover available server configurations.

    Currently only discovers from Claude's config.

    Returns:
        Tuple of (List of server configurations found automatically, Optional system prompt)
    """
    # Use parse_server_configs to process Claude's config
    return parse_server_configs(DEFAULT_CLAUDE_CONFIG)
