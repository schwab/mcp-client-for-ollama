# Non-Interactive Query Mode

**Date:** December 8, 2025
**Feature:** Command-line query execution for scripting and automation
**Status:** ✅ Implemented

---

## Overview

The MCP Client for Ollama now supports non-interactive query execution via the `--query` / `-q` command-line option. This allows the tool to be used in scripts, automation workflows, and CI/CD pipelines without requiring interactive input.

---

## Usage

### Basic Syntax

```bash
ollmcp --query "your query here"
# or
ollmcp -q "your query here"
```

### Quiet Mode (Minimal Output)

For scripting where you only want the response without formatting:

```bash
ollmcp --query "your query" --quiet
# or
ollmcp -q "your query" -Q
```

---

## Examples

### Example 1: Simple Query

```bash
ollmcp -q "What is the capital of France?"
```

**Output:**
```
Executing query: What is the capital of France?

The capital of France is Paris.

Query completed successfully.
```

### Example 2: Delegation Query

```bash
ollmcp -q "delegate Scan all Python files in src/ and create a summary in summary.md"
```

**Output:**
```
Executing query: delegate Scan all Python files in src/ and create a summary in summary.md

[Delegation execution output...]

📋 Final Response:
┌─────────────────────────────────────────┐
│ I have scanned all Python files...     │
│ [Response details]                      │
└─────────────────────────────────────────┘

Query completed successfully.
```

### Example 3: Quiet Mode for Scripting

```bash
ollmcp -q "What is 2+2?" -Q
```

**Output:**
```
2+2 equals 4.
```

Note: In quiet mode, only the response is printed (no formatting, no status messages).

### Example 4: Delegation with Trace Logging

```bash
# Enable trace logging for debugging
ollmcp -q "delegate Scan all Python files and create summary" --trace-enabled --trace-level full

# Or use shorthand
ollmcp -q "delegate Scan all Python files and create summary" --trace --trace-level debug

# Custom trace directory
ollmcp -q "delegate complex task" --trace --trace-dir ./debug/traces
```

**Output:**
```
Trace logging enabled
Trace level set to: full
Trace directory set to: ./debug/traces
Trace configuration saved to .config/config.json

Executing query: delegate Scan all Python files and create summary

[Delegation execution with full trace logging...]

📋 Final Response:
[Response details]

Query completed successfully.

# Check trace file
cat .trace/trace_20251208_*.json
```

### Example 5: Using in Scripts

**Bash script:**
```bash
#!/bin/bash

# Generate a summary from log files with trace logging
RESULT=$(ollmcp -q "delegate Read error.log and summarize the main issues" --trace -Q)

# Save to file
echo "$RESULT" > issues_summary.txt

# Check trace for debugging if needed
if [ -n "$RESULT" ]; then
    echo "Summary generated successfully"
    echo "Trace available in .trace/ directory"
else
    echo "Failed to generate summary"
    echo "Check trace file for details"
    exit 1
fi
```

**Python script:**
```python
import subprocess
import json

# Execute query
result = subprocess.run(
    ['ollmcp', '-q', 'What is the current weather?', '-Q'],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print(f"Response: {result.stdout}")
else:
    print(f"Error: {result.stderr}")
```

---

## Command-Line Options

### `--query` / `-q` TEXT

**Purpose:** Execute a single query non-interactively and exit

**Usage:**
```bash
ollmcp --query "your query here"
ollmcp -q "your query here"
```

**Behavior:**
- Executes the query once
- Displays the response
- Exits automatically
- Does not enter interactive mode
- Supports all query types (normal queries, delegation, etc.)

### `--quiet` / `-Q`

**Purpose:** Minimal output mode for scripting

**Usage:**
```bash
ollmcp --query "your query" --quiet
ollmcp -q "your query" -Q
```

**Behavior:**
- Suppresses rich formatting
- Suppresses status messages
- Only prints the response text
- Errors go to stderr
- Perfect for piping to other commands

### `--trace-enabled` / `--trace`

**Purpose:** Enable delegation trace logging (for debugging delegation queries)

**Usage:**
```bash
ollmcp -q "delegate query" --trace-enabled
ollmcp -q "delegate query" --trace
```

**Behavior:**
- Enables trace logging for delegation execution
- Automatically enables delegation mode
- Creates trace files in trace directory
- Saves configuration for future runs

### `--trace-level` TEXT

**Purpose:** Set the trace detail level

**Usage:**
```bash
ollmcp -q "delegate query" --trace-level full
```

**Options:**
- `off` - No tracing
- `summary` - Task start/end only
- `basic` - Truncated prompts/responses (recommended)
- `full` - Complete prompts/responses
- `debug` - Everything including tool calls

**Default:** `basic`

### `--trace-dir` TEXT

**Purpose:** Specify directory for trace files

**Usage:**
```bash
ollmcp -q "delegate query" --trace-dir ./logs/traces
```

**Default:** `.trace`

**Behavior:**
- Creates directory if it doesn't exist
- Trace files are named with timestamps
- Saves configuration for future runs

---

## Use Cases

### 1. Automated Documentation Generation

```bash
#!/bin/bash
# Generate API documentation from code
ollmcp -q "delegate Read all API files in src/api/ and generate comprehensive documentation in docs/API.md" -Q
```

### 2. Log Analysis

```bash
# Analyze today's logs and create summary
ollmcp -q "delegate Read /var/log/app.log and summarize errors, warnings, and patterns" > daily_summary.txt
```

### 3. Code Review Automation

```bash
# Review changes in git diff
DIFF=$(git diff HEAD~1..HEAD)
ollmcp -q "Review this code change and identify potential issues: $DIFF" -Q > review.txt
```

### 4. CI/CD Integration

```yaml
# GitHub Actions example
- name: Analyze test failures
  if: failure()
  run: |
    ollmcp -q "delegate Read test_results.xml and explain the main failure patterns" -Q > failure_analysis.txt

- name: Upload analysis
  uses: actions/upload-artifact@v2
  with:
    name: failure-analysis
    path: failure_analysis.txt
```

### 5. Data Processing Pipelines

```bash
# Extract insights from CSV data
ollmcp -q "delegate Read data.csv and identify the top 5 trends, save to insights.md" -Q
```

### 6. Scheduled Tasks (Cron)

```bash
# Daily cron job to summarize project status
0 9 * * * /usr/local/bin/ollmcp -q "delegate Scan project files and create daily status report in status_$(date +\%Y\%m\%d).md" >> /var/log/status_gen.log 2>&1
```

---

## Implementation Details

### File Modified

**`mcp_client_for_ollama/client.py`:**

1. **Added command-line arguments** (lines 1876-1885):
   ```python
   query: Optional[str] = typer.Option(
       None, "--query", "-q",
       help="Execute a single query non-interactively and exit (useful for scripts)",
       rich_help_panel="General Options"
   ),
   quiet: bool = typer.Option(
       False, "--quiet", "-Q",
       help="Minimal output mode (use with --query for scripting)",
       rich_help_panel="General Options"
   )
   ```

2. **Added `quiet_mode` attribute** to MCPClient class (line 113):
   ```python
   self.quiet_mode = False
   ```

3. **Updated `async_main()`** to handle query mode (lines 1970-1982):
   ```python
   if query:
       # Set quiet mode on client for minimal output
       client.quiet_mode = quiet

       # Execute single query and exit
       if not quiet:
           console.print(f"[cyan]Executing query: {query}[/cyan]\n")

       await client.handle_user_input(query)

       if not quiet:
           console.print("\n[green]Query completed successfully.[/green]")
   else:
       # Interactive mode - enter chat loop
       await client.chat_loop()
   ```

4. **Added `handle_user_input()` method** (lines 833-916):
   - Processes single queries without interactive loop
   - Handles delegation commands
   - Respects quiet mode for output
   - Sends errors to stderr in quiet mode

---

## Output Behavior

### Normal Mode (`-q` without `-Q`)

- Rich formatting with colors and panels
- Status messages ("Executing query...", "Query completed")
- Tool execution displays
- Error messages with formatting

### Quiet Mode (`-q` with `-Q`)

- Plain text response only
- No status messages
- No rich formatting
- Errors to stderr
- Suitable for piping and parsing

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Success - query completed without errors |
| 1    | Error - query failed or exception occurred |

**Example:**
```bash
ollmcp -q "What is 2+2?" -Q
echo $?  # Prints 0 on success
```

---

## Compatibility

### Works With:
- ✅ All query types (normal, delegation, etc.)
- ✅ All MCP server tools
- ✅ All Ollama models
- ✅ Tool execution
- ✅ File operations (when using delegation)
- ✅ All configuration settings

### Does Not Support:
- ❌ Interactive commands (help, tools, model, etc.)
- ❌ Multi-turn conversations (single query only)
- ❌ Keyboard shortcuts
- ❌ Menu-based configuration

---

## Error Handling

### Error Types and Output

**In Normal Mode:**
```
Error: Model Error: The model llama3.2:3b does not support tools.

To use tools, switch to a model that supports them.
```

**In Quiet Mode:**
```
Error: Model Error: The model llama3.2:3b does not support tools.
```
(Sent to stderr, exit code 1)

---

## Configuration

Non-interactive mode respects all configuration settings:

- Model selection (via `--model` flag or config)
- Enabled tools
- MCP server connections
- Context retention settings
- Thinking mode settings
- Delegation settings

**Example with model override:**
```bash
ollmcp -q "What is AI?" --model llama3.2:3b -Q
```

---

## Best Practices

### 1. Use Quiet Mode for Scripts
```bash
# Good - easy to parse
RESULT=$(ollmcp -q "query" -Q)

# Less ideal - includes formatting
RESULT=$(ollmcp -q "query")
```

### 2. Check Exit Codes
```bash
if ollmcp -q "query" -Q > output.txt; then
    echo "Success"
else
    echo "Failed"
fi
```

### 3. Capture Errors Separately
```bash
ollmcp -q "query" -Q > output.txt 2> errors.txt
```

### 4. Quote Queries with Special Characters
```bash
# Good
ollmcp -q "What's the time?"

# Bad (shell interprets apostrophe)
ollmcp -q What's the time?
```

### 5. Use Delegation for File Operations
```bash
# Delegation can read/write files
ollmcp -q "delegate Read file.txt and summarize" -Q

# Regular queries cannot write files
ollmcp -q "Summarize this text" -Q  # Cannot write output
```

---

## Performance Considerations

### Startup Time

Non-interactive mode has the same startup time as interactive mode:
- MCP server initialization: ~1-3 seconds
- Model loading: depends on Ollama
- First query: ~2-10 seconds

### Optimization Tips

1. **Use --quiet to reduce overhead:**
   ```bash
   ollmcp -q "query" -Q  # Faster, less output processing
   ```

2. **Keep MCP servers running:**
   Configure MCP servers to stay loaded for faster subsequent queries

3. **Use simpler models for quick tasks:**
   ```bash
   ollmcp -q "simple query" --model qwen2.5:7b -Q
   ```

---

## Troubleshooting

### Query Too Short Error
```
Error: Query must be at least 5 characters long.
```
**Solution:** Make sure your query is at least 5 characters.

### Ollama Not Running
```
Error: Ollama is not running!
```
**Solution:** Start Ollama with `ollama serve` before running queries.

### Model Not Found
```
Error: Model not found: llama3.2:3b
```
**Solution:** Pull the model first: `ollama pull llama3.2:3b`

### Permission Denied (Scripting)
```
bash: ollmcp: command not found
```
**Solution:** Use full path or ensure `ollmcp` is in PATH:
```bash
python -m mcp_client_for_ollama -q "query" -Q
```

---

## Future Enhancements

Potential improvements for non-interactive mode:

1. **JSON output mode** - Structured output for easier parsing
2. **Batch query mode** - Process multiple queries from file
3. **Streaming output** - Real-time output for long-running queries
4. **Timeout option** - Maximum execution time
5. **Retry logic** - Automatic retry on transient failures

---

## Summary

The non-interactive query mode enables:
- ✅ Script automation
- ✅ CI/CD integration
- ✅ Scheduled tasks
- ✅ Data processing pipelines
- ✅ Log analysis automation
- ✅ Batch processing workflows

**Simple usage:**
```bash
# Interactive mode (default)
ollmcp

# Non-interactive mode
ollmcp -q "your query"

# Quiet mode for scripting
ollmcp -q "your query" -Q
```

---

**Implemented By:** Claude Sonnet 4.5
**Implementation Date:** December 8, 2025
**Status:** Ready for Use
