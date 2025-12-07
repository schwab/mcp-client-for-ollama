# Collapsible Output and Trace Logging Features

**Version:** 0.23.0+
**Status:** ✅ Implemented

---

## Overview

Two new features have been added to improve the agent delegation debugging and user experience:

1. **Collapsible Output** - Automatically collapse large output blocks for better terminal readability
2. **Trace Logging** - Detailed logging of all LLM calls for debugging agent behavior

---

## Feature 1: Collapsible Output

### What It Does

Large outputs from agent tasks are automatically collapsed into a single-line summary with a preview. This keeps the terminal clean while still allowing you to see the full output when needed.

### How It Works

**Before (traditional output):**
```
✓ task_1 (READER): Read and analyze config file
[... 500 lines of JSON content ...]

✓ task_2 (CODER): Update configuration
[... 300 lines of code changes ...]
```

**After (with collapsible output):**
```
▶ ✓ task_1 (READER) (87 lines, 5432 chars)
  {
    "version": "1.0",
    "config": {

  ... (84 more lines hidden)

▶ ✓ task_2 (CODER) (45 lines, 2891 chars)
  Updated mcp_client_for_ollama/config/settings.py

  ... (42 more lines hidden)
```

### Configuration

Add to your delegation config:

```python
delegation_config = {
    "collapsible_output": {
        "auto_collapse": True,      # Enable auto-collapsing
        "line_threshold": 20,        # Collapse if > 20 lines
        "char_threshold": 1000,      # Collapse if > 1000 chars
    }
}
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `auto_collapse` | bool | `True` | Enable automatic collapsing |
| `line_threshold` | int | `20` | Number of lines before collapsing |
| `char_threshold` | int | `1000` | Number of characters before collapsing |

### Example Configuration File

```json
{
  "delegation": {
    "enabled": true,
    "collapsible_output": {
      "auto_collapse": true,
      "line_threshold": 15,
      "char_threshold": 800
    }
  }
}
```

---

## Feature 2: Trace Logging

### What It Does

Trace logging captures every LLM interaction during agent delegation, including:
- Full prompts sent to each agent
- Complete responses from the LLM
- Tool calls and their results
- Task start/end with timing information
- Planning phase details

This makes it easy to debug why a task failed or produced unexpected results.

### Trace Levels

| Level | Description | What Gets Logged |
|-------|-------------|------------------|
| `OFF` | No tracing | Nothing |
| `SUMMARY` | Minimal logging | Task start/end only |
| `BASIC` | Standard logging | Prompts & responses (truncated to 500 chars) |
| `FULL` | Detailed logging | Complete prompts & responses |
| `DEBUG` | Maximum verbosity | Everything including tool calls |

### Log File Format

Traces are written to `.trace/trace_YYYYMMDD_HHMMSS.jsonl` in JSON Lines format.

**Example trace entry:**
```json
{
  "timestamp": "2025-12-07T10:30:45.123456",
  "entry_type": "llm_call",
  "task_id": "task_1",
  "agent_type": "READER",
  "data": {
    "model": "qwen2.5:7b",
    "temperature": 0.5,
    "loop_iteration": 0,
    "prompt": "You are a code reading specialist...",
    "response": "I'll analyze the file...",
    "prompt_length": 1234,
    "response_length": 5678,
    "tools_used": ["builtin.read_file"]
  }
}
```

### Configuration

```python
delegation_config = {
    "trace_enabled": True,           # Enable tracing
    "trace_level": "full",           # Trace level (off/summary/basic/full/debug)
    "trace_dir": ".trace",           # Directory for trace files
    "trace_console": False,          # Also print to console (DEBUG level only)
    "trace_truncate": 500            # Truncation length for BASIC level
}
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `trace_enabled` | bool | `False` | Enable trace logging |
| `trace_level` | str | `"basic"` | Trace level (off/summary/basic/full/debug) |
| `trace_dir` | str | `".trace"` | Directory for log files |
| `trace_console` | bool | `False` | Print traces to console (DEBUG only) |
| `trace_truncate` | int | `500` | Truncation length for BASIC level |

### Example Configuration File

```json
{
  "delegation": {
    "enabled": true,
    "trace_enabled": true,
    "trace_level": "full",
    "trace_dir": ".trace",
    "trace_console": false
  }
}
```

### Trace Summary

At the end of each delegation session, a summary is automatically printed:

```
🔍 Trace Session Summary
Session ID: 20251207_103045
Log file: .trace/trace_20251207_103045.jsonl

Total trace entries: 45
LLM calls: 12
Tool calls: 8
Tasks completed: 3
Tasks failed: 0
```

### Analyzing Trace Files

The trace files are in JSON Lines format, which can be analyzed with standard tools:

**Count LLM calls per agent:**
```bash
grep '"entry_type": "llm_call"' .trace/trace_*.jsonl | \
  jq -r '.agent_type' | sort | uniq -c
```

**Find failed tasks:**
```bash
grep '"entry_type": "task_end"' .trace/trace_*.jsonl | \
  jq 'select(.data.status == "failed")'
```

**Extract all prompts for a specific task:**
```bash
grep '"task_id": "task_2"' .trace/trace_*.jsonl | \
  jq -r 'select(.entry_type == "llm_call") | .data.prompt'
```

**Calculate average task duration:**
```bash
grep '"entry_type": "task_end"' .trace/trace_*.jsonl | \
  jq '.data.duration_ms' | \
  awk '{sum+=$1; count++} END {print sum/count " ms"}'
```

---

## Usage Example

### Complete Configuration

```python
from mcp_client_for_ollama.agents.delegation_client import DelegationClient

delegation_config = {
    # Basic delegation settings
    "enabled": True,
    "execution_mode": "parallel",
    "max_parallel_tasks": 3,

    # Collapsible output
    "collapsible_output": {
        "auto_collapse": True,
        "line_threshold": 20,
        "char_threshold": 1000
    },

    # Trace logging
    "trace_enabled": True,
    "trace_level": "full",      # Use "basic" for production, "full" for debugging
    "trace_dir": ".trace",
    "trace_console": False
}

delegation_client = DelegationClient(mcp_client, delegation_config)
result = await delegation_client.process_with_delegation(user_query)
```

### JSON Configuration File

Create `.config/delegation.json`:

```json
{
  "delegation": {
    "enabled": true,
    "execution_mode": "parallel",
    "max_parallel_tasks": 3,

    "collapsible_output": {
      "auto_collapse": true,
      "line_threshold": 20,
      "char_threshold": 1000
    },

    "trace_enabled": true,
    "trace_level": "basic",
    "trace_dir": ".trace",
    "trace_console": false,
    "trace_truncate": 500
  }
}
```

Then load it:

```python
import json

with open('.config/delegation.json', 'r') as f:
    config = json.load(f)

delegation_client = DelegationClient(mcp_client, config['delegation'])
```

---

## Debugging Workflow

### 1. Enable Trace Logging

Set `trace_level: "full"` or `"debug"` in your config.

### 2. Run Delegation Query

```python
result = await delegation_client.process_with_delegation(
    "Fix the authentication bug and verify tests pass"
)
```

### 3. Check Trace Summary

The summary is automatically printed at the end:
```
🔍 Trace Session Summary
Session ID: 20251207_103045
Log file: .trace/trace_20251207_103045.jsonl

Total trace entries: 45
LLM calls: 12
Tool calls: 8
Tasks completed: 3
Tasks failed: 0
```

### 4. Analyze the Trace File

Open the trace file and search for issues:

**Find the planning phase:**
```bash
jq 'select(.entry_type == "planning_phase")' .trace/trace_20251207_103045.jsonl
```

**See what DEBUGGER agent did:**
```bash
jq 'select(.agent_type == "DEBUGGER")' .trace/trace_20251207_103045.jsonl
```

**Check failed tool calls:**
```bash
jq 'select(.entry_type == "tool_call" and .data.success == false)' .trace/trace_20251207_103045.jsonl
```

---

## Performance Impact

### Collapsible Output
- **Impact:** Minimal - only affects display, not execution
- **Overhead:** <1ms per task

### Trace Logging

| Level | Overhead | Disk Space | Recommended For |
|-------|----------|------------|-----------------|
| OFF | 0% | 0 KB | Production |
| SUMMARY | <1% | ~10 KB | Production monitoring |
| BASIC | ~2% | ~50 KB | Normal debugging |
| FULL | ~5% | ~500 KB | Deep debugging |
| DEBUG | ~10% | ~2 MB | Tool debugging |

**Note:** Overhead is per delegation session with 5-10 tasks.

---

## Best Practices

### Collapsible Output

1. **Keep defaults** - 20 lines/1000 chars works well for most use cases
2. **Adjust for your workflow** - If you prefer seeing more output, increase thresholds
3. **Disable for CI/CD** - Set `auto_collapse: false` in automated environments

### Trace Logging

1. **Use BASIC in production** - Good balance of detail and performance
2. **Use FULL for debugging** - When you need to see exact prompts
3. **Use DEBUG for tool issues** - When tool calls are failing
4. **Clean up old traces** - Trace files can grow large over time
   ```bash
   find .trace -name "*.jsonl" -mtime +7 -delete  # Delete traces older than 7 days
   ```
5. **Exclude from git** - Add `.trace/` to your `.gitignore`

---

## Files Added

### New Utility Modules
- `mcp_client_for_ollama/utils/collapsible_output.py` - Collapsible output implementation
- `mcp_client_for_ollama/utils/trace_logger.py` - Trace logging implementation

### Modified Files
- `mcp_client_for_ollama/agents/delegation_client.py` - Integrated both features

---

## Future Enhancements

### Collapsible Output
- [ ] Interactive expansion (prompt user to expand)
- [ ] Syntax highlighting in previews
- [ ] Configurable preview line count

### Trace Logging
- [ ] Web UI for trace analysis
- [ ] Automatic trace comparison (before/after)
- [ ] Export to other formats (HTML, CSV)
- [ ] Real-time trace streaming

---

## Troubleshooting

### Collapsible output not working
- Check `auto_collapse` is `True`
- Verify thresholds are set correctly
- Ensure output is actually large enough to trigger collapsing

### Trace files not being created
- Check `trace_enabled` is `True`
- Verify write permissions on trace directory
- Check disk space availability

### Trace files too large
- Lower the `trace_level` (use BASIC instead of FULL)
- Increase `trace_truncate` value
- Clean up old trace files regularly

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/jonigl/mcp-client-for-ollama/issues
- Documentation: This file

**Happy debugging!** 🔍
