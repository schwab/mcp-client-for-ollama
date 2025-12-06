"""
Model pool management for distributed task execution.

This module provides a pool of Ollama model endpoints that can be used
to execute tasks in parallel across multiple servers.
"""

import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ModelEndpoint:
    """
    Represents a single Ollama model endpoint in the pool.

    Attributes:
        url: Base URL of the Ollama server (e.g., "http://localhost:11434")
        model: Name of the model to use on this endpoint (e.g., "qwen2.5:7b")
        max_concurrent: Maximum number of concurrent tasks for this endpoint
        current_load: Current number of tasks running on this endpoint
        total_tasks_executed: Total number of tasks executed (for metrics)
        total_failures: Total number of failed tasks (for metrics)
    """

    url: str
    model: str
    max_concurrent: int = 1
    current_load: int = 0
    total_tasks_executed: int = 0
    total_failures: int = 0

    @property
    def is_available(self) -> bool:
        """Check if this endpoint has capacity for more tasks."""
        return self.current_load < self.max_concurrent

    @property
    def utilization(self) -> float:
        """Calculate current utilization as a percentage."""
        if self.max_concurrent == 0:
            return 100.0
        return (self.current_load / self.max_concurrent) * 100.0

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ModelEndpoint(url={self.url}, model={self.model}, "
            f"load={self.current_load}/{self.max_concurrent})"
        )


class ModelPool:
    """
    Manages a pool of model endpoints for parallel task execution.

    The pool uses a least-loaded strategy to distribute tasks across
    available endpoints. Tasks wait if all endpoints are at capacity.

    Usage:
        pool = ModelPool(endpoints_config)
        endpoint = await pool.acquire()
        try:
            # Use endpoint for task execution
            ...
        finally:
            await pool.release(endpoint)
    """

    def __init__(self, endpoints: List[Dict[str, Any]]):
        """
        Initialize the model pool.

        Args:
            endpoints: List of endpoint configurations, each containing:
                - url: Ollama server URL
                - model: Model name to use
                - max_concurrent: Max concurrent tasks (default: 1)

        Example:
            [
                {
                    "url": "http://localhost:11434",
                    "model": "qwen2.5:7b",
                    "max_concurrent": 2
                },
                {
                    "url": "http://192.168.1.100:11434",
                    "model": "qwen2.5:7b",
                    "max_concurrent": 2
                }
            ]
        """
        self.endpoints = [
            ModelEndpoint(
                url=ep['url'],
                model=ep['model'],
                max_concurrent=ep.get('max_concurrent', 1)
            )
            for ep in endpoints
        ]

        # Lock for thread-safe access to endpoint state
        self._lock = asyncio.Lock()

        # Condition variable for waiting on available endpoints
        self._available = asyncio.Condition(self._lock)

    async def acquire(self) -> Optional[ModelEndpoint]:
        """
        Try to acquire an available model endpoint (non-blocking).

        Uses least-loaded strategy: selects the endpoint with lowest
        current load that still has capacity.

        Returns:
            ModelEndpoint if one is available, None if all are at capacity
        """
        async with self._lock:
            # Find endpoints with available capacity
            available = [ep for ep in self.endpoints if ep.is_available]

            if not available:
                return None

            # Select least loaded endpoint
            endpoint = min(available, key=lambda e: e.current_load)
            endpoint.current_load += 1

            return endpoint

    async def release(self, endpoint: ModelEndpoint, success: bool = True):
        """
        Release a model endpoint back to the pool.

        Args:
            endpoint: The endpoint to release
            success: Whether the task completed successfully (for metrics)
        """
        async with self._available:
            endpoint.current_load -= 1
            endpoint.total_tasks_executed += 1

            if not success:
                endpoint.total_failures += 1

            # Notify waiting tasks that an endpoint is available
            self._available.notify()

    async def wait_for_available(self, timeout: Optional[float] = 60.0) -> ModelEndpoint:
        """
        Wait until an endpoint becomes available (blocking).

        This method will block until an endpoint has capacity, or until
        the timeout is reached.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            ModelEndpoint that was acquired

        Raises:
            TimeoutError: If no endpoint becomes available within timeout
            ValueError: If pool has no endpoints configured
        """
        if not self.endpoints:
            raise ValueError("Model pool has no endpoints configured")

        start_time = asyncio.get_event_loop().time()

        while True:
            # Try to acquire immediately
            endpoint = await self.acquire()
            if endpoint:
                return endpoint

            # Check timeout
            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(
                        f"No model endpoint became available within {timeout}s. "
                        f"All {len(self.endpoints)} endpoints are at capacity."
                    )

            # Wait for notification that an endpoint was released
            async with self._available:
                try:
                    remaining = None if timeout is None else timeout - elapsed
                    await asyncio.wait_for(
                        self._available.wait(),
                        timeout=remaining
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        f"No model endpoint became available within {timeout}s. "
                        f"All {len(self.endpoints)} endpoints are at capacity."
                    )

    def get_status(self) -> Dict[str, Any]:
        """
        Get current pool status for monitoring.

        Returns:
            Dictionary with pool statistics including:
            - total_endpoints: Number of endpoints in pool
            - available_endpoints: Number with available capacity
            - total_capacity: Sum of max_concurrent across all endpoints
            - current_load: Sum of current_load across all endpoints
            - endpoints: List of endpoint status details
        """
        total_capacity = sum(ep.max_concurrent for ep in self.endpoints)
        current_load = sum(ep.current_load for ep in self.endpoints)
        available_count = sum(1 for ep in self.endpoints if ep.is_available)

        return {
            "total_endpoints": len(self.endpoints),
            "available_endpoints": available_count,
            "total_capacity": total_capacity,
            "current_load": current_load,
            "utilization": (current_load / total_capacity * 100) if total_capacity > 0 else 0,
            "endpoints": [
                {
                    "url": ep.url,
                    "model": ep.model,
                    "current_load": ep.current_load,
                    "max_concurrent": ep.max_concurrent,
                    "utilization": ep.utilization,
                    "total_tasks": ep.total_tasks_executed,
                    "total_failures": ep.total_failures,
                }
                for ep in self.endpoints
            ],
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        status = self.get_status()
        return (
            f"ModelPool(endpoints={status['total_endpoints']}, "
            f"load={status['current_load']}/{status['total_capacity']}, "
            f"utilization={status['utilization']:.1f}%)"
        )
