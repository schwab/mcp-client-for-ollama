# Tool State Persistence: How Disabled Tools Are Saved

## Current Implementation

Tool state (enabled/disabled) is **already saved** in the application through the configuration system.

### How It Works Currently

#### 1. **Manual Configuration Save**
When a user disables a tool and wants to persist it:

```
qwen2.5/3-tools❯ tools
[User disables tool in interactive menu]
[User saves config]
qwen2.5/3-tools❯ save-config
Config name (press Enter for 'default'):❯ my-workspace
[Configuration saved with disabled tools]
```

**What gets saved:** `~/.config/ollmcp/my-workspace.json`
```json
{
  "model": "qwen2.5:7b",
  "enabledTools": {
    "filesystem.read_file": true,
    "filesystem.write_file": false,
    "builtin.execute_python_code": true,
    "builtin.set_system_prompt": true
  },
  "contextSettings": {
    "retainContext": true
  },
  ...
}
```

#### 2. **Loading Configuration**
When starting a new session:

```
qwen2.5/3-tools❯ load-config
Config name:❯ my-workspace
[Configuration loaded with previous disabled tools]
```

This restores the exact tool states from when you last saved.

#### 3. **Auto-Load Default Config**
If you save a config as **"default"**, it automatically loads on startup:

```
$ ollmcp
[Loading default config...]
✓ Configuration loaded successfully from ~/.config/ollmcp/config.json
[Your tools are restored to the previous disabled/enabled state]
```

### Code Flow

**File:** `mcp_client_for_ollama/client.py`

1. **Save process (line 1142):**
```python
"enabledTools": self.tool_manager.get_enabled_tools(),
```
Captures ALL current tool states (enabled and disabled)

2. **Load process (lines 1185-1195):**
```python
if "enabledTools" in config_data:
    loaded_tools = config_data["enabledTools"]
    for tool_name, enabled in loaded_tools.items():
        if tool_name in available_tool_names:
            self.tool_manager.set_tool_status(tool_name, enabled)
```
Restores each tool's state from the saved configuration

3. **Auto-load on startup (line 1125):**
```python
self.default_configuration_status = self.load_configuration("default")
```
Automatically loads the default config if it exists

## User Workflows

### Workflow 1: Save Disabled Tools to Named Config
```bash
# Step 1: Start the client
ollmcp

# Step 2: Disable tools you don't want
tools  # Opens interactive menu
[Disable: filesystem.write_file, web.search]

# Step 3: Save this configuration
save-config
Config name:❯ coding-only
✓ Config saved to ~/.config/ollmcp/coding-only.json

# Later: Load this configuration
load-config
Config name:❯ coding-only
✓ Loaded config with disabled tools
```

### Workflow 2: Set Default Configuration (Auto-Load)
```bash
# Step 1: Customize your tool setup
tools
[Disable tools you don't want]

# Step 2: Save as default
save-config
Config name (press Enter for 'default'):❯ [just press Enter]
✓ Config saved to ~/.config/ollmcp/config.json

# Step 3: Next time you start, disabled tools are already set
$ ollmcp
✓ Configuration loaded successfully
[Tools are in the same state as before]
```

### Workflow 3: Multiple Configurations
```bash
# Configuration for coding
save-config coding-session
[Tools: filesystem.*, builtin.execute_python_code enabled]

# Configuration for research
save-config research-session
[Tools: web.search, filesystem.read_file enabled]

# Switch between them
load-config coding-session   # Load coding tools
load-config research-session # Load research tools
```

## Configuration File Structure

**Location:** `~/.config/ollmcp/`

```
~/.config/ollmcp/
├── config.json                 # Default (auto-loaded)
├── coding-workspace.json       # Custom configs
├── research-session.json
└── sessions/
    ├── my-chat-1.json
    └── my-chat-2.json
```

## What Gets Saved With Tool State

When you save a configuration, you're saving:

```python
{
  "model": "qwen2.5:7b",                    # Selected model
  "enabledTools": { ... },                  # ✓ Tool states
  "contextSettings": {
    "retainContext": true                   # Context retention
  },
  "modelSettings": {
    "thinkingMode": true,                   # Thinking mode
    "showThinking": false
  },
  "agentSettings": {
    "loopLimit": 3                          # Agent loop limit
  },
  "modelConfig": {
    "system_prompt": "...",                 # System prompt
    "temperature": 0.7,
    ...
  },
  "displaySettings": {
    "showToolExecution": true,
    "showMetrics": false
  },
  "hilSettings": { ... },                   # Human-in-the-Loop settings
  "sessionSaveDirectory": "./.ollmcp_sessions"
}
```

## Enhancement Suggestion: Auto-Save on Tool Change

Currently, tool state changes are **NOT** auto-saved (only when you explicitly run `save-config`).

If you want auto-save when tools are disabled, this would require:

1. **Modify `tools/manager.py`** to emit a signal when tool state changes
2. **Modify `client.py`** to listen for tool state changes and auto-save to a session config

This would be useful for workflows where you want temporary tool disablement to be preserved.

## Quick Reference: Commands

| Command | Effect |
|---------|--------|
| `tools` or `t` | Open interactive tool selection menu |
| `save-config` or `sc` | Save current tool/model configuration |
| `load-config` or `lc` | Load a previously saved configuration |
| `reset-config` or `rc` | Reset all tools to default (all enabled) |

## Summary

**To save disabled tools to your current session:**

1. **Use save-config with a name:**
   ```
   save-config my-setup
   ```
   Then later:
   ```
   load-config my-setup
   ```

2. **Or use the default config** (auto-loads next time):
   ```
   save-config  # Saves to default
   ```

The tool state is fully persistent and survives restarts - it's already implemented!

## File Locations

- **Config directory:** `~/.config/ollmcp/`
- **Default config:** `~/.config/ollmcp/config.json`
- **Named configs:** `~/.config/ollmcp/{name}.json`
- **Sessions:** `~/.config/ollmcp/sessions/` (or custom directory set with `session-dir`)
