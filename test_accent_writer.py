#!/usr/bin/env python3
"""
Test script for ACCENT_WRITER agent.

This script tests the ACCENT_WRITER agent's ability to:
1. Initialize its memory (goal G_ACCENT_WRITER)
2. Create character accent profiles
3. Review dialogue for consistency
4. Flag inconsistencies
"""

import asyncio
import sys
from pathlib import Path

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_client_for_ollama.agents.delegation_client import DelegationClient
from mcp_client_for_ollama.agents.task import Task, TaskStatus

async def test_accent_writer():
    """Test the ACCENT_WRITER agent with sample dialogue."""

    print("=" * 80)
    print("ACCENT_WRITER Agent Test")
    print("=" * 80)
    print()

    # Initialize delegation client
    client = DelegationClient()

    # Test 1: Review consistent dialogue
    print("TEST 1: Review CONSISTENT dialogue (Scene 1)")
    print("-" * 80)

    dialogue_1 = """
Lady Ashford looked down her nose at the young man. "I am afraid I cannot permit such behavior in my establishment."

Jake shrugged. "Yeah, whatever. I'm outta here anyway."

"Indeed," Lady Ashford replied coolly. "That would be most prudent."
"""

    task_1 = Task(
        id="test_1",
        description=f"Review this dialogue for accent consistency: {dialogue_1}",
        agent_type="ACCENT_WRITER",
        dependencies=[],
        status=TaskStatus.PENDING
    )

    print(f"Task: {task_1.description[:100]}...")
    print()

    try:
        result_1 = await client._execute_task(task_1, {})
        print("RESULT:")
        print(result_1)
        print()
    except Exception as e:
        print(f"ERROR: {e}")
        print()

    # Test 2: Review inconsistent dialogue (characters swapped)
    print("TEST 2: Review INCONSISTENT dialogue (Scene 2 - Characters Swapped)")
    print("-" * 80)

    dialogue_2 = """
Jake straightened his collar and spoke carefully. "I believe we should proceed with the utmost caution in this matter."

Lady Ashford laughed. "Dude, you're totally overthinkin' this. Let's just do it!"
"""

    task_2 = Task(
        id="test_2",
        description=f"Review this dialogue for accent consistency: {dialogue_2}",
        agent_type="ACCENT_WRITER",
        dependencies=[],
        status=TaskStatus.PENDING
    )

    print(f"Task: {task_2.description[:100]}...")
    print()

    try:
        result_2 = await client._execute_task(task_2, {})
        print("RESULT:")
        print(result_2)
        print()
    except Exception as e:
        print(f"ERROR: {e}")
        print()

    # Test 3: Review mixed dialogue
    print("TEST 3: Review MIXED dialogue (Scene 4 - Some consistent, some not)")
    print("-" * 80)

    dialogue_3 = """
Lady Ashford considered the proposal. "That is rather an interesting suggestion."

Jake grinned. "Yeah? I thought you'd like it."

Lady Ashford frowned. "But like, isn't it kinda risky though?"

Jake replied formally, "One must consider all potential ramifications before proceeding."
"""

    task_3 = Task(
        id="test_3",
        description=f"Review this dialogue for accent consistency: {dialogue_3}",
        agent_type="ACCENT_WRITER",
        dependencies=[],
        status=TaskStatus.PENDING
    )

    print(f"Task: {task_3.description[:100]}...")
    print()

    try:
        result_3 = await client._execute_task(task_3, {})
        print("RESULT:")
        print(result_3)
        print()
    except Exception as e:
        print(f"ERROR: {e}")
        print()

    print("=" * 80)
    print("Test Complete!")
    print("=" * 80)

    await client.cleanup()

if __name__ == "__main__":
    asyncio.run(test_accent_writer())
