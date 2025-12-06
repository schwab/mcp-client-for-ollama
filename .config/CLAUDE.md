# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MCP Client for Ollama** (`ollmcp`) is an interactive terminal application (TUI) for connecting local Ollama LLMs to Model Context Protocol (MCP) servers. It enables local models to use tools and integrate with external services via a sophisticated orchestration layer.

- **Language:** Python 3.10+
- **Package Manager:** UV (uv)
- **Main Entry Point:** `mcp_client_for_ollama/cli.py` → `mcp_client_for_ollama/client.py`
- **Current Version:** 0.22.0

## Common Development Commands

### Setup and Installation

```bash
# Create and activate virtual environment
uv venv && source .venv/bin/activate

# Install in development mode
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"
```

### Running the Application

```bash
# Run the CLI
ollmcp

# Run with specific model and auto-discovery
ollmcp --model qwen3 --auto-discovery

# Run with specific MCP servers
ollmcp -s /path/to/server.py -m llama3.2:3b

# Run from source
uv run -m mcp_client_for_ollama
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_client.py

# Run tests matching a pattern
uv run pytest -k "tool_parser"

# Run with verbose output
uv run pytest -v

# Run a single test function
uv run pytest tests/test_tool_parser.py::test_parse_json_tool_call -v
```

### Version Management

The project has two packages that must stay in sync: `mcp-client-for-ollama` (main) and `ollmcp` (CLI wrapper).

```bash
# Bump patch version (0.22.0 -> 0.22.1)
python scripts/bump_version.py patch

# Bump minor version (0.22.0 -> 0.23.0)
python scripts/bump_version.py minor

# Bump major version
python scripts/bump_version.py major

# Preview changes without applying
python scripts/bump_version.py patch --dry-run
```

The script updates both packages' `pyproject.toml` and `__init__.py` files automatically.

### Building

```bash
# Build distribution packages
python -m build

# Build main package
cd . && python -m build

# Build CLI package
cd cli-package && python -m build
```

## Architecture Overview

### Directory Structure

```
mcp-client-for-ollama/
├── mcp_client_for_ollama/       # Main source code
│   ├── cli.py                   # CLI entry point (uses Typer)
│   ├── client.py                # MCPClient - main orchestrator (~1500 lines)
│   ├── config/                  # Configuration persistence (save/load)
│   ├── models/                  # Ollama model selection and parameters
│   ├── server/                  # MCP server connections (STDIO/SSE/HTTP)
│   ├── tools/                   # Tool management and built-in tools
│   └── utils/                   # Utilities (streaming, parsing, display)
├── cli-package/                 # CLI wrapper package (ollmcp)
├── tests/                       # Test suite (pytest)
├── scripts/                     # Utility scripts (version bumping)
└── docs/                        # Additional documentation
```

### Key Components and Responsibilities

#### **MCPClient** (`client.py` - ~1500 lines)
The central orchestrator managing the entire TUI application:
- Interactive chat loop with command processing
- State management (chat history, configuration, settings)
- Coordinates communication between Ollama, MCP servers, and tools
- Handles configuration persistence (save/load/reset)
- Implements agent mode (iterative tool execution)
- Session management (save/load chat history)

**Key Methods:**
- `chat_loop()` - Main interactive loop
- `process_query()` - Handles user queries and tool execution
- `connect_to_servers()` - Establishes MCP server connections
- `select_tools()` / `select_model()` - Interactive selection interfaces
- `configure_model_options()` - Advanced model parameter configuration
- `save_session()` / `load_session()` - Session persistence
- `save_configuration()` / `load_configuration()` - Config persistence

#### **ServerConnector** (`server/connector.py`)
Manages MCP server connections:
- Supports multiple connection types: STDIO (scripts), SSE, Streamable HTTP
- Manages tool availability from connected servers
- Handles server discovery and configuration loading
- Extracts system prompts from server configs
- Provides hot-reload capability

#### **ToolManager** (`tools/manager.py`)
Manages tool selection and availability:
- Enables/disables tools for model use
- Provides interactive tool selection interface
- Organizes tools by server
- Integrates built-in tools (`builtin.set_system_prompt`, `builtin.get_system_prompt`, `builtin.execute_python_code`, `builtin.execute_bash_command`)

#### **ModelManager & ModelConfigManager** (`models/manager.py`, `models/config_manager.py`)
- Lists available Ollama models
- Allows dynamic model switching
- Manages 15+ model parameters (temperature, sampling, context window, etc.)
- Provides interactive configuration interface
- Only sends configured (non-None) parameters to preserve Ollama defaults

#### **ConfigManager** (`config/manager.py`)
Configuration persistence:
- Save/load user configurations in `~/.config/ollmcp/`
- Default config: `~/.config/ollmcp/config.json`
- Named configs: `~/.config/ollmcp/{name}.json`
- Persists: model, tools, parameters, context settings, display preferences

#### **ToolParser** (`utils/tool_parser.py`)
Tool call extraction with composite pattern supporting:
1. **JSON Format** - Standard function call syntax
2. **Python Format** - Python code execution
3. **XML Format** - `<tool_request>...</tool_request>` delimited calls

#### **StreamingManager** (`utils/streaming.py`)
Response processing:
- Handles streaming responses from Ollama
- Manages thinking mode content (for models like DeepSeek R1, Qwen3)
- Extracts tool calls from responses
- Captures performance metrics
- Real-time display handling

#### **HumanInTheLoopManager** (`utils/hil_manager.py`)
Safety controls:
- Tool execution approval workflow
- Global, per-server, and per-tool configuration
- Interactive HIL management

### Data Flow: Query Processing

```
User Input (CLI)
  ↓
[Special Command?] → Execute command handler
  ↓
[Regular Query] → MCPClient.process_query()
  ↓
Build messages (context + system prompt)
  ↓
Get enabled tools from ToolManager
  ↓
Call Ollama Chat API (streaming)
  ↓
StreamingManager.process_streaming_response()
  ├─→ Handle thinking mode (if enabled)
  ├─→ Extract tool calls via ToolParser (JSON/Python/XML)
  └─→ Extract metrics
  ↓
[Loop] For each tool_call AND loop_count < loop_limit:
  ├─→ Check server membership
  ├─→ Request HIL confirmation (if enabled)
  ├─→ Execute on server session
  └─→ Append result to messages
  ↓
Append query + final response to chat_history
```

### Configuration Management

Configurations are stored in `~/.config/ollmcp/` as JSON and include:
- Selected model and model parameters (temperature, context window, etc.)
- Enabled/disabled tools per server
- Context retention preference
- Thinking mode settings
- Agent loop limit
- Display preferences (metrics, thinking, tool execution)
- Human-in-the-Loop settings
- Session save directory preference

Loads automatically from `~/.config/ollmcp/config.json` on startup if it exists.

## Interactive Commands

The application supports 40+ interactive commands with shortcut aliases. Key categories:

**Model Control:** `model`/`m`, `model-config`/`mc`
**Tool Management:** `tools`/`t`, `show-tool-execution`/`ste`
**Agent Mode:** `loop-limit`/`ll` (controls iterative tool execution)
**Context:** `context`/`c`, `clear`/`cc`, `context-info`/`ci`
**Session:** `save-session`/`ss`, `load-session`/`ls`
**Configuration:** `save-config`/`sc`, `load-config`/`lc`, `reset-config`/`rc`
**Thinking Mode:** `thinking-mode`/`tm`, `show-thinking`/`st`
**Safety:** `human-in-loop`/`hil`
**Utility:** `help`/`h`, `quit`/`q`

## Key Features and Implementation

### Agent Mode (Iterative Tool Execution)
- Location: `MCPClient.process_query()` lines ~561-667
- Loop continues while pending tool calls exist
- Configurable loop limit (default: 3) via `loop-limit` command
- Prevents infinite loops through iteration limit

### Thinking Mode
- Supported by models like DeepSeek R1, GPT-OSS, Qwen3
- Separate thinking content handling in StreamingManager
- Toggle with `thinking-mode` command
- Control visibility with `show-thinking` command

### Multiple Tool Call Formats
Support three parsing formats to handle different model outputs:
- JSON function calls
- Python code execution
- XML `<tool_request>` tags (recent addition)

### Multi-Server Support
- STDIO (script-based) servers
- SSE (Server-Sent Events)
- Streamable HTTP endpoints
- Tools namespaced by server (e.g., `filesystem.read_file`)
- Hot-reload without restart via `reload-servers` command

### Auto-Discovery
- Default behavior if no server options specified
- Sources Claude's desktop config: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Extracts system prompts from configurations

### Human-in-the-Loop Safety
- Global enable/disable toggle
- Per-server configuration
- Per-tool configuration
- Interactive approval before tool execution

## Testing

Tests use **pytest** (~8.4.2). Test files located in `tests/`:

```
test_builtin_tools.py     - Built-in tool functionality
test_connector.py         - Server connection logic
test_hil_manager.py       - Human-in-the-Loop safety
test_mcp_client.py        - Main client functionality
test_server_discovery.py  - Auto-discovery logic
test_tool_parser.py       - Composite tool parser
test_tool_parsers.py      - Individual parser implementations
test_version.py           - Version checking
```

Run tests with: `uv run pytest` or for specific tests: `uv run pytest tests/test_client.py -v`

## Dependencies

**Core Dependencies:**
- `mcp~=1.21.0` - Model Context Protocol
- `ollama~=0.6.0` - Ollama client
- `prompt-toolkit~=3.0.52` - Interactive terminal UI
- `rich~=14.2.0` - Terminal formatting
- `typer~=0.20.0` - CLI framework

**Dev Dependencies:**
- `pytest~=8.4.2` - Testing

See `pyproject.toml` for the full specification.

## Release Process

Uses GitHub Actions for automated testing and publishing:

1. Bump version: `python scripts/bump_version.py [patch|minor|major]`
2. Commit: `git add -A && git commit -m "chore(release): bump version to X.Y.Z"`
3. Tag: `git tag -a vX.Y.Z -m "Version X.Y.Z"`
4. Push: `git push origin main --tags`

GitHub Actions will automatically build and publish both packages to PyPI.

## Important Patterns and Conventions

### Composite Pattern
ToolParser uses composition with sub-parsers for different tool call formats (JSON, Python, XML).

### Manager Pattern
Separate manager classes for different concerns: ServerConnector, ToolManager, ModelManager, ConfigManager, etc.

### State Management
MCPClient maintains central application state and coordinates all managers.

### Async/Await
Throughout codebase for non-blocking I/O with Ollama API and servers.

### Configuration Defaults
All model parameters default to `None` (unset), allowing Ollama to use its optimized values. Only configured parameters are sent to the API.

## Notes for Implementation

- **Python 3.10+ required** - Use modern Python features (walrus operator, match/case, etc.)
- **STDIO servers** support both Python and JavaScript MCP servers
- **No external state files** outside `~/.config/ollmcp/` should be created
- **Streaming responses** must preserve real-time display in terminal
- **Tool execution** respects enabled/disabled state per tool
- **Context management** only includes tools when enabled
- **Version consistency** - both packages must have matching versions

## Security Considerations

- Keep dependencies up to date
- MCP servers are external code - validate before use
- HIL provides safety controls for untrusted tools
- Configuration files may contain sensitive data (API keys in server configs)
- Never commit `.env` files or credentials

See `SECURITY.md` for vulnerability reporting guidelines.
