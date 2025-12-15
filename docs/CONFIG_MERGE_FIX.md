# Config Merge Fix - Preserve Existing Keys

**Date:** December 7, 2025
**Issue:** `save-config` was overwriting existing config keys like `mcpServers`

---

## Problem

When users ran `save-config` (or `sc`), the command was creating a new configuration from scratch, which would **overwrite** any keys that weren't managed by the client, such as:

- `mcpServers` - MCP server configurations
- `delegation` - Delegation settings (before the trace menu)
- Any custom keys users might have added

### Example Issue

**Before save-config:**
```json
{
  "model": "qwen2.5:7b",
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
    }
  },
  "delegation": {
    "enabled": true,
    "trace_enabled": true
  }
}
```

**After save-config:**
```json
{
  "model": "qwen2.5:7b",
  "enabledTools": {...},
  "contextSettings": {...},
  "modelSettings": {...}
  // ❌ mcpServers is GONE!
  // ❌ delegation settings are GONE!
}
```

---

## Root Cause

The `save_configuration()` method was creating a fresh config dict:

```python
def save_configuration(self, config_name=None):
    # Build config data
    config_data = {
        "model": self.model_manager.get_current_model(),
        "enabledTools": self.tool_manager.get_enabled_tools(),
        # ... only client-managed keys
    }

    # ❌ This overwrites the entire file
    return self.config_manager.save_configuration(config_data, config_name)
```

---

## Solution

Load the existing configuration first, then **merge** the client-managed keys:

```python
def save_configuration(self, config_name=None):
    # Load existing config to preserve keys we don't manage
    existing_config = self.config_manager.load_configuration(config_name or "default")
    if not existing_config:
        existing_config = {}

    # Update with current client state (only overwrites keys we manage)
    existing_config.update({
        "model": self.model_manager.get_current_model(),
        "enabledTools": self.tool_manager.get_enabled_tools(),
        "contextSettings": {
            "retainContext": self.retain_context
        },
        # ... other client-managed keys
    })

    # ✅ This preserves all existing keys
    return self.config_manager.save_configuration(existing_config, config_name)
```

### How It Works

1. **Load existing config** - Get current file contents
2. **Merge with `.update()`** - Only overwrites client-managed keys
3. **Preserve other keys** - Keys like `mcpServers` are untouched
4. **Save merged config** - Write complete config back to file

---

## Changes Made

### 1. Fixed `save_configuration()` Method

**File:** `mcp_client_for_ollama/client.py:1609-1644`

**Before:**
```python
def save_configuration(self, config_name=None):
    config_data = {
        "model": ...,
        "enabledTools": ...,
        # ... only client keys
    }
    return self.config_manager.save_configuration(config_data, config_name)
```

**After:**
```python
def save_configuration(self, config_name=None):
    # Load existing config to preserve keys we don't manage
    existing_config = self.config_manager.load_configuration(config_name or "default")
    if not existing_config:
        existing_config = {}

    # Merge client-managed keys
    existing_config.update({
        "model": ...,
        "enabledTools": ...,
        # ... client keys
    })

    return self.config_manager.save_configuration(existing_config, config_name)
```

### 2. Fixed `configure_delegation_trace()` Method

**File:** `mcp_client_for_ollama/client.py:1410-1421`

**Before:**
```python
# Build complete config data including delegation settings
config_data = {
    "model": self.model_manager.get_current_model(),
    # ... all client keys
    "delegation": delegation
}

self.config_manager.save_configuration(config_data, config_name)
```

**After:**
```python
# Update the current_config with delegation settings
current_config["delegation"] = delegation

# Save the updated config (preserving other keys like mcpServers)
self.config_manager.save_configuration(current_config, config_name)
```

**Note:** `current_config` was already loaded at the start of the method (line 1304), so we just update it and save.

---

## Keys Preserved

The fix ensures these keys are **preserved** when saving:

### User-Managed Keys
- `mcpServers` - MCP server configurations
- `delegation` - Delegation settings (when set via dt menu)
- Any custom keys users add manually

### Client-Managed Keys (Will Be Updated)
- `model` - Current model selection
- `enabledTools` - Tool enable/disable state
- `contextSettings` - Context retention settings
- `modelSettings` - Thinking mode settings
- `agentSettings` - Loop limit settings
- `modelConfig` - Model parameters
- `displaySettings` - Display preferences
- `hilSettings` - Human-in-the-loop settings
- `sessionSaveDirectory` - Session save location

---

## Testing

### Test Case 1: Preserve mcpServers

**Setup:**
```json
{
  "model": "qwen2.5:7b",
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    }
  }
}
```

**Actions:**
```
You: model
[Select different model]
You: save-config
```

**Expected Result:**
```json
{
  "model": "llama3.2:3b",  // ✅ Updated
  "mcpServers": {          // ✅ Preserved
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    }
  },
  "enabledTools": {...}    // ✅ Added
}
```

### Test Case 2: Preserve delegation settings

**Setup:**
```json
{
  "model": "qwen2.5:7b",
  "delegation": {
    "enabled": true,
    "trace_enabled": true,
    "trace_level": "full"
  }
}
```

**Actions:**
```
You: thinking-mode
You: save-config
```

**Expected Result:**
```json
{
  "model": "qwen2.5:7b",
  "delegation": {           // ✅ Preserved
    "enabled": true,
    "trace_enabled": true,
    "trace_level": "full"
  },
  "modelSettings": {        // ✅ Updated
    "thinkingMode": false
  }
}
```

### Test Case 3: Update delegation via dt menu

**Setup:**
```json
{
  "model": "qwen2.5:7b",
  "mcpServers": {...}
}
```

**Actions:**
```
You: dt
[Configure trace logging]
Save configuration? yes
```

**Expected Result:**
```json
{
  "model": "qwen2.5:7b",
  "mcpServers": {...},      // ✅ Preserved
  "delegation": {           // ✅ Added
    "enabled": true,
    "trace_enabled": true
  }
}
```

---

## Behavior Summary

### What Gets Preserved ✅
- All keys not managed by the client
- User-added custom keys
- `mcpServers` configurations
- Delegation settings (unless updating via dt)

### What Gets Updated 📝
- Keys managed by the client (see list above)
- When using `dt`, the `delegation` key gets updated

### What Gets Removed ❌
- Nothing! All existing keys are preserved

---

## Edge Cases Handled

### Case 1: No existing config file
```python
existing_config = self.config_manager.load_configuration(config_name or "default")
if not existing_config:
    existing_config = {}  # Start with empty dict
```
**Result:** Creates new config without errors

### Case 2: Config file exists but is empty
```python
existing_config = {}  # Returns empty dict
existing_config.update({...})  # Adds client keys
```
**Result:** Populates with client-managed keys

### Case 3: Config has unknown keys
```json
{
  "customKey": "customValue",
  "anotherKey": 123
}
```
**Result:** Unknown keys are preserved in the saved config

---

## Benefits

### For Users
1. ✅ **No data loss** - mcpServers and other settings preserved
2. ✅ **Safe to use** - Can save config without worrying about losing settings
3. ✅ **Additive updates** - Each save adds to config, doesn't replace it
4. ✅ **Custom keys** - Users can add custom keys that won't be removed

### For Development
1. ✅ **Extensible** - New keys can be added without breaking existing configs
2. ✅ **Backward compatible** - Works with old and new config formats
3. ✅ **Predictable** - Only updates keys the client actually manages

---

## Migration

### No migration needed! ✅

This fix is backward compatible:
- Existing configs work as-is
- No user action required
- First save after upgrade will preserve all keys

---

## Related Changes

This fix also benefits:

1. **`delegation-trace` menu** - Now preserves mcpServers when configuring trace
2. **Any future config commands** - Same merge pattern should be used
3. **Config editing** - Users can manually edit config.json safely

---

## Best Practices

### For Future Config Commands

When adding new config commands, follow this pattern:

```python
def new_config_command(self):
    # 1. Load existing config
    config = self.config_manager.load_configuration("default")
    if not config:
        config = {}

    # 2. Update only the keys you manage
    config["yourNewKey"] = your_value

    # 3. Save merged config
    self.config_manager.save_configuration(config, "default")
```

**Don't create fresh config dicts!**

---

## Summary

✅ **Fixed:** `save-config` now merges with existing config
✅ **Preserves:** All user-managed keys (mcpServers, custom keys, etc.)
✅ **Updates:** Only client-managed keys
✅ **Tested:** Works with existing configs and edge cases
✅ **Backward Compatible:** No migration needed

**Result:** Users can safely use `save-config` without losing their mcpServers or other custom settings.
