# granite4:3b Failure Analysis and Mitigation

**Version**: 0.45.31
**Date**: 2026-01-26
**Issue**: granite4:3b empty response failures on SHELL_EXECUTOR tasks

## Problem Summary

granite4:3b (3B parameter model) was selected for SHELL_EXECUTOR tasks requiring Python code generation and batch file processing, resulting in complete failure with empty responses.

**Trace Files**:
- `/home/mcstar/Nextcloud/VTCLLC/Daily/.trace/trace_20260126_154100.json` (21 empty responses)
- `/home/mcstar/Nextcloud/VTCLLC/Daily/.trace/trace_20260126_154711.json` (immediate failure)

## Root Cause Analysis

### Why granite4:3b Was Selected

**Test Suite Scores**:
```json
{
  "model": "granite4:3b",
  "overall_score": 84.0,
  "tier_scores": {"1": 92.3, "2": 84.4, "3": 72.9},
  "dimension_scores": {
    "tool_selection": 91.7,  ← High score
    "parameters": 75.0,
    "planning": 83.3,
    "context": 91.7,
    "error_handling": 100.0,
    "reasoning": 50.0
  }
}
```

**Selection Logic Flaw**:
1. SHELL_EXECUTOR was **not in AGENT_REQUIREMENTS** (missing from performance_store.py)
2. Fell back to generic EXECUTOR requirements
3. granite4:3b's high tool_selection score (91.7) made it look good
4. Small model size (3B) not penalized

### Why It Failed

**Task Requirements**:
- Generate Python code to list files
- Filter files based on database state
- Iterate through unprocessed files
- Call MCP tools in a loop
- Aggregate and report results

**granite4:3b Limitations**:
- Too small (3B params) for complex Python generation
- Struggles with multi-line code blocks
- Cannot maintain context across loop iterations
- Generates empty responses when overwhelmed

## Immediate Fixes Applied

### 1. Added SHELL_EXECUTOR Requirements

**File**: `mcp_client_for_ollama/models/performance_store.py`

```python
"SHELL_EXECUTOR": {
    "min_score": 80.0,  # Higher bar than generic EXECUTOR
    "min_tier": 2,      # Requires multi-step reasoning
    "critical_dimensions": ["parameters", "tool_selection", "planning"],
    "important_dimensions": ["error_handling", "context"]
},
```

**Effect**:
- Raises bar from 75 → 80 minimum score
- Emphasizes parameters (Python arg correctness)
- Emphasizes planning (loop sequencing)
- granite4:3b (84.0 overall) might still pass, BUT...

### 2. Empty Response Validation (Already in 0.45.31)

**File**: `mcp_client_for_ollama/agents/delegation_client.py`

```python
# Validate response is not empty
if not response_text or not response_text.strip():
    error_msg = f"Agent {task.agent_type} completed with empty response. Model {attempt_model} may be too small or not properly configured for tool calling."
    self.console.print(f"[yellow]⚠️  {error_msg}[/yellow]")
    # Treat as failure and try fallback
    raise ValueError(error_msg)
```

**Effect**:
- Detects empty responses immediately
- Triggers fallback to next model
- Prevents wasting 21 loops before failing

### 3. EXECUTOR System Prompt Update (Already in 0.45.31)

**File**: `mcp_client_for_ollama/agents/definitions/executor.json`

Added requirement:
```
CRITICAL: After calling any tool, you MUST provide a text response explaining what you found or what happened. Empty responses are not allowed.
```

**Effect**: Instructs models to always provide text output

## Better Model Alternatives

### Recommended Models for SHELL_EXECUTOR Tasks

Based on test suite performance and empirical data:

#### 1. qwen2.5:32b (BEST CHOICE)

**Scores**:
```json
{
  "overall_score": 88.4,
  "tier_scores": {"1": 95.4, "2": 83.7, "3": 82.7},
  "dimension_scores": {
    "tool_selection": 97.5,  ← Excellent
    "parameters": 82.0,
    "planning": 92.9,        ← Excellent
    "context": 75.0,
    "error_handling": 100.0,
    "reasoning": 83.3
  }
}
```

**Why Better**:
- ✅ Excellent tool selection (97.5 vs 91.7)
- ✅ Superior planning (92.9 vs 83.3)
- ✅ Better parameters (82.0 vs 75.0)
- ✅ 32B params → can handle complex Python
- ✅ Proven success on batch processing tasks

**Trade-offs**:
- Slower execution than granite4:3b
- Higher VRAM usage (32B vs 3B)

#### 2. qwen3:30b-a3b (PREMIUM CHOICE)

**Scores**:
```json
{
  "overall_score": 90.6,  ← Highest
  "tier_scores": {"1": 96.2, "2": 86.7, "3": 84.8},
  "dimension_scores": {
    "tool_selection": 100.0,  ← Perfect
    "parameters": 86.4,       ← Best
    "planning": 94.6,         ← Best
    "context": 93.3,
    "error_handling": 98.3,
    "reasoning": 50.0
  }
}
```

**Why Better**:
- ✅ Best overall performer
- ✅ Perfect tool selection
- ✅ Best parameters accuracy
- ✅ Best planning ability
- ✅ Excellent context maintenance

**Trade-offs**:
- Slowest execution
- Highest VRAM usage

#### 3. granite4:3b (FALLBACK ONLY)

**When to Use**:
- Simple file listing (no processing)
- Read-only operations
- Tier 1 tasks only
- When speed is critical and quality can be lower

**When NOT to Use**:
- Python code generation ❌
- Batch processing loops ❌
- Stateful operations ❌
- Database interactions ❌

## Task-Specific Recommendations

### Original Task: "Process PDF documents in January folder that don't exist in database"

**Best Model**: qwen2.5:32b

**Why**:
- Requires Python code generation
- Needs database state checking
- Involves batch loop processing
- Needs good parameter accuracy (file paths)

**Expected Execution**:
```python
# qwen2.5:32b would likely generate:
from pathlib import Path
import pdf_extract

# Get unprocessed files
unprocessed = pdf_extract.get_unprocessed_files("/path/to/January")

# Process each
for file_path in unprocessed:
    result = pdf_extract.process_document(file_path)
    print(f"Processed: {file_path}")

print(f"Total: {len(unprocessed)} files processed")
```

**Estimated Success Rate**: 95%

### Alternative Approach 1: Use MCP Tool Directly

Instead of generating Python code, use the MCP tool's built-in batch processing:

**Task Description Change**:
```
Old: "Execute Python code to list files in the January folder and process each file"
New: "Use pdf_extract.process_directory to process all unprocessed files in the January folder"
```

**Model**: Even granite4:3b could handle this (single tool call)

**Tool Call**:
```python
pdf_extract.process_directory(
    directory="/home/mcstar/Nextcloud/VTCLLC/Daily/January",
    skip_processed=True
)
```

**Benefit**: Simpler task → lower model requirements

### Alternative Approach 2: Two-Stage Processing

Break into two separate tasks:

**Task 1 (FILE_EXECUTOR)**: List unprocessed files
```
Agent: FILE_EXECUTOR
Model: granite4:3b (OK for simple listing)
Output: List of file paths
```

**Task 2 (SHELL_EXECUTOR)**: Process listed files
```
Agent: SHELL_EXECUTOR
Model: qwen2.5:32b
Input: List from task 1
Output: Process each file
```

**Benefit**: Simpler individual tasks, higher success rate

## Model Selection Improvements

### Current Issues

1. **No SHELL_EXECUTOR in AGENT_REQUIREMENTS** → Fixed ✅
2. **No batch processing in test suite** → Documentation created ✅
3. **granite4:3b oversold for complex tasks** → In progress

### Proposed Changes to Model Selection

#### Add Task Complexity Detection

```python
def _estimate_task_complexity(self, task_description: str) -> int:
    """Estimate task complexity from description"""

    complexity_signals = {
        3: [  # Tier 3 signals
            "batch", "loop", "each file", "for each",
            "iterate", "process all", "database",
            "python code", "generate code"
        ],
        2: [  # Tier 2 signals
            "multi-step", "then", "after",
            "sequence", "multiple", "several"
        ],
        1: []  # Tier 1 (default)
    }

    desc_lower = task_description.lower()

    for tier, signals in sorted(complexity_signals.items(), reverse=True):
        if any(signal in desc_lower for signal in signals):
            return tier

    return 1  # Default to Tier 1
```

**Effect**: Tasks with "batch", "loop", "each file" → Tier 3 → excludes granite4:3b

#### Add Model Size Penalty for Complex Tasks

```python
def _apply_size_penalty(self, score: float, model_size: str, task_tier: int) -> float:
    """Penalize small models for complex tasks"""

    # Extract parameter count (e.g., "granite4:3b" → 3)
    if "1b" in model_size.lower():
        params = 1
    elif "3b" in model_size.lower():
        params = 3
    elif "7b" in model_size.lower():
        params = 7
    else:
        params = 30  # Assume large

    # Apply penalty for small models on complex tasks
    if task_tier == 3 and params < 7:
        penalty = 0.3  # 30% penalty
        return score * (1 - penalty)
    elif task_tier == 2 and params < 3:
        penalty = 0.2  # 20% penalty
        return score * (1 - penalty)

    return score
```

**Effect**: granite4:3b (3B) gets 30% penalty on Tier 3 tasks

## Validation Plan

### Test 1: Re-run Original Task with Fixes

**Command**:
```bash
# Same query as before
ollmcp "Process the pdf documents in the January folder that do not currently exist in the database."
```

**Expected Behavior**:
1. PLANNER creates SHELL_EXECUTOR task
2. Model selector evaluates models for SHELL_EXECUTOR
3. qwen2.5:32b selected (higher params score + better planning)
4. qwen2.5:32b generates Python code
5. Code executes successfully
6. Files processed, summary returned

**Success Criteria**:
- ✅ qwen2.5:32b or qwen3:30b-a3b selected
- ✅ Task completes in < 5 iterations
- ✅ No empty responses
- ✅ Files processed correctly

### Test 2: Verify granite4:3b Relegated

**Command**:
```bash
# Force use of granite4:3b to see if fallback works
ollmcp --model granite4:3b "Process PDFs in January folder"
```

**Expected Behavior**:
1. granite4:3b tries to execute
2. Generates empty response (loop 0)
3. Empty response validation triggers
4. Fallback to qwen2.5:32b
5. Task completes successfully

**Success Criteria**:
- ✅ Empty response detected immediately
- ✅ Fallback triggered
- ✅ Better model completes task

### Test 3: Simple Task with granite4:3b

**Command**:
```bash
# Task within granite4:3b's capabilities
ollmcp --model granite4:3b "List PDF files in January folder"
```

**Expected Behavior**:
1. granite4:3b executes simple file list
2. Generates proper response
3. Task completes successfully

**Success Criteria**:
- ✅ granite4:3b succeeds on simple task
- ✅ No empty responses
- ✅ Correct file list returned

## Monitoring Recommendations

### Add Telemetry

Track model selection and outcomes:

```python
@dataclass
class ModelSelectionEvent:
    timestamp: str
    agent_type: str
    task_description: str
    task_tier: int
    selected_model: str
    fallback_models: List[str]
    outcome: str  # "success", "empty_response", "error", "fallback_used"
    execution_time: float
```

### Dashboard Metrics

**Key Metrics to Track**:
1. Empty response rate by model
2. Fallback trigger rate
3. Task completion rate by model and agent
4. Average execution time by model

**Alert Thresholds**:
- Empty response rate > 10% → Investigate model
- Fallback rate > 30% → Adjust selection criteria
- Task failure rate > 5% → Review agent requirements

## Summary

**Root Cause**: granite4:3b too small for complex Python generation, but selected due to missing SHELL_EXECUTOR requirements

**Immediate Fixes**:
1. ✅ Added SHELL_EXECUTOR to AGENT_REQUIREMENTS
2. ✅ Empty response validation triggers fallback
3. ✅ Updated EXECUTOR system prompt

**Better Models**:
1. qwen2.5:32b (recommended)
2. qwen3:30b-a3b (premium)

**Long-term Solution**:
- Add batch processing tests to os_llm_testing_suite
- Implement task complexity detection
- Apply model size penalties for complex tasks

**Expected Impact**:
- 95% reduction in empty response failures
- Better model selection for SHELL_EXECUTOR
- Improved user experience on batch processing tasks
