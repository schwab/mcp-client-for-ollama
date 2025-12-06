"""
Task management for agent delegation system.

This module defines the Task and TaskStatus classes used to represent
and track subtasks in the delegation workflow.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class TaskStatus(Enum):
    """Status of a task in the delegation workflow."""

    PENDING = "pending"      # Task created but not yet started
    RUNNING = "running"      # Task currently executing
    COMPLETED = "completed"  # Task finished successfully
    FAILED = "failed"        # Task encountered an error
    BLOCKED = "blocked"      # Task waiting on dependencies


@dataclass
class Task:
    """
    Represents a subtask in the agent delegation workflow.

    Each task is a focused piece of work assigned to a specialized agent.
    Tasks can have dependencies on other tasks and maintain their own
    isolated execution context.

    Attributes:
        id: Unique identifier for this task
        description: Clear description of what this task should accomplish
        agent_type: Type of agent to execute this task (e.g., "READER", "CODER")
        status: Current execution status
        parent_id: ID of parent task (for hierarchical task structures)
        dependencies: List of task IDs that must complete before this task
        context: Isolated message history for this task's execution
        tools: List of tool names available to this task
        result: Output from task execution (set when status=COMPLETED)
        error: Error message (set when status=FAILED)
        created_at: Timestamp when task was created
        started_at: Timestamp when task execution began
        completed_at: Timestamp when task finished (success or failure)
        assigned_model_url: URL of the model endpoint executing this task
    """

    id: str
    description: str
    agent_type: str
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

    # Execution context
    context: List[Dict[str, str]] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)

    # Results
    result: Optional[str] = None
    error: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_model_url: Optional[str] = None

    def can_execute(self, completed_task_ids: set) -> bool:
        """
        Check if this task is ready to execute.

        A task can execute if all its dependencies have completed successfully.

        Args:
            completed_task_ids: Set of task IDs that have completed

        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        return all(dep_id in completed_task_ids for dep_id in self.dependencies)

    def get_dependency_results(self, tasks: Dict[str, 'Task']) -> List[str]:
        """
        Get results from dependency tasks for context sharing.

        This implements the "Shared Read" strategy where agents can access
        the results of tasks they depend on.

        Args:
            tasks: Dictionary mapping task IDs to Task objects

        Returns:
            List of formatted strings containing dependency results
        """
        results = []
        for dep_id in self.dependencies:
            if dep_id in tasks and tasks[dep_id].result:
                dep_task = tasks[dep_id]
                # Include the dependency task's description for context
                results.append(
                    f"[Result from task '{dep_id}': {dep_task.description}]\n"
                    f"{dep_task.result}\n"
                )
        return results

    def mark_started(self, model_url: Optional[str] = None):
        """Mark task as running and record start time."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        if model_url:
            self.assigned_model_url = model_url

    def mark_completed(self, result: str):
        """Mark task as completed successfully."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()

    def mark_failed(self, error: str):
        """Mark task as failed with error message."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()

    def mark_blocked(self):
        """Mark task as blocked (waiting on failed dependencies)."""
        self.status = TaskStatus.BLOCKED

    @property
    def duration(self) -> Optional[float]:
        """
        Calculate task execution duration in seconds.

        Returns:
            Duration in seconds if task has started, None otherwise
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary for serialization.

        Returns:
            Dictionary representation of the task
        """
        return {
            "id": self.id,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "assigned_model_url": self.assigned_model_url,
            "duration": self.duration,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Task(id={self.id}, agent_type={self.agent_type}, "
            f"status={self.status.value}, dependencies={self.dependencies})"
        )
