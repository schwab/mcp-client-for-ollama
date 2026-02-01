"""Tests for Phase 2.2 - Dynamic Model Optimization"""
import pytest
from mcp_client_for_ollama.models import ModelOptimizer, ModelSelector, PerformanceStore


@pytest.fixture
def selector():
    """Create ModelSelector with test data"""
    store = PerformanceStore()
    return ModelSelector(performance_store=store)


@pytest.fixture
def optimizer(selector):
    """Create ModelOptimizer with selector"""
    return ModelOptimizer(selector)


class TestModelOptimizer:
    """Tests for ModelOptimizer class"""

    def test_initialization(self, optimizer, selector):
        """Test optimizer initialization"""
        assert optimizer.selector == selector
        assert optimizer.runtime_metrics == {}
        assert optimizer.success_rates == {}
        assert optimizer.agent_model_metrics == {}

    def test_record_execution_success(self, optimizer):
        """Test recording successful execution"""
        optimizer.record_execution(
            model="qwen2.5:32b",
            agent_type="PLANNER",
            execution_time=2.5,
            success=True
        )

        # Check runtime metrics
        assert "qwen2.5:32b" in optimizer.runtime_metrics
        assert 2.5 in optimizer.runtime_metrics["qwen2.5:32b"]

        # Check success rates
        assert "qwen2.5:32b" in optimizer.success_rates
        successes, total = optimizer.success_rates["qwen2.5:32b"]
        assert successes == 1
        assert total == 1

        # Check agent-specific metrics
        assert "PLANNER" in optimizer.agent_model_metrics
        assert "qwen2.5:32b" in optimizer.agent_model_metrics["PLANNER"]
        agent_successes, agent_total = optimizer.agent_model_metrics["PLANNER"]["qwen2.5:32b"]
        assert agent_successes == 1
        assert agent_total == 1

    def test_record_execution_failure(self, optimizer):
        """Test recording failed execution"""
        optimizer.record_execution(
            model="qwen2.5:32b",
            agent_type="PLANNER",
            execution_time=1.5,
            success=False
        )

        # Check success rates (0 successes, 1 total)
        successes, total = optimizer.success_rates["qwen2.5:32b"]
        assert successes == 0
        assert total == 1

        # Check agent-specific metrics
        agent_successes, agent_total = optimizer.agent_model_metrics["PLANNER"]["qwen2.5:32b"]
        assert agent_successes == 0
        assert agent_total == 1

    def test_record_multiple_executions(self, optimizer):
        """Test recording multiple executions"""
        # Record 7 successes and 3 failures
        for i in range(7):
            optimizer.record_execution("qwen2.5:32b", "PLANNER", 2.0 + i * 0.5, True)

        for i in range(3):
            optimizer.record_execution("qwen2.5:32b", "PLANNER", 1.5, False)

        # Check totals
        successes, total = optimizer.success_rates["qwen2.5:32b"]
        assert successes == 7
        assert total == 10

        # Check runtime metrics (should have 10 entries)
        assert len(optimizer.runtime_metrics["qwen2.5:32b"]) == 10

    def test_get_model_metrics_no_data(self, optimizer):
        """Test getting metrics for model with no data"""
        metrics = optimizer.get_model_metrics("unknown-model")

        assert metrics["model"] == "unknown-model"
        assert metrics["total_executions"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["avg_execution_time"] == 0.0

    def test_get_model_metrics_with_data(self, optimizer):
        """Test getting metrics for model with data"""
        # Record some executions
        optimizer.record_execution("qwen2.5:32b", "PLANNER", 2.0, True)
        optimizer.record_execution("qwen2.5:32b", "PLANNER", 3.0, True)
        optimizer.record_execution("qwen2.5:32b", "PLANNER", 1.0, False)

        metrics = optimizer.get_model_metrics("qwen2.5:32b")

        assert metrics["model"] == "qwen2.5:32b"
        assert metrics["total_executions"] == 3
        assert metrics["successes"] == 2
        assert metrics["failures"] == 1
        assert metrics["success_rate"] == pytest.approx(0.667, rel=0.01)
        assert metrics["avg_execution_time"] == 2.0  # (2.0 + 3.0 + 1.0) / 3
        assert metrics["min_execution_time"] == 1.0
        assert metrics["max_execution_time"] == 3.0

    def test_get_agent_model_metrics_no_data(self, optimizer):
        """Test getting agent-model metrics with no data"""
        metrics = optimizer.get_agent_model_metrics("PLANNER", "unknown-model")

        assert metrics["agent_type"] == "PLANNER"
        assert metrics["model"] == "unknown-model"
        assert metrics["total_executions"] == 0
        assert metrics["success_rate"] == 0.0

    def test_get_agent_model_metrics_with_data(self, optimizer):
        """Test getting agent-model metrics with data"""
        # Record executions for PLANNER
        optimizer.record_execution("qwen2.5:32b", "PLANNER", 2.0, True)
        optimizer.record_execution("qwen2.5:32b", "PLANNER", 2.0, True)
        optimizer.record_execution("qwen2.5:32b", "PLANNER", 2.0, False)

        # Record executions for CODER (different agent)
        optimizer.record_execution("qwen2.5:32b", "CODER", 3.0, True)

        metrics = optimizer.get_agent_model_metrics("PLANNER", "qwen2.5:32b")

        assert metrics["agent_type"] == "PLANNER"
        assert metrics["model"] == "qwen2.5:32b"
        assert metrics["total_executions"] == 3
        assert metrics["successes"] == 2
        assert metrics["failures"] == 1
        assert metrics["success_rate"] == pytest.approx(0.667, rel=0.01)

    def test_optimization_recommendation_insufficient_data(self, optimizer):
        """Test recommendation with no execution history"""
        rec = optimizer.get_optimization_recommendation("PLANNER", "qwen2.5:32b")

        assert rec["recommendation"] == "insufficient_data"
        assert rec["current_model"] == "qwen2.5:32b"
        assert "No execution history" in rec["reason"]

    def test_optimization_recommendation_upgrade_quality(self, optimizer):
        """Test recommendation to upgrade quality (low success rate)"""
        # Simulate low success rate (50% < 70% threshold)
        for i in range(5):
            optimizer.record_execution("granite4:1b", "PLANNER", 1.0, True)
        for i in range(5):
            optimizer.record_execution("granite4:1b", "PLANNER", 1.0, False)

        rec = optimizer.get_optimization_recommendation("PLANNER", "granite4:1b")

        assert rec["recommendation"] == "upgrade_quality"
        assert rec["current_model"] == "granite4:1b"
        assert "suggested_model" in rec
        assert rec["suggested_model"] != "granite4:1b"  # Should suggest different model
        assert "too low" in rec["reason"].lower()
        assert rec["metrics"]["success_rate"] == 0.5

    def test_optimization_recommendation_optimize_speed(self, optimizer):
        """Test recommendation to optimize for speed (high success, slow execution)"""
        # Simulate very high success rate (98%) with slow execution (6s avg)
        for i in range(49):
            optimizer.record_execution("qwen3:30b-a3b", "PLANNER", 6.0, True)
        for i in range(1):
            optimizer.record_execution("qwen3:30b-a3b", "PLANNER", 6.0, False)

        rec = optimizer.get_optimization_recommendation("PLANNER", "qwen3:30b-a3b")

        # Should recommend faster model since success rate is high
        assert rec["recommendation"] == "optimize_speed"
        assert rec["current_model"] == "qwen3:30b-a3b"
        assert "suggested_model" in rec
        assert "slow execution" in rec["reason"].lower()
        assert rec["metrics"]["success_rate"] > 0.95
        assert rec["metrics"]["avg_execution_time"] > 5.0

    def test_optimization_recommendation_maintain(self, optimizer):
        """Test recommendation to maintain current model (good performance)"""
        # Simulate good success rate (85%) with reasonable speed (3s)
        for i in range(17):
            optimizer.record_execution("qwen2.5:32b", "PLANNER", 3.0, True)
        for i in range(3):
            optimizer.record_execution("qwen2.5:32b", "PLANNER", 3.0, False)

        rec = optimizer.get_optimization_recommendation("PLANNER", "qwen2.5:32b")

        assert rec["recommendation"] == "maintain"
        assert rec["current_model"] == "qwen2.5:32b"
        assert "good" in rec["reason"].lower()
        assert 0.7 <= rec["metrics"]["success_rate"] <= 0.95

    def test_get_all_recommendations(self, optimizer):
        """Test getting recommendations for all agents"""
        # Record data for multiple agents
        for i in range(10):
            optimizer.record_execution("qwen2.5:32b", "PLANNER", 2.0, True)

        for i in range(5):
            optimizer.record_execution("granite4:1b", "CODER", 1.0, True)
        for i in range(5):
            optimizer.record_execution("granite4:1b", "CODER", 1.0, False)

        all_recs = optimizer.get_all_recommendations()

        # Should have recommendations for both agents
        assert "PLANNER" in all_recs
        assert "CODER" in all_recs

        # Check that recommendations are valid types
        assert all_recs["PLANNER"]["recommendation"] in ["maintain", "insufficient_data", "upgrade_quality", "optimize_speed"]
        assert all_recs["CODER"]["recommendation"] in ["maintain", "insufficient_data", "upgrade_quality", "optimize_speed"]

        # If we got actual data (not insufficient), verify logic
        if all_recs["PLANNER"]["recommendation"] != "insufficient_data":
            # PLANNER should maintain (100% success rate, fast execution)
            assert all_recs["PLANNER"]["recommendation"] in ["maintain", "optimize_speed"]

        if all_recs["CODER"]["recommendation"] != "insufficient_data":
            # CODER should upgrade (50% success rate)
            assert all_recs["CODER"]["recommendation"] == "upgrade_quality"

    def test_get_summary_no_data(self, optimizer):
        """Test summary with no data"""
        summary = optimizer.get_summary()

        assert summary["total_models_tracked"] == 0
        assert summary["total_agents_tracked"] == 0
        assert summary["total_executions"] == 0
        assert summary["overall_success_rate"] == 0.0
        assert summary["top_models"] == []

    def test_get_summary_with_data(self, optimizer):
        """Test summary with execution data"""
        # Record data for multiple models
        for i in range(8):
            optimizer.record_execution("qwen2.5:32b", "PLANNER", 2.0, True)
        for i in range(2):
            optimizer.record_execution("qwen2.5:32b", "PLANNER", 2.0, False)

        for i in range(6):
            optimizer.record_execution("granite4:3b", "CODER", 1.5, True)
        for i in range(0):
            optimizer.record_execution("granite4:3b", "CODER", 1.5, False)

        summary = optimizer.get_summary()

        assert summary["total_models_tracked"] == 2
        assert summary["total_agents_tracked"] == 2
        assert summary["total_executions"] == 16
        # Overall: 14 successes / 16 total = 0.875
        assert summary["overall_success_rate"] == pytest.approx(0.875, rel=0.01)

        # Top models should include both (both have >= 5 executions)
        assert len(summary["top_models"]) == 2
        # granite4:3b should be first (100% success rate)
        assert summary["top_models"][0]["model"] == "granite4:3b"
        assert summary["top_models"][0]["success_rate"] == 1.0

    def test_multiple_agents_different_models(self, optimizer):
        """Test tracking different models for different agents"""
        # PLANNER uses qwen2.5:32b
        for i in range(10):
            optimizer.record_execution("qwen2.5:32b", "PLANNER", 2.0, True)

        # CODER uses granite4:3b
        for i in range(10):
            optimizer.record_execution("granite4:3b", "CODER", 1.5, True)

        # Check agent-specific metrics
        planner_metrics = optimizer.get_agent_model_metrics("PLANNER", "qwen2.5:32b")
        coder_metrics = optimizer.get_agent_model_metrics("CODER", "granite4:3b")

        assert planner_metrics["total_executions"] == 10
        assert coder_metrics["total_executions"] == 10

        # PLANNER shouldn't have granite4:3b data
        planner_granite = optimizer.get_agent_model_metrics("PLANNER", "granite4:3b")
        assert planner_granite["total_executions"] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
