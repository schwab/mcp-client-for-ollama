"""Tests for parallel task execution in delegation system."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from mcp_client_for_ollama.agents.delegation_client import DelegationClient
from mcp_client_for_ollama.agents.task import Task, TaskStatus


class TestParallelExecution:
    """Tests for parallel task execution functionality."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Create a mocked MCPClient."""
        mock = MagicMock()
        mock.host = "http://localhost:11434"
        mock.model_manager = MagicMock()
        mock.model_manager.current_model = "test-model"
        mock.model_manager.get_current_model = MagicMock(return_value="test-model")
        return mock

    @pytest.fixture
    def parallel_config(self):
        """Configuration for parallel execution."""
        return {
            'execution_mode': 'parallel',
            'max_parallel_tasks': 3,
            'model_pool': [{
                'url': 'http://localhost:11434',
                'model': 'test-model',
                'max_concurrent': 3
            }],
            'task_timeout': 30
        }

    @pytest.fixture
    def sequential_config(self):
        """Configuration for sequential execution."""
        return {
            'execution_mode': 'sequential',
            'max_parallel_tasks': 1,
            'model_pool': [{
                'url': 'http://localhost:11434',
                'model': 'test-model',
                'max_concurrent': 1
            }],
            'task_timeout': 30
        }

    @pytest.mark.asyncio
    async def test_parallel_config_creates_semaphore(self, mock_mcp_client, parallel_config):
        """Test that parallel config creates semaphore with correct limit."""
        with patch('mcp_client_for_ollama.agents.delegation_client.AgentConfig.load_all_definitions'):
            client = DelegationClient(mock_mcp_client, parallel_config)

            assert hasattr(client, '_parallelism_semaphore')
            assert client._parallelism_semaphore._value == 3

    @pytest.mark.asyncio
    async def test_execute_wave_respects_concurrency_limit(self, mock_mcp_client, parallel_config):
        """Test that execute_wave respects the semaphore concurrency limit."""
        with patch('mcp_client_for_ollama.agents.delegation_client.AgentConfig.load_all_definitions'):
            client = DelegationClient(mock_mcp_client, parallel_config)

            # Create test tasks
            tasks = [
                Task(id=f"task_{i}", description=f"Task {i}", agent_type="TEST")
                for i in range(5)
            ]

            # Track concurrent executions
            max_concurrent = 0
            current_concurrent = 0
            concurrent_lock = asyncio.Lock()

            async def mock_execute(task):
                nonlocal max_concurrent, current_concurrent

                async with concurrent_lock:
                    current_concurrent += 1
                    max_concurrent = max(max_concurrent, current_concurrent)

                # Simulate work
                await asyncio.sleep(0.05)

                async with concurrent_lock:
                    current_concurrent -= 1

                task.mark_completed("Done")

            # Patch execute_single_task
            client.execute_single_task = mock_execute

            # Execute wave
            await client._execute_wave(tasks)

            # Should not exceed semaphore limit of 3
            assert max_concurrent <= 3
            assert max_concurrent > 1  # Should have some parallelism

    @pytest.mark.asyncio
    async def test_parallel_execution_independent_tasks(self, mock_mcp_client, parallel_config):
        """Test parallel execution of independent tasks."""
        with patch('mcp_client_for_ollama.agents.delegation_client.AgentConfig.load_all_definitions'):
            client = DelegationClient(mock_mcp_client, parallel_config)

            # Create independent tasks (no dependencies)
            tasks = [
                Task(id="task_1", description="Task 1", agent_type="TEST"),
                Task(id="task_2", description="Task 2", agent_type="TEST"),
                Task(id="task_3", description="Task 3", agent_type="TEST"),
            ]

            execution_order = []

            async def mock_execute(task):
                execution_order.append(task.id)
                await asyncio.sleep(0.01)
                task.mark_completed(f"Result from {task.id}")

            client.execute_single_task = mock_execute

            # Execute in parallel
            results = await client.execute_tasks_parallel(tasks)

            # All tasks should complete
            assert len([t for t in results if t.status == TaskStatus.COMPLETED]) == 3
            # All 3 tasks should execute (order may vary due to parallelism)
            assert len(execution_order) == 3

    @pytest.mark.asyncio
    async def test_parallel_execution_with_dependencies(self, mock_mcp_client, parallel_config):
        """Test that parallel execution respects task dependencies."""
        with patch('mcp_client_for_ollama.agents.delegation_client.AgentConfig.load_all_definitions'):
            client = DelegationClient(mock_mcp_client, parallel_config)

            # Create tasks with dependencies
            task_1 = Task(id="task_1", description="First", agent_type="TEST")
            task_2 = Task(id="task_2", description="Second", agent_type="TEST", dependencies=["task_1"])
            task_3 = Task(id="task_3", description="Third", agent_type="TEST", dependencies=["task_1"])
            task_4 = Task(id="task_4", description="Fourth", agent_type="TEST", dependencies=["task_2", "task_3"])

            tasks = [task_1, task_2, task_3, task_4]

            execution_order = []

            async def mock_execute(task):
                execution_order.append(task.id)
                await asyncio.sleep(0.01)
                task.mark_completed(f"Result from {task.id}")

            client.execute_single_task = mock_execute

            # Execute with dependencies
            results = await client.execute_tasks_parallel(tasks)

            # All tasks should complete
            assert len([t for t in results if t.status == TaskStatus.COMPLETED]) == 4

            # task_1 must execute before task_2 and task_3
            assert execution_order.index("task_1") < execution_order.index("task_2")
            assert execution_order.index("task_1") < execution_order.index("task_3")

            # task_2 and task_3 must execute before task_4
            assert execution_order.index("task_2") < execution_order.index("task_4")
            assert execution_order.index("task_3") < execution_order.index("task_4")

    @pytest.mark.asyncio
    async def test_parallel_execution_wave_grouping(self, mock_mcp_client, parallel_config):
        """Test that tasks are grouped into waves correctly."""
        with patch('mcp_client_for_ollama.agents.delegation_client.AgentConfig.load_all_definitions'):
            client = DelegationClient(mock_mcp_client, parallel_config)

            # Wave 1: task_1, task_2 (independent)
            # Wave 2: task_3, task_4 (depend on wave 1)
            task_1 = Task(id="task_1", description="Wave 1 Task 1", agent_type="TEST")
            task_2 = Task(id="task_2", description="Wave 1 Task 2", agent_type="TEST")
            task_3 = Task(id="task_3", description="Wave 2 Task 1", agent_type="TEST", dependencies=["task_1"])
            task_4 = Task(id="task_4", description="Wave 2 Task 2", agent_type="TEST", dependencies=["task_2"])

            tasks = [task_1, task_2, task_3, task_4]

            wave_execution = {}

            async def mock_execute(task):
                # Track which wave each task executes in
                current_time = asyncio.get_event_loop().time()
                wave_execution[task.id] = current_time
                await asyncio.sleep(0.05)
                task.mark_completed(f"Result from {task.id}")

            client.execute_single_task = mock_execute

            # Execute
            await client.execute_tasks_parallel(tasks)

            # task_1 and task_2 should start around the same time (wave 1)
            time_diff_wave1 = abs(wave_execution["task_1"] - wave_execution["task_2"])
            assert time_diff_wave1 < 0.02  # Started within 20ms

            # task_3 and task_4 should start after wave 1 completes
            assert wave_execution["task_3"] > wave_execution["task_1"] + 0.03
            assert wave_execution["task_4"] > wave_execution["task_2"] + 0.03

            # task_3 and task_4 should start around the same time (wave 2)
            time_diff_wave2 = abs(wave_execution["task_3"] - wave_execution["task_4"])
            assert time_diff_wave2 < 0.02

    @pytest.mark.asyncio
    async def test_parallel_execution_handles_failures(self, mock_mcp_client, parallel_config):
        """Test that parallel execution handles task failures correctly."""
        with patch('mcp_client_for_ollama.agents.delegation_client.AgentConfig.load_all_definitions'):
            client = DelegationClient(mock_mcp_client, parallel_config)

            task_1 = Task(id="task_1", description="Successful", agent_type="TEST")
            task_2 = Task(id="task_2", description="Will fail", agent_type="TEST")
            task_3 = Task(id="task_3", description="Depends on failure", agent_type="TEST", dependencies=["task_2"])

            tasks = [task_1, task_2, task_3]

            async def mock_execute(task):
                await asyncio.sleep(0.01)
                if task.id == "task_2":
                    raise Exception("Simulated failure")
                task.mark_completed(f"Result from {task.id}")

            client.execute_single_task = mock_execute

            # Execute
            results = await client.execute_tasks_parallel(tasks)

            # task_1 should succeed
            assert task_1.status == TaskStatus.COMPLETED

            # task_2 should fail
            assert task_2.status == TaskStatus.FAILED

            # task_3 should be blocked
            assert task_3.status == TaskStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_execution_mode_selection(self, mock_mcp_client, parallel_config, sequential_config):
        """Test that execution mode is selected correctly from config."""
        with patch('mcp_client_for_ollama.agents.delegation_client.AgentConfig.load_all_definitions'):
            # Test parallel mode
            client_parallel = DelegationClient(mock_mcp_client, parallel_config)
            assert client_parallel.config['execution_mode'] == 'parallel'

            # Test sequential mode
            client_sequential = DelegationClient(mock_mcp_client, sequential_config)
            assert client_sequential.config['execution_mode'] == 'sequential'

    @pytest.mark.asyncio
    async def test_default_max_parallel_tasks(self, mock_mcp_client):
        """Test that default max_parallel_tasks is 3."""
        config = {
            'execution_mode': 'parallel',
            'model_pool': [{'url': 'http://localhost:11434', 'model': 'test', 'max_concurrent': 1}]
        }

        with patch('mcp_client_for_ollama.agents.delegation_client.AgentConfig.load_all_definitions'):
            client = DelegationClient(mock_mcp_client, config)

            # Default should be 3
            assert client._parallelism_semaphore._value == 3
