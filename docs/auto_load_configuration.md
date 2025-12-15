# Auto-Load Configuration Feature

## Overview

The MCP Client for Ollama now supports automatic loading of project-specific configuration files from the `.config/` directory. This feature eliminates the need to repeatedly specify configuration options via command-line flags, making project-specific setups seamless and portable.

## Features

Two auto-loading capabilities are available:

1. **Project Context** (`.config/CLAUDE.md`) - Automatically loads project documentation and instructions
2. **Server Configuration** (`.config/config.json`) - Automatically loads MCP server configurations

## Auto-Loading Priority

The system follows a clear priority order to determine which configuration to use:

### Server Configuration Priority
1. `--servers-json` flag (highest priority)
2. `.config/config.json` (auto-loaded if no CLI flag)
3. `--auto-discovery` flag (falls back to Claude's config)
4. Auto-discovery from `~/Library/Application Support/Claude/claude_desktop_config.json` (default)

### System Prompt Priority
1. `.config/CLAUDE.md` content (highest priority - prepended)
2. Server config system prompts
3. User-configured system prompts

## Usage

### 1. Project Context (CLAUDE.md)

Create a `.config/CLAUDE.md` file in your project root to provide context about your project:

```markdown
# Project: My Awesome Project

## Overview
Brief description of your project.

## Code Style
- Python 3.10+
- Follow PEP 8
- Use type hints

## Architecture
Key components and their responsibilities.

## Development Guidelines
Important conventions and practices.
```

**On Startup:**
```bash
$ ollmcp
📋 Loaded project context from .config/CLAUDE.md
```

The AI now has immediate context about your project structure, conventions, and requirements.

### 2. Server Configuration (config.json)

Create a `.config/config.json` file to define your project's MCP servers:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/allowed/directory"
      ]
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your-api-key-here"
      }
    },
    "custom-tools": {
      "command": "python",
      "args": ["./scripts/custom_mcp_server.py"]
    }
  }
}
```

**On Startup:**
```bash
$ ollmcp
📋 Auto-loading server configuration from .config/config.json
📋 Loaded project context from .config/CLAUDE.md
```

## File Structure

```bash
your-project/
├── .config/
│   ├── CLAUDE.md         # Project context (tracked in git)
│   ├── config.json       # Server config (ignored by git)
│   ├── session1.json     # Session files (ignored by git)
│   └── session2.json     # Session files (ignored by git)
├── mcp_client_for_ollama/
└── ...
```

## Git Tracking

By default, the `.gitignore` is configured as follows:

| File | Purpose | Git Tracked |
|------|---------|-------------|
| `.config/CLAUDE.md` | Project documentation | ✅ Yes (always) |
| `.config/config.json` | Server configuration | ❌ No (opt-in) |
| `.config/*.json` | Session files | ❌ No (always ignored) |

### Why config.json is not tracked by default

Server configurations often contain:
- Local file paths specific to each developer's machine
- API keys and credentials
- Developer-specific tool preferences

If you want to share server configuration with your team:

```bash
# Explicitly add to git
git add -f .config/config.json
git commit -m "Add shared server configuration"
```

## Overriding Auto-Load Behavior

### Override Server Configuration

Use command-line flags to override `.config/config.json`:

```bash
# Use a different config file
$ ollmcp --servers-json ~/my-test-servers.json

# Use auto-discovery instead
$ ollmcp --auto-discovery

# Specify servers directly
$ ollmcp --mcp-server ./path/to/server.py
```

### Override Project Context

The project context from `CLAUDE.md` is always loaded if the file exists. To modify the system prompt after startup:

```bash
# In the ollmcp interactive session
model/[ACT]/8-tools❯ model-config
# Then edit the system prompt
```

## Use Cases

### 1. Project-Specific Development Environment

Set up once per project, use forever:

```bash
# Initialize project config
mkdir -p .config

# Add project documentation
cat > .config/CLAUDE.md << 'EOF'
# My Web API Project
- REST API using FastAPI
- PostgreSQL database
- pytest for testing
EOF

# Add server configuration
cat > .config/config.json << 'EOF'
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"]
    }
  }
}
EOF

# Now every time you start:
$ ollmcp
# Everything is configured automatically!
```

### 2. Team Onboarding

New team members get instant context:

```bash
# New developer clones repo
$ git clone https://github.com/yourteam/project.git
$ cd project

# CLAUDE.md is already there from git
# They just need to create their local config.json
$ cp .config/config.json.example .config/config.json
$ # Edit with their local paths

$ ollmcp
📋 Loaded project context from .config/CLAUDE.md
# Ready to work with full project context!
```

### 3. Multiple Environments

Different configurations for different contexts:

```bash
# Development (uses .config/config.json)
$ ollmcp

# Testing (override with test servers)
$ ollmcp --servers-json .config/test-servers.json

# Production debugging (use production config)
$ ollmcp --servers-json ~/.config/prod-servers.json
```

## CLI Help

View auto-load documentation:

```bash
$ ollmcp --help

  --servers-json, -j TEXT
      Path to a JSON file with server configurations.
      If not specified, .config/config.json will be
      auto-loaded if it exists.
```

In the interactive help:

```bash
model/[ACT]/8-tools❯ help

Auto-Loading (on startup):
• Create .config/CLAUDE.md to automatically load project context
• Create .config/config.json to automatically load server configuration
```

## Benefits

✅ **Zero Configuration**: Just create the files, they work automatically
✅ **Project-Scoped**: Each project maintains its own configuration
✅ **Portable**: Share project context via git, keep local configs private
✅ **Override-able**: Command-line flags work when you need them
✅ **Team-Friendly**: Consistent experience across team members
✅ **Context-Aware**: AI has immediate understanding of your project

## Troubleshooting

### Auto-load not working

Check if files exist and are in the right location:

```bash
$ ls -la .config/
# Should show CLAUDE.md and/or config.json
```

### Wrong config being loaded

Check the startup messages:

```bash
$ ollmcp
📋 Auto-loading server configuration from .config/config.json
```

If you see this but want to use a different config:

```bash
$ ollmcp --servers-json /path/to/other/config.json
```

### CLAUDE.md not loading project context

Verify the file is readable and contains valid markdown:

```bash
$ cat .config/CLAUDE.md
# Should display content
```

Check startup messages for confirmation:

```bash
$ ollmcp
📋 Loaded project context from .config/CLAUDE.md
```

## Migration from Manual Configuration

### Before (manual flags every time):

```bash
$ ollmcp --servers-json ~/my-servers.json --model qwen3
$ ollmcp --servers-json ~/my-servers.json --model qwen3
$ ollmcp --servers-json ~/my-servers.json --model qwen3
```

### After (auto-load):

```bash
# One-time setup
$ cp ~/my-servers.json .config/config.json

# Every subsequent use
$ ollmcp
📋 Auto-loading server configuration from .config/config.json
```

## Example Project Setup

Complete example for a Python web application:

```bash
# 1. Create .config directory
mkdir -p .config

# 2. Add project context
cat > .config/CLAUDE.md << 'EOF'
# Python Web API Project

## Tech Stack
- FastAPI for REST API
- SQLAlchemy for ORM
- PostgreSQL database
- Pytest for testing

## Code Style
- Follow PEP 8
- Use type hints
- Docstrings for all public functions

## Project Structure
- `src/api/` - API endpoints
- `src/models/` - Database models
- `src/services/` - Business logic
- `tests/` - Test suite

## Development Commands
- `pytest` - Run tests
- `uvicorn src.main:app --reload` - Start dev server
EOF

# 3. Add server configuration (local, not committed)
cat > .config/config.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/user/projects/myapp"
      ]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_URI": "postgresql://localhost/myapp_dev"
      }
    }
  }
}
EOF

# 4. Optional: Create shared config template for team
cat > .config/config.json.example << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/PATH/TO/YOUR/PROJECT"
      ]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_URI": "postgresql://localhost/YOUR_DB"
      }
    }
  }
}
EOF

# 5. Commit the project context and example config
git add .config/CLAUDE.md .config/config.json.example
git commit -m "Add project context and config template"

# 6. Ready to use!
$ ollmcp
📋 Auto-loading server configuration from .config/config.json
📋 Loaded project context from .config/CLAUDE.md
```

## See Also

- [Session and Built-in Tools Migration](session_builtin_tools_migration.md)
- [Tool Request Format Support](tool_request_format_support.md)
- [Built-in Tools Documentation](builtin_tools_bug_fix.md)
