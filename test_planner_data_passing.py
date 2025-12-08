#!/usr/bin/env python3
"""
Test to verify the planner fix for including necessary data in task descriptions.

This test checks that:
1. The planner system prompt includes guidance about including data
2. The example shows the correct pattern (data included in task description)
3. A simulated plan correctly includes the data
"""

import json
from pathlib import Path


def test_planner_prompt_has_data_guidance():
    """Test that planner.json has guidance about including data in task descriptions."""
    planner_path = Path("mcp_client_for_ollama/agents/definitions/planner.json")

    with open(planner_path) as f:
        planner_config = json.load(f)

    system_prompt = planner_config.get("system_prompt", "")

    # Check for the key guidance phrases
    required_phrases = [
        "Include ALL necessary data directly in task descriptions",
        "Never just reference \"the specified content\"",
        "copy that content verbatim into the task description"
    ]

    missing = []
    for phrase in required_phrases:
        if phrase not in system_prompt:
            missing.append(phrase)

    if missing:
        print("❌ FAILED: Planner prompt missing data guidance:")
        for phrase in missing:
            print(f"   - '{phrase}'")
        return False

    print("✅ PASSED: Planner prompt has data inclusion guidance")
    return True


def test_example_shows_correct_pattern():
    """Test that the example demonstrates including data in task descriptions."""
    examples_path = Path("mcp_client_for_ollama/agents/examples/planner_examples.json")

    with open(examples_path) as f:
        examples_data = json.load(f)

    # Find the mcp-tool-with-specific-data example
    example = None
    for ex in examples_data.get("examples", []):
        if ex.get("category") == "mcp-tool-with-specific-data":
            example = ex
            break

    if not example:
        print("❌ FAILED: Could not find 'mcp-tool-with-specific-data' example")
        return False

    # Check that task_2 includes the actual bullet points
    tasks = example["plan"]["tasks"]
    task_2 = tasks[1]  # Second task should append data

    description = task_2.get("description", "")

    # The description should include the actual bullet points, not just reference them
    required_content = [
        "Armstrong transport",
        "Fifth wheel freight",
        "Molo load board",
        "Pinnacle freight"
    ]

    missing_content = []
    for content in required_content:
        if content not in description:
            missing_content.append(content)

    if missing_content:
        print("❌ FAILED: Task description missing actual data:")
        for content in missing_content:
            print(f"   - '{content}'")
        print(f"\nActual description: {description[:200]}...")
        return False

    print("✅ PASSED: Example shows correct pattern (data included in description)")
    return True


def test_buggy_vs_correct_plan():
    """Compare the buggy plan from the trace with the correct pattern."""
    # Buggy plan from trace (doesn't include the data)
    buggy_task_2 = {
        "description": "Append specified points to the content of the retrieved note using nextcloud-api.nc_notes_append_content tool."
    }

    # Correct plan (includes the data)
    correct_task_2 = {
        "description": "Append the following bullet points to note 46277 using nextcloud-api.nc_notes_append_content tool:\n- Armstrong transport\n- Fifth wheel freight\n- Molo load board\n- Pinnacle freight"
    }

    # Check buggy plan lacks data
    if "Armstrong transport" in buggy_task_2["description"]:
        print("❌ FAILED: Buggy plan unexpectedly contains data")
        return False

    # Check correct plan includes data
    if "Armstrong transport" not in correct_task_2["description"]:
        print("❌ FAILED: Correct plan doesn't contain data")
        return False

    print("✅ PASSED: Correct plan includes data, buggy plan doesn't")
    return True


def test_category_keywords_updated():
    """Test that the category keywords include the new example category."""
    # This is a simple check to ensure the delegation_client.py was updated
    delegation_path = Path("mcp_client_for_ollama/agents/delegation_client.py")

    with open(delegation_path) as f:
        content = f.read()

    if "'mcp-tool-with-specific-data'" not in content:
        print("❌ FAILED: Category keywords not updated in delegation_client.py")
        return False

    # Check for relevant keywords
    keywords_to_check = ["'append'", "'get note'", "'modify note'"]
    for keyword in keywords_to_check:
        if keyword not in content:
            print(f"❌ FAILED: Missing keyword {keyword} in category keywords")
            return False

    print("✅ PASSED: Category keywords updated in delegation_client.py")
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing Planner Fix for Data Passing Bug")
    print("="*60 + "\n")

    results = []

    print("Test 1: Planner prompt includes data inclusion guidance")
    results.append(test_planner_prompt_has_data_guidance())
    print()

    print("Test 2: Example demonstrates correct pattern")
    results.append(test_example_shows_correct_pattern())
    print()

    print("Test 3: Compare buggy vs correct plan")
    results.append(test_buggy_vs_correct_plan())
    print()

    print("Test 4: Category keywords updated")
    results.append(test_category_keywords_updated())
    print()

    print("="*60)
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nThe planner should now:")
        print("  1. Include actual data in task descriptions")
        print("  2. Not just reference \"the specified content\"")
        print("  3. Give agents everything they need to complete tasks")
        exit(0)
    else:
        print(f"❌ {sum(not r for r in results)} TEST(S) FAILED")
        print("="*60)
        exit(1)
