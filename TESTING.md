# Testing Guide - Artifact System v0.44.0

**Version:** 0.44.0
**Date:** 2026-01-10
**Status:** ✅ All backend tests passing

## Quick Start

Run the test suite:

```bash
python test_artifact_system.py
```

Expected output:
```
============================================================
Artifact System Test Suite
Version: 0.44.0
============================================================
✓ PASS - Import Test
✓ PASS - Artifact Detector
✓ PASS - Context Manager
✓ PASS - Context Message
✓ PASS - Tool Schema Parser
✓ PASS - Builtin Tools

Total: 6/6 tests passed

🎉 All tests passed!
```

## What Was Tested

### 1. Import Test ✅
Verifies all artifact modules can be imported:
- `ArtifactDetector`
- `ToolSchemaParser`
- `ArtifactContextManager`
- `ArtifactContext`
- `ArtifactExecution`
- `ArtifactType`
- `ArtifactData`

### 2. Artifact Detector ✅
Tests artifact detection from LLM output:
- Parses code fence format: ` ```artifact:type ... ``` `
- Validates artifact structure
- Extracts artifact data

**Test Case:**
```python
llm_output = """
```artifact:spreadsheet
{
  "type": "artifact:spreadsheet",
  "version": "1.0",
  "title": "Test Data",
  "data": { ... }
}
```
"""

artifacts = detector.detect(llm_output)
# Expected: 1 artifact detected
```

### 3. Context Manager ✅
Tests execution recording and reference resolution:
- Records tool executions
- Creates execution summaries
- Resolves temporal references ("what I just loaded")

**Test Case:**
```python
# Record execution
execution = manager.record_execution(
    session_id="test",
    tool_name="builtin.read_file",
    tool_args={"path": "README.md"},
    tool_result="# Test Project..."
)

# Resolve reference
referenced = manager.resolve_references("test", "what I just loaded")
# Expected: Returns the execution just recorded
```

### 4. Context Message Building ✅
Tests LLM context message generation:
- Builds system messages with artifact context
- Includes recent executions
- Formats results for LLM consumption

**Test Case:**
```python
msg = manager.build_context_message(
    session_id="test",
    user_query="what files are there?",
    include_recent=1
)
# Expected: System message with execution details
```

### 5. Tool Schema Parser ✅
Tests widget inference from property names:
- Infers file_picker for "path", "file", "file_path"
- Infers code_editor for "code", "script"
- Infers textarea for "description", "message"

**Test Case:**
```python
widget = parser._infer_widget_from_name("file_path")
# Expected: UIWidget.FILE_PICKER
```

### 6. Builtin Tools ✅
Tests that artifact generation tools are registered:
- `_handle_generate_tool_form`
- `_handle_generate_query_builder`
- `_handle_generate_tool_wizard`
- `_handle_generate_batch_tool`

## Manual Testing

### Test Artifact Detection

```python
from mcp_client_for_ollama.artifacts import ArtifactDetector

detector = ArtifactDetector()

# Test with spreadsheet artifact
test_output = """
```artifact:spreadsheet
{
  "type": "artifact:spreadsheet",
  "version": "1.0",
  "title": "My Data",
  "data": {
    "columns": [
      {"id": "name", "label": "Name", "type": "string"},
      {"id": "age", "label": "Age", "type": "number"}
    ],
    "rows": [
      {"name": "Alice", "age": 30},
      {"name": "Bob", "age": 25}
    ]
  }
}
```
"""

artifacts = detector.detect(test_output)
for artifact in artifacts:
    print(f"Type: {artifact['type']}")
    print(f"Title: {artifact['title']}")
    print(f"Columns: {len(artifact['data']['columns'])}")
    print(f"Rows: {len(artifact['data']['rows'])}")
```

### Test Context Tracking

```python
from mcp_client_for_ollama.artifacts import ArtifactContextManager

manager = ArtifactContextManager()

# Simulate user reading a file
execution1 = manager.record_execution(
    session_id="user_123",
    artifact_type="toolform",
    artifact_title="Read File",
    tool_name="builtin.read_file",
    tool_args={"path": "src/main.py"},
    tool_result="def main():\n    print('Hello')\n"
)

print(f"Execution ID: {execution1.execution_id}")
print(f"Summary: {execution1.result_summary}")

# Simulate user listing files
execution2 = manager.record_execution(
    session_id="user_123",
    artifact_type="toolform",
    artifact_title="List Files",
    tool_name="builtin.list_files",
    tool_args={"path": "src"},
    tool_result="src/main.py\nsrc/utils.py\nsrc/__init__.py"
)

# Test references
print("\n--- Testing References ---")

# Temporal reference
refs = manager.resolve_references("user_123", "what I just loaded")
print(f"'what I just loaded' → {refs[0].tool_name if refs else 'None'}")

# Content reference
refs = manager.resolve_references("user_123", "the main.py file")
print(f"'the main.py file' → {refs[0].tool_name if refs else 'None'}")

# Tool reference
refs = manager.resolve_references("user_123", "what I listed")
print(f"'what I listed' → {refs[0].tool_name if refs else 'None'}")

# Build context message
context_msg = manager.build_context_message(
    session_id="user_123",
    user_query="summarize the code I loaded"
)

print("\n--- Context Message ---")
print(context_msg['content'][:500] + "...")
```

### Test Widget Inference

```python
from mcp_client_for_ollama.artifacts import ToolSchemaParser

parser = ToolSchemaParser()

# Test various property names
test_names = [
    "file_path",
    "code",
    "description",
    "email",
    "is_enabled",
    "tags",
]

print("Widget Inference Test:")
for name in test_names:
    widget = parser._infer_widget_from_name(name)
    print(f"  {name:20} → {widget.value if widget else 'default'}")
```

Expected output:
```
Widget Inference Test:
  file_path            → file_picker
  code                 → code_editor
  description          → textarea
  email                → email
  is_enabled           → (default - will use schema type)
  tags                 → (default - will use schema type)
```

## Integration Testing

### Test with Delegation Client (When Integrated)

```python
# This will work once context manager is integrated into delegation client

from mcp_client_for_ollama.client import DelegationClient

client = DelegationClient()

# User generates a form
response1 = client.generate_response(
    "Create a form to read README.md",
    session_id="test_session"
)
# Should contain artifact:toolform

# User submits the form (simulated)
result = client.execute_artifact_tool(
    session_id="test_session",
    artifact_type="toolform",
    artifact_title="Read File",
    tool_name="builtin.read_file",
    tool_args={"path": "README.md"}
)
# Should record execution in context

# User asks follow-up
response2 = client.generate_response(
    "What did I just load?",
    session_id="test_session"
)
# Should reference README.md from context
```

## Performance Testing

### Large Result Handling

```python
from mcp_client_for_ollama.artifacts import ArtifactContextManager

manager = ArtifactContextManager()

# Create a large result (>10KB)
large_result = "x" * 20000

execution = manager.record_execution(
    session_id="test",
    artifact_type="toolform",
    artifact_title="Large File",
    tool_name="builtin.read_file",
    tool_args={"path": "large.txt"},
    tool_result=large_result
)

# Build context message
msg = manager.build_context_message("test")

# Check that result was truncated
assert "truncated" in msg['content'].lower()
print("✓ Large result truncated correctly")
```

### Many Executions

```python
from mcp_client_for_ollama.artifacts import ArtifactContextManager

manager = ArtifactContextManager()

# Record 100 executions
for i in range(100):
    manager.record_execution(
        session_id="test",
        artifact_type="toolform",
        artifact_title=f"Execution {i}",
        tool_name="builtin.read_file",
        tool_args={"path": f"file{i}.txt"},
        tool_result=f"Content {i}"
    )

# Context should keep only last 50
context = manager.get_or_create_context("test")
assert len(context.executions) == 50
print(f"✓ Context pruned to {len(context.executions)} executions")
```

## Known Issues

None at this time. All backend tests passing.

## Future Testing Needs

### Frontend Tests (Pending Implementation)
- [ ] Artifact renderer component tests
- [ ] Form submission tests
- [ ] Result display tests
- [ ] Execution timeline tests

### Integration Tests (Pending)
- [ ] End-to-end artifact submission flow
- [ ] Context injection into LLM prompts
- [ ] Multi-step wizard workflows
- [ ] Batch processing

### E2E Tests (Pending)
- [ ] Complete user workflow from form to response
- [ ] Multiple artifact interactions in one session
- [ ] Reference resolution in real conversations

## Test Coverage Goals

- **Backend:** 90%+ (Currently: ~85% estimated)
- **Frontend:** 85%+ (Not yet implemented)
- **Integration:** 80%+ (Pending)
- **E2E:** 70%+ (Pending)

## Continuous Testing

Run tests before commits:

```bash
# Run test suite
python test_artifact_system.py

# Run with verbose output
python test_artifact_system.py -v

# Run specific test
python -c "from test_artifact_system import test_artifact_detector; test_artifact_detector()"
```

---

**Test Status:** ✅ All backend tests passing (6/6)
**Version:** 0.44.0
**Last Updated:** 2026-01-10
