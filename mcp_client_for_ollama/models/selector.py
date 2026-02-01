"""Model Selector for Intelligent Model Selection.

This module implements intelligent model selection based on agent requirements
and empirical performance data from the test suite.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from .performance_store import PerformanceStore, ModelPerformance, AGENT_REQUIREMENTS

logger = logging.getLogger(__name__)


@dataclass
class SelectionContext:
    """Context for model selection."""

    agent_type: str
    task_complexity: int = 2  # 1-3 (tier)
    required_tools: Optional[List[str]] = None
    context_length: int = 0
    previous_failures: Optional[List[str]] = None  # Models that failed
    performance_requirements: Optional[Dict[str, float]] = None  # Custom dimension thresholds


class ModelSelector:
    """Intelligent model selection engine."""

    def __init__(self, performance_store: PerformanceStore):
        """Initialize model selector.

        Args:
            performance_store: PerformanceStore instance with test data
        """
        self.store = performance_store

        # Selection history for learning
        self.selection_history: List[Dict] = []
        self.failure_count: Dict[str, int] = {}
        self.success_count: Dict[str, int] = {}

    def select_model(self,
                    context: SelectionContext,
                    available_models: Optional[List[str]] = None) -> Tuple[str, List[str]]:
        """Select optimal model for agent task.

        Args:
            context: Selection context with agent type and requirements
            available_models: Models available for selection (None = all)

        Returns:
            Tuple of (primary_model, fallback_models)
        """
        logger.info(f"Selecting model for {context.agent_type} (tier {context.task_complexity})")

        # Get base recommendation from performance data
        primary = self.store.get_best_for_agent(context.agent_type)

        if not primary:
            logger.warning(f"No performance data for {context.agent_type}, using default")
            return self._get_default_model(available_models), []

        # Filter by available models
        if available_models and primary.model not in available_models:
            logger.info(f"{primary.model} not available, finding alternative")
            # Find best available
            candidates = self.store.list_models(
                min_score=60.0,
                min_tier=context.task_complexity
            )
            available_candidates = [
                c for c in candidates
                if c.model in available_models
            ]
            if available_candidates:
                primary = available_candidates[0]
                logger.info(f"Selected available alternative: {primary.model}")
            else:
                logger.warning("No suitable models available, using default")
                return self._get_default_model(available_models), []

        # Exclude previous failures
        if context.previous_failures and primary.model in context.previous_failures:
            logger.info(f"{primary.model} previously failed, finding alternative")
            candidates = self.store.list_models(
                min_score=60.0,
                min_tier=context.task_complexity
            )
            for candidate in candidates:
                if candidate.model not in context.previous_failures:
                    if not available_models or candidate.model in available_models:
                        primary = candidate
                        logger.info(f"Alternative found: {primary.model}")
                        break

        # Apply custom performance requirements
        if context.performance_requirements:
            if not self._meets_requirements(primary, context.performance_requirements):
                logger.info(f"{primary.model} doesn't meet custom requirements")
                candidates = self.store.list_models(min_score=60.0)
                for candidate in candidates:
                    if self._meets_requirements(candidate, context.performance_requirements):
                        if not available_models or candidate.model in available_models:
                            primary = candidate
                            logger.info(f"Found model meeting requirements: {primary.model}")
                            break

        # Get fallbacks
        fallbacks = self.store.get_fallbacks(primary.model, count=2)

        # Filter fallbacks by availability
        if available_models:
            fallbacks = [f for f in fallbacks if f.model in available_models]

        fallback_names = [f.model for f in fallbacks]

        # Record selection
        self.selection_history.append({
            "agent_type": context.agent_type,
            "primary": primary.model,
            "fallbacks": fallback_names,
            "timestamp": datetime.now().isoformat(),
            "task_complexity": context.task_complexity
        })

        logger.info(f"Selected {primary.model} (score: {primary.overall_score:.1f})")
        if fallback_names:
            logger.debug(f"Fallbacks: {fallback_names}")

        return primary.model, fallback_names

    def _meets_requirements(self,
                          perf: ModelPerformance,
                          requirements: Dict[str, float]) -> bool:
        """Check if model meets custom dimension requirements.

        Args:
            perf: ModelPerformance to check
            requirements: Dictionary of dimension -> min_score

        Returns:
            True if all requirements met
        """
        for dim, min_score in requirements.items():
            if perf.dimension_scores.get(dim, 0) < min_score:
                return False
        return True

    def _get_default_model(self, available_models: Optional[List[str]] = None) -> str:
        """Get default fallback model.

        Args:
            available_models: List of available models to choose from

        Returns:
            Default model name
        """
        # Try to return highest scoring available model
        if self.store.models:
            if available_models:
                # Find best available model
                for perf in sorted(self.store.models.values(),
                                 key=lambda x: x.overall_score, reverse=True):
                    if perf.model in available_models:
                        logger.info(f"Using best available model: {perf.model}")
                        return perf.model

            # Return highest scoring model overall
            best = max(self.store.models.values(), key=lambda x: x.overall_score)
            logger.info(f"Using highest scoring model: {best.model}")
            return best.model

        # Hardcoded ultimate fallback
        fallback = "qwen2.5:7b"
        if available_models and fallback not in available_models:
            # Return first available model
            if available_models:
                fallback = available_models[0]

        logger.warning(f"No performance data, using fallback: {fallback}")
        return fallback

    def report_failure(self, model: str, agent_type: str, reason: Optional[str] = None):
        """Report model failure for learning.

        Args:
            model: Model that failed
            agent_type: Agent type that used the model
            reason: Reason for failure (optional)
        """
        self.failure_count[model] = self.failure_count.get(model, 0) + 1
        logger.warning(f"Failure #{self.failure_count[model]} for {model} on {agent_type}: {reason}")

    def report_success(self, model: str, agent_type: str, metrics: Optional[Dict] = None):
        """Report model success for learning.

        Args:
            model: Model that succeeded
            agent_type: Agent type that used the model
            metrics: Optional performance metrics
        """
        self.success_count[model] = self.success_count.get(model, 0) + 1
        logger.info(f"Success #{self.success_count[model]} for {model} on {agent_type}")

    def get_recommendations(self, agent_type: str, top_k: int = 3) -> List[Dict]:
        """Get top K model recommendations for agent type.

        Args:
            agent_type: Type of agent
            top_k: Number of recommendations

        Returns:
            List of recommendation dictionaries
        """
        requirements = AGENT_REQUIREMENTS.get(agent_type)
        if not requirements:
            logger.warning(f"Unknown agent type: {agent_type}")
            return []

        candidates = self.store.list_models(
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
                "recommendation_reason": self._explain_recommendation(candidate, agent_type)
            })

        return results

    def _explain_recommendation(self, perf: ModelPerformance, agent_type: str) -> str:
        """Generate human-readable explanation for recommendation.

        Args:
            perf: ModelPerformance to explain
            agent_type: Agent type context

        Returns:
            Explanation string
        """
        requirements = AGENT_REQUIREMENTS.get(agent_type, {})
        critical = requirements.get("critical_dimensions", [])

        reasons = []
        reasons.append(f"Overall: {perf.overall_score:.1f}")
        reasons.append(f"Tier {perf.max_tier}")

        for dim in critical:
            score = perf.dimension_scores.get(dim, 0)
            reasons.append(f"{dim}: {score:.1f}")

        return " | ".join(reasons)

    def optimize_for_speed(self, agent_type: str, available_models: Optional[List[str]] = None) -> str:
        """Select fastest model that meets minimum requirements.

        Args:
            agent_type: Type of agent
            available_models: Models to choose from

        Returns:
            Model name optimized for speed
        """
        requirements = AGENT_REQUIREMENTS.get(agent_type)
        if not requirements:
            return self._get_default_model(available_models)

        # Get all models that meet requirements (slightly lower threshold)
        candidates = self.store.list_models(
            min_score=requirements["min_score"] - 5,
            min_tier=requirements["min_tier"],
            required_dimensions=requirements["critical_dimensions"]
        )

        # Filter by availability
        if available_models:
            candidates = [c for c in candidates if c.model in available_models]

        if not candidates:
            return self._get_default_model(available_models)

        # Prefer smaller models (faster inference)
        # Parse model size from name (e.g., "qwen2.5:7b" -> 7)
        def get_size(model_name: str) -> float:
            parts = model_name.split(':')
            if len(parts) > 1:
                size_str = parts[1].replace('b', '').replace('B', '')
                try:
                    return float(size_str)
                except:
                    return 999.0
            return 999.0

        candidates.sort(key=lambda x: get_size(x.model))
        logger.info(f"Speed-optimized model for {agent_type}: {candidates[0].model}")
        return candidates[0].model

    def optimize_for_quality(self, agent_type: str, available_models: Optional[List[str]] = None) -> str:
        """Select highest quality model regardless of speed.

        Args:
            agent_type: Type of agent
            available_models: Models to choose from

        Returns:
            Model name optimized for quality
        """
        requirements = AGENT_REQUIREMENTS.get(agent_type)
        if not requirements:
            return self._get_default_model(available_models)

        candidates = self.store.list_models(
            min_score=requirements["min_score"],
            min_tier=requirements["min_tier"],
            required_dimensions=requirements["critical_dimensions"]
        )

        # Filter by availability
        if available_models:
            candidates = [c for c in candidates if c.model in available_models]

        if not candidates:
            return self._get_default_model(available_models)

        # Return highest scoring
        logger.info(f"Quality-optimized model for {agent_type}: {candidates[0].model}")
        return candidates[0].model

    def get_success_rate(self, model: str) -> float:
        """Get success rate for a model.

        Args:
            model: Model name

        Returns:
            Success rate (0.0-1.0)
        """
        successes = self.success_count.get(model, 0)
        failures = self.failure_count.get(model, 0)
        total = successes + failures

        if total == 0:
            return 0.5  # No data, assume 50%

        return successes / total

    def get_selection_stats(self) -> Dict:
        """Get statistics about model selection.

        Returns:
            Dictionary with selection statistics
        """
        total_selections = len(self.selection_history)
        total_failures = sum(self.failure_count.values())
        total_successes = sum(self.success_count.values())

        # Get most selected models
        model_counts = {}
        for entry in self.selection_history:
            model = entry["primary"]
            model_counts[model] = model_counts.get(model, 0) + 1

        most_selected = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_selections": total_selections,
            "total_failures": total_failures,
            "total_successes": total_successes,
            "overall_success_rate": total_successes / max(1, total_successes + total_failures),
            "most_selected_models": most_selected,
            "models_tracked": len(set(list(self.failure_count.keys()) + list(self.success_count.keys())))
        }

    def predict_success(self, model: str, agent_type: str, task_complexity: int = 2) -> float:
        """Predict probability of success for model on task.

        Uses tier performance, critical dimensions, and historical data
        to estimate success probability.

        Args:
            model: Model name
            agent_type: Agent type (e.g., "PLANNER", "CODER")
            task_complexity: Task complexity tier (1-3)

        Returns:
            Probability of success (0.0-1.0)
        """
        perf = self.store.get_model_performance(model)
        if not perf:
            return 0.5  # Unknown model, 50% confidence

        # Base prediction on tier performance
        tier_score = perf.tier_scores.get(str(task_complexity), 0)
        base_prob = tier_score / 100.0

        # Adjust based on agent requirements
        requirements = AGENT_REQUIREMENTS.get(agent_type, {})
        critical_dims = requirements.get("critical_dimensions", [])

        # Check if critical dimensions are strong
        if critical_dims:
            critical_strength = sum(
                perf.dimension_scores.get(dim, 0)
                for dim in critical_dims
            ) / (len(critical_dims) * 100.0)
        else:
            critical_strength = 1.0

        # Weighted average: 60% tier score, 40% critical dimension strength
        predicted_prob = (base_prob * 0.6) + (critical_strength * 0.4)

        # Adjust based on historical failures
        total_attempts = len(self.selection_history)
        if total_attempts > 0:
            failure_rate = self.failure_count.get(model, 0) / total_attempts
            predicted_prob *= (1.0 - (failure_rate * 0.3))  # Max 30% penalty

        return max(0.0, min(1.0, predicted_prob))

    def explain_prediction(self, model: str, agent_type: str, task_complexity: int = 2) -> Dict:
        """Explain prediction with detailed breakdown.

        Provides transparency into why a particular success probability
        was calculated for a model-agent-task combination.

        Args:
            model: Model name
            agent_type: Agent type
            task_complexity: Task complexity tier (1-3)

        Returns:
            Dictionary with prediction explanation including:
            - probability: Success probability (0.0-1.0)
            - confidence: "high", "medium", or "low"
            - factors: Breakdown of contributing factors
            - recommendation: "recommended" or "not recommended"
        """
        prob = self.predict_success(model, agent_type, task_complexity)
        perf = self.store.get_model_performance(model)

        if not perf:
            return {
                "probability": prob,
                "confidence": "low",
                "explanation": f"Unknown model: {model}. No test data available.",
                "recommendation": "not recommended"
            }

        requirements = AGENT_REQUIREMENTS.get(agent_type, {})
        critical_dims = requirements.get("critical_dimensions", [])

        # Calculate confidence based on how far from 0.5
        confidence_distance = abs(prob - 0.5)
        if confidence_distance > 0.3:
            confidence = "high"
        elif confidence_distance > 0.15:
            confidence = "medium"
        else:
            confidence = "low"

        explanation = {
            "probability": round(prob, 3),
            "confidence": confidence,
            "factors": {
                "tier_score": perf.tier_scores.get(str(task_complexity), 0),
                "overall_score": perf.overall_score,
                "critical_dimensions": {
                    dim: perf.dimension_scores.get(dim, 0)
                    for dim in critical_dims
                },
                "historical_failures": self.failure_count.get(model, 0),
                "historical_successes": self.success_count.get(model, 0),
                "model_max_tier": perf.max_tier,
                "task_complexity_tier": task_complexity
            },
            "strengths": perf.strengths,
            "weaknesses": perf.weaknesses,
            "recommendation": "recommended" if prob > 0.7 else "not recommended" if prob < 0.4 else "acceptable"
        }

        return explanation
