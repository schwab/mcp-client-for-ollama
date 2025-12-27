"""
Memory update tools for agents.

Provides builtin tools that agents can call to update domain memory
(feature status, progress logging, etc.)
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_memory import FeatureStatus, OutcomeType
from .storage import MemoryStorage


class MemoryTools:
    """
    Tools for agents to interact with domain memory.

    These are designed to be registered as builtin tools so agents
    can update memory state through tool calls.
    """

    def __init__(self, storage: MemoryStorage):
        """
        Initialize memory tools.

        Args:
            storage: Memory storage instance
        """
        self.storage = storage
        self.current_session_id: Optional[str] = None
        self.current_domain: Optional[str] = None

    def set_current_session(self, session_id: str, domain: str) -> None:
        """
        Set the current session context.

        This must be called before agents can use memory update tools.

        Args:
            session_id: The active session ID
            domain: The active domain
        """
        self.current_session_id = session_id
        self.current_domain = domain

    def update_feature_status(
        self,
        feature_id: str,
        status: str,
        notes: Optional[str] = None,
    ) -> str:
        """
        Update the status of a feature.

        Tool for agents to mark features as pending/in_progress/completed/failed.

        Args:
            feature_id: ID of the feature to update (e.g., "F1")
            status: New status (pending, in_progress, completed, failed, blocked)
            notes: Optional notes about the update

        Returns:
            Success or error message
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Validate status
            try:
                status_enum = FeatureStatus(status)
            except ValueError:
                return f"Error: Invalid status '{status}'. Must be one of: pending, in_progress, completed, failed, blocked"

            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find and update feature
            feature = memory.get_feature_by_id(feature_id)
            if not feature:
                return f"Error: Feature '{feature_id}' not found in memory"

            old_status = feature.status
            feature.status = status_enum
            feature.updated_at = datetime.now()

            if notes:
                if feature.notes:
                    feature.notes += f"\n{notes}"
                else:
                    feature.notes = notes

            # Update parent goal status
            for goal in memory.goals:
                if any(f.id == feature_id for f in goal.features):
                    goal.update_status_from_features()
                    break

            # Save
            self.storage.save_memory(memory)

            return (
                f"✓ Updated feature {feature_id}: {old_status.value} → {status}\n"
                f"  Description: {feature.description}\n"
                f"  {len(feature.criteria)} criteria defined\n"
                + (f"  Notes: {notes}\n" if notes else "")
            )

        except Exception as e:
            return f"Error updating feature status: {e}"

    def log_progress(
        self,
        agent_type: str,
        action: str,
        outcome: str,
        details: str,
        feature_id: Optional[str] = None,
        artifacts_changed: Optional[list] = None,
    ) -> str:
        """
        Log a progress entry to memory.

        Tool for agents to record what they did during this run.

        Args:
            agent_type: Type of agent (CODER, EXECUTOR, etc.)
            action: What action was taken (e.g., "Implemented login endpoint")
            outcome: Outcome (success, failure, partial, blocked)
            details: Detailed description of what was done
            feature_id: Optional feature ID this relates to
            artifacts_changed: Optional list of files/artifacts modified

        Returns:
            Success or error message
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Validate outcome
            try:
                outcome_enum = OutcomeType(outcome)
            except ValueError:
                return f"Error: Invalid outcome '{outcome}'. Must be one of: success, failure, partial, blocked"

            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Add progress entry
            memory.add_progress_entry(
                agent_type=agent_type,
                action=action,
                outcome=outcome_enum,
                details=details,
                feature_id=feature_id,
                artifacts_changed=artifacts_changed,
            )

            # Save
            self.storage.save_memory(memory)

            emoji = {
                OutcomeType.SUCCESS: "✓",
                OutcomeType.FAILURE: "✗",
                OutcomeType.PARTIAL: "~",
                OutcomeType.BLOCKED: "⊘",
            }[outcome_enum]

            return (
                f"{emoji} Progress logged:\n"
                f"  Agent: {agent_type}\n"
                f"  Action: {action}\n"
                f"  Outcome: {outcome}\n"
                + (f"  Feature: {feature_id}\n" if feature_id else "")
                + (f"  Files changed: {', '.join(artifacts_changed)}\n" if artifacts_changed else "")
            )

        except Exception as e:
            return f"Error logging progress: {e}"

    def add_test_result(
        self,
        feature_id: str,
        test_id: str,
        passed: bool,
        details: Optional[str] = None,
        output: Optional[str] = None,
    ) -> str:
        """
        Add a test result to a feature.

        Tool for agents to record test execution results.

        Args:
            feature_id: ID of the feature being tested
            test_id: ID/name of the test
            passed: Whether the test passed
            details: Optional details about the test
            output: Optional test output

        Returns:
            Success or error message
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            from .base_memory import TestResult

            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find feature
            feature = memory.get_feature_by_id(feature_id)
            if not feature:
                return f"Error: Feature '{feature_id}' not found in memory"

            # Add test result
            test_result = TestResult(
                test_id=test_id,
                feature_id=feature_id,
                passed=passed,
                timestamp=datetime.now(),
                details=details or "",
                output=output or "",
            )
            feature.test_results.append(test_result)

            # Auto-update feature status based on tests
            feature.update_status_from_tests()

            # Update parent goal
            for goal in memory.goals:
                if any(f.id == feature_id for f in goal.features):
                    goal.update_status_from_features()
                    break

            # Save
            self.storage.save_memory(memory)

            status_icon = "✓" if passed else "✗"
            return (
                f"{status_icon} Test result added:\n"
                f"  Feature: {feature_id}\n"
                f"  Test: {test_id}\n"
                f"  Result: {'PASS' if passed else 'FAIL'}\n"
                f"  Feature status auto-updated to: {feature.status.value}\n"
            )

        except Exception as e:
            return f"Error adding test result: {e}"

    def get_memory_state(self) -> str:
        """
        Get current memory state summary.

        Tool for agents to check memory status.

        Returns:
            Formatted memory state summary
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            lines = [
                f"Session: {memory.metadata.session_id}",
                f"Domain: {memory.metadata.domain}",
                f"Description: {memory.metadata.description}",
                f"",
                f"Progress:",
            ]

            total = len(memory.get_all_features())
            completed = sum(1 for f in memory.get_all_features() if f.status == FeatureStatus.COMPLETED)

            lines.append(f"  Completed: {completed}/{total} features ({memory.get_completion_percentage():.1f}%)")
            lines.append(f"")
            lines.append(f"Goals:")

            for goal in memory.goals:
                lines.append(f"  {goal.id}: {goal.description} [{goal.status.value}]")
                for feature in goal.features:
                    status_icon = {
                        FeatureStatus.PENDING: "○",
                        FeatureStatus.IN_PROGRESS: "⟳",
                        FeatureStatus.COMPLETED: "✓",
                        FeatureStatus.FAILED: "✗",
                        FeatureStatus.BLOCKED: "⊘",
                    }[feature.status]
                    lines.append(f"    {status_icon} {feature.id}: {feature.description}")

            return "\n".join(lines)

        except Exception as e:
            return f"Error getting memory state: {e}"

    def get_feature_details(self, feature_id: str) -> str:
        """
        Get detailed information about a specific feature.

        Tool for agents to check feature criteria and status.

        Args:
            feature_id: ID of the feature

        Returns:
            Formatted feature details
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find feature and parent goal
            feature = memory.get_feature_by_id(feature_id)
            if not feature:
                return f"Error: Feature '{feature_id}' not found"

            parent_goal = None
            for goal in memory.goals:
                if any(f.id == feature_id for f in goal.features):
                    parent_goal = goal
                    break

            from .boot_ritual import BootRitual
            feature_context = BootRitual.format_feature_context(feature)

            # Add parent goal context
            if parent_goal:
                return (
                    f"Parent Goal: {parent_goal.id} - {parent_goal.description}\n"
                    f"{'='*70}\n"
                    f"{feature_context}"
                )
            return feature_context

        except Exception as e:
            return f"Error getting feature details: {e}"

    def get_goal_details(self, goal_id: str) -> str:
        """
        Get detailed information about a specific goal and its features.

        Tool for users to quickly view a goal without seeing the entire memory state.

        Args:
            goal_id: ID of the goal (e.g., "G1")

        Returns:
            Formatted goal details with feature summary
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find goal
            goal = memory.get_goal_by_id(goal_id)
            if not goal:
                return f"Error: Goal '{goal_id}' not found in memory"

            lines = []
            lines.append(f"{'='*70}")
            lines.append(f"GOAL {goal.id}: {goal.description}")
            lines.append(f"Status: {goal.status.value}")
            lines.append(f"{'='*70}")

            if goal.constraints:
                lines.append("\nConstraints:")
                for constraint in goal.constraints:
                    lines.append(f"  • {constraint}")

            if not goal.features:
                lines.append("\nNo features defined yet.")
                lines.append("Use builtin.add_feature to add features to this goal.")
            else:
                # Feature summary
                feature_counts = {
                    "pending": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "failed": 0,
                    "blocked": 0
                }

                for feature in goal.features:
                    status_value = feature.status.value if hasattr(feature.status, 'value') else feature.status
                    if status_value in feature_counts:
                        feature_counts[status_value] += 1

                total = len(goal.features)
                completed = feature_counts["completed"]
                progress_pct = (completed / total * 100) if total > 0 else 0

                lines.append(f"\nProgress: {completed}/{total} features ({progress_pct:.0f}%)")
                lines.append("")
                lines.append("Features:")

                for feature in goal.features:
                    status_value = feature.status.value if hasattr(feature.status, 'value') else feature.status
                    status_icon = {
                        "pending": "○",
                        "in_progress": "⟳",
                        "completed": "✓",
                        "failed": "✗",
                        "blocked": "⊘",
                    }.get(status_value, "?")

                    # Truncate long descriptions
                    desc = feature.description
                    if len(desc) > 70:
                        desc = desc[:67] + "..."

                    priority_badge = ""
                    if feature.priority == "high":
                        priority_badge = "[HIGH] "
                    elif feature.priority == "low":
                        priority_badge = "[LOW] "

                    assigned = f" → {feature.assigned_to}" if feature.assigned_to else ""

                    lines.append(f"  {status_icon} {feature.id}: {priority_badge}{desc}{assigned}")

                    # Show criteria count if available
                    if feature.criteria:
                        lines.append(f"      {len(feature.criteria)} criteria defined")

            lines.append("")
            lines.append("💡 Use builtin.get_feature_details to see details about a specific feature")

            return "\n".join(lines)

        except Exception as e:
            return f"Error getting goal details: {e}"

    # ========================================================================
    # INTERACTIVE MEMORY MANAGEMENT TOOLS
    # ========================================================================

    def add_goal(
        self,
        goal_id: Optional[str] = None,
        description: str = "",
        constraints: Optional[list] = None,
    ) -> str:
        """
        Add a new goal to the current memory session.

        Tool for users to add new goals as plans evolve.

        Args:
            goal_id: Optional custom goal ID (e.g., 'G_LORE_KEEPER'). If not provided, auto-generates numeric ID.
            description: Clear description of the goal
            constraints: Optional list of constraints or requirements

        Returns:
            Success message with new goal ID or error
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            from .base_memory import Goal, GoalStatus

            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            existing_ids = [g.id for g in memory.goals]

            # Determine goal ID
            if goal_id:
                # Custom goal ID provided - validate it's not already taken
                if goal_id in existing_ids:
                    return f"Error: Goal ID '{goal_id}' already exists. Use a different ID or omit to auto-generate."
                new_goal_id = goal_id
            else:
                # Auto-generate next numeric goal ID
                next_num = len(existing_ids) + 1
                while f"G{next_num}" in existing_ids:
                    next_num += 1
                new_goal_id = f"G{next_num}"

            # Create new goal
            new_goal = Goal(
                id=new_goal_id,
                description=description,
                constraints=constraints or [],
                features=[],
                status=GoalStatus.PENDING,
            )

            memory.goals.append(new_goal)
            memory.metadata.updated_at = datetime.now()

            # Save
            self.storage.save_memory(memory)

            return (
                f"✓ Added new goal {new_goal_id}:\n"
                f"  Description: {description}\n"
                f"  Constraints: {len(constraints or [])}\n"
                f"  Features: 0 (add features with add_feature tool)\n"
            )

        except Exception as e:
            return f"Error adding goal: {e}"

    def update_goal(
        self,
        goal_id: str,
        description: Optional[str] = None,
        add_constraints: Optional[list] = None,
        remove_constraints: Optional[list] = None,
    ) -> str:
        """
        Update an existing goal's description or constraints.

        Tool for users to modify goals as plans change.

        Args:
            goal_id: ID of the goal to update (e.g., "G1")
            description: New description (optional)
            add_constraints: List of constraints to add (optional)
            remove_constraints: List of constraints to remove (optional)

        Returns:
            Success or error message
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find goal
            goal = memory.get_goal_by_id(goal_id)
            if not goal:
                return f"Error: Goal '{goal_id}' not found in memory"

            changes = []

            if description:
                old_desc = goal.description
                goal.description = description
                changes.append(f"Updated description")

            if add_constraints:
                for constraint in add_constraints:
                    if constraint not in goal.constraints:
                        goal.constraints.append(constraint)
                changes.append(f"Added {len(add_constraints)} constraint(s)")

            if remove_constraints:
                for constraint in remove_constraints:
                    if constraint in goal.constraints:
                        goal.constraints.remove(constraint)
                changes.append(f"Removed {len(remove_constraints)} constraint(s)")

            if not changes:
                return "No changes specified. Provide description, add_constraints, or remove_constraints."

            memory.metadata.updated_at = datetime.now()

            # Save
            self.storage.save_memory(memory)

            return (
                f"✓ Updated goal {goal_id}:\n"
                f"  {', '.join(changes)}\n"
                f"  Current description: {goal.description}\n"
                f"  Constraints: {len(goal.constraints)}\n"
            )

        except Exception as e:
            return f"Error updating goal: {e}"

    def remove_goal(self, goal_id: str, confirm: bool = False) -> str:
        """
        Remove a goal and all its features from memory.

        Tool for users to delete goals that are no longer needed.

        Args:
            goal_id: ID of the goal to remove (e.g., "G1")
            confirm: Must be True to actually delete (safety check)

        Returns:
            Success or error message
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find goal
            goal = memory.get_goal_by_id(goal_id)
            if not goal:
                return f"Error: Goal '{goal_id}' not found in memory"

            feature_count = len(goal.features)

            if not confirm:
                return (
                    f"⚠️  Goal {goal_id} has {feature_count} feature(s).\n"
                    f"To confirm deletion, call with confirm=True"
                )

            # Remove goal
            memory.goals = [g for g in memory.goals if g.id != goal_id]
            memory.metadata.updated_at = datetime.now()

            # Save
            self.storage.save_memory(memory)

            return (
                f"✓ Removed goal {goal_id}\n"
                f"  Deleted {feature_count} associated feature(s)\n"
            )

        except Exception as e:
            return f"Error removing goal: {e}"

    def add_feature(
        self,
        goal_id: str,
        description: str,
        criteria: Optional[list] = None,
        tests: Optional[list] = None,
        priority: str = "medium",
        assigned_to: Optional[str] = None,
    ) -> str:
        """
        Add a new feature to an existing goal.

        Tool for users to add features as requirements emerge.

        Args:
            goal_id: ID of the goal to add feature to (e.g., "G1")
            description: Clear description of the feature
            criteria: Optional list of pass/fail criteria
            tests: Optional list of test names
            priority: Priority level (high, medium, low)
            assigned_to: Optional assignee (agent type or person name)

        Returns:
            Success message with new feature ID or error
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            from .base_memory import Feature, FeatureStatus

            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find goal
            goal = memory.get_goal_by_id(goal_id)
            if not goal:
                return f"Error: Goal '{goal_id}' not found in memory"

            # Generate next feature ID
            all_features = memory.get_all_features()
            existing_ids = [f.id for f in all_features]
            next_num = len(existing_ids) + 1
            while f"F{next_num}" in existing_ids:
                next_num += 1
            new_feature_id = f"F{next_num}"

            # Validate priority
            if priority not in ["high", "medium", "low"]:
                return f"Error: Invalid priority '{priority}'. Must be high, medium, or low"

            # Create new feature
            new_feature = Feature(
                id=new_feature_id,
                description=description,
                criteria=criteria or [],
                tests=tests or [],
                priority=priority,
                status=FeatureStatus.PENDING,
                assigned_to=assigned_to,
                test_results=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            goal.features.append(new_feature)
            goal.update_status_from_features()
            memory.metadata.updated_at = datetime.now()

            # Save
            self.storage.save_memory(memory)

            return (
                f"✓ Added new feature {new_feature_id} to goal {goal_id}:\n"
                f"  Description: {description}\n"
                f"  Priority: {priority}\n"
                f"  Criteria: {len(criteria or [])}\n"
                f"  Tests: {len(tests or [])}\n"
                + (f"  Assigned to: {assigned_to}\n" if assigned_to else "")
            )

        except Exception as e:
            return f"Error adding feature: {e}"

    def update_feature(
        self,
        feature_id: str,
        description: Optional[str] = None,
        add_criteria: Optional[list] = None,
        remove_criteria: Optional[list] = None,
        add_tests: Optional[list] = None,
        remove_tests: Optional[list] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> str:
        """
        Update an existing feature's properties.

        Tool for users to modify features as requirements evolve.

        Args:
            feature_id: ID of the feature to update (e.g., "F1")
            description: New description (optional)
            add_criteria: List of criteria to add (optional)
            remove_criteria: List of criteria to remove (optional)
            add_tests: List of test names to add (optional)
            remove_tests: List of test names to remove (optional)
            priority: New priority (high, medium, low) (optional)
            assigned_to: New assignee (optional)

        Returns:
            Success or error message
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find feature
            feature = memory.get_feature_by_id(feature_id)
            if not feature:
                return f"Error: Feature '{feature_id}' not found in memory"

            changes = []

            if description:
                feature.description = description
                changes.append(f"Updated description")

            if add_criteria:
                for criterion in add_criteria:
                    if criterion not in feature.criteria:
                        feature.criteria.append(criterion)
                changes.append(f"Added {len(add_criteria)} criterion/criteria")

            if remove_criteria:
                for criterion in remove_criteria:
                    if criterion in feature.criteria:
                        feature.criteria.remove(criterion)
                changes.append(f"Removed {len(remove_criteria)} criterion/criteria")

            if add_tests:
                for test in add_tests:
                    if test not in feature.tests:
                        feature.tests.append(test)
                changes.append(f"Added {len(add_tests)} test(s)")

            if remove_tests:
                for test in remove_tests:
                    if test in feature.tests:
                        feature.tests.remove(test)
                changes.append(f"Removed {len(remove_tests)} test(s)")

            if priority:
                if priority not in ["high", "medium", "low"]:
                    return f"Error: Invalid priority '{priority}'. Must be high, medium, or low"
                feature.priority = priority
                changes.append(f"Changed priority to {priority}")

            if assigned_to is not None:  # Allow empty string to unassign
                feature.assigned_to = assigned_to if assigned_to else None
                changes.append(f"Assigned to: {assigned_to or 'unassigned'}")

            if not changes:
                return "No changes specified. Provide at least one parameter to update."

            feature.updated_at = datetime.now()
            memory.metadata.updated_at = datetime.now()

            # Save
            self.storage.save_memory(memory)

            return (
                f"✓ Updated feature {feature_id}:\n"
                f"  {', '.join(changes)}\n"
                f"  Current description: {feature.description}\n"
                f"  Priority: {feature.priority}\n"
                f"  Criteria: {len(feature.criteria)}\n"
                f"  Tests: {len(feature.tests)}\n"
            )

        except Exception as e:
            return f"Error updating feature: {e}"

    def remove_feature(self, feature_id: str, confirm: bool = False) -> str:
        """
        Remove a feature from its parent goal.

        Tool for users to delete features that are no longer needed.

        Args:
            feature_id: ID of the feature to remove (e.g., "F1")
            confirm: Must be True to actually delete (safety check)

        Returns:
            Success or error message
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find feature and parent goal
            feature = memory.get_feature_by_id(feature_id)
            if not feature:
                return f"Error: Feature '{feature_id}' not found in memory"

            parent_goal = None
            for goal in memory.goals:
                if any(f.id == feature_id for f in goal.features):
                    parent_goal = goal
                    break

            if not confirm:
                return (
                    f"⚠️  Feature {feature_id}: {feature.description}\n"
                    f"To confirm deletion, call with confirm=True"
                )

            # Remove feature
            if parent_goal:
                parent_goal.features = [f for f in parent_goal.features if f.id != feature_id]
                parent_goal.update_status_from_features()

            memory.metadata.updated_at = datetime.now()

            # Save
            self.storage.save_memory(memory)

            return (
                f"✓ Removed feature {feature_id}\n"
                f"  From goal: {parent_goal.id if parent_goal else 'Unknown'}\n"
            )

        except Exception as e:
            return f"Error removing feature: {e}"

    def update_session_description(self, description: str) -> str:
        """
        Update the current session's description.

        Tool for users to update session metadata as focus changes.

        Args:
            description: New session description

        Returns:
            Success or error message
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            old_description = memory.metadata.description
            memory.metadata.description = description
            memory.metadata.updated_at = datetime.now()

            # Save
            self.storage.save_memory(memory)

            return (
                f"✓ Updated session description\n"
                f"  Old: {old_description}\n"
                f"  New: {description}\n"
            )

        except Exception as e:
            return f"Error updating session description: {e}"

    def move_feature(self, feature_id: str, target_goal_id: str) -> str:
        """
        Move a feature from one goal to another.

        Tool for users to reorganize features when goal structure changes.

        Args:
            feature_id: ID of the feature to move (e.g., "F1")
            target_goal_id: ID of the goal to move it to (e.g., "G2")

        Returns:
            Success or error message
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Find feature and source goal
            feature = memory.get_feature_by_id(feature_id)
            if not feature:
                return f"Error: Feature '{feature_id}' not found in memory"

            source_goal = None
            for goal in memory.goals:
                if any(f.id == feature_id for f in goal.features):
                    source_goal = goal
                    break

            # Find target goal
            target_goal = memory.get_goal_by_id(target_goal_id)
            if not target_goal:
                return f"Error: Target goal '{target_goal_id}' not found in memory"

            if source_goal and source_goal.id == target_goal_id:
                return f"Error: Feature {feature_id} is already in goal {target_goal_id}"

            # Move feature
            if source_goal:
                source_goal.features = [f for f in source_goal.features if f.id != feature_id]
                source_goal.update_status_from_features()

            target_goal.features.append(feature)
            target_goal.update_status_from_features()

            memory.metadata.updated_at = datetime.now()

            # Save
            self.storage.save_memory(memory)

            return (
                f"✓ Moved feature {feature_id}\n"
                f"  From: {source_goal.id if source_goal else 'Unknown'}\n"
                f"  To: {target_goal_id}\n"
            )

        except Exception as e:
            return f"Error moving feature: {e}"

    def get_project_context(self) -> str:
        """
        Get the cached project context.

        Tool for agents to view the current project structure without re-scanning.

        Returns:
            Formatted project context information
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Check if project context exists in state
            if not memory.state or "project_context" not in memory.state:
                return (
                    "Project context not yet scanned.\n"
                    "It will be automatically built on the first agent call.\n"
                    "Use builtin.rescan_project_context to force a scan now."
                )

            ctx = memory.state["project_context"]
            lines = []
            lines.append("=" * 70)
            lines.append("PROJECT CONTEXT")
            lines.append("=" * 70)
            lines.append("")
            lines.append(f"Working Directory: {ctx['working_directory']}")
            lines.append(f"Project Type: {ctx['project_type']}")
            lines.append("")

            if ctx["key_folders"]:
                lines.append("Key Folders:")
                for folder in ctx["key_folders"]:
                    lines.append(f"  • {folder['name']}/ ({folder['file_count']} files)")
                lines.append("")

            if ctx["important_files"]:
                lines.append(f"Important Files: {', '.join(ctx['important_files'])}")
                lines.append("")

            lines.append("=" * 70)
            return "\n".join(lines)

        except Exception as e:
            return f"Error getting project context: {e}"

    def rescan_project_context(self) -> str:
        """
        Force a rescan of the project structure.

        Tool for agents to update the project context cache when the
        project structure has changed during a session.

        Returns:
            Confirmation message with updated context
        """
        if not self.current_session_id or not self.current_domain:
            return "Error: No active memory session. Memory tools not available."

        try:
            # Load memory
            memory = self.storage.load_memory(self.current_session_id, self.current_domain)
            if not memory:
                return f"Error: Could not load memory for session {self.current_session_id}"

            # Import and rebuild project context
            from .boot_ritual import BootRitual
            new_context = BootRitual._build_project_context()

            # Update memory state
            if memory.state is None:
                memory.state = {}
            memory.state["project_context"] = new_context
            memory.metadata.updated_at = datetime.now()

            # Save
            self.storage.save_memory(memory)

            # Format response showing what was found
            lines = []
            lines.append("✓ Project context rescanned successfully")
            lines.append("")
            lines.append(f"Working Directory: {new_context['working_directory']}")
            lines.append(f"Project Type: {new_context['project_type']}")
            lines.append("")

            if new_context["key_folders"]:
                lines.append(f"Found {len(new_context['key_folders'])} key folders:")
                for folder in new_context["key_folders"]:
                    lines.append(f"  • {folder['name']}/ ({folder['file_count']} files)")

            if new_context["important_files"]:
                lines.append("")
                lines.append(f"Important files: {', '.join(new_context['important_files'])}")

            return "\n".join(lines)

        except Exception as e:
            return f"Error rescanning project context: {e}"
