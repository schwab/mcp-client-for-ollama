#!/usr/bin/env python3
"""
Test script for collapsible output and trace logging features.
"""

from rich.console import Console
from mcp_client_for_ollama.utils.collapsible_output import CollapsibleOutput, TaskOutputCollector
from mcp_client_for_ollama.utils.trace_logger import TraceLogger, TraceLoggerFactory, TraceLevel


def test_collapsible_output():
    """Test the collapsible output functionality."""
    print("=" * 60)
    print("Testing Collapsible Output")
    print("=" * 60)

    console = Console()
    collapsible = CollapsibleOutput(
        console=console,
        line_threshold=5,
        char_threshold=100,
        auto_collapse=True
    )

    # Test 1: Short output (should not collapse)
    print("\n1. Short output (should display fully):")
    short_output = "This is a short response.\nIt has only 3 lines.\nNo collapsing needed."
    collapsible.print_collapsible(
        content=short_output,
        title="Task 1 Result",
        style="green"
    )

    # Test 2: Long output (should collapse)
    print("\n2. Long output (should collapse):")
    long_output = "\n".join([f"Line {i}: This is a longer response with many lines" for i in range(20)])
    collapsible.print_with_preview(
        content=long_output,
        title="Task 2 Result",
        preview_lines=3,
        style="cyan"
    )

    # Test 3: Very long single line (should collapse by char count)
    print("\n3. Long single line (should collapse by character count):")
    long_line = "x" * 2000
    collapsible.print_collapsible(
        content=long_line,
        title="Task 3 Result",
        style="yellow"
    )

    # Test 4: Task output collector
    print("\n4. Task output collector:")
    task_output = TaskOutputCollector(console, collapsible)
    task_output.print_task_result(
        task_id="task_4",
        agent_type="READER",
        description="Read and analyze a large configuration file",
        result="\n".join([f"Config line {i}: value_{i}" for i in range(30)]),
        status="completed"
    )

    print("\n✅ Collapsible output tests completed!\n")


def test_trace_logging():
    """Test the trace logging functionality."""
    print("=" * 60)
    print("Testing Trace Logging")
    print("=" * 60)

    console = Console()

    # Test different trace levels
    for level in [TraceLevel.OFF, TraceLevel.SUMMARY, TraceLevel.BASIC, TraceLevel.FULL]:
        print(f"\n--- Testing TraceLevel.{level.name} ---")

        logger = TraceLogger(
            level=level,
            log_dir=".trace_test",
            console_output=False
        )

        if level == TraceLevel.OFF:
            assert not logger.is_enabled()
            print(f"✓ {level.name}: Tracing disabled")
            continue

        assert logger.is_enabled()

        # Log some events
        logger.log_task_start(
            task_id="test_task_1",
            agent_type="READER",
            description="Test task description",
            dependencies=[]
        )

        logger.log_llm_call(
            task_id="test_task_1",
            agent_type="READER",
            prompt="Test prompt for reading a file",
            response="Test response with file contents",
            model="qwen2.5:7b",
            temperature=0.5,
            loop_iteration=0,
            tools_used=["builtin.read_file"]
        )

        if level in [TraceLevel.FULL, TraceLevel.DEBUG]:
            logger.log_tool_call(
                task_id="test_task_1",
                agent_type="READER",
                tool_name="builtin.read_file",
                arguments={"path": "/test/file.txt"},
                result="File contents here...",
                success=True
            )

        logger.log_task_end(
            task_id="test_task_1",
            agent_type="READER",
            status="completed",
            result="Task completed successfully",
            duration_ms=1234.56
        )

        # Get summary
        summary = logger.get_summary()
        print(f"✓ {level.name}: Logged {summary['total_entries']} entries")
        print(f"  - LLM calls: {summary['llm_calls']}")
        print(f"  - Tool calls: {summary['tool_calls']}")
        print(f"  - Log file: {summary['log_file']}")

    print("\n✅ Trace logging tests completed!\n")


def test_factory_config():
    """Test the trace logger factory with config."""
    print("=" * 60)
    print("Testing TraceLoggerFactory")
    print("=" * 60)

    # Test 1: Disabled config
    config1 = {"trace_enabled": False}
    logger1 = TraceLoggerFactory.from_config(config1)
    assert not logger1.is_enabled()
    print("✓ Config 1: Tracing correctly disabled")

    # Test 2: Basic config
    config2 = {
        "trace_enabled": True,
        "trace_level": "basic",
        "trace_dir": ".trace_test"
    }
    logger2 = TraceLoggerFactory.from_config(config2)
    assert logger2.is_enabled()
    assert logger2.level == TraceLevel.BASIC
    print("✓ Config 2: BASIC level configured correctly")

    # Test 3: Full config
    config3 = {
        "trace_enabled": True,
        "trace_level": "full",
        "trace_dir": ".trace_test",
        "trace_console": True,
        "trace_truncate": 1000
    }
    logger3 = TraceLoggerFactory.from_config(config3)
    assert logger3.is_enabled()
    assert logger3.level == TraceLevel.FULL
    assert logger3.truncate_length == 1000
    print("✓ Config 3: FULL level with custom truncate configured correctly")

    print("\n✅ Factory configuration tests completed!\n")


def test_trace_summary():
    """Test the trace summary output."""
    print("=" * 60)
    print("Testing Trace Summary Output")
    print("=" * 60)

    console = Console()
    logger = TraceLogger(
        level=TraceLevel.FULL,
        log_dir=".trace_test"
    )

    # Simulate a delegation session
    logger.log_planning_phase(
        query="Test query",
        plan={"tasks": [{"id": "task_1", "description": "Test task"}]},
        available_agents=["READER", "CODER"],
        examples_used=["code-modification"]
    )

    for i in range(3):
        task_id = f"task_{i+1}"
        logger.log_task_start(task_id, "READER", f"Task {i+1}", [])
        logger.log_llm_call(task_id, "READER", "prompt", "response", "model", 0.5, 0)
        logger.log_task_end(task_id, "READER", "completed", "result", duration_ms=100.0)

    # Print summary
    logger.print_summary(console)

    summary = logger.get_summary()
    assert summary['tasks_completed'] == 3
    assert summary['llm_calls'] == 3
    print("\n✅ Trace summary tests completed!\n")


def main():
    """Run all tests."""
    print("\n🧪 Testing Collapsible Output and Trace Logging Features\n")

    try:
        test_collapsible_output()
        test_trace_logging()
        test_factory_config()
        test_trace_summary()

        print("=" * 60)
        print("🎉 All tests passed successfully!")
        print("=" * 60)

        # Cleanup
        import shutil
        import os
        if os.path.exists(".trace_test"):
            shutil.rmtree(".trace_test")
            print("\n🧹 Cleaned up test trace directory")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
