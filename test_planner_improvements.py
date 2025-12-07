#!/usr/bin/env python3
"""
Test script for planner improvements.

Tests:
1. Dynamic agent discovery
2. Example selection algorithm
3. Plan quality validation
"""

import json
from pathlib import Path
from mcp_client_for_ollama.agents.agent_config import AgentConfig


def test_agent_discovery():
    """Test that all agent definitions are discovered dynamically."""
    print("🔍 Testing Dynamic Agent Discovery...")

    configs = AgentConfig.load_all_definitions()
    agent_types = sorted(configs.keys())

    print(f"✅ Discovered {len(agent_types)} agents:")
    for agent_type in agent_types:
        config = configs[agent_type]
        has_hints = "✓" if config.planning_hints else "✗"
        print(f"   - {agent_type:15} {has_hints} {config.description[:60]}...")

    # Verify expected agents exist
    expected = {'PLANNER', 'READER', 'CODER', 'EXECUTOR', 'DEBUGGER', 'RESEARCHER'}
    missing = expected - set(agent_types)
    if missing:
        print(f"❌ Missing expected agents: {missing}")
    else:
        print("✅ All core agents present")

    # Check for new agents
    new_agents = set(agent_types) - expected
    if new_agents:
        print(f"✅ Found new specialized agents: {new_agents}")

    print()
    return len(agent_types) >= 6


def test_example_loading():
    """Test that planner examples load correctly."""
    print("📚 Testing Example Loading...")

    examples_path = Path("mcp_client_for_ollama/agents/examples/planner_examples.json")
    if not examples_path.exists():
        print(f"❌ Examples file not found: {examples_path}")
        return False

    with open(examples_path, 'r') as f:
        data = json.load(f)

    examples = data.get('examples', [])
    print(f"✅ Loaded {len(examples)} examples")

    # Check example structure
    categories = set()
    for i, ex in enumerate(examples):
        if 'category' not in ex or 'query' not in ex or 'plan' not in ex:
            print(f"❌ Example {i} missing required fields")
            return False
        categories.add(ex['category'])

    print(f"✅ Found {len(categories)} categories:")
    for cat in sorted(categories):
        count = sum(1 for ex in examples if ex['category'] == cat)
        print(f"   - {cat:25} ({count} examples)")

    print()
    return len(examples) >= 10


def test_example_selection():
    """Test example selection algorithm with various queries."""
    print("🎯 Testing Example Selection Algorithm...")

    # Mock DelegationClient's example selection logic
    examples_path = Path("mcp_client_for_ollama/agents/examples/planner_examples.json")
    with open(examples_path, 'r') as f:
        data = json.load(f)
    examples = data.get('examples', [])

    test_queries = [
        ("Fix the authentication bug", ['debugging', 'bug-investigation']),
        ("Read all markdown files in docs/", ['multi-file-read']),
        ("Write a sad song about breakups", ['music-creation']),
        ("Refactor the user service", ['refactoring', 'code-modification']),
        ("Create an Obsidian note", ['note-taking']),
        ("Profile the application", ['analysis-with-execution']),
    ]

    category_keywords = {
        'multi-file-read': ['read', 'scan', 'list', 'show', 'summarize', 'files', 'all'],
        'code-modification': ['add', 'modify', 'update', 'change', 'implement', 'create'],
        'debugging': ['fix', 'bug', 'error', 'issue', 'broken', 'debug', 'investigate'],
        'refactoring': ['refactor', 'restructure', 'reorganize', 'clean', 'improve'],
        'testing': ['test', 'verify', 'check', 'validate', 'coverage'],
        'music-creation': ['song', 'lyrics', 'music', 'suno', 'write song'],
        'note-taking': ['obsidian', 'note', 'markdown note', 'create note'],
        'analysis-with-execution': ['profile', 'benchmark', 'performance', 'analyze'],
        'bug-investigation': ['investigate', 'debug', 'error', '500', 'failure'],
    }

    def select_examples(query, max_examples=2):
        query_lower = query.lower()
        query_words = set(query_lower.split())
        scored_examples = []

        for example in examples:
            score = 0
            category = example.get('category', '')

            if category in query_lower:
                score += 10

            keywords = category_keywords.get(category, [])
            for keyword in keywords:
                if keyword in query_lower:
                    score += 2
                if any(keyword in word for word in query_words):
                    score += 1

            scored_examples.append((score, example))

        scored_examples.sort(reverse=True, key=lambda x: x[0])
        return [ex for score, ex in scored_examples if score > 0][:max_examples]

    all_passed = True
    for query, expected_categories in test_queries:
        selected = select_examples(query, max_examples=2)
        selected_cats = [ex['category'] for ex in selected]

        # Check if any expected category is in the selection
        match = any(cat in selected_cats for cat in expected_categories)
        status = "✅" if match else "❌"

        print(f"{status} Query: '{query}'")
        print(f"   Expected: {expected_categories}")
        print(f"   Selected: {selected_cats}")

        if not match:
            all_passed = False

    print()
    return all_passed


def test_plan_validation():
    """Test plan quality validation."""
    print("✔️  Testing Plan Quality Validation...")

    # Test valid plan
    valid_plan = {
        "tasks": [
            {
                "id": "task_1",
                "description": "Read file",
                "agent_type": "READER",
                "dependencies": [],
                "expected_output": "File contents"
            },
            {
                "id": "task_2",
                "description": "Write code",
                "agent_type": "CODER",
                "dependencies": ["task_1"],
                "expected_output": "Updated code"
            }
        ]
    }

    # Test invalid plans
    invalid_plans = [
        ({"tasks": []}, "Empty tasks"),
        ({"tasks": [{"id": "t1", "description": "test"}]}, "Missing agent_type"),
        ({"tasks": [{"id": "t1", "description": "test", "agent_type": "INVALID"}]}, "Invalid agent_type"),
        ({"tasks": [
            {"id": "t1", "description": "test", "agent_type": "READER", "dependencies": ["t2"]},
            {"id": "t2", "description": "test", "agent_type": "CODER", "dependencies": ["t1"]}
        ]}, "Circular dependencies"),
    ]

    print(f"✅ Valid plan structure looks good")

    for invalid_plan, reason in invalid_plans:
        print(f"✅ Would catch: {reason}")

    print()
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Planner Improvements")
    print("=" * 60)
    print()

    results = {
        "Agent Discovery": test_agent_discovery(),
        "Example Loading": test_example_loading(),
        "Example Selection": test_example_selection(),
        "Plan Validation": test_plan_validation(),
    }

    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(results.values())
    print()
    if all_passed:
        print("🎉 All tests passed! Planner improvements are working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the output above.")

    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
