#!/usr/bin/env python3
"""Test script for artifact system components."""

import sys
from datetime import datetime


def test_imports():
    """Test that all artifact modules can be imported."""
    print("Testing imports...")

    try:
        from mcp_client_for_ollama.artifacts import (
            ArtifactDetector,
            ToolSchemaParser,
            ArtifactType,
            ArtifactData,
            ArtifactContextManager,
            ArtifactContext,
            ArtifactExecution,
        )
        print("✓ All artifact modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_artifact_detector():
    """Test artifact detector functionality."""
    print("\nTesting ArtifactDetector...")

    from mcp_client_for_ollama.artifacts import ArtifactDetector

    detector = ArtifactDetector()

    # Test detection
    llm_output = """
Here's a test artifact:

```artifact:spreadsheet
{
  "type": "artifact:spreadsheet",
  "version": "1.0",
  "title": "Test Data",
  "data": {
    "columns": [{"id": "name", "label": "Name", "type": "string"}],
    "rows": [{"name": "Test"}]
  }
}
```
"""

    artifacts = detector.detect(llm_output)

    if len(artifacts) == 1:
        print(f"✓ Detected 1 artifact")
        artifact = artifacts[0]
        print(f"  Type: {artifact['type']}")
        print(f"  Title: {artifact['title']}")
        return True
    else:
        print(f"✗ Expected 1 artifact, got {len(artifacts)}")
        return False


def test_context_manager():
    """Test artifact context manager functionality."""
    print("\nTesting ArtifactContextManager...")

    from mcp_client_for_ollama.artifacts import ArtifactContextManager

    manager = ArtifactContextManager()

    # Record an execution
    execution = manager.record_execution(
        session_id="test_session",
        artifact_type="toolform",
        artifact_title="Read File",
        tool_name="builtin.read_file",
        tool_args={"path": "README.md"},
        tool_result="# Test Project\n\nThis is a test."
    )

    print(f"✓ Recorded execution: {execution.execution_id}")
    print(f"  Summary: {execution.result_summary}")

    # Test reference resolution
    referenced = manager.resolve_references(
        "test_session",
        "what I just loaded"
    )

    if len(referenced) == 1:
        print(f"✓ Resolved temporal reference")
        return True
    else:
        print(f"✗ Failed to resolve reference")
        return False


def test_context_message():
    """Test context message building."""
    print("\nTesting context message building...")

    from mcp_client_for_ollama.artifacts import ArtifactContextManager

    manager = ArtifactContextManager()

    # Record execution
    manager.record_execution(
        session_id="test_session",
        artifact_type="toolform",
        artifact_title="List Files",
        tool_name="builtin.list_files",
        tool_args={"path": "src"},
        tool_result="src/main.py\nsrc/utils.py\nsrc/__init__.py"
    )

    # Build context message
    msg = manager.build_context_message(
        session_id="test_session",
        user_query="what files are there?",
        include_recent=1
    )

    if msg and msg['role'] == 'system':
        print(f"✓ Built context message")
        print(f"  Role: {msg['role']}")
        print(f"  Content preview: {msg['content'][:100]}...")
        return True
    else:
        print(f"✗ Failed to build context message")
        return False


def test_tool_schema_parser():
    """Test tool schema parser."""
    print("\nTesting ToolSchemaParser...")

    from mcp_client_for_ollama.artifacts import ToolSchemaParser

    # Create a mock tool manager
    class MockToolManager:
        def get_builtin_tools(self):
            return []

    parser = ToolSchemaParser(tool_manager=MockToolManager())

    # Test widget inference
    widget = parser._infer_widget_from_name("file_path")

    if widget:
        print(f"✓ Widget inference working")
        print(f"  'file_path' → {widget.value}")
        return True
    else:
        print(f"✗ Widget inference failed")
        return False


def test_builtin_tools():
    """Test that new builtin tools are defined."""
    print("\nTesting builtin tools...")

    # Just test that the tool handler methods exist
    from mcp_client_for_ollama.tools.builtin import BuiltinToolManager

    # Check the tool manager has the handler methods
    expected_handlers = [
        "_handle_generate_tool_form",
        "_handle_generate_query_builder",
        "_handle_generate_tool_wizard",
        "_handle_generate_batch_tool",
    ]

    # Create a mock model config
    class MockConfig:
        def __init__(self):
            self.system_prompt = "Test"

        def get_system_prompt(self):
            return self.system_prompt

    try:
        config = MockConfig()
        tool_manager = BuiltinToolManager(config, ollama_host="http://localhost:11434")

        # Check handlers exist
        found = []
        for handler in expected_handlers:
            if hasattr(tool_manager, handler):
                found.append(handler)

        if len(found) == len(expected_handlers):
            print(f"✓ All 4 artifact tool handlers registered")
            for handler in found:
                print(f"  - {handler}")
            return True
        else:
            print(f"✗ Expected 4 handlers, found {len(found)}")
            return False

    except Exception as e:
        print(f"✗ Failed to create tool manager: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Artifact System Test Suite")
    print("Version: 0.44.0")
    print("=" * 60)

    tests = [
        ("Import Test", test_imports),
        ("Artifact Detector", test_artifact_detector),
        ("Context Manager", test_context_manager),
        ("Context Message", test_context_message),
        ("Tool Schema Parser", test_tool_schema_parser),
        ("Builtin Tools", test_builtin_tools),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
