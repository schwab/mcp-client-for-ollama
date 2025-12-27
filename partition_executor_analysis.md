# EXECUTOR Partition Analysis

## Current State
- **System Prompt**: 212 lines (over 2x the recommended 100 lines)
- **Complexity**: Mixes file ops, testing, config, memory, and shell execution
- **Problem**: Too much context for the model to effectively follow all guidelines

## Proposed Partition Strategy

### 1. FILE_EXECUTOR
**Responsibility**: File operations and path handling
**Tools**:
- builtin.read_file
- builtin.validate_file_path
- builtin.list_files
- builtin.file_exists
- builtin.get_file_info
- MCP file tools (nextcloud-api for file ops)

**System Prompt Sections**:
- PATH LOCKING PROTOCOL (required validate_file_path usage)
- File path extraction and validation
- File writing delegation (to CODER)
- Partial file reading with offset/limit

**Size**: ~60 lines

---

### 2. TEST_EXECUTOR
**Responsibility**: Running tests and reporting results
**Tools**:
- builtin.run_pytest
- builtin.add_test_result
- builtin.execute_bash_command (for test-related commands)

**System Prompt Sections**:
- Test execution guidelines (use run_pytest, not bash)
- Test failure handling (report don't fix)
- Test result reporting
- Adding test results to memory

**Size**: ~40 lines

---

### 3. CONFIG_EXECUTOR
**Responsibility**: Configuration management
**Tools**:
- builtin.get_config
- builtin.update_config_section
- builtin.get_system_prompt
- builtin.set_system_prompt
- builtin.list_mcp_servers
- builtin.get_config_path

**System Prompt Sections**:
- Config management workflow (get -> modify -> update -> verify)
- System prompt management
- MCP server configuration

**Size**: ~30 lines

---

### 4. MEMORY_EXECUTOR
**Responsibility**: Memory and feature tracking
**Tools**:
- builtin.update_feature_status
- builtin.log_progress
- builtin.add_test_result
- builtin.get_memory_state
- builtin.get_feature_details
- builtin.get_goal_details

**System Prompt Sections**:
- Conditional task execution (if tests pass, etc.)
- Feature completion validation (never mark completed if tests fail)
- Tool call verification (actually invoke tools)
- Memory status updates

**Size**: ~50 lines

---

### 5. SHELL_EXECUTOR
**Responsibility**: General command and code execution
**Tools**:
- builtin.execute_bash_command
- builtin.execute_python_code
- All MCP tools (nextcloud-api, osm-mcp-server, brave-search, etc.)

**System Prompt Sections**:
- Bash command execution
- Python code execution
- Data filtering with Python
- MCP tool integration
- Never give up guidance
- General task completion workflow

**Size**: ~45 lines

---

## Benefits of Partition

1. **Focused Context**: Each executor has ~30-60 lines instead of 212
2. **Clear Responsibility**: Single purpose per executor
3. **Better Performance**: Model can focus on relevant guidelines
4. **Easier Maintenance**: Update one executor without affecting others
5. **Specialized Expertise**: Each executor is an expert in its domain

## PLANNER Updates Required

Update planning hints to route tasks to specialized executors:
- File operations → FILE_EXECUTOR
- Test execution → TEST_EXECUTOR
- Config changes → CONFIG_EXECUTOR
- Memory updates → MEMORY_EXECUTOR
- Bash/Python/MCP → SHELL_EXECUTOR

## Migration Strategy

1. Create 5 new executor agent definitions
2. Update PLANNER with new agent routing logic
3. Mark old EXECUTOR as deprecated
4. Test with existing traces
5. Remove old EXECUTOR after validation
