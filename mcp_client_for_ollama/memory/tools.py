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

            # Find feature
            feature = memory.get_feature_by_id(feature_id)
            if not feature:
                return f"Error: Feature '{feature_id}' not found"

            from .boot_ritual import BootRitual
            return BootRitual.format_feature_context(feature)

        except Exception as e:
            return f"Error getting feature details: {e}"
