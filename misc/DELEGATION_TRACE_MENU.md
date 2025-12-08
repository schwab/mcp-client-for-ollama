# Delegation Trace Configuration Menu

**Version:** 0.23.0+
**Command:** `delegation-trace` or `dt`

---

## Overview

The delegation trace configuration menu provides an interactive way to enable and configure trace logging for the agent delegation system directly from the ollmcp CLI.

This eliminates the need to manually edit JSON configuration files - you can configure trace logging through a simple question-and-answer interface.

---

## Quick Start

### 1. Start ollmcp
```bash
ollmcp
```

### 2. Type the command
```
You: delegation-trace
```
or
```
You: dt
```

### 3. Follow the prompts

The menu will guide you through:
1. Enabling delegation
2. Enabling trace logging
3. Selecting trace level
4. Configuring trace directory
5. Saving configuration

---

## Menu Walkthrough

### Step 1: View Current Settings

The menu first shows your current delegation trace settings:

```
╭─ Current Delegation Trace Settings ─╮
│ Delegation Enabled    False          │
│ Trace Enabled         False          │
│ Trace Level           basic          │
│ Trace Directory       .trace         │
│ Trace to Console      False          │
╰────────────────────────────────────╯
```

### Step 2: Enable Delegation

```
Enable delegation? (required for trace logging)
Enable delegation? (yes/no, default: yes):
```

**Options:**
- `yes` or `y` - Enable delegation (required for trace logging)
- `no` or `n` - Disable delegation (trace logging will not be available)

### Step 3: Enable Trace Logging

```
Enable trace logging?
Enable trace logging? (yes/no, default: yes):
```

**Options:**
- `yes` or `y` - Enable trace logging
- `no` or `n` - Disable trace logging (you can still use delegation without tracing)

### Step 4: Select Trace Level

```
Select Trace Level:
  1 - OFF (no tracing)
  2 - SUMMARY (task start/end only)
  3 - BASIC (truncated prompts/responses) [recommended]
  4 - FULL (complete prompts/responses)
  5 - DEBUG (everything including tool calls)

Select trace level (1-5, default: 3):
```

**Trace Level Comparison:**

| Level | What Gets Logged | Overhead | File Size | Best For |
|-------|-----------------|----------|-----------|----------|
| 1 - OFF | Nothing | 0% | 0 KB | Production |
| 2 - SUMMARY | Task start/end only | <1% | ~10 KB | Monitoring |
| 3 - BASIC | Prompts/responses (truncated) | ~2% | ~50 KB | **Development** ✅ |
| 4 - FULL | Complete prompts/responses | ~5% | ~500 KB | Deep debugging |
| 5 - DEBUG | Everything + tool calls | ~10% | ~2 MB | Tool issues |

**Recommendation:** Use level 3 (BASIC) for most development work.

### Step 5: Configure Trace Directory

```
Trace directory (default: .trace):
```

**Options:**
- Press Enter to use default (`.trace`)
- Enter custom path (e.g., `.delegation-logs`, `logs/trace`, etc.)

### Step 6: Console Output (DEBUG only)

If you selected DEBUG level, you'll be asked:

```
Also print traces to console? (yes/no, default: no):
```

**Options:**
- `yes` or `y` - Print trace entries to console in real-time
- `no` or `n` - Only write to file

**Note:** Console output is only useful for DEBUG level and can be noisy.

### Step 7: Review New Settings

The menu shows your new configuration:

```
╭─ New Delegation Trace Settings ─╮
│ Delegation Enabled    True       │
│ Trace Enabled         True       │
│ Trace Level           full       │
│ Trace Directory       .trace     │
│ Trace to Console      False      │
╰───────────────────────────────────╯
```

### Step 8: Save Configuration

```
Save configuration? (yes/no, default: yes):
```

**Options:**
- `yes` or `y` - Save the configuration
- `no` or `n` - Discard changes

If you choose to save:

```
Config name (default: default):
```

**Options:**
- Press Enter to save to default config
- Enter a custom name (e.g., `debug`, `production`, `testing`)

### Step 9: Important Reminders

After saving, you'll see important reminders:

```
╭─ Reminder ─╮
│ ⚠️  Important Reminder:                    │
│                                            │
│ Don't forget to add the trace directory   │
│ to your .gitignore:                       │
│                                            │
│ echo '.trace/' >> .gitignore              │
│                                            │
│ Trace files can contain sensitive         │
│ information and should not be committed.  │
╰────────────────────────────────────────────╯

╭─ Usage ─╮
│ ✅ Trace logging configured!              │
│                                            │
│ To use trace logging:                     │
│   1. Use delegation: delegate <query>     │
│      or d <query>                         │
│   2. Check trace summary at end           │
│   3. Analyze trace file:                  │
│      cat .trace/trace_*.json | jq .      │
│                                            │
│ See TRACE_LOGGING_QUICK_REFERENCE.md      │
│ for analysis commands                     │
╰────────────────────────────────────────────╯
```

---

## Example Session

### Complete Example

```
You: dt

╭─ Current Delegation Trace Settings ─╮
│ Delegation Enabled    False          │
│ Trace Enabled         False          │
│ Trace Level           basic          │
│ Trace Directory       .trace         │
│ Trace to Console      False          │
╰────────────────────────────────────╯

Enable delegation? (required for trace logging)
Enable delegation? (yes/no, default: yes): yes

Enable trace logging?
Enable trace logging? (yes/no, default: yes): yes

Select Trace Level:
  1 - OFF (no tracing)
  2 - SUMMARY (task start/end only)
  3 - BASIC (truncated prompts/responses) [recommended]
  4 - FULL (complete prompts/responses)
  5 - DEBUG (everything including tool calls)

Select trace level (1-5, default: 3): 4

Trace directory (default: .trace):

╭─ New Delegation Trace Settings ─╮
│ Delegation Enabled    True       │
│ Trace Enabled         True       │
│ Trace Level           full       │
│ Trace Directory       .trace     │
│ Trace to Console      False      │
╰───────────────────────────────────╯

Save configuration? (yes/no, default: yes): yes

Config name (default: default):

╭─ Config Saved ─╮
│ Configuration saved successfully to:      │
│ ~/.config/mcp-client-for-ollama/config.json │
╰────────────────────────────────────────────╯

[Reminders displayed...]

You: delegate Fix the authentication bug
[Delegation executes with trace logging enabled...]
```

---

## After Configuration

### Using Trace Logging

Once configured, use delegation normally:

```
You: delegate Fix the authentication bug and verify tests pass
```

or

```
You: d Update the API to use async/await
```

### Checking Trace Output

At the end of delegation, you'll see a trace summary:

```
🔍 Trace Session Summary
Session ID: 20251207_153045
Log file: .trace/trace_20251207_153045.json

Total trace entries: 45
LLM calls: 12
Tool calls: 8
Tasks completed: 3
Tasks failed: 0
```

### Analyzing Traces

```bash
# View the full trace
cat .trace/trace_20251207_153045.json | jq .

# See what the planner decided
grep '"entry_type": "planning_phase"' .trace/trace_*.json | jq .

# See what DEBUGGER agent did
grep '"agent_type": "DEBUGGER"' .trace/trace_*.json | jq .
```

---

## Configuration File

The menu updates your configuration file at:
```
~/.config/mcp-client-for-ollama/config.json
```

### Example Generated Config

```json
{
  "model": "qwen2.5:7b",
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

---

## Changing Settings

### To Reconfigure

Simply run the command again:

```
You: dt
```

The menu will show your current settings and allow you to change them.

### To Disable Trace Logging

Run the command and answer `no` to "Enable trace logging?"

```
You: dt
Enable delegation? (yes/no, default: yes): yes
Enable trace logging? (yes/no, default: yes): no
```

### To Change Trace Level

Run the command and select a different level:

```
You: dt
...
Select trace level (1-5, default: 3): 5
```

---

## Common Configurations

### Development Mode

```
Delegation Enabled: yes
Trace Enabled: yes
Trace Level: 3 (BASIC)
Trace Directory: .trace
```

**Use for:** Normal development and debugging

### Deep Debugging Mode

```
Delegation Enabled: yes
Trace Enabled: yes
Trace Level: 4 (FULL)
Trace Directory: .trace
```

**Use for:** Debugging planner decisions and agent behavior

### Tool Debugging Mode

```
Delegation Enabled: yes
Trace Enabled: yes
Trace Level: 5 (DEBUG)
Trace Directory: .trace
Trace to Console: no
```

**Use for:** Debugging tool execution issues

### Production Mode

```
Delegation Enabled: yes
Trace Enabled: no
```

**Use for:** Production use without debugging overhead

---

## Additional Features

### Automatic Settings

The menu automatically configures:

1. **Collapsible Output** - Automatically enabled when trace logging is enabled
   - `auto_collapse`: true
   - `line_threshold`: 20 lines
   - `char_threshold`: 1000 characters

2. **Truncate Length** - Set to 500 characters for BASIC level

### Config Validation

The configuration manager validates all settings:
- Ensures trace levels are valid (off/summary/basic/full/debug)
- Validates numeric thresholds
- Handles missing or invalid values gracefully

---

## Troubleshooting

### Menu Doesn't Appear

**Check:**
- You typed the command correctly: `delegation-trace` or `dt`
- You're running ollmcp version 0.23.0 or later

### Configuration Not Saved

**Check:**
- You answered "yes" to "Save configuration?"
- Write permissions on `~/.config/mcp-client-for-ollama/`
- Disk space available

### Trace Logging Not Working

**Check:**
- Delegation is enabled (`delegation.enabled: true`)
- Trace logging is enabled (`delegation.trace_enabled: true`)
- You're using the `delegate` or `d` command (not regular queries)
- Write permissions on trace directory

---

## Commands Reference

| Command | Aliases | Description |
|---------|---------|-------------|
| `delegation-trace` | `dt`, `trace-config`, `tc` | Open delegation trace configuration menu |
| `delegate <query>` | `d <query>` | Use delegation with configured trace settings |
| `save-config` | `sc` | Save current configuration manually |
| `load-config` | `lc` | Load a saved configuration |

---

## See Also

- **Complete Guide:** `HOW_TO_USE_TRACE_LOGGING.md`
- **Quick Reference:** `TRACE_LOGGING_QUICK_REFERENCE.md`
- **Feature Documentation:** `COLLAPSIBLE_OUTPUT_AND_TRACE_LOGGING.md`
- **Example Config:** `config.example.json`

---

## Summary

The delegation trace menu makes it easy to:

✅ Enable delegation and trace logging
✅ Select appropriate trace level
✅ Configure trace directory
✅ Save configuration
✅ Get usage instructions

**No manual JSON editing required!**
