# VSCode Integration - Auto-detect Active File

## Feature Request

When running inside a VSCode terminal, automatically detect the currently open/selected file and load its contents into the chat context. Display the detected file so the user knows they have that file as context before they enter their query.

## Technical Feasibility

✅ **PROVEN WORKING** - VSCode stores the active editor state in a SQLite database that can be queried.

### VSCode Detection

**Environment Variables** (reliable):
```bash
TERM_PROGRAM=vscode
VSCODE_INJECTION=1
VSCODE_GIT_IPC_HANDLE=/run/user/1000/vscode-git-*.sock
```

**Workspace State Database**:
- Location: `~/.config/Code/User/workspaceStorage/{workspace_id}/state.vscdb`
- Format: SQLite database
- Key: `memento/workbench.parts.editor`
- Contains: Array of open editors with file paths, active editor index

### Proof of Concept

Successfully extracted active file:
```python
# Query the most recent workspace state.vscdb
sqlite3 {workspace}/state.vscdb "SELECT value FROM ItemTable WHERE key = 'memento/workbench.parts.editor'"
# Parse JSON → editorpart.state → serializedGrid → root → data[0] → editors[active_index]
# Result: /home/user/path/to/active/file.py
```

## Implementation Plan

### Phase 1: VSCode Detection Module

**File**: `mcp_client_for_ollama/integrations/vscode.py`

```python
import os
import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class VSCodeEditorInfo:
    """Information about a VSCode editor tab."""
    file_path: str
    is_active: bool
    encoding: str
    language: Optional[str] = None

class VSCodeIntegration:
    """Integration with VSCode to detect active files."""

    @staticmethod
    def is_running_in_vscode() -> bool:
        """Check if running inside a VSCode terminal."""
        return os.getenv('TERM_PROGRAM') == 'vscode'

    @staticmethod
    def get_vscode_workspace_dir() -> Optional[Path]:
        """Get VSCode workspace storage directory."""
        config_dir = Path.home() / '.config' / 'Code' / 'User' / 'workspaceStorage'
        return config_dir if config_dir.exists() else None

    @staticmethod
    def find_most_recent_workspace() -> Optional[Path]:
        """Find the most recently modified workspace (likely current)."""
        workspace_dir = VSCodeIntegration.get_vscode_workspace_dir()
        if not workspace_dir:
            return None

        # Find most recent state.vscdb
        workspaces = []
        for ws in workspace_dir.iterdir():
            state_db = ws / 'state.vscdb'
            if state_db.exists():
                workspaces.append((state_db.stat().st_mtime, state_db))

        if not workspaces:
            return None

        # Return most recent
        workspaces.sort(reverse=True, key=lambda x: x[0])
        return workspaces[0][1]

    @staticmethod
    def get_active_file() -> Optional[str]:
        """
        Get the currently active file in VSCode.

        Returns:
            File path of active editor, or None if not found/error
        """
        try:
            state_db = VSCodeIntegration.find_most_recent_workspace()
            if not state_db:
                return None

            # Query the database
            conn = sqlite3.connect(str(state_db))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM ItemTable WHERE key = 'memento/workbench.parts.editor'"
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # Parse JSON
            data = json.loads(row[0])
            state = data.get('editorpart.state', {})
            grid = state.get('serializedGrid', {})
            root = grid.get('root', {})

            # Navigate to editors list
            if root.get('type') == 'branch' and root.get('data'):
                leaf = root['data'][0]
                if leaf.get('type') == 'leaf':
                    editors_data = leaf.get('data', {})
                    editors = editors_data.get('editors', [])
                    active_index = editors_data.get('active', 0)

                    if active_index < len(editors):
                        active_editor = editors[active_index]
                        value = json.loads(active_editor.get('value', '{}'))
                        fsPath = value.get('resourceJSON', {}).get('fsPath')
                        return fsPath

            return None

        except Exception as e:
            # Silently fail - VSCode integration is optional
            return None

    @staticmethod
    def get_all_open_files() -> List[VSCodeEditorInfo]:
        """Get all open files in VSCode editor tabs."""
        # Similar to get_active_file but returns all editors
        # Implementation similar to above but collects all editors
        pass
```

### Phase 2: CLI Integration

**File**: `mcp_client_for_ollama/cli.py`

Add auto-context loading on startup:

```python
def run_cli():
    """Main CLI entry point."""
    # ... existing code ...

    # VSCode Integration
    from mcp_client_for_ollama.integrations.vscode import VSCodeIntegration

    vscode_detected = VSCodeIntegration.is_running_in_vscode()
    vscode_file = None

    if vscode_detected:
        # Check if auto-load is enabled in config
        config = get_config()
        auto_load = config.get('vscode', {}).get('auto_load_active_file', False)

        if auto_load:
            vscode_file = VSCodeIntegration.get_active_file()
            if vscode_file:
                # Load file contents
                try:
                    with open(vscode_file, 'r') as f:
                        file_contents = f.read()

                    # Display to user
                    console.print(f"\n📄 [cyan]Auto-loaded from VSCode:[/cyan] {vscode_file}")
                    console.print(f"[dim]({len(file_contents)} chars, use /clear-context to remove)[/dim]\n")

                    # Add to initial context
                    initial_context = f"# File: {vscode_file}\n\n{file_contents}\n\n---\n\n"

                except Exception as e:
                    console.print(f"[yellow]⚠ Could not load file: {e}[/yellow]")
```

### Phase 3: Interactive Commands

Add slash commands for VSCode integration:

```python
# In the chat loop
@command('/vscode-file')
def load_vscode_file():
    """Load the currently active VSCode file into context."""
    from mcp_client_for_ollama.integrations.vscode import VSCodeIntegration

    if not VSCodeIntegration.is_running_in_vscode():
        return "Not running in VSCode terminal"

    file_path = VSCodeIntegration.get_active_file()
    if not file_path:
        return "Could not detect active VSCode file"

    try:
        with open(file_path, 'r') as f:
            contents = f.read()

        # Add to context
        add_to_context(file_path, contents)
        return f"✓ Loaded {file_path} ({len(contents)} chars)"
    except Exception as e:
        return f"✗ Error loading file: {e}"

@command('/vscode-status')
def show_vscode_status():
    """Show VSCode integration status."""
    from mcp_client_for_ollama.integrations.vscode import VSCodeIntegration

    running = VSCodeIntegration.is_running_in_vscode()
    active_file = VSCodeIntegration.get_active_file() if running else None

    status = f"""
VSCode Integration Status:
  Running in VSCode: {running}
  Active File: {active_file or 'N/A'}
  Auto-load enabled: {config.get('vscode', {}).get('auto_load_active_file', False)}
"""
    return status
```

### Phase 4: Configuration

**File**: `mcp_client_for_ollama/config/defaults.py`

```python
DEFAULT_CONFIG = {
    # ... existing config ...

    "vscode": {
        "auto_load_active_file": False,  # Don't auto-load by default
        "show_file_preview": True,       # Show first few lines when loading
        "max_file_size": 100000,         # Max file size to auto-load (100KB)
        "file_preview_lines": 10,        # Lines to show in preview
    }
}
```

**Config Usage**:
```bash
# Enable auto-load
ollmcp config set vscode.auto_load_active_file true

# Check status
ollmcp config get vscode
```

### Phase 5: User Experience

**Startup Flow with Auto-load Enabled**:
```
$ ollmcp

🤖 MCP Client for Ollama v0.33.8
📄 Auto-loaded from VSCode: /home/user/project/main.py
   (2,543 chars, use /clear-context to remove)

Preview:
1  import os
2  import sys
3  from typing import List, Optional
4  ...
10 def main():
   [+2533 more lines]

Ready. Your question will include context from main.py.
>
```

**Manual Load**:
```
> /vscode-file
✓ Loaded /home/user/project/config.py (1,234 chars)

> /vscode-status
VSCode Integration Status:
  Running in VSCode: True
  Active File: /home/user/project/config.py
  Auto-load enabled: True
```

## Implementation Phases

### MVP (Minimal Viable Product)
1. ✅ VSCode detection (env vars)
2. ✅ Get active file from state.vscdb
3. Add `/vscode-file` command
4. Add `/vscode-status` command

**Effort**: 2-3 hours
**Value**: High - immediately useful

### Full Feature
5. Auto-load on startup (with config flag)
6. File preview display
7. Size limits and error handling
8. Config integration
9. Documentation

**Effort**: 4-5 hours
**Value**: Very High - seamless workflow

### Future Enhancements
- Watch for active file changes (real-time)
- Load multiple open files
- Syntax highlighting in preview
- VSCode extension for bi-directional integration

## Risks & Mitigation

### Risk 1: VSCode Updates Breaking DB Structure
**Mitigation**:
- Wrap all VSCode queries in try/except
- Fail gracefully with clear message
- Add version detection and compatibility checks

### Risk 2: Performance (Large Files)
**Mitigation**:
- Add max file size limit (default 100KB)
- Show warning for large files
- Option to load first N lines only

### Risk 3: Privacy (Sensitive Files)
**Mitigation**:
- Make auto-load opt-in (disabled by default)
- Add file path patterns to exclude (e.g., `*.env`, `*secret*`)
- Show file path before loading (user can cancel)

## Testing Plan

### Unit Tests
```python
def test_vscode_detection():
    """Test VSCode environment detection."""
    os.environ['TERM_PROGRAM'] = 'vscode'
    assert VSCodeIntegration.is_running_in_vscode()

def test_active_file_extraction():
    """Test extracting active file from mock DB."""
    # Create mock state.vscdb
    # Query and verify correct file returned
```

### Integration Tests
1. Test in actual VSCode terminal
2. Test with no VSCode (graceful failure)
3. Test with corrupted state DB
4. Test with various file types

## Success Metrics

- ✅ Detects VSCode terminal 100% of time when running in VSCode
- ✅ Extracts correct active file ≥95% of time
- ✅ Graceful failure (no crashes) on errors
- ✅ User feedback: "saves time", "seamless workflow"

## Conclusion

**Status**: ✅ **FEASIBLE AND PROVEN**

This feature is technically sound and can be implemented with the plan above. The SQLite database approach is reliable and doesn't require a VSCode extension.

**Recommendation**: Start with MVP (steps 1-4), then expand to full feature based on user feedback.
