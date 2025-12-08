# Delegation Trace Command-Line Flags

**Date:** December 8, 2025
**Feature:** Command-line flags for delegation trace configuration
**Status:** ✅ Implemented

---

## Overview

Delegation trace settings can now be configured via command-line flags, enabling trace logging in non-interactive mode. This is particularly useful for debugging delegation queries in scripts, CI/CD pipelines, and automated workflows.

---

## Command-Line Flags

### `--trace-enabled` / `--trace`

**Purpose:** Enable delegation trace logging

**Type:** Boolean flag

**Usage:**
```bash
ollmcp -q "delegate query" --trace-enabled
ollmcp -q "delegate query" --trace  # shorthand
```

**Behavior:**
- Enables trace logging for delegation execution
- Automatically enables delegation mode
- Creates trace files with timestamped names
- Saves configuration to `.config/config.json`
- Trace files are written in JSON Lines format

**Default:** Not set (uses existing config or defaults to false)

---

### `--trace-level` TEXT

**Purpose:** Set the trace detail level

**Type:** String argument

**Usage:**
```bash
ollmcp -q "delegate query" --trace-level full
```

**Options:**

| Level | Description | Use Case |
|-------|-------------|----------|
| `off` | No tracing | Disable tracing completely |
| `summary` | Task start/end only | Minimal overhead, task tracking |
| `basic` | Truncated prompts/responses | **Recommended** - Good balance |
| `full` | Complete prompts/responses | Detailed debugging |
| `debug` | Everything including tool calls | Comprehensive analysis |

**Default:** `basic` (if trace enabled)

**Details:**

- **OFF**: No trace files created
- **SUMMARY**:
  - Task start timestamps
  - Task end timestamps
  - Task status (completed/failed)
  - Minimal file size

- **BASIC** (Recommended):
  - Task information
  - Truncated prompts (first 500 chars)
  - Truncated responses (first 500 chars)
  - Tool names used
  - Good for most debugging

- **FULL**:
  - Complete LLM prompts
  - Complete LLM responses
  - All task metadata
  - Large file sizes

- **DEBUG**:
  - Everything from FULL
  - Individual tool call details
  - Tool arguments and results
  - Internal state information
  - Very large file sizes

---

### `--trace-dir` TEXT

**Purpose:** Specify directory for trace files

**Type:** String argument (path)

**Usage:**
```bash
ollmcp -q "delegate query" --trace-dir ./logs/traces
ollmcp -q "delegate query" --trace-dir /var/log/ollmcp/traces
```

**Default:** `.trace` (in current directory)

**Behavior:**
- Creates directory if it doesn't exist
- Trace files named with timestamps: `trace_YYYYMMDD_HHMMSS.jsonl`
- Configuration is saved for future runs
- Can be absolute or relative path

---

## Usage Examples

### Example 1: Basic Trace Logging

```bash
# Enable trace with default settings (basic level, .trace directory)
ollmcp -q "delegate Read all Python files in src/ and summarize" --trace
```

**Output:**
```
Trace logging enabled
Trace directory set to: .trace
Trace configuration saved to .config/config.json

Executing query: delegate Read all Python files in src/ and summarize

[Delegation execution...]

Query completed successfully.
```

**Trace File:** `.trace/trace_20251208_143022.jsonl`

---

### Example 2: Full Debug Trace

```bash
# Enable full debug tracing for comprehensive analysis
ollmcp -q "delegate complex multi-step task" --trace --trace-level debug
```

**Output:**
```
Trace logging enabled
Trace level set to: debug
Trace configuration saved to .config/config.json

Executing query: delegate complex multi-step task

[Detailed delegation execution with full logging...]

Query completed successfully.
```

**Trace File Content (debug level):**
```json
{"timestamp": "2025-12-08T14:30:22.123456", "entry_type": "planning_phase", ...}
{"timestamp": "2025-12-08T14:30:23.456789", "entry_type": "task_start", ...}
{"timestamp": "2025-12-08T14:30:24.789012", "entry_type": "llm_call", "data": {"prompt": "...", "response": "..."}}
{"timestamp": "2025-12-08T14:30:25.012345", "entry_type": "tool_call", "data": {"tool_name": "...", "arguments": {...}}}
...
```

---

### Example 3: Custom Trace Directory

```bash
# Use custom trace directory
ollmcp -q "delegate task" --trace --trace-dir /var/log/delegation/traces
```

**Output:**
```
Trace logging enabled
Trace directory set to: /var/log/delegation/traces
Trace configuration saved to .config/config.json

Executing query: delegate task

Query completed successfully.
```

**Trace File:** `/var/log/delegation/traces/trace_20251208_143022.jsonl`

---

### Example 4: Quiet Mode with Trace

```bash
# Enable trace but suppress output (for scripts)
ollmcp -q "delegate task" --trace --trace-level full -Q > result.txt

# Check trace file for debugging
cat .trace/trace_*.jsonl | jq '.entry_type' | sort | uniq -c
```

**Output to stdout:**
```
[Task result only - no status messages]
```

**Trace File:** Contains full debugging information

---

### Example 5: CI/CD Integration

```yaml
# GitHub Actions workflow
name: Analyze Code
on: [push]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Run delegation analysis with trace
        run: |
          ollmcp -q "delegate Analyze code quality and security" \
            --trace \
            --trace-level full \
            --trace-dir ./analysis-traces \
            -Q > analysis_result.txt

      - name: Upload analysis results
        uses: actions/upload-artifact@v2
        with:
          name: analysis-results
          path: |
            analysis_result.txt
            analysis-traces/
```

---

## Trace File Format

Trace files are written in **JSON Lines** format (`.jsonl`), with one JSON object per line.

### Common Entry Types

**1. Planning Phase:**
```json
{
  "timestamp": "2025-12-08T14:30:22.123456",
  "entry_type": "planning_phase",
  "task_id": null,
  "agent_type": "PLANNER",
  "data": {
    "query": "user query here",
    "plan": {
      "tasks": [...]
    },
    "available_agents": [...],
    "examples_used": [...],
    "task_count": 3
  }
}
```

**2. Task Start:**
```json
{
  "timestamp": "2025-12-08T14:30:23.456789",
  "entry_type": "task_start",
  "task_id": "task_1",
  "agent_type": "READER",
  "data": {
    "description": "Read all Python files...",
    "dependencies": []
  }
}
```

**3. LLM Call (BASIC level):**
```json
{
  "timestamp": "2025-12-08T14:30:24.789012",
  "entry_type": "llm_call",
  "task_id": "task_1",
  "agent_type": "READER",
  "data": {
    "model": "qwen2.5-coder:32b",
    "temperature": 0.4,
    "loop_iteration": 0,
    "prompt": "You are a command... [truncated at 500 chars]",
    "response": "Here are the Python files... [truncated at 500 chars]",
    "prompt_length": 1240,
    "response_length": 856,
    "tools_used": ["builtin.list_files", "builtin.read_file"]
  }
}
```

**4. Tool Call (DEBUG level only):**
```json
{
  "timestamp": "2025-12-08T14:30:25.012345",
  "entry_type": "tool_call",
  "task_id": "task_1",
  "agent_type": "READER",
  "data": {
    "tool_name": "builtin.read_file",
    "arguments": {
      "path": "src/main.py"
    },
    "result": "def main():...",
    "result_length": 523,
    "success": true
  }
}
```

**5. Task End:**
```json
{
  "timestamp": "2025-12-08T14:30:26.345678",
  "entry_type": "task_end",
  "task_id": "task_1",
  "agent_type": "READER",
  "data": {
    "status": "completed",
    "result": "Found 15 Python files...",
    "error": null,
    "duration_ms": 2888.889,
    "result_length": 245
  }
}
```

---

## Analyzing Trace Files

### Using jq (JSON processor)

```bash
# Count entry types
cat .trace/trace_*.jsonl | jq -r '.entry_type' | sort | uniq -c

# Extract all task IDs
cat .trace/trace_*.jsonl | jq -r '.task_id' | grep -v null | sort -u

# Find failed tasks
cat .trace/trace_*.jsonl | jq 'select(.entry_type=="task_end" and .data.status=="failed")'

# Get timing for each task
cat .trace/trace_*.jsonl | jq 'select(.entry_type=="task_end") | {task_id, duration: .data.duration_ms}'

# Extract all tool calls
cat .trace/trace_*.jsonl | jq 'select(.entry_type=="tool_call") | {tool: .data.tool_name, success: .data.success}'
```

### Using Python

```python
import json

# Parse trace file
with open('.trace/trace_20251208_143022.jsonl', 'r') as f:
    entries = [json.loads(line) for line in f]

# Analyze planning
planning = [e for e in entries if e['entry_type'] == 'planning_phase'][0]
print(f"Query: {planning['data']['query']}")
print(f"Tasks planned: {planning['data']['task_count']}")

# Find slow tasks
task_ends = [e for e in entries if e['entry_type'] == 'task_end']
slow_tasks = [e for e in task_ends if e['data']['duration_ms'] > 5000]
print(f"Slow tasks (>5s): {len(slow_tasks)}")

# Count tool usage
tool_calls = [e for e in entries if e['entry_type'] == 'tool_call']
tool_counts = {}
for call in tool_calls:
    tool = call['data']['tool_name']
    tool_counts[tool] = tool_counts.get(tool, 0) + 1
print(f"Tool usage: {tool_counts}")
```

---

## Configuration Persistence

When trace flags are used, the settings are saved to `.config/config.json`:

```json
{
  "delegation": {
    "enabled": true,
    "trace_enabled": true,
    "trace_level": "full",
    "trace_dir": ".trace",
    "trace_console": false,
    "trace_truncate": 500,
    "collapsible_output": {
      "auto_collapse": true,
      "line_threshold": 20,
      "char_threshold": 1000
    }
  }
}
```

**Benefits:**
- Settings persist across runs
- Can be overridden by flags on subsequent runs
- Can be edited manually
- Compatible with interactive `dt` command

---

## Best Practices

### 1. Start with BASIC Level

```bash
# Good - reasonable detail, manageable file size
ollmcp -q "delegate task" --trace --trace-level basic
```

### 2. Use DEBUG Only When Needed

```bash
# Use DEBUG for specific debugging sessions
ollmcp -q "delegate problematic task" --trace --trace-level debug

# Then switch back to BASIC
ollmcp -q "delegate normal task" --trace --trace-level basic
```

### 3. Organize Trace Files

```bash
# Use descriptive directories
ollmcp -q "delegate task" --trace --trace-dir ./traces/$(date +%Y%m%d)

# Or by task type
ollmcp -q "delegate code analysis" --trace --trace-dir ./traces/code-analysis
```

### 4. Clean Up Old Traces

```bash
# Remove traces older than 7 days
find .trace -name "trace_*.jsonl" -mtime +7 -delete

# Archive old traces
tar -czf traces-archive-$(date +%Y%m).tar.gz .trace/*.jsonl
rm .trace/*.jsonl
```

### 5. Combine with Quiet Mode for Scripts

```bash
# Script-friendly: result to stdout, trace for debugging
ollmcp -q "delegate task" --trace --trace-level full -Q > result.txt 2> errors.txt
```

---

## Troubleshooting

### Trace Files Not Created

**Problem:** No trace files appear in trace directory

**Possible Causes:**
1. Trace not enabled: Use `--trace-enabled` or `--trace`
2. Wrong directory: Check `--trace-dir` path
3. Permission issues: Ensure write access to trace directory
4. Not a delegation query: Trace only works with `delegate` command

**Solution:**
```bash
# Verify trace is enabled
ollmcp -q "delegate task" --trace --trace-level debug

# Check if trace directory exists and is writable
ls -la .trace/
```

### Trace Level Not Applied

**Problem:** Trace level seems wrong (too much/too little detail)

**Solution:**
```bash
# Explicitly set trace level
ollmcp -q "delegate task" --trace --trace-level basic

# Check saved config
cat .config/config.json | jq '.delegation.trace_level'
```

### Trace Files Too Large

**Problem:** Trace files consuming too much disk space

**Solution:**
```bash
# Use BASIC or SUMMARY level
ollmcp -q "delegate task" --trace --trace-level basic

# Or disable tracing when not needed
ollmcp -q "delegate task"  # No trace flags
```

---

## Comparison: CLI Flags vs Interactive `dt` Command

| Feature | CLI Flags | Interactive `dt` |
|---------|-----------|------------------|
| **Usage** | Non-interactive scripts | Interactive sessions |
| **Configuration** | Per-command | Saved to config |
| **Options** | All trace settings | All trace settings + UI |
| **Convenience** | Quick one-liners | Guided configuration |
| **Automation** | CI/CD friendly | Manual setup |

**When to use CLI flags:**
- Scripts and automation
- CI/CD pipelines
- One-off debugging sessions
- Command-line workflows

**When to use interactive `dt`:**
- First-time setup
- Exploring trace options
- Changing multiple settings
- Interactive debugging sessions

**Both methods:**
- Save to `.config/config.json`
- Are compatible with each other
- Support all trace levels
- Can be overridden

---

## Summary

Delegation trace settings can now be configured via command-line flags:

```bash
# Enable trace with defaults
ollmcp -q "delegate task" --trace

# Full control over trace settings
ollmcp -q "delegate task" \
  --trace \
  --trace-level full \
  --trace-dir ./custom/traces

# Combine with quiet mode for scripts
ollmcp -q "delegate task" --trace --trace-level debug -Q > output.txt
```

**Key Benefits:**
- ✅ Non-interactive trace configuration
- ✅ Script and automation friendly
- ✅ CI/CD integration
- ✅ Flexible trace levels
- ✅ Custom trace directories
- ✅ Configuration persistence
- ✅ Compatible with interactive `dt`

---

**Implemented By:** Claude Sonnet 4.5
**Implementation Date:** December 8, 2025
**Status:** Ready for Use
