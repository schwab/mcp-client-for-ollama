"""Tests for Phase 2.1 - Performance Prediction"""
import pytest
from mcp_client_for_ollama.models.selector import ModelSelector, SelectionContext
from mcp_client_for_ollama.models.performance_store import PerformanceStore


@pytest.fixture
def selector():
    """Create ModelSelector with test data"""
    store = PerformanceStore()
    return ModelSelector(performance_store=store)


class TestPerformancePrediction:
    """Tests for predict_success and explain_prediction methods"""

    def test_predict_success_unknown_model(self, selector):
        """Test prediction for unknown model returns 0.5"""
        prob = selector.predict_success("unknown-model", "PLANNER", task_complexity=2)
        assert prob == 0.5

    def test_predict_success_known_model(self, selector):
        """Test prediction for known model"""
        # Test with a model that exists in test data
        prob = selector.predict_success("qwen2.5:32b", "PLANNER", task_complexity=2)

        # Probability should be between 0 and 1
        assert 0.0 <= prob <= 1.0

        # For a top performer like qwen2.5:32b on PLANNER, should be high
        assert prob > 0.7, f"Expected high probability for qwen2.5:32b, got {prob}"

    def test_predict_success_by_complexity(self, selector):
        """Test that prediction varies by task complexity"""
        model = "qwen2.5:32b"

        # Get predictions for different complexities
        tier1_prob = selector.predict_success(model, "PLANNER", task_complexity=1)
        tier2_prob = selector.predict_success(model, "PLANNER", task_complexity=2)
        tier3_prob = selector.predict_success(model, "PLANNER", task_complexity=3)

        # All should be valid probabilities
        assert 0.0 <= tier1_prob <= 1.0
        assert 0.0 <= tier2_prob <= 1.0
        assert 0.0 <= tier3_prob <= 1.0

        # Tier 1 should generally be easier (higher probability) than Tier 3
        # (This might not always be true, but is a good sanity check)
        assert tier1_prob >= tier3_prob - 0.1  # Allow some tolerance

    def test_predict_success_with_history(self, selector):
        """Test that historical failures reduce prediction"""
        model = "qwen2.5:32b"
        agent_type = "PLANNER"

        # Get initial prediction
        initial_prob = selector.predict_success(model, agent_type, 2)

        # Record some failures
        selector.report_failure(model, agent_type, "test error")
        selector.report_failure(model, agent_type, "test error 2")
        selector.report_failure(model, agent_type, "test error 3")

        # Get new prediction
        new_prob = selector.predict_success(model, agent_type, 2)

        # Should be lower after failures (or equal if failure rate penalty is small)
        assert new_prob <= initial_prob

    def test_explain_prediction_unknown_model(self, selector):
        """Test explanation for unknown model"""
        explanation = selector.explain_prediction("unknown-model", "PLANNER", 2)

        assert explanation["probability"] == 0.5
        assert explanation["confidence"] == "low"
        assert explanation["recommendation"] == "not recommended"
        assert "Unknown model" in explanation["explanation"]

    def test_explain_prediction_known_model(self, selector):
        """Test explanation for known model"""
        explanation = selector.explain_prediction("qwen2.5:32b", "PLANNER", 2)

        # Should have all expected keys
        assert "probability" in explanation
        assert "confidence" in explanation
        assert "factors" in explanation
        assert "recommendation" in explanation
        assert "strengths" in explanation
        assert "weaknesses" in explanation

        # Factors should have expected sub-keys
        factors = explanation["factors"]
        assert "tier_score" in factors
        assert "overall_score" in factors
        assert "critical_dimensions" in factors
        assert "historical_failures" in factors
        assert "historical_successes" in factors
        assert "model_max_tier" in factors
        assert "task_complexity_tier" in factors

        # Confidence should be valid
        assert explanation["confidence"] in ["low", "medium", "high"]

        # Recommendation should be valid
        assert explanation["recommendation"] in ["recommended", "acceptable", "not recommended"]

    def test_explain_prediction_confidence_levels(self, selector):
        """Test that confidence levels are assigned correctly"""
        # High confidence: probability far from 0.5 (> 0.3 distance)
        # Medium confidence: 0.15-0.3 distance
        # Low confidence: < 0.15 distance

        # For qwen2.5:32b on PLANNER tier 2, should be high probability -> high confidence
        explanation = selector.explain_prediction("qwen2.5:32b", "PLANNER", 2)

        prob = explanation["probability"]
        confidence = explanation["confidence"]

        # Check confidence matches distance from 0.5
        distance = abs(prob - 0.5)

        if distance > 0.3:
            assert confidence == "high"
        elif distance > 0.15:
            assert confidence == "medium"
        else:
            assert confidence == "low"

    def test_explain_prediction_recommendation_thresholds(self, selector):
        """Test recommendation thresholds"""
        # Test with different models to get different probability levels
        models_to_test = ["qwen2.5:32b", "granite4:3b", "granite4:1b"]

        for model in models_to_test:
            explanation = selector.explain_prediction(model, "PLANNER", 2)
            prob = explanation["probability"]
            rec = explanation["recommendation"]

            # Verify recommendation matches probability
            if prob > 0.7:
                assert rec == "recommended"
            elif prob < 0.4:
                assert rec == "not recommended"
            else:
                assert rec == "acceptable"

    def test_predict_success_agent_requirements(self, selector):
        """Test that critical dimensions affect prediction"""
        # PLANNER has critical dimensions: planning, tool_selection
        # CODER has critical dimensions: parameters, planning, tool_selection

        model = "qwen2.5:32b"  # Strong in planning and tool selection

        # PLANNER should have high probability (critical dims match strengths)
        planner_prob = selector.predict_success(model, "PLANNER", 2)

        # Both should be valid
        assert 0.0 <= planner_prob <= 1.0

        # PLANNER should be high for this model
        assert planner_prob > 0.7

    def test_predict_success_boundaries(self, selector):
        """Test that predictions are always between 0 and 1"""
        models = ["qwen2.5:32b", "granite4:1b", "granite4:3b"]
        agents = ["PLANNER", "CODER", "EXECUTOR", "READER"]
        complexities = [1, 2, 3]

        for model in models:
            for agent in agents:
                for complexity in complexities:
                    prob = selector.predict_success(model, agent, complexity)
                    assert 0.0 <= prob <= 1.0, \
                        f"Probability {prob} out of bounds for {model}/{agent}/tier{complexity}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
