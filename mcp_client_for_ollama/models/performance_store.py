"""Performance Store for Model Intelligence.

This module loads and manages model performance data from the os_llm_testing_suite.
It provides query capabilities to find the best models for specific agent types.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelPerformance:
    """Model performance metrics from test suite."""

    model: str
    overall_score: float
    passed: bool
    tier_scores: Dict[str, float]  # {"1": 94.2, "2": 86.7, "3": 84.8}
    dimension_scores: Dict[str, float]  # {"tool_selection": 100.0, ...}
    test_count: int
    timestamp: str
    temperature: float

    # Computed fields
    max_tier: int = 0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate derived fields."""
        # Determine max tier passed
        if self.tier_scores.get("3", 0) >= 65:
            self.max_tier = 3
        elif self.tier_scores.get("2", 0) >= 75:
            self.max_tier = 2
        elif self.tier_scores.get("1", 0) >= 85:
            self.max_tier = 1
        else:
            self.max_tier = 0

        # Identify strengths and weaknesses
        self.strengths = [
            dim for dim, score in self.dimension_scores.items()
            if score >= 70.0
        ]
        self.weaknesses = [
            dim for dim, score in self.dimension_scores.items()
            if score < 40.0
        ]


# Agent-specific requirements
AGENT_REQUIREMENTS = {
    "PLANNER": {
        "min_score": 75.0,
        "min_tier": 2,
        "critical_dimensions": ["planning", "tool_selection"],
        "important_dimensions": ["context", "parameters"]
    },
    "CODER": {
        "min_score": 80.0,
        "min_tier": 2,
        "critical_dimensions": ["parameters", "planning", "tool_selection"],
        "important_dimensions": ["context", "error_handling"]
    },
    "READER": {
        "min_score": 70.0,
        "min_tier": 1,
        "critical_dimensions": ["context", "tool_selection"],
        "important_dimensions": ["parameters"]
    },
    "EXECUTOR": {
        "min_score": 75.0,
        "min_tier": 2,
        "critical_dimensions": ["tool_selection", "parameters"],
        "important_dimensions": ["error_handling", "planning"]
    },
    "DEBUGGER": {
        "min_score": 80.0,
        "min_tier": 2,
        "critical_dimensions": ["parameters", "planning", "context"],
        "important_dimensions": ["error_handling", "tool_selection"]
    },
    "RESEARCHER": {
        "min_score": 70.0,
        "min_tier": 2,
        "critical_dimensions": ["context", "planning"],
        "important_dimensions": ["tool_selection", "parameters"]
    },
    "AGGREGATOR": {
        "min_score": 75.0,
        "min_tier": 2,
        "critical_dimensions": ["context", "planning"],
        "important_dimensions": ["tool_selection"]
    },
    "ARTIFACT_AGENT": {
        "min_score": 70.0,
        "min_tier": 2,
        "critical_dimensions": ["parameters", "tool_selection"],
        "important_dimensions": ["planning", "context"]
    },
    "SHELL_EXECUTOR": {
        "min_score": 80.0,
        "min_tier": 2,
        "critical_dimensions": ["parameters", "tool_selection", "planning"],
        "important_dimensions": ["error_handling", "context"]
    },
    "FILE_EXECUTOR": {
        "min_score": 75.0,
        "min_tier": 2,
        "critical_dimensions": ["tool_selection", "parameters"],
        "important_dimensions": ["planning", "context"]
    },
    "TOOL_FORM_AGENT": {
        "min_score": 65.0,
        "min_tier": 1,
        "critical_dimensions": ["tool_selection", "parameters"],
        "important_dimensions": ["context"]
    }
}


class PerformanceStore:
    """Store and query model performance data."""

    def __init__(self, test_suite_path: Optional[str] = None):
        """Initialize performance store.

        Args:
            test_suite_path: Path to os_llm_testing_suite results directory
        """
        self.test_suite_path = test_suite_path or "~/project/os_llm_testing_suite/results"
        self.models: Dict[str, ModelPerformance] = {}
        self.last_update: Optional[datetime] = None

        self.load_test_results()

    def load_test_results(self):
        """Load all test results from test suite."""
        results_dir = Path(self.test_suite_path).expanduser()

        if not results_dir.exists():
            logger.warning(f"Test suite results not found at {results_dir}")
            logger.info("Model intelligence will use fallback selection without performance data")
            return

        # Find all JSON report files
        json_files = list(results_dir.rglob("report_*.json"))

        if not json_files:
            logger.warning(f"No report files found in {results_dir}")
            return

        logger.info(f"Loading test results from {len(json_files)} report files...")

        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # Extract tier details
                tier_scores = {}
                if "tier_details" in data:
                    for tier_num, tier_data in data["tier_details"].items():
                        tier_scores[str(tier_num)] = tier_data.get("average_score", 0.0)

                # Create ModelPerformance object
                perf = ModelPerformance(
                    model=data["model"],
                    overall_score=data["summary"]["overall_score"],
                    passed=data["summary"]["passed"],
                    tier_scores=tier_scores,
                    dimension_scores=data["summary"]["dimension_averages"],
                    test_count=sum(
                        v.get("total_tests", 0)
                        for v in data.get("tier_details", {}).values()
                    ),
                    timestamp=data["timestamp"],
                    temperature=data.get("temperature", 0.2)
                )

                # Store best result per model (highest overall score)
                model_name = perf.model
                if (model_name not in self.models or
                    perf.overall_score > self.models[model_name].overall_score):
                    self.models[model_name] = perf
                    logger.debug(f"Loaded performance data for {model_name}: {perf.overall_score:.1f}")

            except Exception as e:
                logger.warning(f"Error loading {json_file}: {e}")

        self.last_update = datetime.now()
        logger.info(f"Successfully loaded performance data for {len(self.models)} models")

    def get_model_performance(self, model: str) -> Optional[ModelPerformance]:
        """Get performance data for specific model.

        Args:
            model: Model name to query

        Returns:
            ModelPerformance object or None if not found
        """
        return self.models.get(model)

    def list_models(self,
                   min_score: float = 0.0,
                   min_tier: int = 1,
                   required_dimensions: Optional[List[str]] = None) -> List[ModelPerformance]:
        """List models matching criteria.

        Args:
            min_score: Minimum overall score
            min_tier: Minimum tier passed
            required_dimensions: Dimensions that must be strengths (>70)

        Returns:
            List of ModelPerformance objects sorted by score
        """
        results = []

        for perf in self.models.values():
            # Check score threshold
            if perf.overall_score < min_score:
                continue

            # Check tier requirement
            if perf.max_tier < min_tier:
                continue

            # Check dimension requirements
            if required_dimensions:
                if not all(dim in perf.strengths for dim in required_dimensions):
                    continue

            results.append(perf)

        # Sort by overall score descending
        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results

    def get_best_for_agent(self, agent_type: str) -> Optional[ModelPerformance]:
        """Get best model for specific agent type.

        Args:
            agent_type: Type of agent (e.g., "PLANNER", "CODER")

        Returns:
            Best ModelPerformance for agent or None
        """
        # Agent requirements defined above
        requirements = AGENT_REQUIREMENTS.get(agent_type)
        if not requirements:
            logger.warning(f"Unknown agent type: {agent_type}")
            return None

        candidates = self.list_models(
            min_score=requirements["min_score"],
            min_tier=requirements["min_tier"],
            required_dimensions=requirements["critical_dimensions"]
        )

        if not candidates:
            logger.warning(f"No models meet requirements for {agent_type}")
            return None

        # Score candidates based on dimension weights
        def score_model(perf: ModelPerformance) -> float:
            score = perf.overall_score

            # Bonus for critical dimensions
            for dim in requirements["critical_dimensions"]:
                dim_score = perf.dimension_scores.get(dim, 0)
                score += dim_score * 0.1  # 10% bonus per critical dim

            # Bonus for important dimensions
            for dim in requirements.get("important_dimensions", []):
                dim_score = perf.dimension_scores.get(dim, 0)
                score += dim_score * 0.05  # 5% bonus per important dim

            return score

        candidates.sort(key=score_model, reverse=True)
        best = candidates[0]

        logger.info(f"Best model for {agent_type}: {best.model} (score: {best.overall_score:.1f})")
        return best

    def get_fallbacks(self,
                     primary_model: str,
                     count: int = 2,
                     max_score_delta: float = 10.0) -> List[ModelPerformance]:
        """Get fallback models similar to primary.

        Args:
            primary_model: Primary model name
            count: Number of fallbacks to return
            max_score_delta: Maximum score difference from primary

        Returns:
            List of fallback ModelPerformance objects
        """
        primary = self.get_model_performance(primary_model)
        if not primary:
            return []

        # Find models with similar strengths
        candidates = []
        for model_name, perf in self.models.items():
            if model_name == primary_model:
                continue

            # Check score delta
            score_delta = abs(perf.overall_score - primary.overall_score)
            if score_delta > max_score_delta:
                continue

            # Check strength overlap
            overlap = len(set(perf.strengths) & set(primary.strengths))
            if overlap < len(primary.strengths) // 2:
                continue

            candidates.append((perf, overlap))

        # Sort by strength overlap, then score
        candidates.sort(key=lambda x: (x[1], x[0].overall_score), reverse=True)
        fallbacks = [c[0] for c in candidates[:count]]

        if fallbacks:
            logger.info(f"Fallbacks for {primary_model}: {[f.model for f in fallbacks]}")

        return fallbacks

    def export_summary(self) -> Dict:
        """Export summary statistics.

        Returns:
            Dictionary with summary statistics
        """
        if not self.models:
            return {
                "total_models": 0,
                "status": "no_data"
            }

        scores = [m.overall_score for m in self.models.values()]
        passing = [m for m in self.models.values() if m.passed]

        return {
            "total_models": len(self.models),
            "passing_models": len(passing),
            "average_score": sum(scores) / len(scores),
            "top_model": max(self.models.values(), key=lambda x: x.overall_score).model,
            "top_score": max(scores),
            "last_update": self.last_update.isoformat() if self.last_update else None
        }

    def get_agent_recommendations(self, agent_type: str, top_k: int = 3) -> List[Dict]:
        """Get top K model recommendations for agent type.

        Args:
            agent_type: Type of agent
            top_k: Number of recommendations to return

        Returns:
            List of recommendation dictionaries
        """
        requirements = AGENT_REQUIREMENTS.get(agent_type)
        if not requirements:
            return []

        candidates = self.list_models(
            min_score=requirements["min_score"],
            min_tier=requirements["min_tier"],
            required_dimensions=requirements["critical_dimensions"]
        )

        results = []
        for candidate in candidates[:top_k]:
            results.append({
                "model": candidate.model,
                "overall_score": candidate.overall_score,
                "tier_scores": candidate.tier_scores,
                "strengths": candidate.strengths,
                "weaknesses": candidate.weaknesses,
                "max_tier": candidate.max_tier
            })

        return results
