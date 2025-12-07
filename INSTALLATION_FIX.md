# Installation Fix - Missing Agents Module

**Issue:** `ModuleNotFoundError: No module named 'mcp_client_for_ollama.agents'`

**Cause:** The `agents` subpackage and its JSON configuration files were not included in the package distribution.

**Fixed in:** Version 0.23.0

---

## What Was Fixed

Updated `pyproject.toml` to include:

1. **Added `mcp_client_for_ollama.agents` to packages list**
   ```toml
   [tool.setuptools]
   packages = [
       "mcp_client_for_ollama",
       "mcp_client_for_ollama.agents",  # <-- ADDED
       "mcp_client_for_ollama.config",
       ...
   ]
   ```

2. **Added package data for JSON files**
   ```toml
   [tool.setuptools.package-data]
   "mcp_client_for_ollama.agents" = ["definitions/*.json", "examples/*.json"]
   ```

---

## Files Now Included in Distribution

The wheel package now includes:

### Python modules:
- `mcp_client_for_ollama/agents/__init__.py`
- `mcp_client_for_ollama/agents/agent_config.py`
- `mcp_client_for_ollama/agents/delegation_client.py`
- `mcp_client_for_ollama/agents/model_pool.py`
- `mcp_client_for_ollama/agents/task.py`

### Agent definitions (10 JSON files):
- `mcp_client_for_ollama/agents/definitions/coder.json`
- `mcp_client_for_ollama/agents/definitions/debugger.json`
- `mcp_client_for_ollama/agents/definitions/executor.json`
- `mcp_client_for_ollama/agents/definitions/lyricist.json`
- `mcp_client_for_ollama/agents/definitions/obsidian.json`
- `mcp_client_for_ollama/agents/definitions/planner.json`
- `mcp_client_for_ollama/agents/definitions/reader.json`
- `mcp_client_for_ollama/agents/definitions/researcher.json`
- `mcp_client_for_ollama/agents/definitions/style_designer.json`
- `mcp_client_for_ollama/agents/definitions/suno_composer.json`

### Planning examples:
- `mcp_client_for_ollama/agents/examples/planner_examples.json` (15 examples)

---

## How to Install (System-wide)

### Method 1: Install from source (local)
```bash
# Clone and navigate to repo
git clone https://github.com/jonigl/mcp-client-for-ollama.git
cd mcp-client-for-ollama

# Pull latest changes (includes fix)
git pull origin main

# Install system-wide with uv
sudo uv pip install . --system

# Or with pip
sudo pip install .
```

### Method 2: Install from PyPI (when published)
```bash
# Will work once v0.23.0 is published to PyPI
sudo uv pip install --upgrade mcp-client-for-ollama --system
```

### Method 3: Install from built wheel
```bash
# Build the wheel
python -m build --wheel

# Install the wheel
sudo uv pip install dist/mcp_client_for_ollama-0.23.0-py3-none-any.whl --system
```

---

## Verification

After installation, verify the agents module is available:

```bash
python -c "
from mcp_client_for_ollama.agents.delegation_client import DelegationClient
from mcp_client_for_ollama.agents.agent_config import AgentConfig
configs = AgentConfig.load_all_definitions()
print(f'✅ Successfully loaded {len(configs)} agents: {sorted(configs.keys())}')
"
```

Expected output:
```
✅ Successfully loaded 10 agents: ['CODER', 'DEBUGGER', 'EXECUTOR', 'LYRICIST', 'OBSIDIAN', 'PLANNER', 'READER', 'RESEARCHER', 'STYLE_DESIGNER', 'SUNO_COMPOSER']
```

Then run `ollmcp` to start the application.

---

## For Package Maintainers

If you're maintaining a fork or custom package, ensure your `pyproject.toml` includes:

```toml
[tool.setuptools]
packages = [
    "mcp_client_for_ollama",
    "mcp_client_for_ollama.agents",      # Required for delegation system
    "mcp_client_for_ollama.config",
    "mcp_client_for_ollama.models",
    "mcp_client_for_ollama.server",
    "mcp_client_for_ollama.tools",
    "mcp_client_for_ollama.utils"
]

[tool.setuptools.package-data]
"mcp_client_for_ollama.agents" = ["definitions/*.json", "examples/*.json"]
```

This ensures all agent definitions and examples are included in the distribution.
