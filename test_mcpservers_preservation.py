#!/usr/bin/env python3
"""
Test to verify that mcpServers configuration is preserved when saving config.

This test verifies the fix for the bug where save-config after delegation-trace
was overwriting the user's mcpServers section.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock


def test_validate_config_preserves_mcpservers():
    """Test that _validate_config preserves mcpServers from original config."""
    from mcp_client_for_ollama.config.manager import ConfigManager
    from rich.console import Console

    # Create a mock console
    console = Console()
    config_manager = ConfigManager(console)

    # Simulate a config file with mcpServers
    original_config = {
        "model": "qwen2.5-coder:32b",
        "enabledTools": {},
        "mcpServers": {
            "nextcloud-api": {
                "command": "python",
                "args": ["-m", "nextcloud_mcp_server"],
                "env": {
                    "NEXTCLOUD_URL": "https://example.com",
                    "NEXTCLOUD_USERNAME": "user",
                    "NEXTCLOUD_PASSWORD": "pass"
                }
            },
            "osm-mcp-server": {
                "command": "uvx",
                "args": ["osm-mcp-server"]
            }
        },
        "delegation": {
            "enabled": True,
            "trace_enabled": False
        }
    }

    # Run validation
    validated = config_manager._validate_config(original_config)

    # Check that mcpServers was preserved
    if "mcpServers" not in validated:
        print("❌ FAILED: mcpServers was NOT preserved")
        return False

    if validated["mcpServers"] != original_config["mcpServers"]:
        print("❌ FAILED: mcpServers was modified during validation")
        print(f"Original: {original_config['mcpServers']}")
        print(f"Validated: {validated['mcpServers']}")
        return False

    print("✅ PASSED: mcpServers preserved in validation")
    return True


def test_save_load_cycle_preserves_mcpservers():
    """Test that save/load cycle preserves mcpServers."""
    from mcp_client_for_ollama.config.manager import ConfigManager
    from rich.console import Console

    # Create temporary config directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Patch the default config dir
        import mcp_client_for_ollama.config.manager as manager_module
        original_config_dir = manager_module.DEFAULT_CONFIG_DIR
        manager_module.DEFAULT_CONFIG_DIR = tmpdir

        try:
            console = Console()
            config_manager = ConfigManager(console)

            # Original config with mcpServers
            original_config = {
                "model": "qwen2.5-coder:32b",
                "mcpServers": {
                    "test-server": {
                        "command": "test",
                        "args": ["--test"]
                    }
                },
                "delegation": {
                    "enabled": True
                }
            }

            # Save the config
            config_manager.save_configuration(original_config, "test")

            # Load it back
            loaded_config = config_manager.load_configuration("test")

            # Check mcpServers was preserved
            if "mcpServers" not in loaded_config:
                print("❌ FAILED: mcpServers lost in save/load cycle")
                return False

            if loaded_config["mcpServers"] != original_config["mcpServers"]:
                print("❌ FAILED: mcpServers changed in save/load cycle")
                print(f"Original: {original_config['mcpServers']}")
                print(f"Loaded: {loaded_config['mcpServers']}")
                return False

            print("✅ PASSED: mcpServers preserved through save/load cycle")
            return True

        finally:
            # Restore original config dir
            manager_module.DEFAULT_CONFIG_DIR = original_config_dir


def test_delegation_config_preserves_mcpservers():
    """Test that modifying delegation settings preserves mcpServers."""
    from mcp_client_for_ollama.config.manager import ConfigManager
    from rich.console import Console

    with tempfile.TemporaryDirectory() as tmpdir:
        import mcp_client_for_ollama.config.manager as manager_module
        original_config_dir = manager_module.DEFAULT_CONFIG_DIR
        manager_module.DEFAULT_CONFIG_DIR = tmpdir

        try:
            console = Console()
            config_manager = ConfigManager(console)

            # Initial config with mcpServers
            initial_config = {
                "model": "qwen2.5-coder:32b",
                "mcpServers": {
                    "important-server": {
                        "command": "important",
                        "args": ["--critical"]
                    }
                },
                "delegation": {
                    "enabled": False,
                    "trace_enabled": False
                }
            }

            # Save initial config
            config_manager.save_configuration(initial_config, "test")

            # Load config (like configure_delegation_trace does)
            current_config = config_manager.load_configuration("test")

            # Modify delegation settings
            current_config["delegation"]["enabled"] = True
            current_config["delegation"]["trace_enabled"] = True
            current_config["delegation"]["trace_level"] = "basic"

            # Save modified config (simulating what configure_delegation_trace does)
            config_manager.save_configuration(current_config, "test")

            # Load again to verify
            final_config = config_manager.load_configuration("test")

            # Check mcpServers is still there
            if "mcpServers" not in final_config:
                print("❌ FAILED: mcpServers lost when modifying delegation settings")
                return False

            if final_config["mcpServers"] != initial_config["mcpServers"]:
                print("❌ FAILED: mcpServers changed when modifying delegation settings")
                print(f"Initial: {initial_config['mcpServers']}")
                print(f"Final: {final_config['mcpServers']}")
                return False

            # Verify delegation changes were saved
            if not final_config["delegation"]["enabled"]:
                print("❌ FAILED: Delegation settings not saved")
                return False

            print("✅ PASSED: mcpServers preserved when modifying delegation settings")
            return True

        finally:
            manager_module.DEFAULT_CONFIG_DIR = original_config_dir


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing mcpServers Preservation Fix")
    print("="*60 + "\n")

    results = []

    print("Test 1: Validate config preserves mcpServers")
    results.append(test_validate_config_preserves_mcpservers())
    print()

    print("Test 2: Save/load cycle preserves mcpServers")
    results.append(test_save_load_cycle_preserves_mcpservers())
    print()

    print("Test 3: Delegation config changes preserve mcpServers")
    results.append(test_delegation_config_preserves_mcpservers())
    print()

    print("="*60)
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nThe bug is fixed! mcpServers will now be preserved when:")
        print("  1. Running save-config")
        print("  2. Configuring delegation-trace settings")
        print("  3. Any other config save operation")
        exit(0)
    else:
        print(f"❌ {sum(not r for r in results)} TEST(S) FAILED")
        print("="*60)
        exit(1)
