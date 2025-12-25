<p align="center">

  <img src="https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-logo-512.png?raw=true" width="256" />
</p>
<p align="center">
<i>A simple yet powerful Python client for interacting with Model Context Protocol (MCP) servers using Ollama, allowing local LLMs to use tools.</i>
</p>
<p>
This fork of the MCP Client for Ollama is an attempt to overcome the limitations of context windows size of the OLLAMA models by introducing a full Agent Planning system and memory context to support long running problems that span multiple sessions. To accomplish this, claude is leverged heavily and the result is an async code base that has diverted greatly form the original project. 

</p>
<p>

</p>
---

# MCP Client for Ollama (ollmcp)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI - Python Version](https://img.shields.io/pypi/v/ollmcp?label=ollmcp-pypi)](https://pypi.org/project/ollmcp/)
[![PyPI - Python Version](https://img.shields.io/pypi/v/mcp-client-for-ollama?label=mcp-client-for-ollama-pypi)](https://pypi.org/project/mcp-client-for-ollama/)
[![Build, Publish and Release](https://github.com/jonigl/mcp-client-for-ollama/actions/workflows/publish.yml/badge.svg)](https://github.com/jonigl/mcp-client-for-ollama/actions/workflows/publish.yml)
[![CI](https://github.com/jonigl/mcp-client-for-ollama/actions/workflows/ci.yml/badge.svg)](https://github.com/jonigl/mcp-client-for-ollama/actions/workflows/ci.yml)

<p align="center">
  <img src="https://raw.githubusercontent.com/jonigl/mcp-client-for-ollama/v0.15.0/misc/ollmcp-demo.gif" alt="MCP Client for Ollama Demo">
</p>
<p align="center">
  <a href="https://asciinema.org/a/jxc6N8oKZAWrzH8aK867zhXdO" target="_blank">🎥 Watch this demo as an Asciinema recording</a>
</p>

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Command-line Arguments](#command-line-arguments)
  - [Usage Examples](#usage-examples)
  - [How Tool Calls Work](#how-tool-calls-work)
  - [Agent Mode](#agent-mode)
- [Interactive Commands](#interactive-commands)
  - [Tool and Server Selection](#tool-and-server-selection)
  - [Model Selection](#model-selection)
  - [Advanced Model Configuration](#advanced-model-configuration)
  - [Server Reloading for Development](#server-reloading-for-development)
  - [Human-in-the-Loop (HIL) Tool Execution](#human-in-the-loop-hil-tool-execution)
  - [Performance Metrics](#performance-metrics)
- [Multi-Modal Support (Image Analysis)](#multi-modal-support-image-analysis)
- [Autocomplete and Prompt Features](#autocomplete-and-prompt-features)
- [Configuration Management](#configuration-management)
- ✨**NEW** [Auto-Load Configuration](#auto-load-configuration)
- ✨**NEW** [Save and Load Session](#save-and-load-session)
- [Server Configuration Format](#server-configuration-format)
  - [Tips: Where to Put MCP Server Configs and a Working Example](#tips-where-to-put-mcp-server-configs-and-a-working-example)
- [Compatible Models](#compatible-models)
  - [Ollama Cloud Models](#ollama-cloud-models)
- [Where Can I Find More MCP Servers?](#where-can-i-find-more-mcp-servers)
- [Related Projects](#related-projects)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Overview

MCP Client for Ollama (`ollmcp`) is a modern, interactive terminal application (TUI) for connecting local Ollama LLMs to one or more Model Context Protocol (MCP) servers, enabling advanced tool use and workflow automation. With a rich, user-friendly interface, it lets you manage tools, models, and server connections in real time—no coding required. Whether you're building, testing, or just exploring LLM tool use, this client streamlines your workflow with features like fuzzy autocomplete, advanced model configuration, MCP servers hot-reloading for development, and Human-in-the-Loop safety controls.

## Features

- 🎯 **Agent Delegation System**: Break down complex multi-file tasks into focused subtasks executed by specialized agents (READER, CODER, EXECUTOR, RESEARCHER, DEBUGGER). Perfect for small models with limited context windows! ([docs](docs/agent-delegation-user-guide.md))
- 🤖 **Agent Mode**: Iterative tool execution when models request multiple tool calls, with a configurable loop limit to prevent infinite loops
- 🖼️ ✨**NEW** **Multi-Modal Support**: Analyze images using vision-capable models (llava, bakllava, cogvlm, moondream, etc.). Extract information from screenshots, diagrams, charts, and photos directly in your workflow.
- ✨**NEW** **Auto-Load Configuration**: Automatically load project context from `.config/CLAUDE.md` and server configuration from `.config/config.json` on startup ([docs](docs/auto_load_configuration.md))
- ✨**NEW** **Save and Load Session**: Save and load your chat session, including history.
- ✨**NEW** **Reparse Last Response**: A command to re-parse the last model response, useful for debugging or when the model response is slightly malformed.
- 🧠 **Self-Editing System Prompt**: The model can modify its own instructions and persona in real-time using built-in tools (`builtin.get_system_prompt` and `builtin.set_system_prompt`).
- 🌐 **Multi-Server Support**: Connect to multiple MCP servers simultaneously
- 🚀 **Multiple Transport Types**: Supports STDIO, SSE, and Streamable HTTP server connections
- ☁️ **Ollama Cloud Support**: Works seamlessly with Ollama Cloud models for tool calling, enabling access to powerful cloud-hosted models while using local MCP tools
- 🎨 **Rich Terminal Interface**: Interactive console UI with modern styling
- 🌊 **Streaming Responses**: View model outputs in real-time as they're generated
- 🛠️ **Tool Management**: Enable/disable specific tools or entire servers during chat sessions
- 🧑‍💻 **Human-in-the-Loop (HIL)**: Review and approve tool executions before they run for enhanced control and safety
- 🎮 **Advanced Model Configuration**: Fine-tune 15+ model parameters including context window size, temperature, sampling, repetition control, and more
- 💬 **System Prompt Customization**: Define and edit the system prompt to control model behavior and persona
- 🧠 **Context Window Control**: Adjust the context window size (num_ctx) to handle longer conversations and complex tasks
- 🎨 **Enhanced Tool Display**: Beautiful, structured visualization of tool executions with JSON syntax highlighting
- 🧠 **Context Management**: Control conversation memory with configurable retention settings
- 🤔 **Thinking Mode**: Advanced reasoning capabilities with visible thought processes for supported models (e.g., gpt-oss, deepseek-r1, qwen3, etc.)
- 🗣️ **Cross-Language Support**: Seamlessly work with both Python and JavaScript MCP servers
- 🔍 **Auto-Discovery**: Automatically find and use Claude's existing MCP server configurations
- 🔁 **Dynamic Model Switching**: Switch between any installed Ollama model without restarting
- 💾 **Configuration Persistence**: Save and load tool preferences and model settings between sessions
- 🔄 **Server Reloading**: Hot-reload MCP servers during development without restarting the client
- ✨ **Fuzzy Autocomplete**: Interactive, arrow-key command autocomplete with descriptions
- 🏷️ **Dynamic Prompt**: Shows current model, thinking mode, and enabled tools
- 📊 **Performance Metrics**: Detailed model performance data after each query, including duration timings and token counts
- 🔌 **Plug-and-Play**: Works immediately with standard MCP-compliant tool servers
- 🔔 **Update Notifications**: Automatically detects when a new version is available
- 🖥️ **Modern CLI with Typer**: Grouped options, shell autocompletion, and improved help output

## Requirements

- **Python 3.10+** ([Installation guide](https://www.python.org/downloads/))
- **Ollama** running locally ([Installation guide](https://ollama.com/download))
- **UV package manager** ([Installation guide](https://github.com/astral-sh/uv))

## Quick Start

**Option 1:** Install with pip and run

```bash
pip install --upgrade ollmcp
ollmcp
```

**Option 2:** One-step install and run

```bash
uvx ollmcp
```

**Option 3:** Install from source and run using virtual environment

```bash
git clone https://github.com/jonigl/mcp-client-for-ollama.git
cd mcp-client-for-ollama
uv venv && source .venv/bin/activate
uv pip install .
uv run -m mcp_client_for_ollama
```

## Usage

Run with default settings:

```bash
ollmcp
```

> If you don't provide any options, the client will use `auto-discovery` mode to find MCP servers from Claude's configuration.

### Command-line Arguments

> [!TIP]
> The CLI now uses `Typer` for a modern experience: grouped options, rich help, and built-in shell autocompletion. Advanced users can use short flags for faster commands. To enable autocompletion, run:
>
> ```bash
> ollmcp --install-completion
> ```
>
> Then restart your shell or follow the printed instructions.

#### MCP Server Configuration:

- `--mcp-server`, `-s`: Path to one or more MCP server scripts (.py or .js). Can be specified multiple times.
- `--mcp-server-url`, `-u`: URL to one or more SSE or Streamable HTTP MCP servers. Can be specified multiple times. See [Common MCP endpoint paths](#common-mcp-endpoint-paths) for typical endpoints.
- `--servers-json`, `-j`: Path to a JSON file with server configurations. See [Server Configuration Format](#server-configuration-format) for details.
- `--auto-discovery`, `-a`: Auto-discover servers from Claude's default config file (default behavior if no other options provided).

> [!TIP]
> Claude's configuration file is typically located at:
> `~/Library/Application Support/Claude/claude_desktop_config.json`

#### Ollama Configuration:

- `--model`, `-m` MODEL: Ollama model to use. Default: `qwen2.5:7b`
- `--host`, `-H` HOST: Ollama host URL. Default: `http://localhost:11434`

#### General Options:

- `--version`, `-v`: Show version and exit
- `--help`, `-h`: Show help message and exit
- `--install-completion`: Install shell autocompletion scripts for the client
- `--show-completion`: Show available shell completion options

### Usage Examples

Simplest way to run the client:

```bash
ollmcp
```
> [!TIP]
> This will automatically discover and connect to any MCP servers configured in Claude's settings and use the default model `qwen2.5:7b` or the model specified in your configuration file.

Connect to a single server:

```bash
ollmcp --mcp-server /path/to/weather.py --model llama3.2:3b
# Or using short flags:
ollmcp -s /path/to/weather.py -m llama3.2:3b
```

Connect to multiple servers:

```bash
ollmcp --mcp-server /path/to/weather.py --mcp-server /path/to/filesystem.js
# Or using short flags:
ollmcp -s /path/to/weather.py -s /path/to/filesystem.js
```

>[!TIP]
> If model is not specified, the default model `qwen2.5:7b` will be used or the model specified in your configuration file.

Use a JSON configuration file:

```bash
ollmcp --servers-json /path/to/servers.json --model llama3.2:1b
# Or using short flags:
ollmcp -j /path/to/servers.json -m llama3.2:1b
```

>[!TIP]
> See the [Server Configuration Format](#server-configuration-format) section for details on how to structure the JSON file.

Use a custom Ollama host:

```bash
ollmcp --host http://localhost:22545 --servers-json /path/to/servers.json --auto-discovery
# Or using short flags:
ollmcp -H http://localhost:22545 -j /path/to/servers.json -a
```

Connect to SSE or Streamable HTTP servers by URL:

```bash
ollmcp --mcp-server-url http://localhost:8000/sse --model qwen2.5:latest
# Or using short flags:
ollmcp -u http://localhost:8000/sse -m qwen2.5:latest
```

Connect to multiple URL servers:

```bash
ollmcp --mcp-server-url http://localhost:8000/sse --mcp-server-url http://localhost:9000/mcp
# Or using short flags:
ollmcp -u http://localhost:8000/sse -u http://localhost:9000/mcp
```

Mix local scripts and URL servers:

```bash
ollmcp --mcp-server /path/to/weather.py --mcp-server-url http://localhost:8000/mcp --model qwen3:1.7b
# Or using short flags:
ollmcp -s /path/to/weather.py -u http://localhost:8000/mcp -m qwen3:1.7b
```

Use auto-discovery with mixed server types:

```bash
ollmcp --mcp-server /path/to/weather.py --mcp-server-url http://localhost:8000/mcp --auto-discovery
# Or using short flags:
ollmcp -s /path/to/weather.py -u http://localhost:8000/mcp -a
```

## Interactive Commands

During chat, use these commands:

![ollmcp main interface](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-welcome.png?raw=true)

| Command          | Shortcut         | Description                                         |
|------------------|------------------|-----------------------------------------------------|
| `clear`          | `cc`             | Clear conversation history and context              |
| `cls`            | `clear-screen`   | Clear the terminal screen                           |
| `context`        | `c`              | Toggle context retention                            |
| `context-info`   | `ci`             | Display context statistics                          |
| `help`           | `h`              | Display help and available commands                 |
| `human-in-loop`  | `hil`            | Toggle Human-in-the-Loop confirmations for tool execution |
| `list-vision-models` | `lvm`        | List available vision-capable models on Ollama server |
| `load-config`    | `lc`             | Load tool and model configuration from a file       |
| `load-session`   | `ls`             | Load a chat session from a file                     |
| `loop-limit`     | `ll`             | Set maximum iterative tool-loop iterations (Agent Mode). Default: 3 |
| `model`          | `m`              | List and select a different Ollama model            |
| `model-config`   | `mc`             | Configure advanced model parameters and system prompt|
| `quit`, `exit`, `bye`   | `q` or `Ctrl+D`  | Exit the client                                     |
| `reload-servers` | `rs`             | Reload all MCP servers with current configuration   |
| `reparse-last`   | `rl`             | Reparse the last model response                     |
| `reset-config`   | `rc`             | Reset configuration to defaults (all tools enabled) |
| `save-config`    | `sc`             | Save current tool and model configuration to a file |
| `save-session`   | `ss`             | Save the current chat session to a file             |
| `set-vision-model` | `svm`          | Select a vision model for image analysis tasks      |
| `show-metrics`   | `sm`             | Toggle performance metrics display                  |
| `show-thinking`  | `st`             | Toggle thinking text visibility                     |
| `show-tool-execution` | `ste`       | Toggle tool execution display visibility            |
| `tools`          | `t`              | Open the tool selection interface                   |


### Tool and Server Selection

The tool and server selection interface allows you to enable or disable specific tools:

![ollmcp tool and server selection interface](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmpc-tool-and-server-selection.png?raw=true)

- Enter **numbers** separated by commas (e.g. `1,3,5`) to toggle specific tools
- Enter **ranges** of numbers (e.g. `5-8`) to toggle multiple consecutive tools
- Enter **S + number** (e.g. `S1`) to toggle all tools in a specific server
- `a` or `all` - Enable all tools
- `n` or `none` - Disable all tools
- `d` or `desc` - Show/hide tool descriptions
- `j` or `json` - Show detailed tool JSON schemas on enabled tools for debugging purposes
- `s` or `save` - Save changes and return to chat
- `q` or `quit` - Cancel changes and return to chat

### Model Selection

The model selection interface shows all available models in your Ollama installation:

![ollmcp model selection interface](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmpc-model-selection.jpg?raw=true)

- Enter the **number** of the model you want to use
- `s` or `save` - Save the model selection and return to chat
- `q` or `quit` - Cancel the model selection and return to chat

### Advanced Model Configuration

The `model-config` (`mc`) command opens the advanced model settings interface, allowing you to fine-tune how the model generates responses:

> [!IMPORTANT]
> Changes made in the model configuration menu or by the AI's self-editing tools are temporary for the current session. To make them permanent, remember to save your settings using the `save-config` (`sc`) command.

![ollmcp model configuration interface](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-model-configuration.png?raw=true)

#### AI-Controlled System Prompt (Self-Editing)

In addition to manual configuration, the client includes built-in tools that allow the model to get and set its own system prompt during a conversation.

- `builtin.get_system_prompt`: The model can use this tool to retrieve its current system prompt.
- `builtin.set_system_prompt`: The model can use this tool to change its persona, instructions, or behavior on the fly.

This enables dynamic, in-conversation persona switching and instruction refinement, guided by the user's requests. For example, a user could say, "From now on, you are a pirate," and the model can use the `set_system_prompt` tool to update its core instructions accordingly.

#### System Prompt

- **System Prompt**: Set the model's role and behavior to guide responses.

#### Key Parameters

- **System Prompt**: Set the model's role and behavior to guide responses.
- **Context Window (num_ctx)**: Set how much chat history the model uses. Balance with memory usage and performance.
- **Keep Tokens**: Prevent important tokens from being dropped
- **Max Tokens**: Limit response length (0 = auto)
- **Seed**: Make outputs reproducible (set to -1 for random)
- **Temperature**: Control randomness (0 = deterministic, higher = creative)
- **Top K / Top P / Min P / Typical P**: Sampling controls for diversity
- **Repeat Last N / Repeat Penalty**: Reduce repetition
- **Presence/Frequency Penalty**: Encourage new topics, reduce repeats
- **Stop Sequences**: Custom stopping points (up to 8)
 - **Batch Size (num_batch)**: Controls internal batching of requests; larger values can increase throughput but use more memory.

#### Commands

- Enter parameter numbers `1-15` to edit settings
- Enter `sp` to edit the system prompt
- Use `u1`, `u2`, etc. to unset parameters, or `uall` to reset all
- `h`/`help`: Show parameter details and tips
- `undo`: Revert changes
- `s`/`save`: Apply changes
- `q`/`quit`: Cancel

#### Example Configurations

- **Factual:** `temperature: 0.0-0.3`, `top_p: 0.1-0.5`, `seed: 42`
- **Creative:** `temperature: 1.0+`, `top_p: 0.95`, `presence_penalty: 0.2`
- **Reduce Repeats:** `repeat_penalty: 1.1-1.3`, `presence_penalty: 0.2`, `frequency_penalty: 0.3`
- **Balanced:** `temperature: 0.7`, `top_p: 0.9`, `typical_p: 0.7`
- **Reproducible:** `seed: 42`, `temperature: 0.0`
- **Large Context:** `num_ctx: 8192` or higher for complex conversations requiring more context

> [!TIP]
> All parameters default to unset, letting Ollama use its own optimized values. Use `help` in the config menu for details and recommendations. Changes are saved with your configuration.


### Server Reloading for Development

The `reload-servers` command (`rs`) is particularly useful during MCP server development. It allows you to reload all connected servers without restarting the entire client application.

**Key Benefits:**
- 🔄 **Hot Reload**: Instantly apply changes to your MCP server code
- 🛠️ **Development Workflow**: Perfect for iterative development and testing
- 📝 **Configuration Updates**: Automatically picks up changes in server JSON configs or Claude configs
- 🎯 **State Preservation**: Maintains your tool enabled/disabled preferences across reloads
- ⚡️ **Time Saving**: No need to restart the client and reconfigure everything

**When to Use:**
- After modifying your MCP server implementation
- When you've updated server configurations in JSON files
- After changing Claude's MCP configuration
- During debugging to ensure you're testing the latest server version

Simply type `reload-servers` or `rs` in the chat interface, and the client will:
1. Disconnect from all current MCP servers
2. Reconnect using the same parameters (server paths, config files, auto-discovery)
3. Restore your previous tool enabled/disabled settings
4. Display the updated server and tool status

This feature dramatically improves the development experience when building and testing MCP servers.

### Human-in-the-Loop (HIL) Tool Execution

The Human-in-the-Loop feature provides an additional safety layer by allowing you to review and approve tool executions before they run. This is particularly useful for:

- 🛡️ **Safety**: Review potentially destructive operations before execution
- 🔍 **Learning**: Understand what tools the model wants to use and why
- 🎯 **Control**: Selective execution of only the tools you approve
- 🚫 **Prevention**: Stop unwanted tool calls from executing

#### HIL Confirmation Display

When HIL is enabled, you'll see a confirmation prompt before each tool execution:

**Example:**

![ollmcp HIL confirmation screenshot](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-hil-feature.png?raw=true)


### Human-in-the-Loop (HIL) Configuration

- **Default State**: HIL confirmations are enabled by default for safety
- **Toggle Command**: Use `human-in-loop` or `hil` to toggle on/off
- **Persistent Settings**: HIL preference is saved with your configuration
- **Quick Disable**: Choose "disable" during any confirmation to turn off permanently
- **Re-enable**: Use the `hil` command anytime to turn confirmations back on

**Benefits:**
- **Enhanced Safety**: Prevent accidental or unwanted tool executions
- **Awareness**: Understand what actions the model is attempting to perform
- **Selective Control**: Choose which operations to allow on a case-by-case basis
- **Peace of Mind**: Full visibility and control over automated actions

### Performance Metrics

The Performance Metrics feature displays detailed model performance data after each query in a bordered panel. The metrics show duration timings, token counts, and generation rates directly from Ollama's response.

**Displayed Metrics:**
- `total duration`: Total time spent generating the complete response (seconds)
- `load duration`: Time spent loading the model (milliseconds)
- `prompt eval count`: Number of tokens in the input prompt
- `prompt eval duration`: Time spent evaluating the input prompt (milliseconds)
- `eval count`: Number of tokens generated in the response
- `eval duration`: Time spent generating the response tokens (seconds)
- `prompt eval rate`: Speed of input prompt processing (tokens/second)
- `eval rate`: Speed of response token generation (tokens/second)

**Example:**
![ollmcp ollama performance metrics screenshot](https://github.com/jonigl/mcp-client-for-ollama/blob/main/misc/ollmcp-ollama-performance-metrics.png?raw=true)

#### Performance Metrics Configuration

- **Default State**: Metrics are disabled by default for cleaner output
- **Toggle Command**: Use `show-metrics` or `sm` to enable/disable metrics display
- **Persistent Settings**: Metrics preference is saved with your configuration

**Benefits:**
- **Performance Monitoring**: Track model efficiency and response times
- **Token Tracking**: Monitor actual token consumption for analysis
- **Benchmarking**: Compare performance across different models

> [!NOTE]
> **Data Source**: All metrics come directly from Ollama's response, ensuring accuracy and reliability.

## Multi-Modal Support (Image Analysis)

The client now supports analyzing images using vision-capable models like llava, bakllava, cogvlm, moondream, and more. This enables you to extract information from screenshots, diagrams, charts, and photos directly in your workflow.

**📚 [Read the full Multi-Modal Support documentation](docs/MULTI_MODAL_SUPPORT.md)** for detailed usage, troubleshooting, and examples.

### Quick Start

1. **Install a vision model** (if not already available):
   ```bash
   ollama pull llava
   ```

2. **Analyze images** using the `builtin.read_image` tool:
   - Ask the AI to analyze an image by providing the path
   - Example queries:
     - "What's in the image at screenshots/error.png?"
     - "Analyze the diagram at docs/architecture.png"
     - "Read the chart at data/metrics.jpg and summarize the data"

### Vision Model Management

**List available vision models:**
```
lvm
```
or
```
list-vision-models
```

This displays all vision-capable models on your Ollama server with their sizes and which one is currently configured.

**Select a specific vision model:**
```
svm
```
or
```
set-vision-model
```

Choose from available models interactively. The selected model will be used for all image analysis tasks.

### How It Works

- **Auto-Detection**: If you haven't set a preferred model, the tool automatically detects and uses the first available vision model
- **Configuration**: Set a preferred model using `svm` to use it consistently
- **Supported Models**: llava, llava-llama3, llava-phi3, bakllava, llama3.2-vision, llama3-vision, cogvlm, cogvlm2, moondream, minicpm-v, obsidian, and any model with "vision" in the name
- **Supported Formats**: PNG, JPG, JPEG, GIF, BMP, WEBP

### Usage Examples

**Direct tool call via delegation:**
```bash
d analyze the screenshot at test.png
```

**In conversation:**
```
You: What does the error in screenshots/bug.png say?
AI: [Uses builtin.read_image to analyze the image and responds with the error message]
```

**For diagrams and charts:**
```
You: Explain the architecture diagram at docs/system-design.png
AI: [Analyzes the diagram and provides detailed explanation]
```

### Agent Support

The following agents have image analysis capabilities:
- **EXECUTOR**: Can analyze images as part of command execution tasks
- **READER**: Can analyze images when reading and understanding codebases
- **RESEARCHER**: Can analyze diagrams, screenshots, and charts when researching

### Configuration Persistence

Your vision model selection is saved in `~/.config/ollmcp/config.json` and persists across sessions.

## Autocomplete and Prompt Features

### Typer Shell Autocompletion

- The CLI supports shell autocompletion for all options and arguments via Typer
- To enable, run `ollmcp --install-completion` and follow the instructions for your shell
- Enjoy tab-completion for all grouped and general options

### FZF-style Autocomplete

- Fuzzy matching for commands as you type
- Arrow (`▶`) highlights the best match
- Command descriptions shown in the menu
- Case-insensitive matching for convenience
- Centralized command list for consistency

### ✨**NEW** Filesystem Autocompletion (`@` command)

The client now supports autocompletion for filesystem paths using the `@` symbol. When you type `@` followed by a partial path, the completer will suggest files and directories from your system. This feature is available when a `filesystem` tool is enabled and connected to an MCP server.

**Usage:**
- Type `@` followed by a partial path (e.g., `@/home/user/doc`) to get suggestions for files and directories.
- The autocompletion will show both files and directories, allowing you to quickly navigate and select paths.
- This feature leverages the `filesystem.list_directory` tool.

### Contextual Prompt

The chat prompt now gives you clear, contextual information at a glance:

- **Model**: Shows the current Ollama model in use
- **Thinking Mode**: Indicates if "thinking mode" is active (for supported models)
- **Tools**: Displays the number of enabled tools

**Example prompt:**
```
qwen3/show-thinking/12-tools❯
```
- `qwen3` Model name
- `/show-thinking` Thinking mode indicator (if enabled, otherwise `/thinking` or omitted)
- `/12-tools` Number of tools enabled (or `/1-tool` for singular)
- `❯` Prompt symbol

This makes it easy to see your current context before entering a query.

## Configuration Management

> [!TIP]
> It will automatically load the default configuration from `~/.config/ollmcp/config.json` if it exists.

The client supports saving and loading tool configurations between sessions:

- When using `save-config`, you can provide a name for the configuration or use the default
- Configurations are stored in `~/.config/ollmcp/` directory
- The default configuration is saved as `~/.config/ollmcp/config.json`
- Named configurations are saved as `~/.config/ollmcp/{name}.json`

The configuration saves:

- Current model selection
- Advanced model parameters (system prompt, temperature, sampling settings, etc.)
- Enabled/disabled status of all tools
- Context retention settings
- Thinking mode settings
- Tool execution display preferences
- Performance metrics display preferences
- Human-in-the-Loop confirmation settings

## ✨**NEW** Auto-Load Configuration

The client now supports automatic loading of project-specific configuration files from the `.config/` directory in your project root. This feature makes it easy to maintain project-specific settings without manually specifying them each time.

### Automatic Loading on Startup

**Two files are automatically loaded if they exist:**

1. **`.config/CLAUDE.md`** - Project context and documentation
   - Automatically loaded and prepended to the system prompt
   - Provides the AI with immediate project context
   - Perfect for project conventions, architecture, and guidelines
   - **Tracked in git by default** (share with your team)

2. **`.config/config.json`** - Server configuration
   - Automatically loaded as MCP server configuration (like `--servers-json`)
   - No need to specify `--servers-json` every time
   - **Ignored by git by default** (local configurations)
   - Can be explicitly tracked if you want to share server configs

### Quick Setup

```bash
# Create .config directory
mkdir -p .config

# Add project context (tracked in git)
cat > .config/CLAUDE.md << 'EOF'
# My Project
- Tech stack: Python, FastAPI, PostgreSQL
- Code style: PEP 8, type hints required
- Testing: pytest
EOF

# Add server config (local, not tracked)
cat > .config/config.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./"]
    }
  }
}
EOF

# Start ollmcp - configuration loads automatically!
$ ollmcp
📋 Auto-loading server configuration from .config/config.json
📋 Loaded project context from .config/CLAUDE.md
```

### Benefits

✅ **Zero configuration** - Just create the files, they work automatically
✅ **Project-scoped** - Each project has its own settings
✅ **Team-friendly** - Share project context via git
✅ **Override-able** - CLI flags still work when needed

**📚 Full documentation:** [Auto-Load Configuration Guide](docs/auto_load_configuration.md)

### ✨**NEW** Save and Load Session

You can now save and load your entire chat session, including the conversation history. This is useful for resuming a session later or for keeping a record of your conversations.

- `save-session` (`ss`): Save the current chat session to a file.
- `load-session` (`ls`): Load a chat session from a file.

Sessions are saved in the `~/.config/ollmcp/sessions/` directory.

## Server Configuration Format

The JSON configuration file supports STDIO, SSE, and Streamable HTTP server types (MCP 1.10.1):

```json
{
  "systemPrompt": "You are a helpful AI assistant that specializes in providing concise and accurate information.",
  "mcpServers": {
    "stdio-server": {
      "command": "command-to-run",
      "args": ["arg1", "arg2", "..."],
      "env": {
        "ENV_VAR1": "value1",
        "ENV_VAR2": "value2"
      },
      "disabled": false
    },
    "sse-server": {
      "type": "sse",
      "url": "http://localhost:8000/sse",
      "headers": {
        "Authorization": "Bearer your-token-here"
      },
      "disabled": false
    },
    "http-server": {
      "type": "streamable_http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "X-API-Key": "your-api-key-here"
      },
      "disabled": false
    }
  }
}
```
> [!NOTE]
> **System Prompt**: You can include a `systemPrompt` field at the top level of your `servers-json` file. This prompt will be used to initialize the model's system prompt when the client starts or when servers are reloaded. If a system prompt is also configured interactively via the `model-config` command, the one from the `servers-json` file will take precedence upon loading.

> [!NOTE]
> **MCP 1.10.1 Transport Support**: The client now supports the latest Streamable HTTP transport with improved performance and reliability. If you specify a URL without a type, the client will default to using Streamable HTTP transport.

### Tips: where to put MCP server configs and a working example

A common point of confusion is where to store MCP server configuration files and how the TUI's save/load feature is used. Here's a short, practical guide that has helped other users:

- The TUI's `save-config` / `load-config` (or `sc` / `lc`) commands are intended to save *TUI preferences* like which tools you enabled, your selected model, thinking mode, and other client-side settings. They are not required to register MCP server connections with the client.
- For MCP server JSON files (the `mcpServers` object shown above) we recommend keeping them outside the TUI config directory or in a clear subfolder, for example:

```
~/.config/ollmcp/mcp-servers/config.json
```

You can then point `ollmcp` at that file at startup with `-j` / `--servers-json`.

> [!IMPORTANT]
> When using HTTP-based MCP servers, use the `streamable_http` type (not just `http`). Also check the [Common MCP endpoint paths](#common-mcp-endpoint-paths) section below for typical endpoints.

Here a minimal working example let's say this is your `~/.config/ollmcp/mcp-servers/config.json`:

```json
{
  "mcpServers": {
    "github": {
      "type": "streamable_http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer mytoken"
      }
    }
  }
}
```

> [!TIP]
> When using GitHub MCP server, make sure to replace `"mytoken"` with your actual GitHub API token.

With that file in place you can connect using:

```
ollmcp -j ~/.config/ollmcp/mcp-servers/config.json
```

Here you can find a GitHub issue related to this common pitfall: https://github.com/jonigl/mcp-client-for-ollama/issues/112#issuecomment-3446569030

#### Demo

A short demo (asciicast) that should help anyone reproduce the working setup quickly. This example uses an [MCP server example with streamable HTTP protocol](https://github.com/jonigl/mcp-server-with-streamable-http-example) usage:

[![asciicast](https://asciinema.org/a/751387.svg)](https://asciinema.org/a/751387)

#### Common MCP endpoint paths

Streamable HTTP MCP servers typically expose the MCP endpoint at `/mcp` (e.g., `https://host/mcp`), while SSE servers commonly use `/sse` (e.g., `https://host/sse`). Below is an excerpt from the MCP specification (2025-06-18):
> The server MUST provide a single HTTP endpoint path (hereafter referred to as the MCP endpoint) that supports both POST and GET methods. For example, this could be a URL like https://example.com/mcp.

You can find more details in the [MCP specification version 2025-06-18 - Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

## Compatible Models

The following Ollama models work well with tool use:

- qwen2.5
- qwen3
- llama3.1
- llama3.2
- mistral

For a complete list of Ollama models with tool use capabilities, visit the [official Ollama models page](https://ollama.com/search?c=tools).

### Ollama Cloud Models

MCP Client for Ollama now supports [Ollama Cloud models](https://github.com/ollama/ollama/blob/main/docs/cloud.md), allowing you to use powerful cloud-hosted models with tool calling capabilities while leveraging your local MCP tools. Cloud models can run without a powerful local GPU, making it possible to access larger models that wouldn't fit on a personal computer.

**Supported Ollama Cloud models include for example:**
- `gpt-oss:20b-cloud`
- `gpt-oss:120b-cloud`
- `deepseek-v3.1:671b-cloud`
- `qwen3-coder:480b-cloud`

**To use Ollama Cloud models with this client:**

1. First, pull the cloud model:
   ```bash
   ollama pull gpt-oss:120b-cloud
   ```

2. Run the client with your chosen cloud model:
   ```bash
   ollmcp --model gpt-oss:120b-cloud
   ```

> [!NOTE]
> The model `deepseek-v3.1:671b-cloud` only supports tool use when thinking mode is turned off. You can toggle thinking mode in `ollmcp` by typing either `thinking-mode` or `tm`.

For more information about Ollama Cloud, visit the [Ollama Cloud documentation](https://docs.ollama.com/cloud).

### How Tool Calls Work

1. The client sends your query to Ollama with a list of available tools
2. If Ollama decides to use a tool, the client:
   - Displays the tool execution with formatted arguments and syntax highlighting
   - Shows a Human-in-the-Loop confirmation prompt (if enabled) allowing you to review and approve the tool call
   - Extracts the tool name and arguments from the model response
   - Calls the appropriate MCP server with these arguments (only if approved or HIL is disabled)
   - Shows the tool response in a structured, easy-to-read format
   - Sends the tool result back to Ollama
   - If in Agent Mode, repeats the process if the model requests more tool calls
3. Finally, the client:
   - Displays the model's final response incorporating the tool results

### Agent Mode

Some models may request multiple tool calls in a single conversation. The client supports an **Agent Mode** that allows for iterative tool execution:
- When the model requests a tool call, the client executes it and sends the result back to the model
- This process repeats until the model provides a final answer or reaches the configured loop limit
- You can set the maximum number of iterations using the `loop-limit` (`ll`) command
- The default loop limit is `3` to prevent infinite loops

> [!NOTE]
> If you want to prevent using Agent Mode, simply set the loop limit to `1`.

#### Agent Mode Quick Demo:

[![asciicast](https://asciinema.org/a/476qpEamCX9TFQt4jNEXIgHxS.svg)](https://asciinema.org/a/476qpEamCX9TFQt4jNEXIgHxS)

### Agent Delegation System

For complex multi-file tasks, the **Agent Delegation System** breaks down your query into focused subtasks executed by specialized agents. This is particularly powerful for **small models (7B-14B)** with limited context windows.

**How it works:**
1. A **PLANNER** agent analyzes your query and creates a task breakdown
2. Specialized agents execute each task with minimal context requirements
3. Results are aggregated into a final comprehensive response

**Available agent types:**
- **PLANNER** - Decomposes complex queries into subtasks
- **READER** - Reads and analyzes code (read-only)
- **CODER** - Writes and modifies code files
- **EXECUTOR** - Runs bash commands and Python scripts
- **RESEARCHER** - Analyzes and summarizes information
- **DEBUGGER** - Fixes errors and debugs code

**Usage:**
```bash
delegate scan all md files in misc, read and summarize each, create executive summary
# or use the short form:
d refactor authentication across multiple files
```

**Benefits:**
- ✅ Small models (qwen2.5:7b, qwen2.5-coder:14b) handle complex tasks efficiently
- ✅ Faster execution - parallel-capable task breakdown
- ✅ Better success rate - focused agents avoid context overflow
- ✅ Extensible - add new agent types via JSON definition files

**📚 [Read the full documentation](docs/agent-delegation-user-guide.md)** for detailed usage, configuration, and examples.

## Where Can I Find More MCP Servers?

You can explore a collection of MCP servers in the official [MCP Servers repository](https://github.com/modelcontextprotocol/servers).

This repository contains reference implementations for the Model Context Protocol, community-built servers, and additional resources to enhance your LLM tool capabilities.

## Related Projects

- **[Ollama MCP Bridge](https://github.com/jonigl/ollama-mcp-bridge)** - A Python API layer that sits in front of Ollama, automatically adding tools from multiple MCP servers to every chat request. This project provides a transparent proxy solution that pre-loads all MCP servers at startup and seamlessly integrates their tools into the Ollama API.
- **[MCP Server with Streamable HTTP Example](https://github.com/jonigl/mcp-server-with-streamable-http-example)** - An example MCP server demonstrating the usage of the streamable HTTP protocol.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Ollama](https://ollama.com/) for the local LLM runtime
- [Model Context Protocol](https://modelcontextprotocol.io/) for the specification and examples
- [Rich](https://rich.readthedocs.io/) for the terminal user interface
- [Typer](https://typer.tiangolo.com/) for the modern CLI experience
- [Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/) for the interactive command line interface
- [UV](https://www.uvicorn.org/) for the lightning-fast Python package manager and virtual environment management
- [Asciinema](https://asciinema.org/) for the demo recording

---

Made with ❤️ by [jonigl](https://github.com/jonigl)
