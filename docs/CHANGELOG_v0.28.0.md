# Changelog v0.28.0

## Major Architectural Change: EXECUTOR Partitioning

### Summary
Partitioned the monolithic EXECUTOR agent (212 lines) into 5 specialized executors (avg 45 lines each). This major architectural change improves focus, performance, and maintainability by giving each executor a single, well-defined responsibility.

### Motivation
The original EXECUTOR system prompt had grown to 212 lines - over 2x the recommended maximum of 100 lines. It mixed responsibilities for:
- File operations with complex path validation
- Test execution and reporting
- Configuration management
- Memory and feature tracking
- Shell command and Python code execution

This complexity made it difficult for the model to effectively follow all guidelines, leading to:
- Confusion about which guidelines apply to current task
- Reduced effectiveness due to information overload
- Harder maintenance (changes affect unrelated functionality)
- Difficulty adding new features without bloating further

### Solution: Domain-Specific Executors

Created 5 specialized executors, each expert in its domain:

---

#### 1. **FILE_EXECUTOR** (44 lines)
**Responsibility**: File operations with mandatory path validation

**Tools**:
- builtin.read_file (with offset/limit for partial reading)
- builtin.validate_file_path (REQUIRED first step)
- builtin.list_files / builtin.list_directories
- builtin.file_exists / builtin.get_file_info

**Key Features**:
- Enforces PATH LOCKING PROTOCOL
- Must call validate_file_path before any file operation
- Prevents path hallucination
- Supports partial file reading (offset/limit)
- Delegates writes to CODER

**Example Tasks**:
- "Read config.py lines 50-100"
- "List all PDF files in directory"
- "Check if file exists before processing"

---

#### 2. **TEST_EXECUTOR** (35 lines)
**Responsibility**: Test execution and reporting only

**Tools**:
- builtin.run_pytest (primary tool)
- builtin.add_test_result (for memory tracking)
- builtin.execute_bash_command (test-related only)

**Key Features**:
- ALWAYS uses run_pytest (not manual bash commands)
- Reports results clearly (PASSED/FAILED)
- NEVER modifies test code (delegates to CODER/DEBUGGER)
- Logs test results to memory

**Example Tasks**:
- "Run unit tests in tests/"
- "Execute pytest with verbose output"
- "Report test status for feature F1.3"

---

#### 3. **CONFIG_EXECUTOR** (38 lines)
**Responsibility**: Application configuration management

**Tools**:
- builtin.get_config / builtin.update_config_section
- builtin.get_system_prompt / builtin.set_system_prompt
- builtin.list_mcp_servers / builtin.get_config_path

**Key Features**:
- Workflow: Get → Modify → Update Complete Section → Verify
- MUST provide ALL fields when updating sections
- Manages system prompts and MCP server configs

**Example Tasks**:
- "Enable memory system in config"
- "List configured MCP servers"
- "Update system prompt for assistant"

---

#### 4. **MEMORY_EXECUTOR** (46 lines)
**Responsibility**: Memory state and feature tracking with validation

**Tools**:
- builtin.update_feature_status / builtin.log_progress
- builtin.add_test_result
- builtin.get_memory_state / builtin.get_feature_details / builtin.get_goal_details

**Key Features**:
- CRITICAL validation: Never mark completed if tests failed
- Checks conditional task execution ("if tests pass...")
- Verifies tool calls actually happen (not just described)
- Tracks progress and test results

**Example Tasks**:
- "Mark F1.3 as completed if tests pass"
- "Log progress for feature implementation"
- "Update goal status based on completion"

---

#### 5. **SHELL_EXECUTOR** (54 lines)
**Responsibility**: Shell commands, Python code, and MCP tool integration

**Tools**:
- builtin.execute_bash_command
- builtin.execute_python_code
- All MCP tools (pdf_extract, nextcloud-api, osm-mcp-server, brave-search, etc.)

**Key Features**:
- Bash for system operations (mv, cp, mkdir -p)
- Python for data filtering/sorting
- MCP tools for external integrations
- "Never give up" - investigate and solve
- Can move files but not edit code (use CODER)

**Example Tasks**:
- "Move files to archive/ directory"
- "Filter files modified today using Python"
- "Search web for documentation"
- "Process PDF with pdf_extract tool"

---

### PLANNER Updates

Enhanced agent assignment rules (guideline #8) with:

**Decision Tree for Task Assignment**:
1. File operation? → **FILE_EXECUTOR**
2. Test execution? → **TEST_EXECUTOR**
3. Config changes? → **CONFIG_EXECUTOR**
4. Memory tracking? → **MEMORY_EXECUTOR**
5. Bash/Python/MCP? → **SHELL_EXECUTOR**
6. Code writing? → **CODER**
7. Code analysis? → **READER**

**Benefits**:
- Clear routing logic
- Each executor is domain expert
- Better performance with focused prompts
- Easier to add new specialized executors

---

### Comparison

**Before (v0.27.1)**:
- 1 monolithic EXECUTOR: 212 lines
- Mixed responsibilities
- Information overload for model
- Difficult to maintain

**After (v0.28.0)**:
- 5 specialized executors: avg 45 lines each
- Single responsibility per executor
- Focused, effective prompts
- Easy to maintain and extend

**Prompt Size Reduction**:
```
Original EXECUTOR:     212 lines
FILE_EXECUTOR:          44 lines (79% reduction)
TEST_EXECUTOR:          35 lines (84% reduction)
CONFIG_EXECUTOR:        38 lines (82% reduction)
MEMORY_EXECUTOR:        46 lines (78% reduction)
SHELL_EXECUTOR:         54 lines (75% reduction)
```

---

### Migration Notes

**Backward Compatibility**:
- Original EXECUTOR agent still exists
- PLANNER updated to prefer specialized executors
- Old configurations continue to work
- Gradual migration path available

**For Users**:
- No action required
- PLANNER automatically routes to specialized executors
- Improved performance and accuracy
- More predictable behavior

**For Developers**:
- Agent definitions in mcp_client_for_ollama/agents/definitions/
- 5 new files: file_executor.json, test_executor.json, config_executor.json, memory_executor.json, shell_executor.json
- PLANNER updated with routing logic
- Can deprecate old EXECUTOR in future version

---

### Future Enhancements

This partition strategy enables:
1. **Easy Addition**: New specialized executors for specific domains
2. **Per-Executor Tuning**: Different models/temperatures per executor
3. **Targeted Improvements**: Update one executor without affecting others
4. **Better Testing**: Test each executor's domain independently
5. **Performance Optimization**: Smaller prompts = faster, cheaper execution

---

### Files Created/Modified

**New Agent Definitions**:
- mcp_client_for_ollama/agents/definitions/file_executor.json
- mcp_client_for_ollama/agents/definitions/test_executor.json
- mcp_client_for_ollama/agents/definitions/config_executor.json
- mcp_client_for_ollama/agents/definitions/memory_executor.json
- mcp_client_for_ollama/agents/definitions/shell_executor.json

**Modified**:
- mcp_client_for_ollama/agents/definitions/planner.json (updated agent assignment rules)
- pyproject.toml (version 0.28.0)
- mcp_client_for_ollama/__init__.py (version 0.28.0)

**Documentation**:
- docs/feature_suggestions.md (marked as implemented)
- partition_executor_analysis.md (design document)
- CHANGELOG_v0.28.0.md (this file)

---

**Version**: 0.28.0
**Date**: 2025-12-26
**Category**: Major Architecture Change
**Impact**: Agent System, Performance, Maintainability
**Breaking Changes**: None (backward compatible)
