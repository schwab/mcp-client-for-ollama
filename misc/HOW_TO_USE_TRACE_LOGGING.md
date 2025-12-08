# How to Use Trace Logging

Trace logging allows you to capture and analyze every LLM interaction during agent delegation, making it easy to debug issues and understand what each agent is doing.

---

## Quick Start

### Step 1: Create a Configuration File

Create or edit your configuration file at `.config/config.json`:

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

### Step 2: Add .trace/ to .gitignore

```bash
echo ".trace/" >> .gitignore
```

### Step 3: Use Delegation

Start `ollmcp` and use the `@delegate` command:

```bash
ollmcp
```

Then in the prompt:
```
You: @delegate Fix the bug in authentication.py and verify the tests pass
```

### Step 4: Check Trace Output

At the end of delegation, you'll see a summary:

```
🔍 Trace Session Summary
Session ID: 20251207_153045
Log file: .trace/trace_20251207_153045.jsonl

Total trace entries: 45
LLM calls: 12
Tool calls: 8
Tasks completed: 3
Tasks failed: 0
```

### Step 5: Analyze Trace File

```bash
# View the trace file
cat .trace/trace_20251207_153045.jsonl | jq .

# See what the planner decided
grep '"entry_type": "planning_phase"' .trace/trace_*.jsonl | jq .

# See all prompts sent to DEBUGGER agent
grep '"agent_type": "DEBUGGER"' .trace/trace_*.jsonl | jq -r '.data.prompt'
```

---

## Configuration Options

### Minimal Configuration (Enable Trace Logging)

```json
{
  "delegation": {
    "enabled": true,
    "trace_enabled": true
  }
}
```

**Defaults:**
- `trace_level`: "basic" (prompts/responses truncated to 500 chars)
- `trace_dir`: ".trace"
- `trace_console`: false

### Recommended Development Configuration

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
    "trace_dir": ".trace"
  }
}
```

### Full Debugging Configuration

```json
{
  "delegation": {
    "enabled": true,
    "execution_mode": "sequential",

    "collapsible_output": {
      "auto_collapse": true,
      "line_threshold": 15,
      "char_threshold": 800
    },

    "trace_enabled": true,
    "trace_level": "full",
    "trace_dir": ".trace",
    "trace_console": false,
    "trace_truncate": 1000
  }
}
```

### Maximum Verbosity (Tool Debugging)

```json
{
  "delegation": {
    "enabled": true,
    "trace_enabled": true,
    "trace_level": "debug",
    "trace_console": true
  }
}
```

---

## Trace Levels Explained

### OFF
- **What:** No tracing
- **Use When:** Production or when you don't need debugging
- **Overhead:** 0%
- **File Size:** 0 KB

### SUMMARY
- **What:** Task start/end only
- **Use When:** Production monitoring, just want to know what tasks ran
- **Overhead:** <1%
- **File Size:** ~10 KB per session
- **Example:**
  ```json
  {"entry_type": "task_start", "task_id": "task_1", "agent_type": "READER"}
  {"entry_type": "task_end", "task_id": "task_1", "status": "completed"}
  ```

### BASIC (Default)
- **What:** Prompts and responses, truncated to 500 characters
- **Use When:** Normal development and debugging
- **Overhead:** ~2%
- **File Size:** ~50 KB per session
- **Example:**
  ```json
  {
    "entry_type": "llm_call",
    "data": {
      "prompt": "You are a code reader... (truncated)",
      "response": "I'll analyze the file... (truncated)",
      "prompt_length": 2345,
      "response_length": 1234
    }
  }
  ```

### FULL
- **What:** Complete prompts and responses, no truncation
- **Use When:** Deep debugging, need to see exact prompts
- **Overhead:** ~5%
- **File Size:** ~500 KB per session
- **Example:**
  ```json
  {
    "entry_type": "llm_call",
    "data": {
      "prompt": "You are a code reading specialist...[full prompt]",
      "response": "I'll analyze the file step by step...[full response]"
    }
  }
  ```

### DEBUG
- **What:** Everything including tool calls with full arguments and results
- **Use When:** Tool execution issues, need maximum detail
- **Overhead:** ~10%
- **File Size:** ~2 MB per session
- **Also Logs:**
  ```json
  {
    "entry_type": "tool_call",
    "data": {
      "tool_name": "builtin.read_file",
      "arguments": {"path": "config.py"},
      "result": "[full file contents]",
      "success": true
    }
  }
  ```

---

## Configuration File Location

The config file is loaded from:

**Default location:**
```
~/.config/mcp-client-for-ollama/config.json
```

**Or environment variable:**
```bash
export MCP_CLIENT_CONFIG_DIR="/path/to/config"
```

**Or specify at runtime:**
```bash
ollmcp --config /path/to/config.json
```

---

## Using Trace Logging

### Enable Delegation with Trace Logging

1. **Edit your config file** (`~/.config/mcp-client-for-ollama/config.json`):
   ```json
   {
     "delegation": {
       "enabled": true,
       "trace_enabled": true,
       "trace_level": "full"
     }
   }
   ```

2. **Start ollmcp:**
   ```bash
   ollmcp
   ```

3. **Use delegation:**
   ```
   You: @delegate Read auth.py and fix the login bug
   ```

4. **Watch the output:**
   - Tasks execute with status updates
   - Collapsible output keeps terminal clean
   - Trace summary shows at the end

5. **Analyze the trace:**
   ```bash
   # List all trace files
   ls -lh .trace/

   # View latest trace
   cat .trace/trace_*.jsonl | tail -100 | jq .
   ```

---

## Analyzing Trace Files

Trace files are in JSON Lines format - one JSON object per line.

### View Entire Trace

```bash
cat .trace/trace_20251207_153045.jsonl | jq .
```

### Find Planning Phase

See what tasks the planner created:

```bash
grep '"entry_type": "planning_phase"' .trace/trace_*.jsonl | jq .
```

**Output:**
```json
{
  "timestamp": "2025-12-07T15:30:45.123",
  "entry_type": "planning_phase",
  "agent_type": "PLANNER",
  "data": {
    "query": "Fix authentication bug",
    "plan": {
      "tasks": [
        {
          "id": "task_1",
          "agent_type": "READER",
          "description": "Read and analyze auth.py"
        },
        {
          "id": "task_2",
          "agent_type": "DEBUGGER",
          "description": "Identify the bug"
        }
      ]
    }
  }
}
```

### See All Prompts for a Specific Agent

```bash
grep '"agent_type": "DEBUGGER"' .trace/trace_*.jsonl | \
  jq -r 'select(.entry_type == "llm_call") | .data.prompt'
```

### See All Responses from a Task

```bash
grep '"task_id": "task_2"' .trace/trace_*.jsonl | \
  jq -r 'select(.entry_type == "llm_call") | .data.response'
```

### Find Failed Tasks

```bash
grep '"entry_type": "task_end"' .trace/trace_*.jsonl | \
  jq 'select(.data.status == "failed")'
```

### Find Failed Tool Calls

```bash
grep '"entry_type": "tool_call"' .trace/trace_*.jsonl | \
  jq 'select(.data.success == false)'
```

### Count LLM Calls per Agent

```bash
grep '"entry_type": "llm_call"' .trace/trace_*.jsonl | \
  jq -r '.agent_type' | sort | uniq -c
```

**Output:**
```
  5 DEBUGGER
  3 PLANNER
  4 READER
  2 CODER
```

### Calculate Task Durations

```bash
grep '"entry_type": "task_end"' .trace/trace_*.jsonl | \
  jq -r '.data.duration_ms' | \
  awk '{sum+=$1; count++} END {print "Average: " sum/count " ms"}'
```

### Extract All Tool Names Used

```bash
grep '"entry_type": "llm_call"' .trace/trace_*.jsonl | \
  jq -r '.data.tools_used[]' | sort -u
```

---

## Common Debugging Workflows

### Debug: Why Did Planning Fail?

1. **Find the planning phase:**
   ```bash
   grep '"entry_type": "planning_phase"' .trace/trace_*.jsonl | jq .
   ```

2. **Check the planner's prompt:**
   ```bash
   grep '"agent_type": "PLANNER"' .trace/trace_*.jsonl | \
     jq -r 'select(.entry_type == "llm_call") | .data.prompt'
   ```

3. **Check the planner's response:**
   ```bash
   grep '"agent_type": "PLANNER"' .trace/trace_*.jsonl | \
     jq -r 'select(.entry_type == "llm_call") | .data.response'
   ```

### Debug: Why Did a Task Fail?

1. **Find which task failed:**
   ```bash
   grep '"status": "failed"' .trace/trace_*.jsonl | jq .
   ```

2. **See all LLM calls for that task:**
   ```bash
   grep '"task_id": "task_2"' .trace/trace_*.jsonl | \
     jq 'select(.entry_type == "llm_call")'
   ```

3. **Check if any tool calls failed:**
   ```bash
   grep '"task_id": "task_2"' .trace/trace_*.jsonl | \
     jq 'select(.entry_type == "tool_call" and .data.success == false)'
   ```

### Debug: Why Is a Task Taking So Long?

1. **Check loop iterations:**
   ```bash
   grep '"task_id": "task_3"' .trace/trace_*.jsonl | \
     jq 'select(.entry_type == "llm_call") | .data.loop_iteration'
   ```

2. **Count tool calls:**
   ```bash
   grep '"task_id": "task_3"' .trace/trace_*.jsonl | \
     grep '"entry_type": "tool_call"' | wc -l
   ```

3. **Check task duration:**
   ```bash
   grep '"task_id": "task_3"' .trace/trace_*.jsonl | \
     jq 'select(.entry_type == "task_end") | .data.duration_ms'
   ```

---

## Example Session

### 1. Enable Trace Logging

Edit `~/.config/mcp-client-for-ollama/config.json`:
```json
{
  "delegation": {
    "enabled": true,
    "trace_enabled": true,
    "trace_level": "full"
  }
}
```

### 2. Run Delegation

```bash
ollmcp
```

```
You: @delegate Fix the authentication timeout bug and verify tests pass

🤖 Planning tasks...

✅ Task Plan Created:
  • task_1 (READER): Read and analyze authentication code
  • task_2 (DEBUGGER): Identify timeout bug
  • task_3 (CODER): Fix the bug
  • task_4 (EXECUTOR): Run tests to verify fix

▶ ✓ task_1 (READER) (87 lines, 5432 chars)
  Analyzed auth.py and found...
  ... (84 more lines hidden)

▶ ✓ task_2 (DEBUGGER) (45 lines, 2891 chars)
  Found timeout issue in session handler...
  ... (42 more lines hidden)

▶ ✓ task_3 (CODER) (34 lines, 1823 chars)
  Modified auth.py to fix timeout...
  ... (31 more lines hidden)

▶ ✓ task_4 (EXECUTOR) (12 lines, 567 chars)
  All tests passed ✓
  ... (9 more lines hidden)

🔍 Trace Session Summary
Session ID: 20251207_153045
Log file: .trace/trace_20251207_153045.jsonl

Total trace entries: 45
LLM calls: 12
Tool calls: 8
Tasks completed: 4
Tasks failed: 0

📋 Final Response:
Fixed the authentication timeout bug. The issue was in the session handler...
```

### 3. Analyze What Happened

```bash
# What did the planner decide?
grep '"entry_type": "planning_phase"' .trace/trace_20251207_153045.jsonl | jq .

# What did DEBUGGER find?
grep '"agent_type": "DEBUGGER"' .trace/trace_20251207_153045.jsonl | \
  jq -r 'select(.entry_type == "llm_call") | .data.response'

# What code changes did CODER make?
grep '"agent_type": "CODER"' .trace/trace_20251207_153045.jsonl | \
  jq -r 'select(.entry_type == "llm_call") | .data.response'
```

---

## Trace File Management

### Clean Up Old Traces

```bash
# Delete traces older than 7 days
find .trace -name "*.jsonl" -mtime +7 -delete

# Delete all traces
rm -rf .trace/
```

### Archive Important Traces

```bash
# Create archive directory
mkdir -p .trace/archive

# Move specific trace
mv .trace/trace_20251207_153045.jsonl .trace/archive/

# Compress old traces
tar -czf traces-backup-$(date +%Y%m%d).tar.gz .trace/*.jsonl
mv traces-backup-*.tar.gz .trace/archive/
```

### Disk Space Monitoring

```bash
# Check trace directory size
du -sh .trace/

# List traces by size
ls -lhS .trace/
```

---

## Best Practices

### 1. Use BASIC in Development
- Good balance of detail and performance
- Sufficient for most debugging

### 2. Use FULL for Deep Debugging
- When you need to see exact prompts
- When debugging prompt engineering issues

### 3. Use DEBUG Only When Needed
- Tool execution issues
- High overhead and large files

### 4. Always Add .trace/ to .gitignore
```bash
echo ".trace/" >> .gitignore
```

### 5. Clean Up Old Traces Regularly
```bash
find .trace -name "*.jsonl" -mtime +7 -delete
```

### 6. Disable in Production
```json
{
  "delegation": {
    "trace_enabled": false
  }
}
```

---

## Troubleshooting

### Trace Files Not Being Created

**Check:**
1. `trace_enabled` is `true` in config
2. Write permissions on `.trace/` directory
3. Disk space available

**Solution:**
```bash
mkdir -p .trace
chmod 755 .trace
df -h .  # Check disk space
```

### Trace Files Too Large

**Solution 1:** Lower trace level
```json
{
  "delegation": {
    "trace_level": "basic"  // Instead of "full"
  }
}
```

**Solution 2:** Increase truncate length
```json
{
  "delegation": {
    "trace_level": "basic",
    "trace_truncate": 200  // Instead of 500
  }
}
```

**Solution 3:** Clean up old traces
```bash
find .trace -name "*.jsonl" -mtime +7 -delete
```

### Can't Parse JSON

Trace files are **JSON Lines** format (one JSON object per line), not regular JSON.

**Wrong:**
```bash
cat .trace/trace_*.jsonl | jq .  # May fail on large files
```

**Right:**
```bash
cat .trace/trace_*.jsonl | jq -c .  # Compact output
grep '"entry_type": "llm_call"' .trace/trace_*.jsonl | jq .  # Filter first
```

---

## Summary

### To Enable Trace Logging:

1. **Add to config:**
   ```json
   {
     "delegation": {
       "enabled": true,
       "trace_enabled": true,
       "trace_level": "full"
     }
   }
   ```

2. **Use delegation:**
   ```
   @delegate Your query here
   ```

3. **Check trace summary:**
   - Automatically printed at end

4. **Analyze trace file:**
   ```bash
   cat .trace/trace_*.jsonl | jq .
   ```

### Configuration Options:

| Option | Values | Default | Use |
|--------|--------|---------|-----|
| `trace_enabled` | true/false | false | Enable/disable |
| `trace_level` | off/summary/basic/full/debug | basic | Verbosity |
| `trace_dir` | path | .trace | Output directory |
| `trace_console` | true/false | false | Also print to console |
| `trace_truncate` | number | 500 | Truncation length for BASIC |

### Recommended Settings:

- **Development:** `trace_level: "basic"`
- **Deep Debugging:** `trace_level: "full"`
- **Tool Issues:** `trace_level: "debug"`
- **Production:** `trace_enabled: false`

**Happy debugging!** 🔍
