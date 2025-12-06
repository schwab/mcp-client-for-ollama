"""
Agent Delegation System

This module provides an agent delegation system that allows small language models
to handle complex multi-file tasks by decomposing them into smaller, focused subtasks
executed by specialized agents.

Key Components:
- Task: Represents a subtask to be executed
- AgentConfig: Configuration for agent types loaded from JSON definitions
- ModelPool: Manages a pool of Ollama model endpoints for parallel execution
- DelegationClient: Main orchestrator for the delegation workflow

Usage:
    from mcp_client_for_ollama.agents import DelegationClient

    delegation_client = DelegationClient(mcp_client, config)
    result = await delegation_client.process_with_delegation(user_query)
"""

from .task import Task, TaskStatus
from .agent_config import AgentConfig
from .model_pool import ModelPool, ModelEndpoint
from .delegation_client import DelegationClient

__all__ = [
    'Task',
    'TaskStatus',
    'AgentConfig',
    'ModelPool',
    'ModelEndpoint',
    'DelegationClient',
]
