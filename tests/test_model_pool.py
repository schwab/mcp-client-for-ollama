"""Unit tests for ModelPool and ModelEndpoint classes."""

import pytest
import asyncio
from mcp_client_for_ollama.agents.model_pool import ModelEndpoint, ModelPool


class TestModelEndpoint:
    """Tests for ModelEndpoint class."""

    def test_endpoint_creation_defaults(self):
        """Test creating endpoint with default values."""
        endpoint = ModelEndpoint(
            url="http://localhost:11434",
            model="qwen2.5:7b"
        )

        assert endpoint.url == "http://localhost:11434"
        assert endpoint.model == "qwen2.5:7b"
        assert endpoint.max_concurrent == 1
        assert endpoint.current_load == 0
        assert endpoint.total_tasks_executed == 0
        assert endpoint.total_failures == 0

    def test_endpoint_creation_with_max_concurrent(self):
        """Test creating endpoint with custom max_concurrent."""
        endpoint = ModelEndpoint(
            url="http://server:11434",
            model="llama3:8b",
            max_concurrent=5
        )

        assert endpoint.max_concurrent == 5
        assert endpoint.is_available is True

    def test_is_available_when_under_capacity(self):
        """Test is_available returns True when under capacity."""
        endpoint = ModelEndpoint(
            url="http://localhost:11434",
            model="test",
            max_concurrent=3
        )

        endpoint.current_load = 0
        assert endpoint.is_available is True

        endpoint.current_load = 2
        assert endpoint.is_available is True

    def test_is_available_at_capacity(self):
        """Test is_available returns False at capacity."""
        endpoint = ModelEndpoint(
            url="http://localhost:11434",
            model="test",
            max_concurrent=2
        )

        endpoint.current_load = 2
        assert endpoint.is_available is False

    def test_is_available_over_capacity(self):
        """Test is_available returns False when over capacity."""
        endpoint = ModelEndpoint(
            url="http://localhost:11434",
            model="test",
            max_concurrent=2
        )

        endpoint.current_load = 3
        assert endpoint.is_available is False

    def test_utilization_zero_load(self):
        """Test utilization calculation with zero load."""
        endpoint = ModelEndpoint(
            url="http://localhost:11434",
            model="test",
            max_concurrent=4
        )

        assert endpoint.utilization == 0.0

    def test_utilization_partial_load(self):
        """Test utilization calculation with partial load."""
        endpoint = ModelEndpoint(
            url="http://localhost:11434",
            model="test",
            max_concurrent=4
        )

        endpoint.current_load = 2
        assert endpoint.utilization == 50.0

    def test_utilization_full_load(self):
        """Test utilization calculation at full capacity."""
        endpoint = ModelEndpoint(
            url="http://localhost:11434",
            model="test",
            max_concurrent=3
        )

        endpoint.current_load = 3
        assert endpoint.utilization == 100.0

    def test_utilization_zero_max_concurrent(self):
        """Test utilization returns 100% when max_concurrent is 0."""
        endpoint = ModelEndpoint(
            url="http://localhost:11434",
            model="test",
            max_concurrent=0
        )

        assert endpoint.utilization == 100.0

    def test_repr(self):
        """Test string representation."""
        endpoint = ModelEndpoint(
            url="http://localhost:11434",
            model="qwen2.5:7b",
            max_concurrent=3
        )
        endpoint.current_load = 2

        repr_str = repr(endpoint)

        assert "ModelEndpoint(" in repr_str
        assert "url=http://localhost:11434" in repr_str
        assert "model=qwen2.5:7b" in repr_str
        assert "load=2/3" in repr_str


class TestModelPool:
    """Tests for ModelPool class."""

    @pytest.fixture
    def single_endpoint_config(self):
        """Configuration for a pool with single endpoint."""
        return [
            {
                "url": "http://localhost:11434",
                "model": "qwen2.5:7b",
                "max_concurrent": 2
            }
        ]

    @pytest.fixture
    def multi_endpoint_config(self):
        """Configuration for a pool with multiple endpoints."""
        return [
            {
                "url": "http://localhost:11434",
                "model": "qwen2.5:7b",
                "max_concurrent": 2
            },
            {
                "url": "http://server2:11434",
                "model": "llama3:8b",
                "max_concurrent": 3
            },
            {
                "url": "http://server3:11434",
                "model": "qwen2.5:14b",
                "max_concurrent": 1
            }
        ]

    def test_pool_initialization_single_endpoint(self, single_endpoint_config):
        """Test pool initialization with single endpoint."""
        pool = ModelPool(single_endpoint_config)

        assert len(pool.endpoints) == 1
        assert pool.endpoints[0].url == "http://localhost:11434"
        assert pool.endpoints[0].model == "qwen2.5:7b"
        assert pool.endpoints[0].max_concurrent == 2

    def test_pool_initialization_multi_endpoint(self, multi_endpoint_config):
        """Test pool initialization with multiple endpoints."""
        pool = ModelPool(multi_endpoint_config)

        assert len(pool.endpoints) == 3
        assert pool.endpoints[0].max_concurrent == 2
        assert pool.endpoints[1].max_concurrent == 3
        assert pool.endpoints[2].max_concurrent == 1

    def test_pool_initialization_default_max_concurrent(self):
        """Test that default max_concurrent is 1 if not specified."""
        config = [{"url": "http://localhost:11434", "model": "test"}]
        pool = ModelPool(config)

        assert pool.endpoints[0].max_concurrent == 1

    @pytest.mark.asyncio
    async def test_acquire_from_empty_pool(self, single_endpoint_config):
        """Test acquiring endpoint from pool with available capacity."""
        pool = ModelPool(single_endpoint_config)

        endpoint = await pool.acquire()

        assert endpoint is not None
        assert endpoint.url == "http://localhost:11434"
        assert endpoint.current_load == 1

    @pytest.mark.asyncio
    async def test_acquire_returns_none_when_full(self, single_endpoint_config):
        """Test acquire returns None when all endpoints are at capacity."""
        pool = ModelPool(single_endpoint_config)

        # Acquire all available capacity
        ep1 = await pool.acquire()
        ep2 = await pool.acquire()

        assert ep1 is not None
        assert ep2 is not None

        # Try to acquire when full
        ep3 = await pool.acquire()
        assert ep3 is None

    @pytest.mark.asyncio
    async def test_acquire_uses_least_loaded_strategy(self, multi_endpoint_config):
        """Test that acquire uses least-loaded strategy."""
        pool = ModelPool(multi_endpoint_config)

        # First acquisition should go to endpoint with load 0
        ep1 = await pool.acquire()
        assert ep1 is not None

        # Manually set different loads
        pool.endpoints[0].current_load = 2  # Server 1
        pool.endpoints[1].current_load = 1  # Server 2 (least loaded)
        pool.endpoints[2].current_load = 1  # Server 3

        # Next acquisition should go to server 2 (least loaded with capacity)
        ep2 = await pool.acquire()
        assert ep2 is not None
        # Should pick one of the endpoints with load 1
        assert ep2.current_load == 2  # Now incremented

    @pytest.mark.asyncio
    async def test_release_decrements_load(self, single_endpoint_config):
        """Test that release decrements current load."""
        pool = ModelPool(single_endpoint_config)

        endpoint = await pool.acquire()
        assert endpoint.current_load == 1

        await pool.release(endpoint, success=True)
        assert endpoint.current_load == 0

    @pytest.mark.asyncio
    async def test_release_updates_metrics_success(self, single_endpoint_config):
        """Test that release updates metrics for successful task."""
        pool = ModelPool(single_endpoint_config)

        endpoint = await pool.acquire()
        initial_tasks = endpoint.total_tasks_executed
        initial_failures = endpoint.total_failures

        await pool.release(endpoint, success=True)

        assert endpoint.total_tasks_executed == initial_tasks + 1
        assert endpoint.total_failures == initial_failures

    @pytest.mark.asyncio
    async def test_release_updates_metrics_failure(self, single_endpoint_config):
        """Test that release updates metrics for failed task."""
        pool = ModelPool(single_endpoint_config)

        endpoint = await pool.acquire()
        initial_tasks = endpoint.total_tasks_executed
        initial_failures = endpoint.total_failures

        await pool.release(endpoint, success=False)

        assert endpoint.total_tasks_executed == initial_tasks + 1
        assert endpoint.total_failures == initial_failures + 1

    @pytest.mark.asyncio
    async def test_wait_for_available_immediate(self, single_endpoint_config):
        """Test wait_for_available returns immediately when capacity available."""
        pool = ModelPool(single_endpoint_config)

        endpoint = await pool.wait_for_available(timeout=5.0)

        assert endpoint is not None
        assert endpoint.current_load == 1

    @pytest.mark.asyncio
    async def test_wait_for_available_after_release(self, single_endpoint_config):
        """Test wait_for_available waits and acquires after release."""
        pool = ModelPool(single_endpoint_config)

        # Fill the pool
        ep1 = await pool.acquire()
        ep2 = await pool.acquire()

        async def release_after_delay():
            """Release an endpoint after a short delay."""
            await asyncio.sleep(0.1)
            await pool.release(ep1)

        # Start release task
        release_task = asyncio.create_task(release_after_delay())

        # This should wait and then acquire
        endpoint = await pool.wait_for_available(timeout=2.0)

        assert endpoint is not None
        await release_task

    @pytest.mark.asyncio
    async def test_wait_for_available_timeout(self, single_endpoint_config):
        """Test wait_for_available raises TimeoutError on timeout."""
        pool = ModelPool(single_endpoint_config)

        # Fill the pool
        await pool.acquire()
        await pool.acquire()

        # Try to wait with short timeout (no release)
        with pytest.raises(TimeoutError) as exc_info:
            await pool.wait_for_available(timeout=0.1)

        assert "No model endpoint became available" in str(exc_info.value)
        assert "0.1s" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_wait_for_available_empty_pool(self):
        """Test wait_for_available raises ValueError for empty pool."""
        pool = ModelPool([])

        with pytest.raises(ValueError) as exc_info:
            await pool.wait_for_available()

        assert "no endpoints configured" in str(exc_info.value)

    def test_get_status_empty_pool(self):
        """Test get_status with empty pool."""
        pool = ModelPool([])

        status = pool.get_status()

        assert status["total_endpoints"] == 0
        assert status["available_endpoints"] == 0
        assert status["total_capacity"] == 0
        assert status["current_load"] == 0
        assert status["utilization"] == 0
        assert status["endpoints"] == []

    def test_get_status_single_endpoint_idle(self, single_endpoint_config):
        """Test get_status with single idle endpoint."""
        pool = ModelPool(single_endpoint_config)

        status = pool.get_status()

        assert status["total_endpoints"] == 1
        assert status["available_endpoints"] == 1
        assert status["total_capacity"] == 2
        assert status["current_load"] == 0
        assert status["utilization"] == 0

        ep_status = status["endpoints"][0]
        assert ep_status["url"] == "http://localhost:11434"
        assert ep_status["model"] == "qwen2.5:7b"
        assert ep_status["current_load"] == 0
        assert ep_status["max_concurrent"] == 2
        assert ep_status["utilization"] == 0.0

    @pytest.mark.asyncio
    async def test_get_status_with_active_tasks(self, multi_endpoint_config):
        """Test get_status with active tasks."""
        pool = ModelPool(multi_endpoint_config)

        # Acquire some endpoints
        ep1 = await pool.acquire()
        ep2 = await pool.acquire()

        status = pool.get_status()

        assert status["total_endpoints"] == 3
        assert status["total_capacity"] == 6  # 2 + 3 + 1
        assert status["current_load"] == 2
        assert status["available_endpoints"] >= 1  # At least one still available

    @pytest.mark.asyncio
    async def test_get_status_all_at_capacity(self, single_endpoint_config):
        """Test get_status when all endpoints are at capacity."""
        pool = ModelPool(single_endpoint_config)

        # Fill the pool
        await pool.acquire()
        await pool.acquire()

        status = pool.get_status()

        assert status["available_endpoints"] == 0
        assert status["current_load"] == 2
        assert status["utilization"] == 100.0

    @pytest.mark.asyncio
    async def test_get_status_includes_metrics(self, single_endpoint_config):
        """Test get_status includes task execution metrics."""
        pool = ModelPool(single_endpoint_config)

        # Execute some tasks
        ep = await pool.acquire()
        await pool.release(ep, success=True)

        ep = await pool.acquire()
        await pool.release(ep, success=False)

        status = pool.get_status()
        ep_status = status["endpoints"][0]

        assert ep_status["total_tasks"] == 2
        assert ep_status["total_failures"] == 1

    def test_repr(self, multi_endpoint_config):
        """Test string representation."""
        pool = ModelPool(multi_endpoint_config)

        repr_str = repr(pool)

        assert "ModelPool(" in repr_str
        assert "endpoints=3" in repr_str
        assert "utilization" in repr_str

    @pytest.mark.asyncio
    async def test_concurrent_acquire_release(self, multi_endpoint_config):
        """Test concurrent acquire and release operations."""
        pool = ModelPool(multi_endpoint_config)

        async def acquire_use_release():
            """Acquire, use briefly, then release."""
            endpoint = await pool.wait_for_available(timeout=5.0)
            await asyncio.sleep(0.05)  # Simulate work
            await pool.release(endpoint)

        # Run multiple concurrent tasks
        tasks = [acquire_use_release() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Pool should be empty after all tasks complete
        status = pool.get_status()
        assert status["current_load"] == 0
        assert status["available_endpoints"] == 3

    @pytest.mark.asyncio
    async def test_pool_fairness_least_loaded(self, multi_endpoint_config):
        """Test that pool fairly distributes load using least-loaded strategy."""
        pool = ModelPool(multi_endpoint_config)

        # Acquire multiple endpoints
        endpoints = []
        for _ in range(5):
            ep = await pool.acquire()
            if ep:
                endpoints.append(ep)

        # Check that load is distributed across endpoints
        loads = [ep.current_load for ep in pool.endpoints]

        # With 3 endpoints (2, 3, 1 capacity) and 5 acquisitions,
        # the distribution should be relatively balanced
        assert sum(loads) == 5
        # No endpoint should be completely idle if others are loaded
        assert max(loads) - min(loads) <= 2  # Load difference shouldn't be too large
