# Agent Selection Guide

Complete reference for all available agents and their trigger conditions.

## Table of Contents

- [Specialized Executors](#specialized-executors)
- [Code Agents](#code-agents)
- [Ghost Writer Agents](#ghost-writer-agents)
- [Music & Creative Agents](#music--creative-agents)
- [Special Agents](#special-agents)
- [Quick Reference Decision Tree](#quick-reference-decision-tree)

---

## 🔧 Specialized Executors

These replace the old generic EXECUTOR with focused, domain-specific agents.

### FILE_EXECUTOR 📁

**When to Use:**
- File reading operations
- Directory listing
- File existence checks
- Path validation

**Trigger Words/Phrases:**
- "read file", "read lines"
- "list files", "list directory"
- "check if file exists"
- "validate file path"
- "access file via nextcloud"
- "show contents of"

**What it Does:**
- Reads files (full or partial with offset/limit)
- Lists files and directories
- Checks file existence
- Validates file paths (MANDATORY: builtin.validate_file_path)
- Accesses files via MCP tools (nextcloud-api)
- **Cannot write/modify files** (use CODER for that)

**Example Tasks:**
- "Read config.py lines 50-100"
- "List PDF files in directory"
- "Validate path for processing"

---

### TEST_EXECUTOR 🧪

**When to Use:**
- Running pytest tests
- Reporting test results
- Test execution only

**Trigger Words/Phrases:**
- "run tests", "execute tests"
- "run pytest"
- "test the code"
- "report test results"
- "check if tests pass"

**What it Does:**
- Runs pytest tests (builtin.run_pytest)
- Reports test results (pass/fail)
- Adds test results to memory
- **Never fixes test code** (use CODER or DEBUGGER)

**Example Tasks:**
- "Run unit tests"
- "Execute pytest in tests/"
- "Report test status"

---

### CONFIG_EXECUTOR ⚙️

**When to Use:**
- Configuration queries
- Configuration updates
- System settings management

**Trigger Words/Phrases:**
- "get config", "show config"
- "update config", "change settings"
- "enable/disable delegation"
- "list MCP servers"
- "configure system"

**What it Does:**
- Queries config (builtin.get_config)
- Updates config sections (builtin.update_config_section)
- Manages system prompts
- MCP server configuration

**Example Tasks:**
- "Get memory config"
- "Enable delegation"
- "List MCP servers"

---

### MEMORY_EXECUTOR 💾

**When to Use:**
- Memory and feature tracking
- Progress logging
- Status updates

**Trigger Words/Phrases:**
- "mark feature as complete"
- "update feature status"
- "log progress"
- "add test result"
- "track progress"
- "update goal"

**What it Does:**
- Updates feature status (builtin.update_feature_status)
- Logs progress (builtin.log_progress)
- Adds test results (builtin.add_test_result)
- Validates feature completion (never marks complete if tests failed!)
- Conditional task execution (checks "if" conditions)

**Example Tasks:**
- "Mark F1.3 as completed if tests pass"
- "Log progress for feature"
- "Update goal status"

---

### SHELL_EXECUTOR 🐚

**When to Use:**
- Shell commands
- Python scripts
- MCP tool operations
- Data processing

**Trigger Words/Phrases:**
- "run bash", "execute command"
- "run Python code", "execute Python"
- "move file", "rename", "mkdir"
- "use [MCP tool name]"
- "search web", "process PDF"
- "filter files", "sort data"

**What it Does:**
- Bash commands (builtin.execute_bash_command)
- Python code (builtin.execute_python_code)
- MCP tool operations (pdf_extract, osm-mcp-server, brave-search)
- Data filtering/sorting with Python
- File moves/renames (mv, cp, mkdir -p via bash)

**Example Tasks:**
- "Move files to archive/"
- "Filter files by date using Python"
- "Search web for X"
- "Process PDF with pdf_extract"

---

## 💻 Code Agents

### CODER 👨‍💻

**When to Use:**
- Writing new code
- Modifying existing code
- File creation
- Feature implementation

**Trigger Words/Phrases:**
- "create new file"
- "modify code", "update function"
- "add feature to class"
- "fix bug in code"
- "write code for"
- "implement", "build"

**What it Does:**
- Creates new files (builtin.write_file)
- Modifies existing code (builtin.patch_file)
- Creates directories (builtin.create_directory)
- **Never assign file modifications to executors!**

**Example Tasks:**
- "Create new module"
- "Fix bug in function"
- "Add feature to class"

---

### READER 📖

**When to Use:**
- Code analysis
- Understanding existing code
- Searching for patterns
- Read-only operations

**Trigger Words/Phrases:**
- "analyze code", "understand how"
- "explain this code"
- "search for pattern"
- "find all instances of"
- "how does X work?"

**What it Does:**
- Analyzes code structure
- Reads files for information
- Searches code patterns
- **Cannot modify anything**

**Example Tasks:**
- "Understand how auth works"
- "Find all API endpoints"
- "Analyze imports"

---

### DEBUGGER 🔍

**When to Use:**
- Investigating bugs
- Debugging failures
- Root cause analysis

**Trigger Words/Phrases:**
- "debug", "investigate bug"
- "why is this failing?"
- "find root cause"
- "reproduce error"
- "fix failing test"

**What it Does:**
- Investigates bugs
- Runs tests to reproduce issues
- Proposes fixes (but CODER implements them)

**Example Tasks:**
- "Debug failing test"
- "Investigate error X"
- "Find root cause"

---

### RESEARCHER 🔬

**When to Use:**
- Web research
- Information gathering
- Documentation lookup

**Trigger Words/Phrases:**
- "research", "investigate"
- "find information about"
- "look up", "search for"
- "what is", "how to"

**What it Does:**
- Web searches
- Information gathering
- Documentation research

**Example Tasks:**
- "Research Python async patterns"
- "Find documentation for library X"
- "What is the best practice for Y?"

---

## ✍️ Ghost Writer Agents

Story writing assistance agents that maintain consistency and quality.

### ACCENT_WRITER 🗣️

**When to Use:**
- Character speech pattern consistency
- Dialogue review
- Accent verification

**Trigger Words/Phrases:**
- "review dialogue"
- "check accent consistency"
- "verify character voice"
- "check speech pattern"
- "does this sound like [character]?"

**What it Does:**
- Maintains consistency in how each character speaks
- Tracks accents, dialects, vocabulary, grammar patterns
- Reviews dialogue for consistency with established patterns
- Self-manages memory via goal G_ACCENT_WRITER

**Example Tasks:**
- "Review this dialogue for accent consistency"
- "Check if Elena's speech matches her formal pattern"

---

### LORE_KEEPER 🌍

**When to Use:**
- World-building consistency
- Lore creation/extraction
- Magic system validation
- Geography/history verification

**Trigger Words/Phrases:**
- "create lore", "extract lore", "analyze lore"
- "verify lore", "check world consistency"
- "review world-building"
- "validate magic/geography/history/culture/technology"
- "store world-building details"
- "build lore database", "lore analysis"

**What it Does:**
- Tracks world rules, religious systems, geography, history, culture, technology
- Verifies new writing against established lore
- Flags contradictions, anachronisms, timeline conflicts
- Self-manages memory via goal G_LORE_KEEPER

**Example Tasks:**
- "Check if this religious practice follows established rules"
- "Verify this location matches the geography"
- "Review this scene for lore consistency"
- "Extract lore from these story files"

---

### CHARACTER_KEEPER 👥

**When to Use:**
- Character consistency tracking
- Behavior verification
- Character arc monitoring

**Trigger Words/Phrases:**
- "check character consistency"
- "verify character behavior"
- "is this in-character?"
- "track character development"
- "character knowledge/abilities"
- "character arc"

**What it Does:**
- Tracks character details (appearance, personality, background, relationships, arcs, knowledge, abilities)
- Verifies new scenes against established character profiles
- Flags out-of-character behavior and knowledge inconsistencies
- Monitors character development arcs for coherence
- Self-manages memory via goal G_CHARACTER_KEEPER

**Example Tasks:**
- "Check if this character action matches their personality"
- "Verify character knowledge consistency"
- "Review character development arc"

---

### STYLE_MONITOR ✨

**When to Use:**
- Writing style consistency
- POV/tense verification
- Formatting consistency

**Trigger Words/Phrases:**
- "check style consistency"
- "verify POV", "check tense"
- "dialogue format"
- "formatting consistency"

**What it Does:**
- Monitors writing style, POV, tense, formatting consistency
- Checks for style violations
- Ensures consistent formatting

**Example Tasks:**
- "Check if this chapter maintains third-person POV"
- "Verify tense consistency"
- "Review dialogue formatting"

---

### QUALITY_MONITOR ⭐

**When to Use:**
- Grammar checking
- Writing quality review
- Plot consistency

**Trigger Words/Phrases:**
- "check grammar", "verify clarity"
- "review quality"
- "plot consistency"
- "writing quality"

**What it Does:**
- Checks grammar, clarity, plot quality
- Reviews overall writing quality
- Identifies areas for improvement

**Example Tasks:**
- "Review this chapter for grammar"
- "Check plot consistency"
- "Verify writing quality"

---

### DETAIL_CONTRIVER 🎨

**When to Use:**
- Minor detail generation
- Background element creation
- World flavor

**Trigger Words/Phrases:**
- "generate minor details"
- "create inn name"
- "minor character name"
- "background details"

**What it Does:**
- Generates minor world details (inn names, minor characters, etc.)
- Creates background flavor
- Adds richness to world-building

**Example Tasks:**
- "Generate name for a tavern"
- "Create minor NPC for this scene"
- "Add background details to market scene"

---

## 🎵 Music & Creative Agents

### LYRICIST 🎤

**When to Use:**
- Song lyric writing
- Poetic composition

**Trigger Words/Phrases:**
- "write lyrics"
- "create song"
- "compose lyrics"

**What it Does:**
- Writes song lyrics
- Creates poetic content

**Example Tasks:**
- "Write lyrics for a folk song"
- "Compose a ballad about X"

---

### SUNO_COMPOSER 🎼

**When to Use:**
- Music composition with Suno
- Audio generation

**Trigger Words/Phrases:**
- "compose music with Suno"
- "create song with Suno"
- "generate music"

**What it Does:**
- Music composition using Suno MCP server
- Audio generation

**Example Tasks:**
- "Compose background music"
- "Create theme song"

---

### STYLE_DESIGNER 🎨

**When to Use:**
- Artistic style design
- Visual style creation

**Trigger Words/Phrases:**
- "design style"
- "create artistic style"

**What it Does:**
- Artistic style design
- Visual style definition

**Example Tasks:**
- "Design art style for project"
- "Create visual theme"

---

## 🔄 Special Agents

### AGGREGATOR 📊

**When to Use:**
- Combining multiple results
- Synthesizing findings
- Final answer formatting

**Trigger Words/Phrases:**
- (Used automatically as final step)
- "combine results"
- "summarize all findings"

**What it Does:**
- Combines outputs from multiple agents
- Creates cohesive answers
- Formats results for user

**Example Tasks:**
- (Automatically used to synthesize task results)

---

### INITIALIZER 🏁

**When to Use:**
- (Automatically - never manually assigned)

**Trigger Words/Phrases:**
- (Used automatically only once per memory session)

**What it Does:**
- Bootstraps new memory sessions
- Creates initial goals and features
- Sets up project structure in memory

**Example Tasks:**
- (Automatic session initialization)

---

### PLANNER 📋

**When to Use:**
- (Automatically - never manually assigned)

**Trigger Words/Phrases:**
- (Used automatically for complex tasks)

**What it Does:**
- Breaks down complex tasks into subtasks
- Assigns appropriate agents to each subtask
- Manages task dependencies

**Example Tasks:**
- (Automatic task decomposition)

---

### OBSIDIAN 📝

**When to Use:**
- Obsidian vault operations
- Note management

**Trigger Words/Phrases:**
- "create Obsidian note"
- "update Obsidian vault"
- "Obsidian operations"

**What it Does:**
- Obsidian vault management
- Note creation and updates

**Example Tasks:**
- "Create note in Obsidian"
- "Update daily note"

---

## 🎯 Quick Reference Decision Tree

```
┌─ File operation? ────────────→ FILE_EXECUTOR
├─ Test execution? ───────────→ TEST_EXECUTOR
├─ Config changes? ───────────→ CONFIG_EXECUTOR
├─ Memory tracking? ──────────→ MEMORY_EXECUTOR
├─ Bash/Python/MCP? ──────────→ SHELL_EXECUTOR
├─ Write/modify code? ────────→ CODER
├─ Analyze code? ─────────────→ READER
├─ Debug issues? ─────────────→ DEBUGGER
├─ Research info? ────────────→ RESEARCHER
│
├─ Story Writing:
│  ├─ Dialogue/accent ───────→ ACCENT_WRITER
│  ├─ Lore/world ────────────→ LORE_KEEPER
│  ├─ Characters ────────────→ CHARACTER_KEEPER
│  ├─ Style/format ──────────→ STYLE_MONITOR
│  ├─ Grammar/quality ───────→ QUALITY_MONITOR
│  └─ Minor details ─────────→ DETAIL_CONTRIVER
│
├─ Music/Creative:
│  ├─ Lyrics ────────────────→ LYRICIST
│  ├─ Music composition ─────→ SUNO_COMPOSER
│  └─ Artistic style ────────→ STYLE_DESIGNER
│
└─ Other:
   ├─ Obsidian notes ────────→ OBSIDIAN
   ├─ Combine results ───────→ AGGREGATOR (automatic)
   └─ Complex tasks ─────────→ PLANNER (automatic)
```

---

## 📝 Usage Tips

1. **Be Specific**: Use trigger words that clearly indicate which agent you need
2. **Single Purpose**: Each agent is specialized - use the right tool for the job
3. **Combinations**: Complex tasks may use multiple agents in sequence
4. **Automatic Selection**: PLANNER automatically selects agents based on your request
5. **Ghost Writers**: Designed for creative writing projects - they maintain consistency across your story

---

## 🔗 Related Documentation

- [VSCode Integration Plan](vscode_integration_plan.md)
- [QA Bugs & Fixes](qa_bugs.md)
- [Ghost Writer Progress](ghost_writer_progress.md)

---

**Last Updated**: v0.35.2
