"""Constants used throughout the MCP Client for Ollama application."""

import os
import platform

# Default Claude config file location (platform-specific)
_system = platform.system()
if _system == "Darwin":  # macOS
    DEFAULT_CLAUDE_CONFIG = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
elif _system == "Windows":
    DEFAULT_CLAUDE_CONFIG = os.path.expanduser("~/AppData/Roaming/Claude/claude_desktop_config.json")
else:  # Linux and other Unix-like systems
    DEFAULT_CLAUDE_CONFIG = os.path.expanduser("~/.config/Claude/claude_desktop_config.json")

# Default config directory and filename for MCP client for Ollama
# Note: Directory creation is handled by ConfigManager when needed, not at import time
DEFAULT_CONFIG_DIR = ".config"
DEFAULT_CONFIG_FILE = "config.json"

# Default model
DEFAULT_MODEL = "qwen2.5:32b"

# Default ollama lcoal url for API requests
DEFAULT_OLLAMA_HOST = "https://vicunaapi.ngrok.io"


# URL for checking package updates on PyPI
PYPI_PACKAGE_URL = "https://pypi.org/pypi/mcp-client-for-ollama/json"

# MCP Protocol Version
MCP_PROTOCOL_VERSION = "2025-06-18"

# Interactive commands and their descriptions for autocomplete
INTERACTIVE_COMMANDS = {
    'bye': ('Exit the application', False),
    'q': ('Exit the application', False),
    'exit': ('Exit the application', False),
    'quit': ('Exit the application', False),

    'clear-screen': ('Clear terminal screen', False),
    'cls': ('Clear terminal screen', False),

    'clear': ('Clear conversation context', False),
    'cc': ('Clear conversation context', False),

    'context-info': ('Show context information', False),
    'ci': ('Show context information', False),

    'context': ('Toggle context retention', False),
    'c': ('Toggle context retention', False),

    'help': ('Show help information', False),
    'h': ('Show help information', False),

    'human-in-the-loop': ('Toggle global HIL confirmations', False),
    'hil': ('Toggle global HIL confirmations', False),

    'hil-config': ('Configure granular HIL settings', True), # NEW
    'hc': ('Configure granular HIL settings', True), # NEW

    'load-config': ('Load saved configuration', False),
    'lc': ('Load saved configuration', False),

    'loop-limit': ('Set agent max loop limit', False),
    'll': ('Set agent max loop limit', False),

    'plan-mode': ('Toggle PLAN/ACT mode (Shift+Tab)', True), # NEW
    'pm': ('Toggle PLAN/ACT mode (Shift+Tab)', True), # NEW

    'model-config': ('Configure model parameters', False),
    'mc': ('Configure model parameters', False),

    'model': ('Select Ollama model', False),
    'm': ('Select Ollama model', False),

    'reload-servers': ('Reload MCP servers', False),
    'rs': ('Reload MCP servers', False),

    'reparse-last': ('Re-run tool parser on last response', True), # NEW
    'rl': ('Re-run tool parser on last response', True), # NEW

    'reset-config': ('Reset to default config', False),
    'rc': ('Reset to default config', False),

    'save-config': ('Save current configuration', False),
    'sc': ('Save current configuration', False),

    'save-session': ('Save current chat session', True), # NEW
    'ss': ('Save current chat session', True), # NEW

    'load-session': ('Load previous chat session', True), # NEW
    'ls': ('Load previous chat session', True), # NEW

    'session-dir': ('Change session save directory', False),
    'sd': ('Change session save directory', False),

    'show-metrics': ('Toggle performance metrics display', False),
    'sm': ('Toggle performance metrics display', False),

    'show-thinking': ('Toggle thinking visibility', False),
    'st': ('Toggle thinking visibility', False),

    'show-tool-execution': ('Toggle tool execution display', False),
    'ste': ('Toggle tool execution display', False),

    'thinking-mode': ('Toggle thinking mode', False),
    'tm': ('Toggle thinking mode', False),

    'tools': ('Configure available tools', False),
    't': ('Configure available tools', False),

    'execute-python-code': ('Execute arbitrary Python code', True), # NEW
    'epc': ('Execute arbitrary Python code', True), # NEW

    'delegate': ('Use multi-agent delegation (delegate <query>)', True), # NEW
    'd': ('Use multi-agent delegation (d <query>)', True), # NEW

    'delegation-trace': ('Configure delegation trace logging', True), # NEW
    'dt': ('Configure delegation trace logging', True), # NEW
    'trace-config': ('Configure delegation trace logging', True), # NEW
    'tc': ('Configure delegation trace logging', True), # NEW

    'memory-sessions': ('List all memory sessions', True), # NEW
    'ms': ('List all memory sessions', True), # NEW

    'memory-resume': ('Resume a memory session', True), # NEW
    'mr': ('Resume a memory session', True), # NEW

    'memory-new': ('Create a new memory session', True), # NEW
    'mn': ('Create a new memory session', True), # NEW

    'memory-status': ('Show current memory session status', True), # NEW
    'mst': ('Show current memory session status', True), # NEW

    'memory-enable': ('Enable the memory system', True), # NEW
    'me': ('Enable the memory system', True), # NEW

    'memory-disable': ('Disable the memory system', True), # NEW
    'md': ('Disable the memory system', True), # NEW
}

# Default completion menu style (used by prompt_toolkit in interactive mode)
DEFAULT_COMPLETION_STYLE = {
    'prompt': 'ansibrightyellow bold',
    'completion-menu.completion': 'bg:#1e1e1e #ffffff',
    'completion-menu.completion.current': 'bg:#1e1e1e #00ff00 bold reverse',
    'completion-menu.meta': 'bg:#1e1e1e #888888 italic',
    'completion-menu.meta.current': 'bg:#1e1e1e #ffffff italic reverse',
    'bottom-toolbar': 'reverse',
}
