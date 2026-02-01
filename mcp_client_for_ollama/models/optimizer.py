"""Dynamic model optimization based on runtime performance.

This module provides the ModelOptimizer class which tracks execution metrics
and recommends model changes based on success rates and execution times.
"""

import logging
from typing import Dict, List, Tuple, Optional
from .selector import ModelSelector

logger = logging.getLogger(__name__)


class ModelOptimizer:
    """Optimize model selection based on runtime metrics.

    Tracks execution times and success rates to recommend model changes:
    - Upgrade to better quality model if success rate is too low
    - Downgrade to faster model if success rate is very high but execution is slow
    """

    def __init__(self, selector: ModelSelector):
        """Initialize optimizer with model selector.

        Args:
            selector: ModelSelector instance for recommendations
        """
        self.selector = selector
        self.runtime_metrics: Dict[str, List[float]] = {}  # model -> [execution_times]
        self.success_rates: Dict[str, Tuple[int, int]] = {}  # model -> (successes, total)
        self.agent_model_metrics: Dict[str, Dict[str, Tuple[int, int]]] = {}  # agent -> model -> (successes, total)

    def record_execution(self,
                        model: str,
                        agent_type: str,
                        execution_time: float,
                        success: bool,
                        tokens_used: int = 0):
        """Record execution metrics for a model.

        Args:
            model: Model name
            agent_type: Agent type that used the model
            execution_time: Execution time in seconds
            success: Whether execution succeeded
            tokens_used: Number of tokens used (optional)
        """
        # Track execution time
        if model not in self.runtime_metrics:
            self.runtime_metrics[model] = []
        self.runtime_metrics[model].append(execution_time)

        # Track overall success rate
        if model not in self.success_rates:
            self.success_rates[model] = (0, 0)

        successes, total = self.success_rates[model]
        if success:
            successes += 1
        total += 1
        self.success_rates[model] = (successes, total)

        # Track per-agent success rate
        if agent_type not in self.agent_model_metrics:
            self.agent_model_metrics[agent_type] = {}

        if model not in self.agent_model_metrics[agent_type]:
            self.agent_model_metrics[agent_type][model] = (0, 0)

        agent_successes, agent_total = self.agent_model_metrics[agent_type][model]
        if success:
            agent_successes += 1
        agent_total += 1
        self.agent_model_metrics[agent_type][model] = (agent_successes, agent_total)

        logger.debug(f"Recorded execution: {model}/{agent_type} - {execution_time:.2f}s - {'success' if success else 'failure'}")

    def get_model_metrics(self, model: str) -> Dict:
        """Get runtime metrics for a model.

        Args:
            model: Model name

        Returns:
            Dictionary with execution times, success rate, etc.
        """
        if model not in self.success_rates:
            return {
                "model": model,
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "min_execution_time": 0.0,
                "max_execution_time": 0.0
            }

        successes, total = self.success_rates[model]
        success_rate = successes / total if total > 0 else 0.0

        exec_times = self.runtime_metrics.get(model, [])
        avg_time = sum(exec_times) / len(exec_times) if exec_times else 0.0
        min_time = min(exec_times) if exec_times else 0.0
        max_time = max(exec_times) if exec_times else 0.0

        return {
            "model": model,
            "total_executions": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": round(success_rate, 3),
            "avg_execution_time": round(avg_time, 2),
            "min_execution_time": round(min_time, 2),
            "max_execution_time": round(max_time, 2)
        }

    def get_agent_model_metrics(self, agent_type: str, model: str) -> Dict:
        """Get metrics for specific agent-model combination.

        Args:
            agent_type: Agent type
            model: Model name

        Returns:
            Dictionary with success rate and execution count
        """
        if agent_type not in self.agent_model_metrics:
            return {
                "agent_type": agent_type,
                "model": model,
                "total_executions": 0,
                "success_rate": 0.0
            }

        if model not in self.agent_model_metrics[agent_type]:
            return {
                "agent_type": agent_type,
                "model": model,
                "total_executions": 0,
                "success_rate": 0.0
            }

        successes, total = self.agent_model_metrics[agent_type][model]
        success_rate = successes / total if total > 0 else 0.0

        return {
            "agent_type": agent_type,
            "model": model,
            "total_executions": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": round(success_rate, 3)
        }

    def get_optimization_recommendation(self, agent_type: str, current_model: Optional[str] = None) -> Dict:
        """Recommend model optimization for agent.

        Analyzes current performance and recommends:
        - Upgrade to quality if success rate < 70%
        - Optimize for speed if success rate > 95% and avg time > 5s
        - Maintain if performance is good

        Args:
            agent_type: Agent type to optimize
            current_model: Current model being used (if None, gets best from selector)

        Returns:
            Dictionary with recommendation:
            - recommendation: "upgrade_quality", "optimize_speed", "maintain", or "insufficient_data"
            - current_model: Current model name
            - suggested_model: Recommended model (if applicable)
            - reason: Explanation of recommendation
            - metrics: Current performance metrics
        """
        # Get current model if not provided
        if not current_model:
            # Get top recommendation from selector
            recommendations = self.selector.get_recommendations(agent_type, top_k=1)
            if not recommendations:
                return {"recommendation": "insufficient_data", "reason": "No model recommendations available"}
            current_model = recommendations[0]["model"]

        # Get metrics for current model with this agent
        agent_metrics = self.get_agent_model_metrics(agent_type, current_model)

        if agent_metrics["total_executions"] == 0:
            return {
                "recommendation": "insufficient_data",
                "current_model": current_model,
                "reason": "No execution history for this agent-model combination"
            }

        # Get overall model metrics
        model_metrics = self.get_model_metrics(current_model)

        success_rate = agent_metrics["success_rate"]
        avg_time = model_metrics["avg_execution_time"]

        # Decision logic
        if success_rate < 0.7:
            # Need better quality
            better_model = self.selector.optimize_for_quality(agent_type)
            return {
                "recommendation": "upgrade_quality",
                "current_model": current_model,
                "suggested_model": better_model,
                "reason": f"Success rate too low: {success_rate:.2%} (target: 70%+)",
                "metrics": {
                    "success_rate": success_rate,
                    "avg_execution_time": avg_time,
                    "executions": agent_metrics["total_executions"]
                }
            }

        if success_rate > 0.95 and avg_time > 5.0:
            # Can use faster model
            faster_model = self.selector.optimize_for_speed(agent_type)
            if faster_model != current_model:  # Only recommend if different
                return {
                    "recommendation": "optimize_speed",
                    "current_model": current_model,
                    "suggested_model": faster_model,
                    "reason": f"High success rate ({success_rate:.2%}), slow execution ({avg_time:.1f}s) - can use faster model",
                    "metrics": {
                        "success_rate": success_rate,
                        "avg_execution_time": avg_time,
                        "executions": agent_metrics["total_executions"]
                    }
                }

        # Performance is acceptable
        return {
            "recommendation": "maintain",
            "current_model": current_model,
            "success_rate": success_rate,
            "avg_execution_time": avg_time,
            "reason": f"Performance is good (success: {success_rate:.2%}, time: {avg_time:.1f}s)",
            "metrics": {
                "success_rate": success_rate,
                "avg_execution_time": avg_time,
                "executions": agent_metrics["total_executions"]
            }
        }

    def get_all_recommendations(self) -> Dict[str, Dict]:
        """Get optimization recommendations for all agents with execution history.

        Returns:
            Dictionary mapping agent_type -> recommendation
        """
        recommendations = {}

        for agent_type in self.agent_model_metrics.keys():
            rec = self.get_optimization_recommendation(agent_type)
            recommendations[agent_type] = rec

        return recommendations

    def get_summary(self) -> Dict:
        """Get summary of all tracked metrics.

        Returns:
            Dictionary with overall statistics
        """
        total_models = len(self.success_rates)
        total_agents = len(self.agent_model_metrics)

        # Calculate overall success rate
        total_successes = sum(s for s, _ in self.success_rates.values())
        total_executions = sum(t for _, t in self.success_rates.values())
        overall_success_rate = total_successes / total_executions if total_executions > 0 else 0.0

        # Get model rankings by success rate
        model_rankings = []
        for model, (successes, total) in self.success_rates.items():
            if total >= 5:  # Only include models with sufficient data
                rate = successes / total
                model_rankings.append({
                    "model": model,
                    "success_rate": round(rate, 3),
                    "executions": total
                })

        model_rankings.sort(key=lambda x: x["success_rate"], reverse=True)

        return {
            "total_models_tracked": total_models,
            "total_agents_tracked": total_agents,
            "total_executions": total_executions,
            "overall_success_rate": round(overall_success_rate, 3),
            "top_models": model_rankings[:5]
        }
