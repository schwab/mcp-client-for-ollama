"""
VSCode integration for detecting and loading active files.

This module provides functionality to detect when running inside a VSCode terminal
and extract the currently active file from VSCode's workspace state database.
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class VSCodeFileInfo:
    """Information about a VSCode file."""
    file_path: str
    exists: bool
    size: int
    encoding: str = "utf8"


class VSCodeIntegration:
    """Integration with VSCode to detect active files."""

    @staticmethod
    def is_running_in_vscode() -> bool:
        """
        Check if running inside a VSCode terminal.

        Returns:
            True if running in VSCode terminal, False otherwise
        """
        # VSCode sets TERM_PROGRAM=vscode when running in integrated terminal
        term_program = os.getenv('TERM_PROGRAM', '').lower()
        vscode_injection = os.getenv('VSCODE_INJECTION')

        return term_program == 'vscode' or vscode_injection is not None

    @staticmethod
    def get_vscode_workspace_dir() -> Optional[Path]:
        """
        Get VSCode workspace storage directory.

        Returns:
            Path to workspace storage directory, or None if not found
        """
        # Check Linux/Mac location
        config_dir = Path.home() / '.config' / 'Code' / 'User' / 'workspaceStorage'
        if config_dir.exists():
            return config_dir

        # Check Windows location
        if os.name == 'nt':
            appdata = os.getenv('APPDATA')
            if appdata:
                config_dir = Path(appdata) / 'Code' / 'User' / 'workspaceStorage'
                if config_dir.exists():
                    return config_dir

        return None

    @staticmethod
    def find_most_recent_workspace() -> Optional[Path]:
        """
        Find the most recently modified workspace state database.

        This is likely the currently active VSCode workspace.

        Returns:
            Path to state.vscdb file, or None if not found
        """
        workspace_dir = VSCodeIntegration.get_vscode_workspace_dir()
        if not workspace_dir or not workspace_dir.exists():
            return None

        # Find all state.vscdb files and sort by modification time
        workspaces = []
        for ws in workspace_dir.iterdir():
            if not ws.is_dir():
                continue

            state_db = ws / 'state.vscdb'
            if state_db.exists():
                mtime = state_db.stat().st_mtime
                workspaces.append((mtime, state_db))

        if not workspaces:
            return None

        # Return most recently modified
        workspaces.sort(reverse=True, key=lambda x: x[0])
        return workspaces[0][1]

    @staticmethod
    def get_active_file() -> Optional[str]:
        """
        Get the currently active file in VSCode.

        Queries VSCode's workspace state database to find the active editor.

        Returns:
            Absolute file path of active editor, or None if not found/error
        """
        try:
            state_db = VSCodeIntegration.find_most_recent_workspace()
            if not state_db:
                return None

            # Query the SQLite database
            conn = sqlite3.connect(str(state_db))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM ItemTable WHERE key = 'memento/workbench.parts.editor'"
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # Parse the JSON structure
            data = json.loads(row[0])
            state = data.get('editorpart.state', {})
            grid = state.get('serializedGrid', {})
            root = grid.get('root', {})

            # Navigate to the editors list
            if root.get('type') == 'branch' and root.get('data'):
                # Get the first leaf (editor group)
                leaf = root['data'][0]
                if leaf.get('type') == 'leaf':
                    editors_data = leaf.get('data', {})
                    editors = editors_data.get('editors', [])
                    active_index = editors_data.get('active', 0)

                    # Get the active editor
                    if active_index < len(editors):
                        active_editor = editors[active_index]
                        value_str = active_editor.get('value', '{}')

                        # Some values are double-encoded JSON
                        try:
                            value = json.loads(value_str)
                        except json.JSONDecodeError:
                            return None

                        # Extract file path
                        resource = value.get('resourceJSON', {})
                        fs_path = resource.get('fsPath')

                        # Validate it's a file:// scheme
                        scheme = resource.get('scheme', '')
                        if scheme == 'file' and fs_path:
                            return fs_path

            return None

        except Exception:
            # Silently fail - VSCode integration is optional and best-effort
            return None

    @staticmethod
    def get_file_info(file_path: str) -> Optional[VSCodeFileInfo]:
        """
        Get information about a file.

        Args:
            file_path: Path to the file

        Returns:
            VSCodeFileInfo with file details, or None if file doesn't exist
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return VSCodeFileInfo(
                    file_path=file_path,
                    exists=False,
                    size=0
                )

            size = path.stat().st_size
            return VSCodeFileInfo(
                file_path=file_path,
                exists=True,
                size=size
            )
        except Exception:
            return None

    @staticmethod
    def get_status() -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Get VSCode integration status.

        Returns:
            Tuple of (is_vscode, active_file, error_message)
        """
        is_vscode = VSCodeIntegration.is_running_in_vscode()

        if not is_vscode:
            return (False, None, "Not running in VSCode terminal")

        try:
            active_file = VSCodeIntegration.get_active_file()

            if not active_file:
                return (True, None, "Could not detect active file")

            return (True, active_file, None)

        except Exception as e:
            return (True, None, f"Error: {str(e)}")
