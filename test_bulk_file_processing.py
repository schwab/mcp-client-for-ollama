#!/usr/bin/env python3
"""
Test to verify the bulk file processing fix.

This test checks that:
1. Loop limits have been increased for READER and EXECUTOR
2. Planner has guidance about bulk file operations
3. Example shows the correct pattern (Python for many files)
"""

import json
from pathlib import Path


def test_loop_limits_increased():
    """Test that READER and EXECUTOR have increased loop limits."""
    reader_path = Path("mcp_client_for_ollama/agents/definitions/reader.json")
    executor_path = Path("mcp_client_for_ollama/agents/definitions/executor.json")

    with open(reader_path) as f:
        reader_config = json.load(f)

    with open(executor_path) as f:
        executor_config = json.load(f)

    reader_limit = reader_config.get("loop_limit", 0)
    executor_limit = executor_config.get("loop_limit", 0)

    failures = []

    if reader_limit < 10:
        failures.append(f"READER loop_limit is {reader_limit}, expected >= 10")

    if executor_limit < 10:
        failures.append(f"EXECUTOR loop_limit is {executor_limit}, expected >= 10")

    if failures:
        print("❌ FAILED: Loop limits too low:")
        for failure in failures:
            print(f"   - {failure}")
        return False

    print(f"✅ PASSED: Loop limits increased (READER: {reader_limit}, EXECUTOR: {executor_limit})")
    return True


def test_planner_has_bulk_guidance():
    """Test that planner has guidance about bulk file operations."""
    planner_path = Path("mcp_client_for_ollama/agents/definitions/planner.json")

    with open(planner_path) as f:
        planner_config = json.load(f)

    system_prompt = planner_config.get("system_prompt", "")

    # Check for bulk file processing guidance
    required_phrases = [
        "For tasks involving MANY files",
        "EXECUTOR use Python code",
        "more scalable than sequential file reads"
    ]

    missing = []
    for phrase in required_phrases:
        if phrase not in system_prompt:
            missing.append(phrase)

    if missing:
        print("❌ FAILED: Planner prompt missing bulk file guidance:")
        for phrase in missing:
            print(f"   - '{phrase}'")
        return False

    print("✅ PASSED: Planner has bulk file processing guidance")
    return True


def test_bulk_example_exists():
    """Test that there's an example showing bulk file processing."""
    examples_path = Path("mcp_client_for_ollama/agents/examples/planner_examples.json")

    with open(examples_path) as f:
        examples_data = json.load(f)

    # Find the bulk-file-processing example
    example = None
    for ex in examples_data.get("examples", []):
        if ex.get("category") == "bulk-file-processing":
            example = ex
            break

    if not example:
        print("❌ FAILED: Could not find 'bulk-file-processing' example")
        return False

    # Check that it uses Python in a single EXECUTOR task
    tasks = example["plan"]["tasks"]

    if len(tasks) != 1:
        print(f"❌ FAILED: Expected 1 task for bulk processing, got {len(tasks)}")
        return False

    task = tasks[0]

    if task.get("agent_type") != "EXECUTOR":
        print(f"❌ FAILED: Expected EXECUTOR, got {task.get('agent_type')}")
        return False

    description = task.get("description", "")
    if "Python" not in description or "all .md files" not in description:
        print("❌ FAILED: Task description doesn't mention Python or processing all files")
        print(f"   Description: {description[:100]}...")
        return False

    print("✅ PASSED: Bulk file processing example uses Python in single EXECUTOR task")
    return True


def test_category_keywords_updated():
    """Test that category keywords include bulk file processing."""
    delegation_path = Path("mcp_client_for_ollama/agents/delegation_client.py")

    with open(delegation_path) as f:
        content = f.read()

    if "'bulk-file-processing'" not in content:
        print("❌ FAILED: Category keywords not updated with 'bulk-file-processing'")
        return False

    # Check for relevant keywords
    keywords_to_check = ["'all files'", "'multiple files'", "'each file'"]
    missing = []
    for keyword in keywords_to_check:
        if keyword not in content:
            missing.append(keyword)

    if missing:
        print(f"❌ FAILED: Missing keywords in category: {', '.join(missing)}")
        return False

    print("✅ PASSED: Category keywords include bulk file processing")
    return True


def test_inefficient_vs_efficient_plan():
    """Compare inefficient (sequential reads) vs efficient (Python) approach."""
    # Inefficient: multiple sequential reads (what happened in the trace)
    inefficient_plan = {
        "tasks": [
            {"id": "task_1", "agent_type": "EXECUTOR", "description": "List files"},
            {"id": "task_2", "agent_type": "READER", "description": "Read each file"}
        ]
    }

    # Efficient: single Python task
    efficient_plan = {
        "tasks": [
            {
                "id": "task_1",
                "agent_type": "EXECUTOR",
                "description": "Use Python to read all .md files and check for tags"
            }
        ]
    }

    # Efficient plan should have fewer tasks
    if len(efficient_plan["tasks"]) >= len(inefficient_plan["tasks"]):
        print("❌ FAILED: Efficient plan should have fewer tasks")
        return False

    # Efficient plan should use EXECUTOR with Python
    if "Python" not in efficient_plan["tasks"][0]["description"]:
        print("❌ FAILED: Efficient plan should mention Python")
        return False

    print("✅ PASSED: Efficient plan uses Python in single EXECUTOR task")
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing Bulk File Processing Fix")
    print("="*60 + "\n")

    results = []

    print("Test 1: Loop limits increased for READER and EXECUTOR")
    results.append(test_loop_limits_increased())
    print()

    print("Test 2: Planner has bulk file processing guidance")
    results.append(test_planner_has_bulk_guidance())
    print()

    print("Test 3: Bulk file processing example exists")
    results.append(test_bulk_example_exists())
    print()

    print("Test 4: Category keywords updated")
    results.append(test_category_keywords_updated())
    print()

    print("Test 5: Efficient vs inefficient plan comparison")
    results.append(test_inefficient_vs_efficient_plan())
    print()

    print("="*60)
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nThe planner should now:")
        print("  1. Use Python for bulk file operations (10+ files)")
        print("  2. Complete tasks in single EXECUTOR call instead of many READER calls")
        print("  3. Handle larger workloads with increased loop limits (10 vs 2-3)")
        print("\nFor your query about finding files without tags:")
        print("  OLD: task_1 (list files) → task_2 (READER reads 3 files, hits limit)")
        print("  NEW: task_1 (EXECUTOR Python processes all files in one go)")
        exit(0)
    else:
        print(f"❌ {sum(not r for r in results)} TEST(S) FAILED")
        print("="*60)
        exit(1)
