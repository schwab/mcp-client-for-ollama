"""
Memory system for persistent domain-specific agent state.

This package implements the domain memory architecture for AI agents,
providing persistent storage of goals, state, progress, and artifacts
across sessions.
"""

from .base_memory import (
    DomainMemory,
    Goal,
    Feature,
    ProgressEntry,
    TestResult,
    MemoryMetadata,
    FeatureStatus,
    GoalStatus,
    OutcomeType,
)
from .storage import MemoryStorage
from .schemas import MemorySchema, DomainType
from .initializer import MemoryInitializer, InitializerPromptBuilder
from .boot_ritual import BootRitual
from .tools import MemoryTools

__all__ = [
    "DomainMemory",
    "Goal",
    "Feature",
    "ProgressEntry",
    "TestResult",
    "MemoryMetadata",
    "FeatureStatus",
    "GoalStatus",
    "OutcomeType",
    "MemoryStorage",
    "MemorySchema",
    "DomainType",
    "MemoryInitializer",
    "InitializerPromptBuilder",
    "BootRitual",
    "MemoryTools",
]
