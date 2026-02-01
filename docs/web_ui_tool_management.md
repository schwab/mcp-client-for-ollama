# Web UI Tool Management

## Overview

The web UI now supports managing tools both individually and by server/group, providing better control over which MCP servers and tools are active in your session.

## Features

### 1. Server-Level Tool Management

Instead of enabling/disabling tools one by one, you can now enable/disable all tools from an MCP server at once.

**API Endpoints:**

```
GET  /api/tools/servers?session_id=xxx
POST /api/tools/servers/toggle
GET  /api/tools/groups?session_id=xxx
```

### 2. Configuration Path Display

When starting the web server, detailed configuration paths are now printed to help debug configuration issues:

```
======================================================================
📁 Configuration File Paths
======================================================================
✓ Loaded config from: /home/user/.config/ollmcp/config.json
  └─ 3 MCP server(s) configured:
     • filesystem
     • obsidian
     • git
  └─ Delegation system: configured
  └─ Memory system: enabled
  └─ Model intelligence: enabled

Configuration paths checked:
  ✓ Primary config: /home/user/.config/ollmcp/config.json
  ✗ Claude context: /home/user/.config/ollmcp/.config/CLAUDE.md
  ✗ Project config: /home/user/.config/ollmcp/.config/config.json
======================================================================
```

## API Usage

### List Servers with Status

Get all MCP servers with tool counts and enabled status:

```bash
curl "http://localhost:5222/api/tools/servers?session_id=abc123"
```

Response:
```json
{
  "servers": [
    {
      "name": "builtin",
      "tool_count": 15,
      "enabled_count": 15,
      "disabled_count": 0,
      "enabled": true,
      "partial": false
    },
    {
      "name": "filesystem",
      "tool_count": 8,
      "enabled_count": 5,
      "disabled_count": 3,
      "enabled": false,
      "partial": true
    },
    {
      "name": "obsidian",
      "tool_count": 6,
      "enabled_count": 6,
      "disabled_count": 0,
      "enabled": true,
      "partial": false
    }
  ]
}
```

**Field Descriptions:**
- `enabled`: `true` if all tools from the server are enabled
- `partial`: `true` if some (but not all) tools are enabled
- `enabled_count`: Number of enabled tools
- `disabled_count`: Number of disabled tools
- `tool_count`: Total number of tools from this server

### Toggle Server

Enable or disable all tools from a server:

```bash
curl -X POST http://localhost:5222/api/tools/servers/toggle \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123",
    "server_name": "obsidian",
    "enabled": false
  }'
```

Response:
```json
{
  "status": "ok",
  "server_name": "obsidian",
  "enabled": false
}
```

### Get Tools Grouped by Server

Get all tools organized by server:

```bash
curl "http://localhost:5222/api/tools/groups?session_id=abc123"
```

Response:
```json
{
  "groups": {
    "builtin": [
      {
        "name": "builtin.list_files",
        "description": "List files in a directory",
        "enabled": true
      },
      {
        "name": "builtin.read_file",
        "description": "Read file contents",
        "enabled": true
      }
    ],
    "filesystem": [
      {
        "name": "filesystem.read",
        "description": "Read a file",
        "enabled": true
      },
      {
        "name": "filesystem.write",
        "description": "Write to a file",
        "enabled": false
      }
    ],
    "obsidian": [
      {
        "name": "obsidian.get_note",
        "description": "Get an Obsidian note",
        "enabled": true
      }
    ]
  }
}
```

## Web UI Integration

### Current State

The existing web UI supports:
- ✅ Individual tool enable/disable via `/api/tools/toggle`
- ✅ List all tools via `/api/tools/list`
- ✅ List enabled/disabled tools

### New Capabilities

With the new server-level endpoints, the web UI can now:
- ✅ Display tools grouped by server
- ✅ Enable/disable entire servers with one click
- ✅ Show server-level status (enabled/partial/disabled)
- ✅ Provide better visual organization

### Recommended UI Layout

```
┌─────────────────────────────────────┐
│ Tools                               │
├─────────────────────────────────────┤
│ ☑ builtin (15 tools)                │
│   ├─ ☑ list_files                   │
│   ├─ ☑ read_file                    │
│   └─ ☑ write_file                   │
│                                     │
│ ☑ filesystem (8 tools)              │
│   ├─ ☑ read                         │
│   ├─ ☐ write                        │
│   └─ ☑ list                         │
│                                     │
│ ☐ obsidian (6 tools) [DISABLED]    │
│   ├─ ☐ get_note                     │
│   ├─ ☐ create_note                  │
│   └─ ☐ search_notes                 │
└─────────────────────────────────────┘
```

## Implementation Notes

### Current Limitations

1. **Persistence**: Tool enabled/disabled state is only saved in the current session cache. It does **not** persist to `config.json` yet.

   - When you create a new session, tools will reset to their default enabled state
   - To persist changes, you would need to manually edit `config.json`

2. **Workaround**: For now, to permanently disable a server's tools:
   - Edit your `config.json`
   - Remove the server from `mcpServers` section
   - Or add a `disabledTools` array to your config

### Future Enhancements

The following features are planned:

1. **Config Persistence** - Save tool/server enabled state to `config.json`
2. **Default States** - Load tool enabled states from config on session creation
3. **Per-User Preferences** - In Nextcloud mode, save preferences per user
4. **Tool Categories** - Group tools by function (filesystem, search, etc.) in addition to server
5. **Bulk Operations** - Enable/disable multiple servers at once

## Examples

### Disable All Tools from a Server

To disable all tools from the Obsidian server:

```javascript
// JavaScript/Fetch example
fetch('/api/tools/servers/toggle', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: sessionId,
    server_name: 'obsidian',
    enabled: false
  })
})
.then(res => res.json())
.then(data => console.log('Server toggled:', data));
```

### Build a Server Toggle UI

```javascript
// Get server list
fetch(`/api/tools/servers?session_id=${sessionId}`)
  .then(res => res.json())
  .then(data => {
    data.servers.forEach(server => {
      console.log(`${server.name}: ${server.enabled ? 'ON' : 'OFF'}`);
      console.log(`  ${server.enabled_count}/${server.tool_count} tools enabled`);
    });
  });
```

### Group Tools by Server in UI

```javascript
// Get grouped tools
fetch(`/api/tools/groups?session_id=${sessionId}`)
  .then(res => res.json())
  .then(data => {
    Object.entries(data.groups).forEach(([serverName, tools]) => {
      console.log(`\n${serverName}:`);
      tools.forEach(tool => {
        const status = tool.enabled ? '✓' : '✗';
        console.log(`  ${status} ${tool.name}`);
      });
    });
  });
```

## Comparison: CLI vs Web UI

### CLI (Command Line Interface)

```bash
# Disable an entire MCP server
ollmcp --disable-server obsidian

# List servers
ollmcp --list-servers

# Re-enable server
ollmcp --enable-server obsidian
```

### Web UI (Browser Interface)

```javascript
// Disable an entire MCP server
POST /api/tools/servers/toggle
{ "server_name": "obsidian", "enabled": false }

// List servers with status
GET /api/tools/servers

// Re-enable server
POST /api/tools/servers/toggle
{ "server_name": "obsidian", "enabled": true }
```

Both interfaces now provide equivalent functionality for server-level tool management.

## Troubleshooting

### Tools Not Persisting

**Problem**: Tool enabled/disabled state resets when creating a new session.

**Solution**: This is expected behavior in the current version. Tool state is only saved in the session cache. To make permanent changes:

1. Edit `~/.config/ollmcp/config.json`
2. Modify the `mcpServers` section
3. Restart the web server

### Server Not Found

**Problem**: `POST /api/tools/servers/toggle` returns 404 "Server not found"

**Possible causes**:
1. Server name is misspelled (case-sensitive)
2. Server has no tools loaded
3. Session ID is invalid

**Solution**: Call `GET /api/tools/servers` first to see available server names.

### Config Paths Not Showing

**Problem**: When starting web server, config paths section is empty.

**Solution**:
- Ensure you passed `--config-dir` parameter when starting the server
- Check that the config directory exists and is readable
- Verify `config.json` exists and is valid JSON

---

**Version**: 1.1
**Date**: 2026-01-26
**Status**: Fully Implemented (Including Persistence)
