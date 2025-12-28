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
    def get_workspace_folder(workspace_storage_dir: Path) -> Optional[str]:
        """
        Get the workspace folder path from a workspace storage directory.

        Args:
            workspace_storage_dir: Path to workspace storage directory

        Returns:
            Workspace folder path, or None if not found
        """
        # Try workspace.json file first
        workspace_json = workspace_storage_dir / 'workspace.json'
        if workspace_json.exists():
            try:
                with open(workspace_json, 'r') as f:
                    data = json.load(f)
                    # Extract folder URI
                    if 'folder' in data:
                        folder_uri = data['folder']
                        # Handle file:// URI format
                        if folder_uri.startswith('file://'):
                            # Decode URL-encoded path
                            from urllib.parse import unquote
                            return unquote(folder_uri[7:])
            except (json.JSONDecodeError, KeyError, IOError):
                pass

        # Fallback: try to get folder from state database
        state_db = workspace_storage_dir / 'state.vscdb'
        if state_db.exists():
            try:
                conn = sqlite3.connect(str(state_db))
                cursor = conn.cursor()
                # Try to find workspace folder in state
                cursor.execute(
                    "SELECT value FROM ItemTable WHERE key = 'workbench.panel.markers.hidden'"
                )
                cursor.execute(
                    "SELECT value FROM ItemTable WHERE key LIKE '%folderUri%' OR key LIKE '%workspace.folder%' LIMIT 1"
                )
                row = cursor.fetchone()
                conn.close()

                if row:
                    data = json.loads(row[0])
                    if isinstance(data, str) and data.startswith('file://'):
                        from urllib.parse import unquote
                        return unquote(data[7:])
            except Exception:
                pass

        return None

    @staticmethod
    def find_current_workspace() -> Optional[Path]:
        """
        Find the workspace state database that matches the current working directory.

        First tries to match workspace folder to current directory, then falls back
        to most recently modified workspace.

        Returns:
            Path to state.vscdb file, or None if not found
        """
        workspace_dir = VSCodeIntegration.get_vscode_workspace_dir()
        if not workspace_dir or not workspace_dir.exists():
            return None

        current_dir = os.getcwd()
        workspaces = []
        matched_workspace = None
        best_match_len = 0  # Track longest matching path

        # Collect all workspaces and try to match current directory
        for ws in workspace_dir.iterdir():
            if not ws.is_dir():
                continue

            state_db = ws / 'state.vscdb'
            if state_db.exists():
                mtime = state_db.stat().st_mtime
                workspaces.append((mtime, state_db))

                # Try to match workspace folder to current directory
                ws_folder = VSCodeIntegration.get_workspace_folder(ws)
                if ws_folder:
                    # Check if current directory is within this workspace
                    # Use the most specific match (longest path)
                    if current_dir.startswith(ws_folder):
                        match_len = len(ws_folder)
                        if match_len > best_match_len:
                            matched_workspace = state_db
                            best_match_len = match_len

        # Return matched workspace if found
        if matched_workspace:
            return matched_workspace

        # Fallback: return most recently modified workspace
        if workspaces:
            workspaces.sort(reverse=True, key=lambda x: x[0])
            return workspaces[0][1]

        return None

    @staticmethod
    def find_most_recent_workspace() -> Optional[Path]:
        """
        Find the most recently modified workspace state database.

        Deprecated: Use find_current_workspace() instead for better accuracy.

        Returns:
            Path to state.vscdb file, or None if not found
        """
        # Now just calls find_current_workspace for better matching
        return VSCodeIntegration.find_current_workspace()

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
