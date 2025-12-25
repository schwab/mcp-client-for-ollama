"""
Boot ritual for worker agents.

Implements the standardized boot-up sequence that all worker agents
follow before taking action. This ensures agents are grounded in the
current memory state.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import subprocess

from .base_memory import DomainMemory, Feature, FeatureStatus


class BootRitual:
    """
    Standardized boot-up sequence for worker agents.

    Following the Anthropic pattern: Every agent run must begin by
    reading memory to understand the current state before taking action.
    """

    @staticmethod
    def _build_project_context() -> Dict[str, Any]:
        """
        Build project context by analyzing the current directory structure.

        Returns:
            Dictionary with project structure information
        """
        cwd = os.getcwd()
        context = {
            "working_directory": cwd,
            "key_folders": [],
            "project_type": "unknown",
            "important_files": [],
            "python_packages": []
        }

        # Check for common project folders
        common_folders = ["src", "tests", "docs", "lib", "bin", "config", "scripts", "data"]
        for folder in common_folders:
            folder_path = os.path.join(cwd, folder)
            if os.path.isdir(folder_path):
                try:
                    # Count files in folder
                    file_count = sum(1 for _ in os.scandir(folder_path) if _.is_file())
                    context["key_folders"].append({
                        "name": folder,
                        "path": folder_path,
                        "file_count": file_count
                    })
                except (PermissionError, OSError):
                    pass

        # Detect project type
        if os.path.exists(os.path.join(cwd, "pyproject.toml")):
            context["project_type"] = "Python package"
            context["important_files"].append("pyproject.toml")
        elif os.path.exists(os.path.join(cwd, "setup.py")):
            context["project_type"] = "Python package (legacy)"
            context["important_files"].append("setup.py")
        elif os.path.exists(os.path.join(cwd, "package.json")):
            context["project_type"] = "Node.js/JavaScript"
            context["important_files"].append("package.json")
        elif os.path.exists(os.path.join(cwd, "Cargo.toml")):
            context["project_type"] = "Rust"
            context["important_files"].append("Cargo.toml")

        # Detect Python packages (directories with __init__.py)
        if context["project_type"].startswith("Python"):
            for entry in os.scandir(cwd):
                if entry.is_dir() and not entry.name.startswith('.'):
                    # Check if it's a Python package
                    init_file = os.path.join(entry.path, "__init__.py")
                    if os.path.exists(init_file):
                        # Found a package, scan its structure
                        package_info = {
                            "name": entry.name,
                            "path": entry.name,  # Relative path from cwd
                            "submodules": []
                        }
                        # Scan for submodules
                        try:
                            for subentry in os.scandir(entry.path):
                                if subentry.is_dir() and not subentry.name.startswith('.'):
                                    sub_init = os.path.join(subentry.path, "__init__.py")
                                    if os.path.exists(sub_init):
                                        package_info["submodules"].append(subentry.name)
                                elif subentry.is_file() and subentry.name.endswith('.py') and subentry.name != '__init__.py':
                                    package_info["submodules"].append(subentry.name[:-3])  # Remove .py
                        except (PermissionError, OSError):
                            pass
                        context["python_packages"].append(package_info)

        # Check for common config files
        config_files = ["README.md", ".gitignore", "requirements.txt", "Makefile", "docker-compose.yml"]
        for config in config_files:
            if os.path.exists(os.path.join(cwd, config)) and config not in context["important_files"]:
                context["important_files"].append(config)

        return context

    @staticmethod
    def get_project_context(memory: DomainMemory) -> Dict[str, Any]:
        """
        Get or build project context, caching it in memory state.

        Args:
            memory: The domain memory to store context in

        Returns:
            Project context dictionary
        """
        # Check if already cached
        if memory.state and "project_context" in memory.state:
            return memory.state["project_context"]

        # Build and cache
        context = BootRitual._build_project_context()
        if memory.state is None:
            memory.state = {}
        memory.state["project_context"] = context

        return context

    @staticmethod
    def build_memory_context(
        memory: DomainMemory,
        agent_type: str,
        task_description: Optional[str] = None,
        max_recent_progress: int = 5,
    ) -> str:
        """
        Build memory context for an agent's system message.

        This creates a structured summary of the current memory state
        that gets injected into the agent's context.

        Args:
            memory: The domain memory to read from
            agent_type: Type of agent (CODER, EXECUTOR, etc.)
            task_description: Optional specific task for this run
            max_recent_progress: Number of recent progress entries to include

        Returns:
            Formatted context string for the agent
        """
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("MEMORY CONTEXT - READ THIS BEFORE TAKING ACTION")
        lines.append("=" * 80)
        lines.append("")

        # Session info
        lines.append(f"Session ID: {memory.metadata.session_id}")
        lines.append(f"Domain: {memory.metadata.domain}")
        lines.append(f"Description: {memory.metadata.description}")
        lines.append(f"Last Updated: {memory.metadata.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Project context (cached)
        project_ctx = BootRitual.get_project_context(memory)
        lines.append("PROJECT CONTEXT:")
        lines.append(f"  Working Directory: {project_ctx['working_directory']}")
        lines.append(f"  Project Type: {project_ctx['project_type']}")
        if project_ctx["key_folders"]:
            lines.append("  Key Folders:")
            for folder in project_ctx["key_folders"]:
                lines.append(f"    - {folder['name']}/ ({folder['file_count']} files)")
        if project_ctx["important_files"]:
            lines.append(f"  Important Files: {', '.join(project_ctx['important_files'])}")
        if project_ctx.get("python_packages"):
            lines.append("  Python Packages:")
            for pkg in project_ctx["python_packages"]:
                if pkg["submodules"]:
                    lines.append(f"    - {pkg['path']}/ (modules: {', '.join(pkg['submodules'][:5])}{'...' if len(pkg['submodules']) > 5 else ''})")
                else:
                    lines.append(f"    - {pkg['path']}/")
        lines.append("")

        # Progress summary
        total_features = len(memory.get_all_features())
        completed = sum(1 for f in memory.get_all_features() if f.status == FeatureStatus.COMPLETED)
        pending = sum(1 for f in memory.get_all_features() if f.status == FeatureStatus.PENDING)
        in_progress = sum(1 for f in memory.get_all_features() if f.status == FeatureStatus.IN_PROGRESS)
        failed = sum(1 for f in memory.get_all_features() if f.status == FeatureStatus.FAILED)

        lines.append("PROGRESS SUMMARY:")
        lines.append(f"  Total Features: {total_features}")
        lines.append(f"  ✓ Completed: {completed}")
        lines.append(f"  ○ Pending: {pending}")
        lines.append(f"  ⟳ In Progress: {in_progress}")
        lines.append(f"  ✗ Failed: {failed}")
        lines.append(f"  Completion: {memory.get_completion_percentage():.1f}%")
        lines.append("")

        # Goals and features
        lines.append("GOALS AND FEATURES:")
        for goal in memory.goals:
            status_symbol = {
                "pending": "○",
                "in_progress": "⟳",
                "completed": "✓",
                "failed": "✗",
                "cancelled": "⊘",
            }.get(goal.status.value, "?")

            lines.append(f"\n{status_symbol} Goal {goal.id}: {goal.description}")

            if goal.constraints:
                lines.append("  Constraints:")
                for constraint in goal.constraints:
                    lines.append(f"    - {constraint}")

            lines.append("  Features:")
            for feature in goal.features:
                feature_symbol = {
                    FeatureStatus.PENDING: "○",
                    FeatureStatus.IN_PROGRESS: "⟳",
                    FeatureStatus.COMPLETED: "✓",
                    FeatureStatus.FAILED: "✗",
                    FeatureStatus.BLOCKED: "⊘",
                }.get(feature.status, "?")

                lines.append(f"    {feature_symbol} {feature.id}: {feature.description}")

                # Show criteria
                if feature.criteria:
                    lines.append("       Pass/Fail Criteria:")
                    for criterion in feature.criteria:
                        lines.append(f"         - {criterion}")

                # Show test info
                if feature.tests:
                    test_status = ""
                    if feature.test_results:
                        latest_results = {}
                        for result in sorted(feature.test_results, key=lambda x: x.timestamp, reverse=True):
                            if result.test_id not in latest_results:
                                latest_results[result.test_id] = result

                        passed = sum(1 for r in latest_results.values() if r.passed)
                        total = len(latest_results)
                        test_status = f" [{passed}/{total} passing]"

                    lines.append(f"       Tests: {', '.join(feature.tests)}{test_status}")

        lines.append("")

        # Domain-specific state
        if memory.state:
            lines.append("DOMAIN STATE:")
            if "test_harness" in memory.state:
                th = memory.state["test_harness"]
                lines.append(f"  Test Framework: {th.get('framework', 'unknown')}")
                lines.append(f"  Test Command: {th.get('run_command', 'unknown')}")

            if "scaffolding" in memory.state:
                sc = memory.state["scaffolding"]
                if "language" in sc:
                    lines.append(f"  Language: {sc['language']}")
                if "git_enabled" in sc:
                    lines.append(f"  Git Enabled: {sc['git_enabled']}")

            lines.append("")

        # Recent progress
        recent = memory.get_recent_progress(limit=max_recent_progress)
        if recent:
            lines.append("RECENT PROGRESS:")
            for entry in recent:
                lines.append(f"  {entry.to_log_line()}")
            lines.append("")

        # Agent-specific guidance
        lines.append("YOUR TASK:")
        if task_description:
            lines.append(f"  {task_description}")
        lines.append("")

        lines.append("PROTOCOL:")
        lines.append("  1. Review the memory state above")
        lines.append("  2. Pick ONE feature to work on (preferably pending or failed)")
        lines.append("  3. Implement your changes")
        lines.append("  4. Test your changes (if applicable)")
        lines.append("  5. Update the feature status using memory update tools")
        lines.append("  6. Log your progress")
        lines.append("")
        lines.append("IMPORTANT:")
        lines.append("  - Work on ONE feature at a time")
        lines.append("  - Do not mark features as completed unless tests pass")
        lines.append("  - Always leave the code in a clean, working state")
        lines.append("  - Use the memory update tools to record your work")
        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    @staticmethod
    def get_next_feature_suggestion(
        memory: DomainMemory,
        agent_type: str,
    ) -> Optional[Feature]:
        """
        Suggest the next feature for an agent to work on.

        Uses simple heuristics:
        - Prioritize failed features (need fixing)
        - Then pending features
        - Prefer higher priority if available

        Args:
            memory: The domain memory
            agent_type: Type of agent

        Returns:
            Suggested feature, or None if no work available
        """
        all_features = memory.get_all_features()

        # Filter to pending or failed
        workable = [
            f for f in all_features
            if f.status in [FeatureStatus.PENDING, FeatureStatus.FAILED]
        ]

        if not workable:
            return None

        # Sort by priority (if priority info in notes)
        # High priority first, then failed features, then pending
        def priority_score(feature: Feature) -> int:
            score = 0

            # Failed features are urgent
            if feature.status == FeatureStatus.FAILED:
                score += 100

            # Priority from notes
            if "priority: high" in feature.notes.lower():
                score += 50
            elif "priority: medium" in feature.notes.lower():
                score += 25
            # Low priority gets +0

            return score

        workable.sort(key=priority_score, reverse=True)
        return workable[0]

    @staticmethod
    def format_feature_context(feature: Feature) -> str:
        """
        Format detailed context for a specific feature.

        Args:
            feature: The feature to format

        Returns:
            Formatted feature context
        """
        lines = [
            f"FEATURE: {feature.id}",
            f"Description: {feature.description}",
            f"Status: {feature.status.value}",
            "",
            "Pass/Fail Criteria:",
        ]

        for i, criterion in enumerate(feature.criteria, 1):
            lines.append(f"  {i}. {criterion}")

        if feature.tests:
            lines.append("")
            lines.append("Required Tests:")
            for test in feature.tests:
                lines.append(f"  - {test}")

        if feature.test_results:
            lines.append("")
            lines.append("Recent Test Results:")
            latest = sorted(feature.test_results, key=lambda x: x.timestamp, reverse=True)[:3]
            for result in latest:
                status = "✓ PASS" if result.passed else "✗ FAIL"
                lines.append(f"  {status}: {result.test_id} ({result.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
                if result.details:
                    lines.append(f"         {result.details}")

        if feature.notes:
            lines.append("")
            lines.append(f"Notes: {feature.notes}")

        return "\n".join(lines)

    @staticmethod
    def build_tool_update_message(
        feature_id: str,
        new_status: str,
        details: str,
    ) -> str:
        """
        Build a message instructing the agent to update memory.

        Args:
            feature_id: ID of feature to update
            new_status: New status value
            details: Details about what was done

        Returns:
            Instruction message
        """
        return (
            f"\nREMEMBER: After completing your work, update the memory:\n"
            f"1. Use builtin.update_feature_status to mark {feature_id} as '{new_status}'\n"
            f"2. Use builtin.log_progress to record what you did\n"
            f"3. Provide clear details: {details}\n"
        )
