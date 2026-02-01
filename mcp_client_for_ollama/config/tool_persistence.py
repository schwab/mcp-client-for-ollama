"""Tool state persistence for web UI.

This module handles saving and loading tool enabled/disabled states to config.json.
"""
import json
import os
from pathlib import Path
from typing import List, Set, Optional
import threading


class ToolStatePersistence:
    """Manages persistence of tool enabled/disabled states to config.json"""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize tool state persistence.

        Args:
            config_dir: Path to config directory (default: ~/.config/ollmcp)
        """
        if config_dir:
            self.config_dir = Path(config_dir).expanduser()
        else:
            self.config_dir = Path.home() / '.config' / 'ollmcp'

        self.config_file = self.config_dir / 'config.json'
        self._lock = threading.Lock()

    def _ensure_config_exists(self):
        """Ensure config directory and file exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if not self.config_file.exists():
            # Create minimal config
            with open(self.config_file, 'w') as f:
                json.dump({}, f, indent=2)

    def _load_config(self) -> dict:
        """Load config from file (thread-safe)"""
        with self._lock:
            self._ensure_config_exists()

            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_file}: {e}")
                return {}

    def _save_config(self, config: dict) -> bool:
        """Save config to file (thread-safe)

        Args:
            config: Configuration dictionary to save

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                self._ensure_config_exists()

                # Write to temp file first, then rename (atomic operation)
                temp_file = self.config_file.with_suffix('.json.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(config, f, indent=2)

                # Atomic rename
                temp_file.replace(self.config_file)
                return True

            except Exception as e:
                print(f"Error: Failed to save config to {self.config_file}: {e}")
                return False

    def get_disabled_tools(self) -> Set[str]:
        """Get set of disabled tool names from config

        Returns:
            Set of disabled tool names (e.g., {'filesystem.write', 'obsidian.create'})
        """
        config = self._load_config()
        disabled = config.get('disabledTools', [])
        return set(disabled) if isinstance(disabled, list) else set()

    def get_disabled_servers(self) -> Set[str]:
        """Get set of disabled server names from config

        Returns:
            Set of disabled server names (e.g., {'git', 'slack'})
        """
        config = self._load_config()
        disabled = config.get('disabledServers', [])
        return set(disabled) if isinstance(disabled, list) else set()

    def set_tool_enabled(self, tool_name: str, enabled: bool) -> bool:
        """Set tool enabled state and persist to config

        Args:
            tool_name: Fully qualified tool name (e.g., 'filesystem.write')
            enabled: Whether tool should be enabled

        Returns:
            True if successful, False otherwise
        """
        # Lock entire operation to prevent race conditions
        with self._lock:
            self._ensure_config_exists()

            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = {}

            # Get current disabled tools list
            disabled_tools = set(config.get('disabledTools', []))

            # Update the set
            if enabled:
                # Remove from disabled list
                disabled_tools.discard(tool_name)
            else:
                # Add to disabled list
                disabled_tools.add(tool_name)

            # Save back to config
            config['disabledTools'] = sorted(list(disabled_tools))

            try:
                # Write to temp file first, then rename (atomic operation)
                temp_file = self.config_file.with_suffix('.json.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(config, f, indent=2)

                # Atomic rename
                temp_file.replace(self.config_file)
                return True

            except Exception as e:
                print(f"Error: Failed to save config: {e}")
                return False

    def set_server_enabled(self, server_name: str, enabled: bool) -> bool:
        """Set server enabled state and persist to config

        Args:
            server_name: Server name (e.g., 'filesystem', 'obsidian')
            enabled: Whether server should be enabled

        Returns:
            True if successful, False otherwise
        """
        config = self._load_config()

        # Get current disabled servers list
        disabled_servers = set(config.get('disabledServers', []))

        # Update the set
        if enabled:
            # Remove from disabled list
            disabled_servers.discard(server_name)
        else:
            # Add to disabled list
            disabled_servers.add(server_name)

        # Save back to config
        config['disabledServers'] = sorted(list(disabled_servers))
        return self._save_config(config)

    def set_multiple_tools_enabled(self, tool_names: List[str], enabled: bool) -> bool:
        """Set multiple tools enabled/disabled at once (more efficient)

        Args:
            tool_names: List of tool names
            enabled: Whether tools should be enabled

        Returns:
            True if successful, False otherwise
        """
        config = self._load_config()
        disabled_tools = set(config.get('disabledTools', []))

        # Update the set for all tools
        for tool_name in tool_names:
            if enabled:
                disabled_tools.discard(tool_name)
            else:
                disabled_tools.add(tool_name)

        # Save back to config
        config['disabledTools'] = sorted(list(disabled_tools))
        return self._save_config(config)

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled

        Args:
            tool_name: Fully qualified tool name

        Returns:
            True if enabled, False if disabled
        """
        disabled_tools = self.get_disabled_tools()
        return tool_name not in disabled_tools

    def is_server_enabled(self, server_name: str) -> bool:
        """Check if a server is enabled

        Args:
            server_name: Server name

        Returns:
            True if enabled, False if disabled
        """
        disabled_servers = self.get_disabled_servers()
        return server_name not in disabled_servers

    def clear_all_disabled_tools(self) -> bool:
        """Clear all disabled tools (enable everything)

        Returns:
            True if successful, False otherwise
        """
        config = self._load_config()
        config['disabledTools'] = []
        return self._save_config(config)

    def clear_all_disabled_servers(self) -> bool:
        """Clear all disabled servers (enable everything)

        Returns:
            True if successful, False otherwise
        """
        config = self._load_config()
        config['disabledServers'] = []
        return self._save_config(config)

    def get_config_path(self) -> str:
        """Get path to config file

        Returns:
            Path to config.json
        """
        return str(self.config_file)
