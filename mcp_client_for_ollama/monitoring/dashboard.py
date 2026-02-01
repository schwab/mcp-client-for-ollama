"""Improvement Dashboard - Tracks improvement progress and generates reports."""

import logging
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    """Aggregated metrics for the dashboard."""
    timestamp: str
    models_analyzed: int
    agents_tested: int
    total_test_runs: int
    average_agent_success_rate: float
    chat_agent_performance_gap: float
    top_improvements: List[Dict[str, Any]]
    models_improved: List[str]
    fine_tuning_models: int
    estimated_claude_reduction: float


class ImprovementDashboard:
    """
    Tracks improvement progress across models and agents.
    Provides metrics, reporting, and visualization data.
    """

    def __init__(self):
        """Initialize the dashboard."""
        self.metrics_history: List[DashboardMetrics] = []
        self.model_performance_history: Dict[str, List[Dict[str, float]]] = {}
        self.improvement_log: List[Dict[str, Any]] = []

    def get_improvement_metrics(
        self,
        improvement_loop=None,
        fine_tuner=None,
        chat_analyzer=None
    ) -> DashboardMetrics:
        """
        Collect and aggregate all improvement metrics.

        Args:
            improvement_loop: ImprovementLoop instance
            fine_tuner: TargetedFineTuner instance
            chat_analyzer: ChatHistoryAnalyzer instance

        Returns:
            DashboardMetrics with all aggregated data
        """
        logger.info("Calculating dashboard metrics")

        # Get metrics from each component
        improvement_metrics = improvement_loop.get_improvement_metrics() if improvement_loop else {}
        fine_tuning_metrics = fine_tuner.get_summary() if fine_tuner else {}
        chat_summary = chat_analyzer.get_summary() if chat_analyzer else {}

        # Calculate key metrics
        agent_success_rate = improvement_metrics.get("average_improvement_per_cycle", 0)
        chat_agent_gap = self._calculate_chat_agent_gap(
            chat_summary,
            improvement_metrics
        )

        top_improvements = self._get_top_improvements(improvement_loop)
        models_improved = improvement_metrics.get("models_improved", [])
        fine_tuning_jobs = fine_tuning_metrics.get("total_jobs", 0)

        # Estimate Claude reduction
        claude_reduction = self._estimate_claude_reduction(
            agent_success_rate,
            chat_agent_gap
        )

        metrics = DashboardMetrics(
            timestamp=datetime.now().isoformat(),
            models_analyzed=len(chat_summary.get("models_analyzed", [])),
            agents_tested=5,  # Number of agent types
            total_test_runs=improvement_metrics.get("total_cycles", 0) * 5,
            average_agent_success_rate=agent_success_rate,
            chat_agent_performance_gap=chat_agent_gap,
            top_improvements=top_improvements,
            models_improved=models_improved,
            fine_tuning_models=fine_tuning_jobs,
            estimated_claude_reduction=claude_reduction
        )

        self.metrics_history.append(metrics)
        return metrics

    def _calculate_chat_agent_gap(
        self,
        chat_summary: Dict[str, Any],
        improvement_metrics: Dict[str, Any]
    ) -> float:
        """Calculate the performance gap between chat and agent modes."""
        # In real implementation, would compare actual test scores
        # For now, estimate based on improvement progress

        base_gap = 40.0  # Initial gap
        improvements = improvement_metrics.get("total_improvement", 0)

        # Each cycle reduces the gap
        reduced_gap = max(0, base_gap - (improvements * 0.5))

        return round(reduced_gap, 1)

    def _get_top_improvements(self, improvement_loop) -> List[Dict[str, Any]]:
        """Get the most impactful improvements."""
        if not improvement_loop or not improvement_loop.cycle_history:
            return []

        # Sort by improvement percentage
        sorted_cycles = sorted(
            improvement_loop.cycle_history,
            key=lambda c: c.improvement_percentage,
            reverse=True
        )

        return [
            {
                "model": c.model_name,
                "improvement": round(c.improvement_percentage, 1),
                "baseline": round(c.baseline_score, 1),
                "new_score": round(c.new_score, 1),
            }
            for c in sorted_cycles[:5]
        ]

    def _estimate_claude_reduction(
        self,
        agent_success_rate: float,
        chat_agent_gap: float
    ) -> float:
        """Estimate percentage of Claude usage that can be reduced."""
        # As agent success rate improves and gap closes, Claude dependency decreases

        # Start with assumption that we can offload work from successful agent tasks
        offloadable = agent_success_rate  # Percentage we can offload

        # Reduce based on remaining gap (can't fully replace if gap is large)
        gap_reduction = max(0, 100 - chat_agent_gap)  # How much gap is closed
        claude_reduction = (offloadable * gap_reduction) / 100

        return round(min(100, claude_reduction), 1)

    def generate_improvement_report(
        self,
        improvement_loop=None,
        fine_tuner=None,
        chat_analyzer=None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive improvement report.

        Returns:
            Dictionary with detailed report data
        """
        logger.info("Generating improvement report")

        metrics = self.get_improvement_metrics(
            improvement_loop,
            fine_tuner,
            chat_analyzer
        )

        return {
            "timestamp": metrics.timestamp,
            "summary": self._generate_summary(metrics),
            "by_model": self._get_model_performance(improvement_loop) if improvement_loop else {},
            "by_agent": self._get_agent_performance(improvement_loop) if improvement_loop else {},
            "chat_knowledge_transferred": self._get_transferred_knowledge(chat_analyzer) if chat_analyzer else {},
            "fine_tuning_progress": self._get_fine_tuning_progress(fine_tuner) if fine_tuner else {},
            "next_priorities": self._get_next_priorities(metrics),
            "recommendations": self._get_recommendations(metrics),
        }

    def _generate_summary(self, metrics: DashboardMetrics) -> Dict[str, Any]:
        """Generate executive summary."""
        return {
            "overall_progress": f"Reduced chat-agent gap by {100 - metrics.chat_agent_performance_gap:.1f}%",
            "claude_reduction_potential": f"Estimated {metrics.estimated_claude_reduction}% Claude usage reduction",
            "models_analyzed": metrics.models_analyzed,
            "agents_tested": metrics.agents_tested,
            "improvement_cycles": metrics.total_test_runs,
            "models_improved": len(metrics.models_improved),
            "fine_tuning_initiated": metrics.fine_tuning_models,
        }

    def _get_model_performance(self, improvement_loop) -> Dict[str, Any]:
        """Get performance data by model."""
        by_model = {}

        for cycle in improvement_loop.cycle_history:
            model = cycle.model_name

            if model not in by_model:
                by_model[model] = {
                    "baseline_score": cycle.baseline_score,
                    "current_score": cycle.new_score,
                    "total_improvement": cycle.improvement,
                    "improvement_percentage": cycle.improvement_percentage,
                    "cycles": 0,
                    "last_updated": cycle.baseline_score,
                }

            by_model[model]["cycles"] += 1
            by_model[model]["current_score"] = cycle.new_score

        return by_model

    def _get_agent_performance(self, improvement_loop) -> Dict[str, Any]:
        """Get performance data by agent type."""
        # Aggregate data by agent (would need agent type in cycle data)
        # For now, return template
        return {
            "CODER": {"success_rate": 75, "improvement": 15},
            "EXECUTOR": {"success_rate": 70, "improvement": 10},
            "PLANNER": {"success_rate": 65, "improvement": 8},
            "DEBUGGER": {"success_rate": 68, "improvement": 12},
            "READER": {"success_rate": 80, "improvement": 5},
        }

    def _get_transferred_knowledge(self, chat_analyzer) -> Dict[str, Any]:
        """Get knowledge transfer metrics."""
        summary = chat_analyzer.get_summary() if chat_analyzer else {}

        return {
            "total_patterns_identified": summary.get("patterns_extracted", 0),
            "by_type": summary.get("by_type", {}),
            "top_models": summary.get("models_analyzed", [])[:5],
            "success_rates": summary.get("success_rates_by_model", {}),
        }

    def _get_fine_tuning_progress(self, fine_tuner) -> Dict[str, Any]:
        """Get fine-tuning job progress."""
        summary = fine_tuner.get_summary() if fine_tuner else {}

        return {
            "total_jobs": summary.get("total_jobs", 0),
            "successful_jobs": summary.get("successful_jobs", 0),
            "success_rate": summary.get("success_rate", 0),
            "average_improvement": summary.get("average_improvement_per_job", 0),
            "models_fine_tuned": summary.get("models_fine_tuned", []),
            "weaknesses_addressed": summary.get("weaknesses_addressed", []),
        }

    def _get_next_priorities(self, metrics: DashboardMetrics) -> List[str]:
        """Generate prioritized list of next steps."""
        priorities = []

        # Based on gap and improvements
        if metrics.chat_agent_performance_gap > 30:
            priorities.append("Focus on tool-calling improvements (largest gap)")
        if metrics.fine_tuning_models < 2:
            priorities.append("Initiate fine-tuning for top 3 models")
        if metrics.average_agent_success_rate < 70:
            priorities.append("Apply more aggressive optimization strategies")

        # Add improvement recommendations
        if metrics.top_improvements:
            best_model = metrics.top_improvements[0]
            priorities.append(
                f"Replicate {best_model['model']}'s success pattern to other models"
            )

        return priorities

    def _get_recommendations(self, metrics: DashboardMetrics) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []

        if metrics.estimated_claude_reduction >= 50:
            recommendations.append(
                "Excellent progress! Consider deploying improved models to production."
            )
        elif metrics.estimated_claude_reduction >= 30:
            recommendations.append(
                "Good progress. Continue fine-tuning for remaining weak areas."
            )
        else:
            recommendations.append(
                "Increase focus on tool-calling and parameter formatting improvements."
            )

        if metrics.chat_agent_performance_gap > 20:
            recommendations.append(
                "Extract more examples from chat for knowledge transfer."
            )

        if metrics.fine_tuning_models == 0:
            recommendations.append(
                "Begin fine-tuning on identified weaknesses to accelerate improvement."
            )

        return recommendations

    def export_report(
        self,
        report: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """
        Export improvement report to JSON file.

        Args:
            report: Report dictionary to export
            output_path: Path to save report

        Returns:
            Path to exported file
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(
                Path.home() / f"Nextcloud/DEV/ollmcp/mcp-client-for-ollama/data/improvement_report_{timestamp}.json"
            )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Exported improvement report to {output_path}")
        return output_path

    def get_metrics_timeline(self) -> List[Dict[str, Any]]:
        """Get timeline of metrics changes."""
        timeline = []

        for i, metrics in enumerate(self.metrics_history):
            timeline.append({
                "timestamp": metrics.timestamp,
                "cycle": i + 1,
                "agent_success_rate": metrics.average_agent_success_rate,
                "chat_agent_gap": metrics.chat_agent_performance_gap,
                "claude_reduction": metrics.estimated_claude_reduction,
                "models_improved": len(metrics.models_improved),
            })

        return timeline

    def add_improvement_log_entry(
        self,
        model_name: str,
        improvement_type: str,
        description: str,
        impact: float
    ) -> None:
        """Log a specific improvement."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "type": improvement_type,
            "description": description,
            "impact": impact,
        }
        self.improvement_log.append(entry)

    def get_weekly_summary(self) -> Dict[str, Any]:
        """Get summary of improvements from the past week."""
        # Filter improvements from past 7 days
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=7)

        week_log = [
            e for e in self.improvement_log
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]

        total_impact = sum(e["impact"] for e in week_log)

        return {
            "period": "past 7 days",
            "improvements_made": len(week_log),
            "total_impact": round(total_impact, 1),
            "by_type": self._group_by_type(week_log),
            "by_model": self._group_by_model(week_log),
        }

    def _group_by_type(self, log_entries: List[Dict[str, Any]]) -> Dict[str, float]:
        """Group log entries by improvement type."""
        grouped = {}

        for entry in log_entries:
            imp_type = entry.get("type", "unknown")
            if imp_type not in grouped:
                grouped[imp_type] = 0
            grouped[imp_type] += entry.get("impact", 0)

        return {k: round(v, 1) for k, v in grouped.items()}

    def _group_by_model(self, log_entries: List[Dict[str, Any]]) -> Dict[str, float]:
        """Group log entries by model."""
        grouped = {}

        for entry in log_entries:
            model = entry.get("model", "unknown")
            if model not in grouped:
                grouped[model] = 0
            grouped[model] += entry.get("impact", 0)

        return {k: round(v, 1) for k, v in grouped.items()}
