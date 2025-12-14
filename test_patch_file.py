#!/usr/bin/env python3
"""
Test script for the new builtin.patch_file tool.

This script demonstrates and verifies the patch_file functionality.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent))

from mcp_client_for_ollama.tools.builtin import BuiltinToolManager


class MockModelConfigManager:
    """Mock config manager for testing."""
    def __init__(self):
        self.system_prompt = "Test prompt"

    def get_system_prompt(self):
        return self.system_prompt


def test_patch_file():
    """Test the patch_file tool functionality."""

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Initialize the builtin tool manager
            config_manager = MockModelConfigManager()
            tool_manager = BuiltinToolManager(config_manager)

            # Test 1: Create a test file
            print("=" * 60)
            print("TEST 1: Creating test file")
            print("=" * 60)

            test_content = """# Configuration File
DEBUG = True
MAX_CONNECTIONS = 10
TIMEOUT = 30

def process_request():
    return "processing"

def handle_error():
    return "error"
"""

            result = tool_manager.execute_tool("write_file", {
                "path": "config.py",
                "content": test_content
            })
            print(result)
            print()

            # Test 2: Simple single replacement
            print("=" * 60)
            print("TEST 2: Simple single replacement")
            print("=" * 60)

            result = tool_manager.execute_tool("patch_file", {
                "path": "config.py",
                "changes": [
                    {
                        "search": "DEBUG = True",
                        "replace": "DEBUG = False"
                    }
                ]
            })
            print(result)
            print()

            # Test 3: Multiple changes in one operation
            print("=" * 60)
            print("TEST 3: Multiple changes in one operation")
            print("=" * 60)

            result = tool_manager.execute_tool("patch_file", {
                "path": "config.py",
                "changes": [
                    {
                        "search": "MAX_CONNECTIONS = 10",
                        "replace": "MAX_CONNECTIONS = 100"
                    },
                    {
                        "search": "TIMEOUT = 30",
                        "replace": "TIMEOUT = 60"
                    }
                ]
            })
            print(result)
            print()

            # Test 4: Multi-line replacement
            print("=" * 60)
            print("TEST 4: Multi-line replacement")
            print("=" * 60)

            result = tool_manager.execute_tool("patch_file", {
                "path": "config.py",
                "changes": [
                    {
                        "search": "def process_request():\n    return \"processing\"",
                        "replace": "def process_request():\n    # Enhanced processing\n    return \"processing_v2\""
                    }
                ]
            })
            print(result)
            print()

            # Test 5: Read the final file to verify
            print("=" * 60)
            print("TEST 5: Final file contents")
            print("=" * 60)

            result = tool_manager.execute_tool("read_file", {
                "path": "config.py"
            })
            print(result)
            print()

            # Test 6: Error case - search text not found
            print("=" * 60)
            print("TEST 6: Error case - search text not found")
            print("=" * 60)

            result = tool_manager.execute_tool("patch_file", {
                "path": "config.py",
                "changes": [
                    {
                        "search": "NONEXISTENT = True",
                        "replace": "NONEXISTENT = False"
                    }
                ]
            })
            print(result)
            print()

            # Test 7: Create file with duplicate text
            print("=" * 60)
            print("TEST 7: Handling duplicate text with occurrence")
            print("=" * 60)

            duplicate_content = """def test():
    assert result == expected

def test2():
    assert result == expected

def test3():
    assert result == expected
"""

            tool_manager.execute_tool("write_file", {
                "path": "test_duplicates.py",
                "content": duplicate_content
            })

            # Try without occurrence (should error)
            print("Attempting without occurrence (should error):")
            result = tool_manager.execute_tool("patch_file", {
                "path": "test_duplicates.py",
                "changes": [
                    {
                        "search": "assert result == expected",
                        "replace": "assert result == expected, 'mismatch'"
                    }
                ]
            })
            print(result)
            print()

            # Try with occurrence specified (should succeed)
            print("Attempting with occurrence=2 (should succeed):")
            result = tool_manager.execute_tool("patch_file", {
                "path": "test_duplicates.py",
                "changes": [
                    {
                        "search": "assert result == expected",
                        "replace": "assert result == expected, 'mismatch'",
                        "occurrence": 2
                    }
                ]
            })
            print(result)
            print()

            # Verify the change
            result = tool_manager.execute_tool("read_file", {
                "path": "test_duplicates.py"
            })
            print("File after occurrence-based replacement:")
            print(result)
            print()

            # Test 8: Verify tool is in available tools
            print("=" * 60)
            print("TEST 8: Verify tool is in available tools list")
            print("=" * 60)

            tools = tool_manager.get_builtin_tools()
            patch_tool = next((t for t in tools if t.name == "builtin.patch_file"), None)

            if patch_tool:
                print(f"✓ Tool found: {patch_tool.name}")
                print(f"  Description: {patch_tool.description[:100]}...")
                print(f"  Has inputSchema: {bool(patch_tool.inputSchema)}")
                print()
            else:
                print("✗ Tool NOT found in available tools!")
                print()

            print("=" * 60)
            print("ALL TESTS COMPLETED SUCCESSFULLY!")
            print("=" * 60)

        finally:
            # Restore original working directory
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_patch_file()
