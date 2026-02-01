"""Tests for Model Intelligence System (Phase 1)."""
import pytest
import json
import tempfile
from pathlib import Path

from mcp_client_for_ollama.models import (
    PerformanceStore,
    ModelPerformance,
    ModelSelector,
    SelectionContext,
    AGENT_REQUIREMENTS
)


@pytest.fixture
def sample_test_results():
    """Create sample test results for testing."""
    return {
        "qwen3:30b-a3b": {
            "model": "qwen3:30b-a3b",
            "timestamp": "2026-01-25T12:00:00",
            "temperature": 0.2,
            "summary": {
                "overall_score": 90.6,
                "passed": True,
                "dimension_averages": {
                    "tool_selection": 100.0,
                    "parameters": 86.4,
                    "planning": 94.6,
                    "context": 93.3,
                    "error_handling": 98.3,
                    "reasoning": 55.6
                }
            },
            "tier_details": {
                "1": {"average_score": 96.2, "total_tests": 20},
                "2": {"average_score": 86.7, "total_tests": 5},
                "3": {"average_score": 84.8, "total_tests": 5}
            }
        },
        "granite4:3b": {
            "model": "granite4:3b",
            "timestamp": "2026-01-25T12:00:00",
            "temperature": 0.2,
            "summary": {
                "overall_score": 84.0,
                "passed": True,
                "dimension_averages": {
                    "tool_selection": 95.0,
                    "parameters": 75.0,
                    "planning": 85.0,
                    "context": 91.7,
                    "error_handling": 97.5,
                    "reasoning": 45.0
                }
            },
            "tier_details": {
                "1": {"average_score": 92.3, "total_tests": 20},
                "2": {"average_score": 84.4, "total_tests": 5},
                "3": {"average_score": 72.9, "total_tests": 5}
            }
        }
    }


@pytest.fixture
def temp_test_suite_dir(sample_test_results):
    """Create temporary directory with test results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create result files
        for model_name, data in sample_test_results.items():
            model_dir = test_dir / model_name.replace(":", "_")
            model_dir.mkdir()
            result_file = model_dir / f"report_{model_name.replace(':', '_')}_latest.json"
            with open(result_file, 'w') as f:
                json.dump(data, f)

        yield test_dir


class TestPerformanceStore:
    """Tests for PerformanceStore."""

    def test_init_no_data(self):
        """Test initialization with no test data."""
        store = PerformanceStore(test_suite_path="/nonexistent/path")
        assert len(store.models) == 0
        assert store.last_update is None

    def test_load_test_results(self, temp_test_suite_dir):
        """Test loading test results from directory."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))

        assert len(store.models) == 2
        assert "qwen3:30b-a3b" in store.models
        assert "granite4:3b" in store.models
        assert store.last_update is not None

    def test_model_performance_fields(self, temp_test_suite_dir):
        """Test ModelPerformance fields are correctly populated."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        perf = store.get_model_performance("qwen3:30b-a3b")

        assert perf is not None
        assert perf.overall_score == 90.6
        assert perf.passed is True
        assert perf.max_tier == 3  # Passes all tiers
        assert "planning" in perf.strengths  # 94.6 > 70
        assert "reasoning" not in perf.strengths  # 55.6 < 70

    def test_list_models_filtering(self, temp_test_suite_dir):
        """Test model filtering by criteria."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))

        # Filter by minimum score
        high_score = store.list_models(min_score=88.0)
        assert len(high_score) == 1
        assert high_score[0].model == "qwen3:30b-a3b"

        # Filter by tier
        tier2_models = store.list_models(min_tier=2)
        assert len(tier2_models) == 2  # Both pass tier 2

        # Filter by required dimensions
        planning_strong = store.list_models(required_dimensions=["planning"])
        assert len(planning_strong) == 2  # Both have planning > 70

    def test_get_best_for_agent(self, temp_test_suite_dir):
        """Test getting best model for agent type."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))

        # PLANNER needs planning + tool_selection
        best_planner = store.get_best_for_agent("PLANNER")
        assert best_planner is not None
        assert best_planner.model == "qwen3:30b-a3b"  # Highest score

        # READER needs context + tool_selection (lower requirements)
        best_reader = store.get_best_for_agent("READER")
        assert best_reader is not None
        # Could be either model depending on scoring

    def test_get_fallbacks(self, temp_test_suite_dir):
        """Test getting fallback models."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))

        fallbacks = store.get_fallbacks("qwen3:30b-a3b", count=1)
        assert len(fallbacks) <= 1
        if fallbacks:
            assert fallbacks[0].model != "qwen3:30b-a3b"

    def test_export_summary(self, temp_test_suite_dir):
        """Test summary statistics export."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        summary = store.export_summary()

        assert summary["total_models"] == 2
        assert summary["passing_models"] == 2
        assert summary["top_model"] == "qwen3:30b-a3b"
        assert summary["average_score"] > 0


class TestModelSelector:
    """Tests for ModelSelector."""

    def test_init(self, temp_test_suite_dir):
        """Test selector initialization."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        assert selector.store == store
        assert len(selector.selection_history) == 0
        assert len(selector.failure_count) == 0

    def test_select_model_basic(self, temp_test_suite_dir):
        """Test basic model selection."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        context = SelectionContext(
            agent_type="PLANNER",
            task_complexity=2
        )

        primary, fallbacks = selector.select_model(context)

        assert primary is not None
        assert isinstance(fallbacks, list)
        assert len(selector.selection_history) == 1

    def test_select_with_available_models(self, temp_test_suite_dir):
        """Test selection filtered by available models."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        context = SelectionContext(
            agent_type="CODER",
            task_complexity=2
        )

        # Only granite4:3b available
        primary, fallbacks = selector.select_model(
            context,
            available_models=["granite4:3b"]
        )

        assert primary == "granite4:3b"

    def test_select_with_previous_failures(self, temp_test_suite_dir):
        """Test selection excludes failed models."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        context = SelectionContext(
            agent_type="CODER",
            task_complexity=2,
            previous_failures=["qwen3:30b-a3b"]
        )

        primary, fallbacks = selector.select_model(context)

        assert primary != "qwen3:30b-a3b"  # Should avoid failed model

    def test_report_success_failure(self, temp_test_suite_dir):
        """Test success/failure reporting."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        # Report success
        selector.report_success("qwen3:30b-a3b", "CODER")
        assert selector.success_count["qwen3:30b-a3b"] == 1

        # Report failure
        selector.report_failure("qwen3:30b-a3b", "CODER", "Timeout")
        assert selector.failure_count["qwen3:30b-a3b"] == 1

    def test_get_recommendations(self, temp_test_suite_dir):
        """Test getting recommendations."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        recommendations = selector.get_recommendations("PLANNER", top_k=2)

        assert len(recommendations) <= 2
        assert all("model" in r for r in recommendations)
        assert all("overall_score" in r for r in recommendations)

    def test_optimize_for_speed(self, temp_test_suite_dir):
        """Test speed optimization."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        # granite4:3b (3B) should be preferred over qwen3:30b-a3b (30B)
        speed_model = selector.optimize_for_speed("READER")

        # Should select smaller model if it meets requirements
        assert speed_model in ["granite4:3b", "qwen3:30b-a3b"]

    def test_optimize_for_quality(self, temp_test_suite_dir):
        """Test quality optimization."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        quality_model = selector.optimize_for_quality("CODER")

        # Should select highest scoring model
        assert quality_model == "qwen3:30b-a3b"

    def test_get_success_rate(self, temp_test_suite_dir):
        """Test success rate calculation."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        # No data
        rate = selector.get_success_rate("unknown_model")
        assert rate == 0.5  # Default

        # With data
        selector.report_success("qwen3:30b-a3b", "CODER")
        selector.report_success("qwen3:30b-a3b", "CODER")
        selector.report_failure("qwen3:30b-a3b", "CODER")

        rate = selector.get_success_rate("qwen3:30b-a3b")
        assert rate == 2/3  # 2 successes out of 3 total

    def test_get_selection_stats(self, temp_test_suite_dir):
        """Test selection statistics."""
        store = PerformanceStore(test_suite_path=str(temp_test_suite_dir))
        selector = ModelSelector(store)

        # Make some selections
        context = SelectionContext(agent_type="PLANNER", task_complexity=2)
        selector.select_model(context)
        selector.select_model(context)

        selector.report_success("qwen3:30b-a3b", "PLANNER")
        selector.report_failure("qwen3:30b-a3b", "PLANNER")

        stats = selector.get_selection_stats()

        assert stats["total_selections"] == 2
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 1
        assert stats["overall_success_rate"] == 0.5


class TestAgentRequirements:
    """Test agent requirement definitions."""

    def test_all_agents_have_requirements(self):
        """Test all standard agents have requirements defined."""
        expected_agents = [
            "PLANNER", "CODER", "READER", "EXECUTOR",
            "DEBUGGER", "RESEARCHER", "AGGREGATOR",
            "ARTIFACT_AGENT", "TOOL_FORM_AGENT"
        ]

        for agent in expected_agents:
            assert agent in AGENT_REQUIREMENTS
            reqs = AGENT_REQUIREMENTS[agent]
            assert "min_score" in reqs
            assert "min_tier" in reqs
            assert "critical_dimensions" in reqs

    def test_requirement_tiers_valid(self):
        """Test requirement tiers are valid (1-3)."""
        for agent, reqs in AGENT_REQUIREMENTS.items():
            assert 1 <= reqs["min_tier"] <= 3

    def test_requirement_scores_valid(self):
        """Test requirement scores are valid (0-100)."""
        for agent, reqs in AGENT_REQUIREMENTS.items():
            assert 0 <= reqs["min_score"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
