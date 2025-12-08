# Bug: Planner Doesn't Know About MCP Server Tools

**Severity:** High
**Impact:** Delegation system cannot utilize MCP server capabilities
**Discovered:** December 7, 2025

---

## Problem Summary

When using agent delegation with MCP servers available, the planner **does not know about MCP server tools** and therefore cannot plan tasks that utilize them.

Instead, the planner falls back to suboptimal solutions like asking EXECUTOR to write Python code, which may fail.

---

## Reproduction

### Test Case

**Environment:**
- MCP server running: `osm-mcp-server`
- Available tools: `osm-mcp-server.geocode_address`, `osm-mcp-server.get_route_directions`

**Command:**
```
You: delegate find the distance between San Antonio TX and Enid OK
```

**Expected Behavior:**
Planner should create a plan that uses `osm-mcp-server.geocode_address` to get coordinates, then `osm-mcp-server.get_route_directions` to calculate distance.

**Actual Behavior:**
Planner creates plan asking EXECUTOR to calculate distance using Python geolocation math, ignoring the available MCP tools.

**Trace Evidence:**
```json
{
  "entry_type": "planning_phase",
  "data": {
    "query": "find the distance between San Antonio Tx and Enid OK",
    "plan": {
      "tasks": [{
        "id": "task_1",
        "description": "Use geolocation data to calculate the distance...",
        "agent_type": "EXECUTOR"
      }]
    },
    "available_agents": ["OBSIDIAN", "RESEARCHER", "EXECUTOR", ...],
    // ❌ No mention of osm-mcp-server tools!
  }
}
```

---

## Root Cause Analysis

### Issue 1: Planner Prompt Doesn't Include MCP Tools

**Location:** `delegation_client.py:293-304`

The planner's prompt includes:
- ✅ Available agent types and descriptions
- ✅ Few-shot examples
- ❌ **Missing: Available MCP tools and their descriptions**

**Current Prompt Structure:**
```
{system_prompt}

Available agents:
- READER: Analyzes and reads code files...
- CODER: Writes and modifies code files...
- EXECUTOR: Executes bash commands and Python code...
...

{examples}

Now create a plan for: {query}
```

**What's Missing:**
```
Available MCP Tools:
- osm-mcp-server.geocode_address: Converts addresses to coordinates
- osm-mcp-server.get_route_directions: Gets route and distance between locations
...
```

### Issue 2: Agents Don't Receive Tool Context

Even if the planner knew about MCP tools, individual agents (EXECUTOR, READER, etc.) need to:
1. Know what tools are available
2. Understand which tools to use for their task
3. Have those tools in their tool list when executing

**Current Agent Prompt:**
```
You are a command execution specialist...
Your capabilities:
- Execute bash commands
- Run Python code
// ❌ No mention of available MCP tools!
```

---

## Impact

### High Priority Issues

1. **Underutilization of MCP Servers**
   - Users install MCP servers expecting delegation to use them
   - Delegation ignores them and uses inferior solutions

2. **Poor Task Planning**
   - Planner creates suboptimal plans
   - Tasks fail or produce poor results

3. **Confusion for Users**
   - "Why isn't it using my filesystem server?"
   - "Why is it writing Python when I have a weather API server?"

### Example Failures

**With filesystem MCP server:**
```
Query: "List all Python files in /projects and count their lines"
Expected: Use filesystem.list_directory and filesystem.read_file
Actual: Asks EXECUTOR to run bash `find` and `wc`
```

**With weather API MCP server:**
```
Query: "What's the weather in London?"
Expected: Use weather-api.get_current_weather
Actual: Asks EXECUTOR to write Python code to scrape weather sites (fails)
```

**With database MCP server:**
```
Query: "Find all users created in the last week"
Expected: Use database.query with SQL
Actual: Asks READER to read database dump files (doesn't work)
```

---

## Solution Design

### Approach 1: Add MCP Tools to Planner Prompt (Recommended)

**Pros:**
- Planner can make informed decisions
- Agents still use tools as they do now
- Minimal changes to agent prompts

**Cons:**
- Increases planner prompt size
- May need tool categorization for large tool lists

**Implementation:**
```python
def create_plan(self, query: str) -> Dict[str, Any]:
    # ... existing code ...

    # Get available MCP tools
    available_tools = self._get_available_tool_descriptions()

    # Build tools section
    tools_section = ""
    if available_tools:
        tools_section = "\n\nAvailable MCP Tools:\n"
        for tool in available_tools:
            tools_section += f"- {tool['name']}: {tool['description']}\n"

    planning_prompt = f"""
{planner_config.system_prompt}

Available agents:
{chr(10).join(available_agents)}
{tools_section}
{examples_section}

Now create a plan for: {query}
"""
```

### Approach 2: Tool-Aware Agent Prompts

**Enhance each agent's prompt to include relevant tools:**

```python
def _build_agent_prompt(self, agent_config, task, available_tools):
    # Filter tools relevant to this agent type
    relevant_tools = self._filter_tools_for_agent(agent_config.agent_type, available_tools)

    tools_info = ""
    if relevant_tools:
        tools_info = "\n\nAvailable tools for this task:\n"
        for tool in relevant_tools:
            tools_info += f"- {tool['name']}: {tool['description']}\n"

    prompt = f"""
{agent_config.system_prompt}
{tools_info}

Your task:
{task.description}
"""
    return prompt
```

### Approach 3: Hybrid (Best Solution)

Combine both approaches:

1. **Planner knows about tools** - Can plan tasks that utilize MCP capabilities
2. **Agents get tool context** - Know which tools to use for their specific task
3. **Tool filtering** - Each agent only sees relevant tools

---

## Proposed Solution

### Phase 1: Add MCP Tools to Planner Prompt

**File:** `delegation_client.py`

**Changes:**

1. **Add method to get tool descriptions:**
```python
def _get_available_tool_descriptions(self) -> List[Dict[str, str]]:
    """Get descriptions of all available MCP tools."""
    tool_descriptions = []

    # Get MCP server tools
    if self.mcp_client.tool_manager:
        enabled_tools = self.mcp_client.tool_manager.get_enabled_tool_objects()
        for tool in enabled_tools:
            tool_descriptions.append({
                "name": tool.name,
                "description": tool.description or "No description available"
            })

    return tool_descriptions
```

2. **Update `create_plan()` to include tools:**
```python
async def create_plan(self, query: str) -> Dict[str, Any]:
    # ... existing agent list building ...

    # Get available MCP tools
    available_tools = self._get_available_tool_descriptions()

    # Build tools section (categorize if too many)
    tools_section = ""
    if available_tools:
        tools_section = "\n\nAvailable MCP Tools (agents can use these):\n"

        # Limit to most relevant or categorize
        if len(available_tools) > 20:
            # Group by prefix or category
            tools_by_server = {}
            for tool in available_tools:
                server = tool['name'].split('.')[0] if '.' in tool['name'] else 'other'
                if server not in tools_by_server:
                    tools_by_server[server] = []
                tools_by_server[server].append(tool)

            for server, tools in tools_by_server.items():
                tools_section += f"\n{server} server:\n"
                for tool in tools[:5]:  # Limit per server
                    tools_section += f"  - {tool['name']}: {tool['description']}\n"
                if len(tools) > 5:
                    tools_section += f"  ... and {len(tools)-5} more tools\n"
        else:
            for tool in available_tools:
                tools_section += f"- {tool['name']}: {tool['description']}\n"

    planning_prompt = f"""
{planner_config.system_prompt}

Available agents:
{chr(10).join(available_agents)}
{tools_section}
{examples_section}

When planning tasks, consider:
1. What MCP tools are available that could solve this task directly
2. Which agent type is best suited to use those tools
3. EXECUTOR can use any MCP tool via tool calls
4. Prefer using MCP tools over writing custom Python code when available

Now create a plan for: {query}
"""
```

3. **Update planner examples to show MCP tool usage:**

Add to `planner_examples.json`:
```json
{
  "category": "mcp-tool-usage",
  "query": "Find the distance between two cities",
  "plan": {
    "tasks": [
      {
        "id": "task_1",
        "description": "Use osm-mcp-server.geocode_address to get coordinates for both cities",
        "agent_type": "EXECUTOR",
        "dependencies": [],
        "expected_output": "Coordinates for both locations"
      },
      {
        "id": "task_2",
        "description": "Use osm-mcp-server.get_route_directions to calculate distance",
        "agent_type": "EXECUTOR",
        "dependencies": ["task_1"],
        "expected_output": "Distance in miles/kilometers"
      }
    ]
  }
}
```

### Phase 2: Enhance Agent Prompts (Optional)

Add tool awareness to individual agents:

```python
def _execute_task_with_agent(self, task, agent_config):
    # Get tools available for this agent
    agent_tools = self._get_tools_for_agent(agent_config)

    # Add tools context to agent prompt
    tools_context = ""
    if agent_tools:
        tools_context = f"\n\nYou have access to these tools:\n"
        for tool in agent_tools[:10]:  # Limit to avoid bloat
            tools_context += f"- {tool.name}: {tool.description}\n"
        if len(agent_tools) > 10:
            tools_context += f"... and {len(agent_tools)-10} more tools\n"

    enhanced_prompt = f"""
{agent_config.system_prompt}
{tools_context}

Your task:
{task.description}
"""
```

---

## Secondary Bug: Python Executor Math Module Issue

**Problem:**
The Python code executor is failing with `NameError: name 'math' is not defined` even though the code includes `import math`.

**Trace Evidence:**
```json
{
  "entry_type": "tool_call",
  "data": {
    "tool_name": "builtin.execute_python_code",
    "arguments": {
      "code": "import math\ndef haversine(...)..."
    },
    "result": "Execution failed.\nError: NameError: name 'math' is not defined"
  }
}
```

**Root Cause:**
The Python code execution environment is not properly maintaining imports across statements.

**Solution:**
Check `builtin_tools.py` Python executor implementation and ensure imports are preserved in the execution namespace.

---

## Testing Plan

### Test 1: MCP Tool Awareness

**Setup:**
- Install OSM MCP server
- Enable geocode and route tools

**Test:**
```
You: delegate find distance between New York and Los Angeles
```

**Expected:**
- Planner creates tasks using `osm-mcp-server.*` tools
- EXECUTOR uses those tools instead of Python math

### Test 2: Multiple MCP Servers

**Setup:**
- Filesystem server
- Weather server
- Database server

**Test:**
```
You: delegate list all Python files and check today's weather
```

**Expected:**
- Planner creates tasks for both
- Uses filesystem MCP tools
- Uses weather MCP tools

### Test 3: Tool Preference

**Setup:**
- Both MCP tools and Python available

**Test:**
```
You: delegate calculate distance between two cities
```

**Expected:**
- Prefers MCP tools over Python when available
- Falls back to Python if no relevant MCP tools

---

## Implementation Priority

### P0 (Critical):
1. ✅ Add MCP tools to planner prompt - **COMPLETED**
2. ✅ Add few-shot examples with MCP usage - **COMPLETED**
3. ⏳ Fix Python executor math import issue - **NOT YET ADDRESSED**

### P1 (High):
4. ✅ Add tool filtering/categorization for large tool lists - **COMPLETED**
5. ⏳ Enhance agent prompts with tool context - **DEFERRED** (optional enhancement)

### P2 (Medium):
6. ⏳ Add tool preference hints - **DEFERRED** (included in planner guidance)
7. ⏳ Better error messages when tools fail - **FUTURE WORK**

---

## Implementation Summary

### What Was Implemented (December 7, 2025)

**File:** `mcp_client_for_ollama/agents/delegation_client.py`

#### 1. Added `_get_available_tool_descriptions()` Method (Lines 1024-1042)

```python
def _get_available_tool_descriptions(self) -> List[Dict[str, str]]:
    """
    Get descriptions of all available MCP tools for the planner.

    Returns:
        List of dicts with 'name' and 'description' keys
    """
    tool_descriptions = []

    # Get MCP server tools (not builtin tools - those are agent capabilities)
    if self.mcp_client.tool_manager:
        enabled_tool_objects = self.mcp_client.tool_manager.get_enabled_tool_objects()
        for tool in enabled_tool_objects:
            tool_descriptions.append({
                "name": tool.name,
                "description": tool.description or "No description available"
            })

    return tool_descriptions
```

#### 2. Updated `create_plan()` Method (Lines 293-338)

**Changes:**
- Calls `_get_available_tool_descriptions()` to get MCP tools
- Builds `tools_section` for planner prompt
- Implements tool categorization for large tool lists (>20 tools)
- Groups tools by server prefix to reduce prompt bloat
- Adds tools section between "Available agents" and examples
- Includes planning guidance to prefer MCP tools over Python code

**Key Features:**
- Lists all tools if ≤20 tools available
- Categorizes by server and limits to 5 tools per server if >20 tools
- Shows count of additional tools per server
- Provides explicit guidance on MCP tool usage

#### 3. Added MCP Tool Usage Examples

**File:** `mcp_client_for_ollama/agents/examples/planner_examples.json`

Added 4 new example categories:

1. **mcp-tool-usage-geocoding**: Distance calculation using OSM MCP server
   - Shows geocoding addresses to coordinates
   - Shows route/distance calculation
   - Matches the original bug scenario

2. **mcp-tool-usage-filesystem**: File listing and line counting
   - Shows filesystem.list_directory usage
   - Shows filesystem.read_file for analysis

3. **mcp-tool-usage-web-search**: Web search and summarization
   - Shows brave-search.web_search usage
   - Combines search with analysis

4. **mcp-tool-usage-database**: Database querying
   - Shows database.query usage
   - Combines query with data analysis

---

## Benefits

After fix:
- ✅ Delegation can utilize all MCP server capabilities
- ✅ Better task planning with awareness of available tools
- ✅ Less reliance on fragile Python code generation
- ✅ Users get value from their MCP servers
- ✅ More reliable task execution
- ✅ Automatic tool categorization prevents prompt bloat
- ✅ Few-shot examples teach planner optimal MCP tool usage

---

## Testing Status

### Unit Test Results
✅ `_get_available_tool_descriptions()` method tested and verified
- Correctly retrieves tool objects from tool_manager
- Properly formats tool name and description
- Handles missing descriptions gracefully

### Integration Testing Required
⏳ **Manual testing needed with OSM MCP server** to verify:
- Planner includes MCP tools in prompt
- Planner creates plans that use MCP tools
- Tasks execute successfully with MCP tools
- Tool categorization works with large tool lists

### Suggested Test Command
```bash
# With OSM MCP server configured
You: delegate find the distance between San Antonio TX and Enid OK
```

**Expected Result:**
- Planner creates tasks using `osm-mcp-server.geocode_address` and `osm-mcp-server.get_route_directions`
- EXECUTOR successfully calls these MCP tools
- Distance is calculated without Python code fallback

---

## Known Issues

### Python Executor Math Import Bug (Separate Issue)
**Status:** NOT ADDRESSED in this fix

The Python code executor fails with `NameError: name 'math' is not defined` even when code includes `import math`.

**Location:** Likely in `builtin_tools.py` Python executor implementation

**Impact:** Low priority since fix encourages using MCP tools over Python code

**Next Steps:** Investigate Python execution environment and ensure imports are preserved in namespace

---

## Files Modified

1. ✅ `mcp_client_for_ollama/agents/delegation_client.py`
   - Added `_get_available_tool_descriptions()` method
   - Updated `create_plan()` to include MCP tools in prompt

2. ✅ `mcp_client_for_ollama/agents/examples/planner_examples.json`
   - Added 4 MCP tool usage examples

---

**Status:** Phase 1 Implementation Complete - Ready for Testing
