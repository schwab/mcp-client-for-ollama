"""Unit tests for Task and TaskStatus classes."""

import pytest
from datetime import datetime
from time import sleep
from mcp_client_for_ollama.agents.task import Task, TaskStatus


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self):
        """Test that TaskStatus enum has correct values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.BLOCKED.value == "blocked"

    def test_task_status_count(self):
        """Test that all expected statuses exist."""
        assert len(TaskStatus) == 5


class TestTask:
    """Tests for Task class."""

    @pytest.fixture
    def basic_task(self):
        """Create a basic task for testing."""
        return Task(
            id="task_1",
            description="Test task",
            agent_type="READER"
        )

    @pytest.fixture
    def task_with_dependencies(self):
        """Create a task with dependencies."""
        return Task(
            id="task_2",
            description="Dependent task",
            agent_type="CODER",
            dependencies=["task_1"]
        )

    def test_task_creation_defaults(self, basic_task):
        """Test that task is created with correct defaults."""
        assert basic_task.id == "task_1"
        assert basic_task.description == "Test task"
        assert basic_task.agent_type == "READER"
        assert basic_task.status == TaskStatus.PENDING
        assert basic_task.parent_id is None
        assert basic_task.dependencies == []
        assert basic_task.context == []
        assert basic_task.tools == []
        assert basic_task.result is None
        assert basic_task.error is None
        assert isinstance(basic_task.created_at, datetime)
        assert basic_task.started_at is None
        assert basic_task.completed_at is None
        assert basic_task.assigned_model_url is None

    def test_task_creation_with_dependencies(self, task_with_dependencies):
        """Test task creation with dependencies."""
        assert task_with_dependencies.dependencies == ["task_1"]
        assert task_with_dependencies.status == TaskStatus.PENDING

    def test_can_execute_no_dependencies(self, basic_task):
        """Test can_execute returns True when task has no dependencies."""
        assert basic_task.can_execute(set()) is True
        assert basic_task.can_execute({"other_task"}) is True

    def test_can_execute_with_satisfied_dependencies(self, task_with_dependencies):
        """Test can_execute returns True when all dependencies are completed."""
        completed_tasks = {"task_1"}
        assert task_with_dependencies.can_execute(completed_tasks) is True

    def test_can_execute_with_unsatisfied_dependencies(self, task_with_dependencies):
        """Test can_execute returns False when dependencies are not completed."""
        completed_tasks = set()
        assert task_with_dependencies.can_execute(completed_tasks) is False

    def test_can_execute_with_multiple_dependencies(self):
        """Test can_execute with multiple dependencies."""
        task = Task(
            id="task_3",
            description="Multi-dep task",
            agent_type="EXECUTOR",
            dependencies=["task_1", "task_2"]
        )

        # No dependencies completed
        assert task.can_execute(set()) is False

        # Only one dependency completed
        assert task.can_execute({"task_1"}) is False

        # All dependencies completed
        assert task.can_execute({"task_1", "task_2"}) is True

        # Extra completed tasks don't affect result
        assert task.can_execute({"task_1", "task_2", "task_4"}) is True

    def test_get_dependency_results_no_dependencies(self, basic_task):
        """Test get_dependency_results returns empty list when no dependencies."""
        results = basic_task.get_dependency_results({})
        assert results == []

    def test_get_dependency_results_with_completed_dependencies(self):
        """Test get_dependency_results returns formatted results."""
        # Create dependency task with result
        dep_task = Task(
            id="task_1",
            description="Read config file",
            agent_type="READER"
        )
        dep_task.mark_completed("Config content: key=value")

        # Create dependent task
        task = Task(
            id="task_2",
            description="Process config",
            agent_type="CODER",
            dependencies=["task_1"]
        )

        # Get dependency results
        tasks = {"task_1": dep_task}
        results = task.get_dependency_results(tasks)

        assert len(results) == 1
        assert "task_1" in results[0]
        assert "Read config file" in results[0]
        assert "Config content: key=value" in results[0]

    def test_get_dependency_results_with_incomplete_dependencies(self):
        """Test get_dependency_results ignores dependencies without results."""
        # Create dependency task without result
        dep_task = Task(
            id="task_1",
            description="Read file",
            agent_type="READER"
        )

        # Create dependent task
        task = Task(
            id="task_2",
            description="Process file",
            agent_type="CODER",
            dependencies=["task_1"]
        )

        tasks = {"task_1": dep_task}
        results = task.get_dependency_results(tasks)

        assert results == []

    def test_get_dependency_results_with_multiple_dependencies(self):
        """Test get_dependency_results with multiple completed dependencies."""
        # Create multiple dependency tasks
        dep1 = Task(id="task_1", description="Task 1", agent_type="READER")
        dep1.mark_completed("Result 1")

        dep2 = Task(id="task_2", description="Task 2", agent_type="EXECUTOR")
        dep2.mark_completed("Result 2")

        # Create dependent task
        task = Task(
            id="task_3",
            description="Combine results",
            agent_type="RESEARCHER",
            dependencies=["task_1", "task_2"]
        )

        tasks = {"task_1": dep1, "task_2": dep2}
        results = task.get_dependency_results(tasks)

        assert len(results) == 2
        assert any("Result 1" in r for r in results)
        assert any("Result 2" in r for r in results)

    def test_mark_started(self, basic_task):
        """Test mark_started updates status and timestamp."""
        model_url = "http://localhost:11434"
        basic_task.mark_started(model_url)

        assert basic_task.status == TaskStatus.RUNNING
        assert isinstance(basic_task.started_at, datetime)
        assert basic_task.assigned_model_url == model_url

    def test_mark_started_without_model_url(self, basic_task):
        """Test mark_started works without model_url."""
        basic_task.mark_started()

        assert basic_task.status == TaskStatus.RUNNING
        assert isinstance(basic_task.started_at, datetime)
        assert basic_task.assigned_model_url is None

    def test_mark_completed(self, basic_task):
        """Test mark_completed updates status, result, and timestamp."""
        result = "Task completed successfully"
        basic_task.mark_completed(result)

        assert basic_task.status == TaskStatus.COMPLETED
        assert basic_task.result == result
        assert isinstance(basic_task.completed_at, datetime)

    def test_mark_failed(self, basic_task):
        """Test mark_failed updates status, error, and timestamp."""
        error = "Task failed: File not found"
        basic_task.mark_failed(error)

        assert basic_task.status == TaskStatus.FAILED
        assert basic_task.error == error
        assert isinstance(basic_task.completed_at, datetime)

    def test_mark_blocked(self, basic_task):
        """Test mark_blocked updates status."""
        basic_task.mark_blocked()

        assert basic_task.status == TaskStatus.BLOCKED
        # completed_at should not be set for blocked tasks
        assert basic_task.completed_at is None

    def test_duration_not_started(self, basic_task):
        """Test duration returns None when task hasn't started."""
        assert basic_task.duration is None

    def test_duration_started_not_completed(self, basic_task):
        """Test duration returns None when task is running but not completed."""
        basic_task.mark_started()
        assert basic_task.duration is None

    def test_duration_completed(self, basic_task):
        """Test duration calculation for completed task."""
        basic_task.mark_started()
        sleep(0.1)  # Small delay to ensure measurable duration
        basic_task.mark_completed("Done")

        duration = basic_task.duration
        assert duration is not None
        assert duration >= 0.1
        assert duration < 1.0  # Should be less than 1 second

    def test_duration_failed(self, basic_task):
        """Test duration calculation for failed task."""
        basic_task.mark_started()
        sleep(0.05)
        basic_task.mark_failed("Error")

        duration = basic_task.duration
        assert duration is not None
        assert duration >= 0.05

    def test_to_dict(self, basic_task):
        """Test to_dict serialization."""
        basic_task.mark_started("http://localhost:11434")
        basic_task.mark_completed("Success")

        task_dict = basic_task.to_dict()

        assert task_dict["id"] == "task_1"
        assert task_dict["description"] == "Test task"
        assert task_dict["agent_type"] == "READER"
        assert task_dict["status"] == "completed"
        assert task_dict["parent_id"] is None
        assert task_dict["dependencies"] == []
        assert task_dict["result"] == "Success"
        assert task_dict["error"] is None
        assert task_dict["assigned_model_url"] == "http://localhost:11434"
        assert isinstance(task_dict["created_at"], str)
        assert isinstance(task_dict["started_at"], str)
        assert isinstance(task_dict["completed_at"], str)
        assert isinstance(task_dict["duration"], float)

    def test_to_dict_with_dependencies(self, task_with_dependencies):
        """Test to_dict includes dependencies."""
        task_dict = task_with_dependencies.to_dict()
        assert task_dict["dependencies"] == ["task_1"]

    def test_to_dict_failed_task(self, basic_task):
        """Test to_dict for failed task."""
        basic_task.mark_started()
        basic_task.mark_failed("Error occurred")

        task_dict = basic_task.to_dict()

        assert task_dict["status"] == "failed"
        assert task_dict["error"] == "Error occurred"
        assert task_dict["result"] is None

    def test_repr(self, basic_task):
        """Test string representation."""
        repr_str = repr(basic_task)

        assert "Task(" in repr_str
        assert "id=task_1" in repr_str
        assert "agent_type=READER" in repr_str
        assert "status=pending" in repr_str
        assert "dependencies=[]" in repr_str

    def test_repr_with_dependencies(self, task_with_dependencies):
        """Test string representation with dependencies."""
        repr_str = repr(task_with_dependencies)

        assert "task_2" in repr_str
        assert "CODER" in repr_str
        assert "['task_1']" in repr_str

    def test_task_lifecycle_complete_flow(self):
        """Test complete task lifecycle from creation to completion."""
        task = Task(
            id="lifecycle_task",
            description="Complete workflow test",
            agent_type="EXECUTOR",
            dependencies=[]
        )

        # Initial state
        assert task.status == TaskStatus.PENDING
        assert task.can_execute(set()) is True

        # Start task
        task.mark_started("http://localhost:11434")
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

        # Complete task
        task.mark_completed("All done!")
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "All done!"
        assert task.completed_at is not None
        assert task.duration is not None

    def test_task_lifecycle_failure_flow(self):
        """Test task lifecycle with failure."""
        task = Task(
            id="failure_task",
            description="Test failure",
            agent_type="CODER"
        )

        # Start task
        task.mark_started()
        assert task.status == TaskStatus.RUNNING

        # Fail task
        task.mark_failed("Compilation error")
        assert task.status == TaskStatus.FAILED
        assert task.error == "Compilation error"
        assert task.result is None

    def test_task_lifecycle_blocked_flow(self):
        """Test task lifecycle with blocking."""
        task = Task(
            id="blocked_task",
            description="Test blocking",
            agent_type="READER",
            dependencies=["missing_task"]
        )

        # Task cannot execute
        assert task.can_execute(set()) is False

        # Mark as blocked
        task.mark_blocked()
        assert task.status == TaskStatus.BLOCKED
        assert task.completed_at is None
