"""Test path resolution fix for delegation system."""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock
from mcp_client_for_ollama.tools.builtin import BuiltinToolManager


class TestPathResolution:
    """Tests for path resolution in builtin tools."""

    @pytest.fixture
    def mock_model_config_manager(self):
        """Fixture for a mocked ModelConfigManager."""
        mock = MagicMock()
        mock.system_prompt = None
        mock.get_system_prompt.side_effect = lambda: mock.system_prompt
        return mock

    @pytest.fixture
    def temp_project_dir(self, mock_model_config_manager):
        """Create a temporary project directory with subdirectories and files."""
        # Create temp directory
        temp_dir = tempfile.mkdtemp()

        # Create subdirectory structure
        misc_dir = Path(temp_dir) / "misc"
        misc_dir.mkdir()

        docs_dir = Path(temp_dir) / "docs"
        docs_dir.mkdir()

        # Create test files
        (misc_dir / "file1.md").write_text("Content of file 1")
        (misc_dir / "file2.md").write_text("Content of file 2")
        (docs_dir / "readme.md").write_text("Readme content")
        (Path(temp_dir) / "root.txt").write_text("Root file")

        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Create builtin tool manager with temp dir as working directory
        manager = BuiltinToolManager(mock_model_config_manager)
        manager.working_directory = temp_dir

        yield temp_dir, manager

        # Cleanup
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_list_files_returns_correct_relative_paths(self, temp_project_dir):
        """Test that list_files returns paths relative to working directory."""
        temp_dir, manager = temp_project_dir

        # List files in misc subdirectory
        result = manager.execute_tool("list_files", {"path": "misc"})

        # Should contain "misc/file1.md" and "misc/file2.md"
        assert "misc/file1.md" in result or "misc\\file1.md" in result  # Handle Windows paths
        assert "misc/file2.md" in result or "misc\\file2.md" in result
        # Should NOT contain just "file1.md"
        assert "  - file1.md\n" not in result
        assert "  - file2.md\n" not in result

    def test_list_files_current_directory(self, temp_project_dir):
        """Test that list_files in current directory returns simple filenames."""
        temp_dir, manager = temp_project_dir

        # List files in current directory
        result = manager.execute_tool("list_files", {"path": "."})

        # Should contain "root.txt" (no directory prefix for current dir)
        assert "root.txt" in result

    def test_list_files_recursive_preserves_paths(self, temp_project_dir):
        """Test that recursive list_files preserves full relative paths."""
        temp_dir, manager = temp_project_dir

        # List all files recursively
        result = manager.execute_tool("list_files", {
            "path": ".",
            "recursive": True,
            "respect_gitignore": False
        })

        # Should contain paths relative to working directory
        # Check for either forward or back slashes (cross-platform)
        has_misc_files = ("misc/file1.md" in result or "misc\\file1.md" in result)
        has_docs_files = ("docs/readme.md" in result or "docs\\readme.md" in result)

        assert has_misc_files
        assert has_docs_files
        assert "root.txt" in result

    def test_read_file_after_list_files(self, temp_project_dir):
        """Test that files can be read using paths returned by list_files."""
        temp_dir, manager = temp_project_dir

        # List files in misc directory
        list_result = manager.execute_tool("list_files", {"path": "misc"})

        # Extract first file path from result
        # Format: "Files in 'misc' (2 files):\n  - misc/file1.md\n  - misc/file2.md"
        lines = list_result.split("\n")
        file_lines = [l.strip("  - ") for l in lines if l.strip().startswith("- ")]

        assert len(file_lines) >= 1
        first_file = file_lines[0]

        # Now read that file using the returned path
        read_result = manager.execute_tool("read_file", {"path": first_file})

        # Should succeed and contain content
        assert "Error" not in read_result
        assert "read successfully" in read_result
        assert "Content of file" in read_result

    def test_delegation_scenario_list_then_read(self, temp_project_dir):
        """Simulate the delegation scenario: list files, then read them."""
        temp_dir, manager = temp_project_dir

        # Task 1: List markdown files in misc directory
        list_result = manager.execute_tool("list_files", {
            "path": "misc",
            "recursive": False
        })

        assert "misc" in list_result
        assert "file1.md" in list_result

        # Task 2: Read files using paths from Task 1
        # Extract paths (handle both Unix and Windows separators)
        if "misc/file1.md" in list_result:
            file_path = "misc/file1.md"
        elif "misc\\file1.md" in list_result:
            file_path = "misc\\file1.md"
        else:
            pytest.fail("Could not find expected file path in list result")

        read_result = manager.execute_tool("read_file", {"path": file_path})

        # Should successfully read the file
        assert f"File '{file_path}' read successfully" in read_result
        assert "Content of file 1" in read_result

    def test_list_files_in_subdirectory_non_recursive(self, temp_project_dir):
        """Test non-recursive listing in subdirectory."""
        temp_dir, manager = temp_project_dir

        result = manager.execute_tool("list_files", {
            "path": "misc",
            "recursive": False
        })

        # Should show files with directory prefix
        assert "misc" in result
        # Should have both files
        assert "file1.md" in result
        assert "file2.md" in result
        # Should not show files from other directories
        assert "readme.md" not in result
        assert "root.txt" not in result
