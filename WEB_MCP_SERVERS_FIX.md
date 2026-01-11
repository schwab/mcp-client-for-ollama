# Web MCP Servers Fix - v0.44.4

**Issue**: Web interface only showed builtin tools, while CLI showed all MCP servers (biblerag, obsidian)

**Status**: ✅ FIXED in v0.44.4

---

## The Problem

When starting the web server with a config file:
```bash
python3 -m mcp_client_for_ollama web --config-dir /home/mcstar/Nextcloud/Vault/Journal/.config
```

**Before v0.44.4:**
- Web interface: Only builtin tools visible
- CLI version: All tools visible (builtin + biblerag + obsidian)

**Root Cause:**
The `run_web_server()` function in `web/app.py` only stored the `config_dir` path without actually loading the config.json file. This meant the `mcpServers` section was never read, so web sessions had no knowledge of configured MCP servers.

---

## The Fix

**File**: `mcp_client_for_ollama/web/app.py` (lines 204-230)

**What changed:**
```python
# BEFORE (v0.44.3 and earlier):
set_global_config({
    'ollama_host': ollama_host,
    'config_dir': config_dir  # Just the path, not the content!
})

# AFTER (v0.44.4):
global_config = {'ollama_host': ollama_host, 'config_dir': config_dir}

if config_dir:
    config_file = os.path.join(config_dir, 'config.json')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            file_config = json.load(f)
        # Merge ALL config settings including mcpServers
        global_config.update(file_config)
        global_config['config_dir'] = config_dir  # Preserve path
        print(f"Loaded config from: {config_file}")
        if 'mcpServers' in file_config:
            print(f"Found {len(file_config['mcpServers'])} MCP server(s) in config")

set_global_config(global_config)
```

**Result:**
- Config file is now loaded and parsed
- mcpServers section is available in global config
- All sessions created by web interface have access to MCP server definitions

---

## How It Works Now

1. **Server Startup:**
   ```bash
   python3 -m mcp_client_for_ollama web --config-dir /path/to/.config
   ```

2. **Config Loading:**
   - `run_web_server()` loads `/path/to/.config/config.json`
   - Parses JSON and extracts `mcpServers` section
   - Merges into global config
   - Logs: "Loaded config from: ..." and "Found 3 MCP server(s) in config"

3. **Session Creation:**
   - Browser requests `/api/sessions/create`
   - `create_session()` calls `get_global_config()`
   - Returns config WITH mcpServers
   - Creates `WebMCPClient` with full config

4. **MCP Client Initialization:**
   - `WebMCPClient` receives config with `config_dir`
   - Uses provided config_dir (doesn't create temp dir)
   - `_create_mcp_client()` finds config.json at that path
   - `MCPClient.connect_to_servers()` loads MCP servers from config
   - Tools from biblerag and obsidian now available!

---

## Testing Steps

### 1. Start Web Server
```bash
cd /home/mcstar/Nextcloud/DEV/ollmcp/mcp-client-for-ollama
python3 -m mcp_client_for_ollama web --config-dir /home/mcstar/Nextcloud/Vault/Journal/.config
```

### 2. Check Console Output
You should see:
```
Loaded config from: /home/mcstar/Nextcloud/Vault/Journal/.config/config.json
Found 3 MCP server(s) in config
Starting MCP Client Web Server on http://0.0.0.0:5222
Ollama API: http://localhost:11434
```

### 3. Open Web UI
```
http://localhost:5222
```

### 4. Check Tools Panel (Left Sidebar)
You should now see tools from:
- ✅ **biblerag** (enabled: true in config)
  - Example: biblerag.search_verses, biblerag.get_commentary, etc.
- ✅ **obsidian** (enabled: true in config)
  - Example: obsidian.create_note, obsidian.search_notes, etc.
- ❌ **nextcloud-api** (enabled: false in config - correctly excluded)
- ✅ **builtin** (always available)
  - Example: builtin.read_file, builtin.list_files, etc.

### 5. Verify MCP Server Count
In browser console (F12), check network tab for `/api/tools/list`:
```json
{
  "tools": [
    {"name": "biblerag.search_verses", ...},
    {"name": "obsidian.create_note", ...},
    {"name": "builtin.read_file", ...},
    ...
  ]
}
```

Should have tools from multiple servers, not just builtin.

---

## Config File Reference

Your config at `/home/mcstar/Nextcloud/Vault/Journal/.config/config.json` has:

```json
{
  "mcpServers": {
    "nextcloud-api": {
      "enabled": false,  // ❌ Will NOT be loaded
      "url": "http://127.0.0.1:8005/mcp"
    },
    "biblerag": {
      "enabled": true,   // ✅ WILL be loaded
      "type": "sse",
      "url": "http://localhost:8010/sse"
    },
    "obsidian": {
      "enabled": true,   // ✅ WILL be loaded
      "command": "uvx",
      "args": ["mcp-obsidian"],
      "env": {
        "OBSIDIAN_API_KEY": "...",
        "OBSIDIAN_HOST": "127.0.0.1",
        "OBSIDIAN_PORT": "27124"
      }
    }
  }
}
```

**Expected Result:**
- Web interface loads 2 MCP servers (biblerag + obsidian)
- nextcloud-api correctly excluded (enabled: false)
- Same behavior as CLI version

---

## Troubleshooting

### If MCP servers still don't appear:

1. **Check console output** when starting web server
   - Should see "Loaded config from: ..." and "Found X MCP server(s)"
   - If not, config file may not be found

2. **Verify config file path**
   ```bash
   ls -la /home/mcstar/Nextcloud/Vault/Journal/.config/config.json
   # Should exist and be readable
   ```

3. **Check MCP servers are running**
   ```bash
   # Test biblerag
   curl http://localhost:8010/sse
   
   # Test obsidian (if local API is running)
   # Check that Obsidian is running with Local REST API plugin
   ```

4. **Check browser console (F12)**
   - Look for errors in Network tab when loading tools
   - Check `/api/tools/list` response

5. **Compare with CLI**
   ```bash
   # Test that CLI works
   python3 -m mcp_client_for_ollama --config /home/mcstar/Nextcloud/Vault/Journal/.config/config.json
   
   # List tools in CLI
   # Should see biblerag and obsidian tools
   ```

---

## Version History

- **v0.44.3**: Web only showed builtin tools (BUG)
- **v0.44.4**: Web loads all MCP servers from config (FIXED)

---

**Status**: ✅ Ready for testing
**Action**: Restart web server with --config-dir flag and verify tools appear
