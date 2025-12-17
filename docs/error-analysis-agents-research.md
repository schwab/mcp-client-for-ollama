# Error Analysis and Correction Agents - Research & Recommendations

## Background

Research from 2025 shows emerging patterns in AI agent error detection, analysis, and correction. This document explores how these patterns could enhance our delegation system.

## Research Findings (2025)

### Key Concepts from Industry

**Sources:**
- [AI Agents for Software Error Resolution](https://www.akira.ai/blog/ai-agents-for-debugging)
- [Debugging AI Software Systems in 2025](https://www.codiste.com/ways-of-debugging-ai-software-systems)
- [Error Pattern Detection AI Agents](https://relevanceai.com/agent-templates-tasks/error-pattern-detection)
- [Galileo: Debug AI Agents - 10 Failure Modes + Fixes](https://galileo.ai/blog/debug-ai-agents)
- [Google DeepMind: CodeMender](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/)

### 1. Error Pattern Detection

**Concept**: AI systems identify, analyze, and predict software failures using machine learning to understand normal behavior patterns and detect subtle anomalies.

**Application to our system**:
- Monitor delegation traces for common failure patterns
- Detect when agents repeatedly fail on similar tasks
- Identify systematic issues (like the absolute path bug)

### 2. Self-Correction with Critique

**Concept**: Agents use critique mechanisms to verify their own work and self-correct when issues detected.

**From CodeMender (Google DeepMind)**:
- LLM-based critique tool highlights differences between original and modified code
- Agent self-corrects based on LLM judge's feedback when failures detected
- Well-constructed critiques significantly boost agent performance

**Application to our system**:
- After CODER modifies a file, run self-critique before declaring success
- DEBUGGER could review CODER's changes for common mistakes
- Add verification step: "Did the file actually get written where intended?"

### 3. Categorized Error Taxonomy

**Concept**: Classify errors into precise categories for better handling.

**Common categories**:
- **Tool Misuse**: Incorrect tool usage or parameters
- **PII Leak**: Unintended exposure of sensitive data
- **Ungrounded Summary**: Agent makes claims not supported by data
- **Parameter Extraction Errors**: Incorrect parameter extraction from user input
- **Authentication Failures**: API rate limits or expired credentials
- **Timeout/Latency Issues**: Operations taking too long
- **Reasoning Failures**: Agent logic errors (common in DA-Code benchmark)

**Application to our system**:
- Categorize failures in trace logs
- Route errors to appropriate handlers based on category
- Generate statistics on error patterns

### 4. AgentCompass Framework

**Concept**: Enables debugging of AI agents in under 5 minutes through:
- Automated error clustering
- Cause graphs showing failure relationships
- Workflow-integrated "Fix Recipes"

**Key Features**:
- Analyzes every trace and assigns failures to taxonomy categories
- State-of-the-art performance on TRAIL benchmark
- Significantly outperforms general-purpose LLMs on trace debugging

**Application to our system**:
- Implement trace analysis for common failure patterns
- Create "Fix Recipes" for known issues
- Build cause graphs to understand error relationships

### 5. Common Failure Modes

**From Galileo's research on 10 failure modes**:

1. **Hallucination**: Agent fabricates information
2. **Tool Selection Errors**: Wrong tool chosen for task
3. **Tool Parameter Errors**: Incorrect arguments to tools
4. **Context Loss**: Agent forgets important information
5. **Infinite Loops**: Agent gets stuck repeating actions
6. **Incomplete Tasks**: Agent declares success prematurely
7. **Permission Errors**: Agent can't access required resources
8. **Data Format Errors**: Mishandling of data types/formats
9. **State Management Issues**: Agent loses track of progress
10. **Resource Constraints**: Timeouts, memory limits, etc.

**Examples we've encountered**:
- ✅ **Tool Parameter Errors**: Passing JSON string instead of object (v0.24.12 fix)
- ✅ **Permission Errors**: Absolute path blocking (v0.24.15 fix)
- ✅ **Incomplete Tasks**: CODER saving to wrong location (v0.24.15 fix)

## Current System Analysis

### What We Have

**DEBUGGER Agent** (debugger.json):
- Diagnoses and fixes errors in code
- Can read, execute, and modify code
- Analyzes error messages and stack traces
- Focused on code-level bugs

**Strengths**:
- Good for fixing runtime/compilation errors
- Can execute code to reproduce issues
- Makes focused, minimal changes

**Limitations**:
- Only invoked manually by PLANNER
- No automatic error detection
- No self-critique mechanism
- Doesn't handle agent workflow errors
- No pattern detection across multiple failures

### What We're Missing

1. **Automatic Error Detection**
   - No monitoring of agent failures
   - Errors only visible in trace logs
   - No real-time detection during execution

2. **Self-Critique System**
   - Agents don't verify their own work
   - No post-action validation
   - Success declared prematurely

3. **Error Pattern Analysis**
   - No detection of recurring failures
   - Manual trace analysis required
   - No automated failure clustering

4. **Automatic Retry with Correction**
   - Failed tasks don't automatically retry
   - No learning from previous failures
   - Manual intervention required

## Recommendations

### Phase 1: Enhanced Validation (Quick Win)

**Add post-action verification to critical agents:**

```json
// CODER agent enhancement
"After modifying a file, verify the changes:
1. Read the file back to confirm content
2. Check file exists at expected location
3. For absolute paths, confirm user's target location
4. Report actual location file was saved to"
```

**Benefits**:
- Catches "file written to wrong location" bugs
- Simple to implement (prompt enhancement)
- No new infrastructure needed

### Phase 2: Self-Critique Agent

**Create CRITIC agent that reviews other agents' work:**

```json
{
  "agent_type": "CRITIC",
  "description": "Reviews and validates other agents' work",
  "capabilities": [
    "Compare intended vs actual results",
    "Detect common failure patterns",
    "Suggest corrections",
    "Verify file operations succeeded"
  ]
}
```

**Workflow**:
```
CODER modifies file
  → CRITIC reviews changes
    → If issues found: DEBUGGER fixes
    → If OK: Declare success
```

**Benefits**:
- Catches errors before user sees them
- Improves overall reliability
- Enables self-correction

### Phase 3: Error Pattern Detection

**Implement trace analysis system:**

1. **Automatic Failure Classification**
   - Categorize errors using taxonomy
   - Track failure frequency by category
   - Identify systematic issues

2. **Pattern Detection**
   - Detect recurring failure signatures
   - Cluster similar errors
   - Generate "Fix Recipes" for common issues

3. **Proactive Fixes**
   - Automatically invoke DEBUGGER for known patterns
   - Apply Fix Recipes without user intervention
   - Learn from successful corrections

**Implementation**:
- Extend TraceLogger with error classification
- Add failure pattern analyzer
- Create Fix Recipe database

### Phase 4: Intelligent Retry System

**Automatic retry with correction:**

```python
async def execute_task_with_retry(task):
    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        try:
            result = await execute_task(task)

            # Validate result
            if await critic.validate(result):
                return result

            # Validation failed, analyze error
            error_pattern = await analyzer.classify_failure(result)

            # Try to fix
            if fix_recipe := get_fix_recipe(error_pattern):
                task = await apply_fix_recipe(task, fix_recipe)
                attempts += 1
                continue

            # No known fix, invoke DEBUGGER
            fixed_task = await debugger_agent.fix(task, result)
            attempts += 1

        except Exception as e:
            error_pattern = await analyzer.classify_exception(e)
            # ... handle exception with retry
```

**Benefits**:
- Reduces user intervention
- Learns from failures
- Improves over time

## Examples of Error-Correction Integration

### Example 1: File Write Verification

**Current behavior**:
```
User: "Edit /path/to/file.md"
CODER: "I've edited the file"
[Actually saved to ./file.md]
```

**With critique**:
```
User: "Edit /path/to/file.md"
CODER: Attempts edit
CRITIC: "File saved to ./file.md but user wanted /path/to/file.md"
DEBUGGER: Copies file to correct location
Success: "File edited and saved to /path/to/file.md"
```

### Example 2: Tool Parameter Error

**Current behavior**:
```
Agent: builtin.update_config_section(section="memory", data="{\"enabled\": true}")
Error: Data is string, not object
[User sees error]
```

**With error detection**:
```
Agent: builtin.update_config_section(section="memory", data="{\"enabled\": true}")
Pattern Detector: "JSON string instead of object" - Common error #47
Auto-Fix: Parse string to object, retry
Success: Config updated
```

### Example 3: Permission Error Recovery

**Current behavior**:
```
Agent: Write to /absolute/path
Error: Absolute paths not allowed
[Task fails]
```

**With intelligent retry**:
```
Agent: Write to /absolute/path
Error: Absolute paths not allowed
Error Analyzer: "Permission issue - needs user approval"
Auto-Action: Request permission from user
User: Approves
Retry: Write to /absolute/path
Success: File written
```

## Priority Recommendations

### Immediate (v0.25.x):
1. ✅ **Fix absolute path permission system** (Done in v0.24.15)
2. **Add post-action verification to CODER**
   - Verify file write location matches intent
   - Read back written content to confirm
3. **Enhance error messages in builtin tools**
   - Include suggestions for common mistakes
   - Show correct parameter format when validation fails

### Short-term (v0.26.x):
1. **Create CRITIC agent**
   - Review CODER output
   - Validate file operations
   - Detect common mistakes
2. **Add error classification to trace logs**
   - Categorize failures automatically
   - Track error patterns
3. **Implement basic Fix Recipes**
   - JSON string → object parsing
   - Path resolution for common errors
   - Parameter format corrections

### Long-term (v0.27.x+):
1. **Full error pattern detection system**
   - Analyze traces for patterns
   - Cluster similar failures
   - Generate Fix Recipes automatically
2. **Intelligent retry system**
   - Auto-retry with corrections
   - Learning from failures
   - Proactive error prevention
3. **Self-debugging agents**
   - Agents monitor their own execution
   - Self-correct in real-time
   - Request help when stuck

## Conclusion

Error analysis and correction agents represent a significant opportunity to improve our delegation system's reliability. The research shows clear patterns and proven techniques we can adopt incrementally.

**Key takeaway**: Start with simple validation and self-critique, then build toward automated error detection and correction. Each phase adds value while laying groundwork for the next.

**Next steps**:
1. Review this document with the team
2. Prioritize quick wins (Phase 1)
3. Plan CRITIC agent design (Phase 2)
4. Begin trace analysis prototyping (Phase 3)
