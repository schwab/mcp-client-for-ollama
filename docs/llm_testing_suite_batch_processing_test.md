# Adding Batch File Processing Test to os_llm_testing_suite

**Date**: 2026-01-26
**Issue**: granite4:3b selected for SHELL_EXECUTOR tasks but completely fails with empty responses
**Trace**: `/home/mcstar/Nextcloud/VTCLLC/Daily/.trace/trace_20260126_154100.json`

## Problem Description

### What Happened
granite4:3b was selected by the model intelligence system for a SHELL_EXECUTOR task that required:
1. Listing unprocessed PDF files in a directory
2. Processing each file using MCP tools (`pdf_extract.process_document`)
3. Saving results to a database

**Result**: Complete failure - 21 consecutive empty responses before hitting loop limit.

### Why This Matters
This exposes a critical gap in the test suite: **batch file processing with stateful operations** (checking database, processing only unprocessed files). The current tests don't capture this workflow, so models can score well overall but fail catastrophically on real-world tasks.

## Test Suite Gap Analysis

### Current os_llm_testing_suite Coverage

**What IS tested:**
- Basic tool selection (Tier 1)
- Multi-step planning (Tier 2)
- Complex workflows (Tier 3)
- Tool calling with parameters
- Error handling

**What is NOT tested:**
- Batch file processing loops
- Stateful operations (database checks)
- Python code generation for iteration
- MCP tool integration in loops

### granite4:3b Performance Profile

From test suite data:
```json
{
  "model": "granite4:3b",
  "overall_score": 84.0,
  "tier_scores": {"1": 92.3, "2": 84.4, "3": 72.9},
  "dimension_scores": {
    "tool_selection": 91.7,
    "parameters": 75.0,
    "planning": 83.3,
    "context": 91.7,
    "error_handling": 100.0,
    "reasoning": 50.0
  }
}
```

**Why it was selected**: High tool_selection (91.7) and decent parameters (75.0)

**Why it failed**: Despite good test scores, granite4:3b cannot:
- Generate complex Python code
- Maintain state across loop iterations
- Properly format tool call responses
- Handle multi-file batch operations

## Proposed New Test Category

### Test Category: "Batch Processing with Stateful Operations" (Tier 3)

**Test ID**: `batch_file_processing_001`

**Description**: Test model's ability to:
1. Generate Python code to list files matching criteria
2. Check stateful condition (file processed status in database/file system)
3. Loop through unprocessed items
4. Call MCP tools for each item
5. Aggregate results and report summary

**Test Scenario**:
```
Scenario: Process unprocessed documents in directory
Given: A directory with 10 PDF files
And: 5 files are already processed (tracked in a state file)
When: User requests "process unprocessed PDFs in /test/dir"
Then:
  1. Model should generate Python code to list all PDFs
  2. Model should check processed status (read state file)
  3. Model should identify 5 unprocessed files
  4. Model should call process_document tool for each unprocessed file
  5. Model should update state tracking
  6. Model should return summary: "Processed 5 files, skipped 5 already processed"
```

**Success Criteria**:
- ✅ Generates syntactically correct Python code
- ✅ Correctly reads and interprets state file
- ✅ Processes only unprocessed files (no duplicates)
- ✅ Calls tool with correct parameters for each file
- ✅ Provides clear summary of actions taken
- ✅ Does not enter infinite loop or generate empty responses

**Difficulty**: Tier 3 (Complex Workflow)

**Weight Distribution**:
- Parameters: 35% (must provide correct file paths to each tool call)
- Planning: 30% (must sequence: list → check state → filter → process loop)
- Tool Selection: 20% (must choose correct builtin and MCP tools)
- Context: 10% (maintain file list across loop)
- Error Handling: 5% (handle missing state file gracefully)

## Implementation in os_llm_testing_suite

### Test Structure

**File**: `tests/tier3/test_batch_processing.py`

```python
"""
Batch File Processing Tests - Tier 3
Tests model's ability to handle stateful batch operations
"""

import json
import os
from pathlib import Path


class TestBatchFileProcessing:
    """Test batch file processing with stateful tracking"""

    def setup_test_environment(self):
        """Create test directory with files and state"""
        test_dir = Path("/tmp/llm_test_batch")
        test_dir.mkdir(exist_ok=True)

        # Create 10 test PDF files
        for i in range(10):
            (test_dir / f"document_{i}.pdf").write_text(f"Test PDF {i}")

        # Create state file marking 5 as processed
        state = {
            "processed_files": [
                str(test_dir / f"document_{i}.pdf") for i in range(5)
            ]
        }
        (test_dir / "processed.json").write_text(json.dumps(state, indent=2))

        return test_dir

    def test_batch_processing_basic(self, llm_client):
        """Test: Process unprocessed files in directory"""
        test_dir = self.setup_test_environment()

        prompt = f"""
        Process all unprocessed PDF files in {test_dir}.
        The file {test_dir}/processed.json contains a list of already processed files.
        For each unprocessed file:
        1. Extract text content
        2. Save to output.txt
        3. Update processed.json

        Tools available:
        - builtin.list_files(directory) - List files
        - builtin.read_file(path) - Read file content
        - builtin.write_file(path, content) - Write file
        """

        response = llm_client.chat(prompt)

        # Evaluation criteria
        scores = {
            "tool_selection": 0,
            "parameters": 0,
            "planning": 0,
            "context": 0,
            "error_handling": 0
        }

        # Check tool selection
        if "builtin.list_files" in response:
            scores["tool_selection"] += 40
        if "builtin.read_file" in response:
            scores["tool_selection"] += 30
        if "builtin.write_file" in response:
            scores["tool_selection"] += 30

        # Check parameters
        correct_dir_param = f'"{test_dir}"' in response or f"'{test_dir}'" in response
        if correct_dir_param:
            scores["parameters"] += 50

        reads_state = "processed.json" in response
        if reads_state:
            scores["parameters"] += 50

        # Check planning (correct sequence)
        list_before_process = response.index("list_files") < response.index("read_file") if "list_files" in response and "read_file" in response else False
        if list_before_process:
            scores["planning"] += 50

        has_loop = "for " in response.lower() or "while " in response.lower()
        if has_loop:
            scores["planning"] += 50

        # Check context (maintains file list)
        if "unprocessed" in response.lower():
            scores["context"] += 100

        # Check error handling
        if "exist" in response.lower() or "try" in response.lower():
            scores["error_handling"] += 100

        return scores
```

### Mock Tools for Testing

```python
class MockMCPTools:
    """Mock MCP tools for testing without real services"""

    def __init__(self):
        self.processed_files = []

    def list_files(self, directory):
        """Return list of files in directory"""
        return [f"document_{i}.pdf" for i in range(10)]

    def read_file(self, path):
        """Read file content"""
        if "processed.json" in path:
            return json.dumps({
                "processed_files": [f"document_{i}.pdf" for i in range(5)]
            })
        return f"Content of {path}"

    def write_file(self, path, content):
        """Write to file"""
        if path.endswith("output.txt"):
            self.processed_files.append(content)
        return f"Written to {path}"
```

### Expected Results by Model Category

**Large Models (30B+)**:
- Score: 90-100%
- Expected: Correctly generates Python, loops through 5 unprocessed files, maintains state

**Medium Models (7-14B)**:
- Score: 70-85%
- Expected: Generates code with some issues, may need guidance on state management

**Small Models (1-3B)**:
- Score: 30-50% (FAIL)
- Expected: May generate empty responses, incorrect loops, or malformed tool calls
- **granite4:3b would FAIL this test**, exposing the gap in current test coverage

## Integration with Model Intelligence

### Agent Requirements Update

**SHELL_EXECUTOR requirements**:
```python
"SHELL_EXECUTOR": {
    "min_score": 80.0,  # Raise from 75
    "min_tier": 2,
    "critical_dimensions": ["parameters", "tool_selection", "planning"],
    "important_dimensions": ["error_handling", "context"],
    "required_tests": ["batch_file_processing_001"]  # NEW
}
```

### Fallback Strategy

When batch processing tests are added:
1. Models like granite4:3b will score low on this test
2. Their overall score will decrease
3. Model selector will prefer qwen2.5:32b or similar for SHELL_EXECUTOR
4. granite4:3b relegated to simpler tasks (READER, basic EXECUTOR)

## Implementation Timeline

### Phase 1: Test Creation (1-2 days)
- Create `tests/tier3/test_batch_processing.py`
- Add mock tools and test fixtures
- Implement scoring logic

### Phase 2: Run Tests on All Models (1 day)
- Run batch processing tests on all 32 models
- Update test suite results JSON files
- Identify failures

### Phase 3: Update Model Intelligence (1 day)
- Add SHELL_EXECUTOR requirements
- Update agent-model mappings
- Test model selection with new data

### Phase 4: Validation (1 day)
- Re-run original failing scenario
- Verify better model is selected
- Confirm task completes successfully

## Expected Impact

**Before (with current test suite)**:
- granite4:3b selected for SHELL_EXECUTOR
- 21 empty responses → complete failure
- User experience: frustrating, task fails

**After (with batch processing test)**:
- qwen2.5:32b or qwen3:30b-a3b selected
- 1-2 tool calls → task completes
- User experience: smooth, task succeeds

**Model Rankings Change**:
```
Current SHELL_EXECUTOR rankings:
1. granite4:3b (84.0 overall, 91.7 tool_selection)
2. qwen2.5:32b (88.4 overall)

After batch processing test:
1. qwen2.5:32b (88.4 overall, 95% batch_processing)
2. qwen3:30b-a3b (90.6 overall, 92% batch_processing)
...
10. granite4:3b (84.0 overall, 30% batch_processing) ← Dropped
```

## Additional Test Scenarios

### Test 2: Database State Checking
```
Scenario: Process only new records
Given: Database with 100 records, 20 need processing
When: "Process unprocessed database records"
Then: Generate SQL query, filter unprocessed, batch process
```

### Test 3: Error Recovery in Batch
```
Scenario: Continue processing after failure
Given: 10 files, file 3 is corrupted
When: "Process all files, skip failures"
Then: Process 1-2, skip 3, continue 4-10, report summary
```

### Test 4: Parallel Batch Processing
```
Scenario: Process multiple files concurrently
Given: 20 large files
When: "Process files in parallel (max 5 concurrent)"
Then: Generate async/threading code, respect concurrency limit
```

## Summary

Adding batch file processing tests to os_llm_testing_suite will:
1. ✅ Expose granite4:3b's inability to handle complex Python generation
2. ✅ Better align test scores with real-world performance
3. ✅ Improve model selection accuracy for SHELL_EXECUTOR tasks
4. ✅ Reduce user frustration from empty responses and task failures
5. ✅ Provide data-driven evidence for model selection decisions

**Recommended Action**: Implement batch processing tests (Tier 3) in next os_llm_testing_suite update.
