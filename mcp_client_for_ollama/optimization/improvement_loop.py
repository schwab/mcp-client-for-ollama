"""Improvement Loop - Runs tests, identifies gaps, and applies improvements."""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of running tests on a model."""
    model_name: str
    timestamp: str
    overall_score: float  # 0-100
    success_rate: float  # 0-100
    task_scores: Dict[str, float]  # By task type
    failures: List[Dict[str, Any]]
    total_tests: int
    passed_tests: int


@dataclass
class IdentifiedGap:
    """A gap between expected and actual performance."""
    task_type: str
    current_score: float
    target_score: float
    failure_pattern: str
    affected_tests: int
    priority: float  # 0-1, higher = more important


@dataclass
class AppliedImprovement:
    """An improvement applied to address a gap."""
    improvement_type: str  # "prompt", "tool", "config", "training"
    description: str
    target_gap: str
    expected_impact: float  # 0-1
    applied_at: str


@dataclass
class ImprovementCycleResult:
    """Result of one complete improvement cycle."""
    model_name: str
    baseline_score: float
    new_score: float
    improvement: float
    improvement_percentage: float
    gaps_identified: int
    gaps_fixed: int
    applied_improvements: List[AppliedImprovement]
    validation_passed: bool


class ImprovementLoop:
    """
    Runs tests, implements improvements, validates results.
    One complete cycle: test -> analyze gaps -> generate improvements -> apply -> validate.
    """

    def __init__(self):
        """Initialize the improvement loop."""
        self.cycle_history: List[ImprovementCycleResult] = []
        self.applied_improvements_store: Dict[str, List[AppliedImprovement]] = {}

    async def improvement_cycle(
        self,
        model_name: str,
        test_suite_runner: Optional[Any] = None,
        chat_analyzer: Optional[Any] = None,
        knowledge_extractor: Optional[Any] = None
    ) -> ImprovementCycleResult:
        """
        One complete improvement cycle for a model.

        Args:
            model_name: Name of the model to improve
            test_suite_runner: Object that can run test suite
            chat_analyzer: ChatHistoryAnalyzer for getting successful patterns
            knowledge_extractor: KnowledgeExtractor for extracting improvements

        Returns:
            ImprovementCycleResult with metrics on this cycle
        """
        logger.info(f"Starting improvement cycle for {model_name}")

        # 1. Run current tests (baseline)
        baseline = await self._run_test_suite(model_name, test_suite_runner)
        logger.info(f"Baseline score: {baseline.overall_score}%")

        # 2. Analyze failures against chat successes
        gaps = await self._analyze_gaps(
            model_name,
            baseline,
            chat_analyzer
        )
        logger.info(f"Identified {len(gaps)} performance gaps")

        # 3. Generate improvements
        improvements = await self._generate_improvements(
            model_name,
            gaps,
            knowledge_extractor
        )
        logger.info(f"Generated {len(improvements)} improvements")

        # 4. Apply improvements
        await self._apply_improvements(model_name, improvements)

        # 5. Validate improvements
        new_score = await self._run_test_suite(model_name, test_suite_runner)
        logger.info(f"New score: {new_score.overall_score}%")

        # Calculate improvement
        score_improvement = new_score.overall_score - baseline.overall_score
        improvement_percentage = (score_improvement / baseline.overall_score * 100) if baseline.overall_score > 0 else 0

        # Create cycle result
        cycle_result = ImprovementCycleResult(
            model_name=model_name,
            baseline_score=baseline.overall_score,
            new_score=new_score.overall_score,
            improvement=score_improvement,
            improvement_percentage=improvement_percentage,
            gaps_identified=len(gaps),
            gaps_fixed=sum(1 for i in improvements if i.expected_impact > 0),
            applied_improvements=improvements,
            validation_passed=new_score.overall_score >= baseline.overall_score
        )

        self.cycle_history.append(cycle_result)
        return cycle_result

    async def _run_test_suite(
        self,
        model_name: str,
        test_suite_runner: Optional[Any] = None
    ) -> TestResult:
        """
        Run test suite on model and get results.

        In real implementation, would interface with actual test suite.
        """
        logger.debug(f"Running test suite for {model_name}")

        # Placeholder - would integrate with actual test suite
        return TestResult(
            model_name=model_name,
            timestamp=datetime.now().isoformat(),
            overall_score=65.0,  # Placeholder
            success_rate=65.0,
            task_scores={
                "command_execution": 70.0,
                "code_generation": 60.0,
                "tool_selection": 50.0,
                "parameter_formatting": 55.0,
            },
            failures=[
                {"task": "tool_calling", "error": "malformed_tool_call", "count": 3},
                {"task": "parameter_formatting", "error": "wrong_format", "count": 5},
            ],
            total_tests=20,
            passed_tests=13
        )

    async def _analyze_gaps(
        self,
        model_name: str,
        baseline: TestResult,
        chat_analyzer: Optional[Any] = None
    ) -> List[IdentifiedGap]:
        """
        Analyze failures to identify gaps between chat and agent mode.

        Returns:
            List of identified gaps, prioritized by impact
        """
        logger.debug(f"Analyzing gaps for {model_name}")

        gaps: List[IdentifiedGap] = []

        # Analyze each task type
        target_scores = {
            "command_execution": 90.0,
            "code_generation": 85.0,
            "tool_selection": 80.0,
            "parameter_formatting": 85.0,
        }

        for task_type, target in target_scores.items():
            current = baseline.task_scores.get(task_type, 0.0)

            if current < target:
                gap_size = target - current

                # Find failure pattern
                failure_pattern = self._find_failure_pattern(baseline.failures, task_type)

                # Calculate priority
                priority = min(1.0, gap_size / 50.0)  # Normalize to 0-1

                gaps.append(IdentifiedGap(
                    task_type=task_type,
                    current_score=current,
                    target_score=target,
                    failure_pattern=failure_pattern,
                    affected_tests=int(gap_size / 5),  # Estimate
                    priority=priority
                ))

        # Sort by priority
        gaps.sort(key=lambda g: g.priority, reverse=True)
        return gaps

    def _find_failure_pattern(self, failures: List[Dict[str, Any]], task_type: str) -> str:
        """Identify common failure patterns for a task type."""
        for failure in failures:
            if failure.get("task") == task_type:
                return failure.get("error", "unknown")
        return "unknown"

    async def _generate_improvements(
        self,
        model_name: str,
        gaps: List[IdentifiedGap],
        knowledge_extractor: Optional[Any] = None
    ) -> List[AppliedImprovement]:
        """
        Generate improvements to address identified gaps.

        Returns:
            List of improvements ready to apply
        """
        logger.debug(f"Generating improvements for {model_name}")

        improvements: List[AppliedImprovement] = []

        for gap in gaps[:3]:  # Focus on top 3 gaps
            # Generate different types of improvements based on gap
            if gap.failure_pattern == "malformed_tool_call":
                improvements.append(AppliedImprovement(
                    improvement_type="prompt",
                    description="Add tool calling format examples to prompt",
                    target_gap=gap.task_type,
                    expected_impact=0.7,
                    applied_at=datetime.now().isoformat()
                ))

            elif gap.failure_pattern == "wrong_format":
                improvements.append(AppliedImprovement(
                    improvement_type="training",
                    description="Fine-tune on formatting examples from chat",
                    target_gap=gap.task_type,
                    expected_impact=0.6,
                    applied_at=datetime.now().isoformat()
                ))

            elif gap.priority > 0.7:
                improvements.append(AppliedImprovement(
                    improvement_type="config",
                    description=f"Adjust temperature and top_p for {gap.task_type}",
                    target_gap=gap.task_type,
                    expected_impact=0.3,
                    applied_at=datetime.now().isoformat()
                ))

        return improvements

    async def _apply_improvements(
        self,
        model_name: str,
        improvements: List[AppliedImprovement]
    ) -> None:
        """Apply improvements to the model."""
        logger.info(f"Applying {len(improvements)} improvements to {model_name}")

        for improvement in improvements:
            logger.debug(f"Applying {improvement.improvement_type}: {improvement.description}")

            # In real implementation, would:
            # - Update prompt templates
            # - Queue fine-tuning job
            # - Modify configuration
            # - etc.

            # For now, just log the improvement
            if model_name not in self.applied_improvements_store:
                self.applied_improvements_store[model_name] = []
            self.applied_improvements_store[model_name].append(improvement)

    def get_improvement_metrics(self) -> Dict[str, Any]:
        """Get overall improvement metrics across all cycles."""
        if not self.cycle_history:
            return {"total_cycles": 0}

        total_improvement = sum(c.improvement for c in self.cycle_history)
        avg_improvement = total_improvement / len(self.cycle_history) if self.cycle_history else 0
        successful_cycles = sum(1 for c in self.cycle_history if c.validation_passed)

        return {
            "total_cycles": len(self.cycle_history),
            "total_improvement": round(total_improvement, 1),
            "average_improvement_per_cycle": round(avg_improvement, 1),
            "successful_cycles": successful_cycles,
            "success_rate": round((successful_cycles / len(self.cycle_history) * 100), 1) if self.cycle_history else 0,
            "models_improved": list(set(c.model_name for c in self.cycle_history)),
        }

    def get_model_improvement_history(self, model_name: str) -> List[ImprovementCycleResult]:
        """Get improvement history for a specific model."""
        return [c for c in self.cycle_history if c.model_name == model_name]

    def export_cycle_results(self, output_path: Optional[str] = None) -> str:
        """Export all improvement cycle results to JSON."""
        if output_path is None:
            output_path = str(Path.home() / "Nextcloud/DEV/ollmcp/mcp-client-for-ollama/data/improvement_cycles.json")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JSON-serializable format
        cycles_data = []
        for cycle in self.cycle_history:
            cycle_dict = asdict(cycle)
            cycle_dict["applied_improvements"] = [
                asdict(imp) for imp in cycle.applied_improvements
            ]
            cycles_data.append(cycle_dict)

        with open(output_path, 'w') as f:
            json.dump(cycles_data, f, indent=2)

        logger.info(f"Exported {len(self.cycle_history)} improvement cycles to {output_path}")
        return output_path
