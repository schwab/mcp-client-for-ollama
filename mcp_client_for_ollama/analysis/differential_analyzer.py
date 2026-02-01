"""Differential Analyzer - Compares chat vs agent performance."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution mode for testing."""
    CHAT = "chat"
    AGENT = "agent"


@dataclass
class ExecutionResult:
    """Result of executing a task in a specific mode."""
    mode: ExecutionMode
    task_description: str
    success: bool
    output: str
    error: Optional[str] = None
    reasoning_steps: List[str] = None
    tools_used: List[str] = None
    execution_time: float = 0.0
    quality_score: float = 0.0  # 0-100


@dataclass
class ComparisonResult:
    """Result of comparing task execution across modes."""
    task_description: str
    task_type: str
    chat_result: ExecutionResult
    agent_result: ExecutionResult
    chat_advantages: List[str]
    agent_advantages: List[str]
    performance_gap: float  # Percentage difference
    recommendations: List[str]


class DifferentialAnalyzer:
    """Compares chat vs agent performance on identical tasks."""

    def __init__(self):
        """Initialize the differential analyzer."""
        self.comparison_history: List[ComparisonResult] = []

    async def run_comparison_test(self, task_description: str, task_type: str) -> ComparisonResult:
        """
        Run same task in both modes and compare results.

        Args:
            task_description: Description of the task to execute
            task_type: Type of task (command_execution, code_generation, etc.)

        Returns:
            ComparisonResult with analysis of both modes
        """
        logger.info(f"Running comparison test for: {task_description[:50]}...")

        # Run task in both modes
        chat_result = await self._run_chat_mode(task_description, task_type)
        agent_result = await self._run_agent_mode(task_description, task_type)

        # Analyze differences
        comparison = self._compare_outputs(
            task_description,
            task_type,
            chat_result,
            agent_result
        )

        self.comparison_history.append(comparison)
        return comparison

    async def _run_chat_mode(self, task_description: str, task_type: str) -> ExecutionResult:
        """
        Simulate running task in chat mode.
        In real implementation, would interface with actual chat system.
        """
        logger.debug(f"Executing in CHAT mode: {task_type}")

        # Placeholder - would integrate with actual chat interface
        return ExecutionResult(
            mode=ExecutionMode.CHAT,
            task_description=task_description,
            success=True,  # Placeholder
            output="Chat mode output",
            reasoning_steps=["Step 1", "Step 2"],
            tools_used=[],
            quality_score=85.0
        )

    async def _run_agent_mode(self, task_description: str, task_type: str) -> ExecutionResult:
        """
        Simulate running task in agent mode.
        In real implementation, would interface with actual agent system.
        """
        logger.debug(f"Executing in AGENT mode: {task_type}")

        # Placeholder - would integrate with actual agent interface
        return ExecutionResult(
            mode=ExecutionMode.AGENT,
            task_description=task_description,
            success=False,  # Placeholder
            output="Agent mode output",
            error="Tool calling failed",
            reasoning_steps=["Step 1"],
            tools_used=[],
            quality_score=45.0
        )

    def _compare_outputs(
        self,
        task_description: str,
        task_type: str,
        chat_result: ExecutionResult,
        agent_result: ExecutionResult
    ) -> ComparisonResult:
        """Analyze and compare results from both modes."""

        # Extract advantages from each mode
        chat_advantages = self._extract_advantages(chat_result)
        agent_advantages = self._extract_advantages(agent_result)

        # Calculate performance gap
        gap = chat_result.quality_score - agent_result.quality_score

        # Generate recommendations
        recommendations = self._generate_recommendations(
            task_type,
            chat_result,
            agent_result,
            chat_advantages
        )

        return ComparisonResult(
            task_description=task_description,
            task_type=task_type,
            chat_result=chat_result,
            agent_result=agent_result,
            chat_advantages=chat_advantages,
            agent_advantages=agent_advantages,
            performance_gap=gap,
            recommendations=recommendations
        )

    def _extract_advantages(self, result: ExecutionResult) -> List[str]:
        """Extract what this mode did well."""
        advantages = []

        if result.success:
            advantages.append("successful_execution")
        if result.reasoning_steps and len(result.reasoning_steps) > 2:
            advantages.append("detailed_reasoning")
        if result.tools_used:
            advantages.append("proper_tool_selection")
        if result.quality_score >= 80:
            advantages.append("high_quality_output")
        if not result.error:
            advantages.append("no_errors")

        return advantages

    def _generate_recommendations(
        self,
        task_type: str,
        chat_result: ExecutionResult,
        agent_result: ExecutionResult,
        chat_advantages: List[str]
    ) -> List[str]:
        """Generate recommendations for improving agent mode."""
        recommendations = []

        if "detailed_reasoning" in chat_advantages and agent_result.success:
            recommendations.append("Enhance agent reasoning prompts with step-by-step examples")

        if "proper_tool_selection" in chat_advantages:
            recommendations.append("Add tool selection training examples from successful chat interactions")

        if agent_result.error:
            error_type = self._categorize_error(agent_result.error)
            if error_type == "tool_calling":
                recommendations.append("Improve tool calling format in agent prompts")
            elif error_type == "parameter":
                recommendations.append("Add parameter formatting examples from chat successes")

        if chat_result.quality_score > 80 and agent_result.quality_score < 50:
            recommendations.append("Consider fine-tuning agent model on chat success patterns")

        return recommendations

    def _categorize_error(self, error: str) -> str:
        """Categorize the type of error that occurred."""
        error_lower = error.lower()

        if "tool" in error_lower or "call" in error_lower:
            return "tool_calling"
        elif "parameter" in error_lower or "format" in error_lower or "argument" in error_lower:
            return "parameter"
        elif "syntax" in error_lower:
            return "syntax"
        else:
            return "unknown"

    def get_comparison_summary(self) -> Dict[str, Any]:
        """Get summary statistics from all comparisons."""
        if not self.comparison_history:
            return {"total_comparisons": 0}

        total = len(self.comparison_history)
        avg_gap = sum(c.performance_gap for c in self.comparison_history) / total
        successful_chats = sum(1 for c in self.comparison_history if c.chat_result.success)
        successful_agents = sum(1 for c in self.comparison_history if c.agent_result.success)

        return {
            "total_comparisons": total,
            "chat_success_rate": (successful_chats / total) * 100,
            "agent_success_rate": (successful_agents / total) * 100,
            "average_performance_gap": round(avg_gap, 1),
            "most_common_advantages_in_chat": self._get_most_common_advantages(),
        }

    def _get_most_common_advantages(self) -> List[str]:
        """Get the most common advantages identified in chat mode."""
        advantage_counts: Dict[str, int] = {}

        for comparison in self.comparison_history:
            for advantage in comparison.chat_advantages:
                advantage_counts[advantage] = advantage_counts.get(advantage, 0) + 1

        # Sort by frequency
        sorted_advantages = sorted(
            advantage_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [adv for adv, _ in sorted_advantages[:5]]
