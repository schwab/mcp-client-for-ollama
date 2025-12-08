# Trace Logging - Quick Reference

## Enable Trace Logging (3 Steps)

### 1. Edit Config
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

### 2. Add to .gitignore
```bash
echo ".trace/" >> .gitignore
```

### 3. Use Delegation
```bash
ollmcp
```
```
You: @delegate Fix the bug in auth.py
```

---

## Configuration

```json
{
  "delegation": {
    "trace_enabled": true,      // Enable/disable trace logging
    "trace_level": "basic",     // off | summary | basic | full | debug
    "trace_dir": ".trace",      // Output directory
    "trace_console": false,     // Print to console (DEBUG only)
    "trace_truncate": 500       // Truncation length for BASIC
  }
}
```

---

## Trace Levels

| Level | What Gets Logged | Overhead | File Size | Use Case |
|-------|-----------------|----------|-----------|----------|
| `off` | Nothing | 0% | 0 KB | Production |
| `summary` | Task start/end | <1% | ~10 KB | Monitoring |
| `basic` | Prompts/responses (truncated) | ~2% | ~50 KB | **Development** ✅ |
| `full` | Complete prompts/responses | ~5% | ~500 KB | Deep debugging |
| `debug` | Everything + tool calls | ~10% | ~2 MB | Tool issues |

**Recommended:** Use `basic` for development, `full` for debugging.

---

## Common Analysis Commands

### View Entire Trace
```bash
cat .trace/trace_*.json | jq .
```

### What Did the Planner Decide?
```bash
grep '"entry_type": "planning_phase"' .trace/trace_*.json | jq .
```

### What Did DEBUGGER Agent Do?
```bash
grep '"agent_type": "DEBUGGER"' .trace/trace_*.json | \
  jq 'select(.entry_type == "llm_call")'
```

### Which Tasks Failed?
```bash
grep '"entry_type": "task_end"' .trace/trace_*.json | \
  jq 'select(.data.status == "failed")'
```

### Which Tool Calls Failed?
```bash
grep '"entry_type": "tool_call"' .trace/trace_*.json | \
  jq 'select(.data.success == false)'
```

### Count LLM Calls per Agent
```bash
grep '"entry_type": "llm_call"' .trace/trace_*.json | \
  jq -r '.agent_type' | sort | uniq -c
```

### All Prompts for a Specific Agent
```bash
grep '"agent_type": "CODER"' .trace/trace_*.json | \
  jq -r 'select(.entry_type == "llm_call") | .data.prompt'
```

### All Responses from a Task
```bash
grep '"task_id": "task_2"' .trace/trace_*.json | \
  jq -r 'select(.entry_type == "llm_call") | .data.response'
```

### Task Duration Statistics
```bash
grep '"entry_type": "task_end"' .trace/trace_*.json | \
  jq -r '.data.duration_ms' | \
  awk '{sum+=$1; count++} END {print "Average: " sum/count " ms"}'
```

---

## Trace File Management

### List Traces
```bash
ls -lh .trace/
```

### Check Directory Size
```bash
du -sh .trace/
```

### Delete Old Traces (7+ days)
```bash
find .trace -name "*.json" -mtime +7 -delete
```

### Delete All Traces
```bash
rm -rf .trace/
```

### Archive Traces
```bash
tar -czf traces-backup-$(date +%Y%m%d).tar.gz .trace/*.json
mv traces-backup-*.tar.gz .trace/archive/
```

---

## Trace Entry Types

| Entry Type | What It Logs |
|------------|--------------|
| `planning_phase` | Planner's query and generated task plan |
| `task_start` | Task begins execution |
| `llm_call` | LLM prompt and response |
| `tool_call` | Tool execution (DEBUG level only) |
| `task_end` | Task completion with status and duration |

---

## Example Trace Entries

### Planning Phase
```json
{
  "timestamp": "2025-12-07T15:30:45.123",
  "entry_type": "planning_phase",
  "agent_type": "PLANNER",
  "data": {
    "query": "Fix auth bug",
    "plan": { "tasks": [...] }
  }
}
```

### LLM Call (BASIC level)
```json
{
  "timestamp": "2025-12-07T15:30:46.456",
  "entry_type": "llm_call",
  "task_id": "task_1",
  "agent_type": "READER",
  "data": {
    "model": "qwen2.5:7b",
    "prompt": "You are a code reader... (truncated)",
    "response": "I'll analyze... (truncated)",
    "prompt_length": 2345,
    "response_length": 1234,
    "tools_used": ["builtin.read_file"]
  }
}
```

### Tool Call (DEBUG level only)
```json
{
  "timestamp": "2025-12-07T15:30:47.789",
  "entry_type": "tool_call",
  "task_id": "task_1",
  "agent_type": "READER",
  "data": {
    "tool_name": "builtin.read_file",
    "arguments": {"path": "auth.py"},
    "result": "[file contents]",
    "success": true
  }
}
```

### Task End
```json
{
  "timestamp": "2025-12-07T15:30:50.123",
  "entry_type": "task_end",
  "task_id": "task_1",
  "agent_type": "READER",
  "data": {
    "status": "completed",
    "result": "Analysis complete...",
    "duration_ms": 3334
  }
}
```

---

## Debugging Workflows

### My Task Failed - Why?

```bash
# 1. Find which task failed
grep '"status": "failed"' .trace/trace_*.json | jq .

# 2. Get task ID (e.g., "task_2")

# 3. See all LLM calls for that task
grep '"task_id": "task_2"' .trace/trace_*.json | \
  jq 'select(.entry_type == "llm_call")'

# 4. Check for failed tool calls
grep '"task_id": "task_2"' .trace/trace_*.json | \
  jq 'select(.entry_type == "tool_call" and .data.success == false)'
```

### Planner Made Bad Decisions - Why?

```bash
# 1. See what the planner was given
grep '"entry_type": "planning_phase"' .trace/trace_*.json | \
  jq '.data.query'

# 2. See the planner's prompt
grep '"agent_type": "PLANNER"' .trace/trace_*.json | \
  jq -r 'select(.entry_type == "llm_call") | .data.prompt'

# 3. See what plan it generated
grep '"entry_type": "planning_phase"' .trace/trace_*.json | \
  jq '.data.plan'
```

### Task Is Slow - Why?

```bash
# 1. Check how many LLM calls
grep '"task_id": "task_3"' .trace/trace_*.json | \
  grep '"entry_type": "llm_call"' | wc -l

# 2. Check loop iterations
grep '"task_id": "task_3"' .trace/trace_*.json | \
  jq 'select(.entry_type == "llm_call") | .data.loop_iteration'

# 3. Check total duration
grep '"task_id": "task_3"' .trace/trace_*.json | \
  jq 'select(.entry_type == "task_end") | .data.duration_ms'
```

---

## Tips & Tricks

### Tail the Latest Trace in Real-Time
```bash
tail -f .trace/trace_$(ls -t .trace/ | head -1)
```

### Pretty Print Latest Trace
```bash
cat .trace/trace_$(ls -t .trace/ | head -1) | jq .
```

### Search All Traces for a Pattern
```bash
grep -r "authentication" .trace/*.json | jq .
```

### Extract Only Task Descriptions
```bash
grep '"entry_type": "task_start"' .trace/trace_*.json | \
  jq -r '.data.description'
```

### Count Total LLM Calls
```bash
grep '"entry_type": "llm_call"' .trace/trace_*.json | wc -l
```

### Get Summary Stats
```bash
echo "Tasks: $(grep '"entry_type": "task_end"' .trace/trace_*.json | wc -l)"
echo "LLM Calls: $(grep '"entry_type": "llm_call"' .trace/trace_*.json | wc -l)"
echo "Tool Calls: $(grep '"entry_type": "tool_call"' .trace/trace_*.json | wc -l)"
```

---

## Common Issues

### Trace Files Not Created
- Check `trace_enabled: true` in config
- Check write permissions: `chmod 755 .trace`
- Check disk space: `df -h .`

### Files Too Large
- Lower trace level: `"trace_level": "basic"`
- Reduce truncate length: `"trace_truncate": 200`
- Clean old traces: `find .trace -mtime +7 -delete`

### Can't Parse JSON
- Use `jq -c` for compact output
- Filter first: `grep ... | jq .`
- Remember: JSON Lines format (one object per line)

---

## See Also

- **Full Documentation:** `COLLAPSIBLE_OUTPUT_AND_TRACE_LOGGING.md`
- **Detailed Guide:** `HOW_TO_USE_TRACE_LOGGING.md`
- **Example Config:** `config.example.json`

---

**Quick Start:**
1. Add to config: `"trace_enabled": true, "trace_level": "full"`
2. Use: `@delegate Your query`
3. Analyze: `cat .trace/trace_*.json | jq .`

**That's it!** 🔍
