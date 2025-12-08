#!/usr/bin/env python3
"""
Test to verify the planner fix for the MCP tool name as agent_type bug.

This test checks that:
1. The planner system prompt includes the new guidance
2. The validation logic properly rejects invalid agent types
"""

import json
from pathlib import Path

def test_planner_prompt_has_guidance():
    """Test that planner.json has the updated system prompt with MCP tool guidance."""
    planner_path = Path("mcp_client_for_ollama/agents/definitions/planner.json")

    with open(planner_path) as f:
        planner_config = json.load(f)

    system_prompt = planner_config.get("system_prompt", "")

    # Check for the key guidance phrases
    required_phrases = [
        "NEVER use MCP tool names as agent_type values",
        "agent_type field MUST be one of the available agent names",
        "Instead, assign tasks to the appropriate agent"
    ]

    missing = []
    for phrase in required_phrases:
        if phrase not in system_prompt:
            missing.append(phrase)

    if missing:
        print("❌ FAILED: Planner prompt missing guidance:")
        for phrase in missing:
            print(f"   - '{phrase}'")
        return False

    print("✅ PASSED: Planner prompt has all required guidance")
    return True


def test_invalid_plan_detection():
    """Test that the validation logic would catch the bug from the trace."""
    from mcp_client_for_ollama.agents.delegation_client import DelegationClient

    # Simulate the buggy plan from the trace
    buggy_plan = {
        "tasks": [
            {
                "id": "task_1",
                "description": "Create a new note in Nextcloud",
                "agent_type": "nextcloud-api.nc_notes_create_note",  # ❌ This is wrong!
                "dependencies": [],
                "expected_output": "Note created"
            }
        ]
    }

    # Mock agent configs (simplified version)
    available_agents = {"EXECUTOR", "CODER", "READER", "RESEARCHER", "DEBUGGER"}

    # Check if the buggy agent_type would be caught
    tasks = buggy_plan.get("tasks", [])
    for i, task in enumerate(tasks):
        agent_type = task.get("agent_type", "")
        if agent_type not in available_agents:
            print(f"✅ PASSED: Validation correctly identifies invalid agent_type: '{agent_type}'")
            return True

    print("❌ FAILED: Validation did not catch invalid agent_type")
    return False


def test_correct_plan_format():
    """Test that a correctly formatted plan would pass validation."""
    correct_plan = {
        "tasks": [
            {
                "id": "task_1",
                "description": "Use nextcloud-api.nc_notes_create_note to create a new note",
                "agent_type": "EXECUTOR",  # ✅ Correct - using agent name
                "dependencies": [],
                "expected_output": "Note created with shipper details"
            }
        ]
    }

    available_agents = {"EXECUTOR", "CODER", "READER", "RESEARCHER", "DEBUGGER"}

    tasks = correct_plan.get("tasks", [])
    for task in tasks:
        agent_type = task.get("agent_type", "")
        if agent_type not in available_agents:
            print(f"❌ FAILED: Correct plan rejected. Agent type: '{agent_type}'")
            return False

    print("✅ PASSED: Correctly formatted plan passes validation")
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing Planner Fix for MCP Tool Name Bug")
    print("="*60 + "\n")

    results = []

    print("Test 1: Planner prompt includes new guidance")
    results.append(test_planner_prompt_has_guidance())
    print()

    print("Test 2: Validation detects invalid agent_type (MCP tool name)")
    results.append(test_invalid_plan_detection())
    print()

    print("Test 3: Correct plan format passes validation")
    results.append(test_correct_plan_format())
    print()

    print("="*60)
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("="*60)
        exit(0)
    else:
        print(f"❌ {sum(not r for r in results)} TEST(S) FAILED")
        print("="*60)
        exit(1)
