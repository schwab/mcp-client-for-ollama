# Model Intelligence Integration Roadmap
## Intelligent Agent-Model Matching via LLM Testing Suite

## Executive Summary

This roadmap outlines the integration of the **os_llm_testing_suite** performance data into mcp_client_for_ollama's agent delegation system. The goal is to create an intelligent model selection engine that automatically matches the optimal model to each agent based on empirical performance data across 6 dimensions and 3 complexity tiers.

**Key Insight:** The testing suite reveals that **parameter accuracy** (avg: 31.1/100) and **multi-step planning** (avg: 58.2/100) are the primary differentiators between models. Only 3/32 models pass all tiers, making intelligent selection critical for agent success.

---

## Current State Analysis

### Testing Suite Capabilities

**62 Tests Across 3 Tiers:**
- **Tier 1** (Basic Tool Calling): 20 tests, 85% pass threshold
- **Tier 2** (Multi-Step Reasoning): 21 tests, 75% pass threshold
- **Tier 3** (Complex Workflows): 21 tests, 65% pass threshold

**6 Performance Dimensions:**
1. **Tool Selection** (25% weight) - Choosing correct tools
2. **Parameters** (30% weight) - Accurate parameter values **[CRITICAL]**
3. **Planning** (20% weight) - Correct sequencing **[CRITICAL]**
4. **Context Maintenance** (10% weight) - Multi-turn tracking
5. **Error Handling** (10% weight) - Recovery strategies
6. **Reasoning Transparency** (5% weight) - Decision clarity

**32 Models Tested** with scores ranging from 38.5 to 90.6 (only 3 passing)

### Current Agent System

**9 Specialized Agents in mcp_client_for_ollama:**
- PLANNER - Task decomposition
- READER - Code analysis
- CODER - Code writing
- EXECUTOR - Command execution
- DEBUGGER - Bug fixing
- RESEARCHER - Analysis
- AGGREGATOR - Results synthesis
- ARTIFACT_AGENT - Visualization
- TOOL_FORM_AGENT - Tool wrapping

**Current Model Selection:** Single global model or manual per-agent configuration

---

## Key Findings from Testing Suite

### Top Performers (Overall Score)

| Rank | Model | Score | Tier 1 | Tier 2 | Tier 3 | Key Strengths |
|------|-------|-------|--------|--------|--------|---------------|
| 1 | qwen3:30b-a3b | 90.6 | 96.2 | 86.7 | 84.8 | Parameters (86.4), Planning (94.6) |
| 2 | qwen2.5:32b | 88.4 | 95.4 | 83.7 | 82.7 | Tool Selection (97.5), Planning (92.9) |
| 3 | granite4:3b | 84.0 | 92.3 | 84.4 | 72.9 | Balanced, efficient (3B params) |
| 4 | qwen3-vl:8b | 77.9 | 96.7 | 64.6 | 66.4 | Tool Selection (92.5), vision capable |
| 5 | granite4:1b | 77.4 | 89.9 | 71.7 | 65.3 | Ultra-fast, good Tier 1 |

### Performance by Dimension

**Critical Weaknesses Across Models:**
- **Parameters** (31.1 avg) - Most models struggle with accurate values
- **Reasoning** (30.1 avg) - Explanation quality is poor
- **Planning** (58.2 avg) - Multi-step sequencing is hard

**Universal Strengths:**
- **Error Handling** (98.5 avg) - Consistently excellent
- **Output Format** (100.0 avg) - Perfect compliance

### Agent-Specific Insights

**For PLANNER Agent:**
- Needs: High planning (20% weight), tool selection (25% weight)
- Best models: qwen3:30b-a3b (94.6 planning), qwen2.5:32b (92.9 planning)
- Minimum tier: 2 (multi-step reasoning required)

**For CODER Agent:**
- Needs: High parameters (30% weight), planning (20% weight), tool selection (25% weight)
- Best models: qwen3:30b-a3b (86.4 params), qwen2.5:32b (82.0 params)
- Minimum tier: 2 (complex code workflows)

**For READER Agent:**
- Needs: High context (10% weight), tool selection (25% weight)
- Best models: qwen3:30b-a3b (93.3 context), granite4:3b (91.7 context)
- Minimum tier: 1 (basic tool calling sufficient)

**For EXECUTOR Agent:**
- Needs: High tool selection (25% weight), error handling (10% weight), parameters (30% weight)
- Best models: qwen2.5:32b (97.5 tool selection), qwen3:30b-a3b (98.3 error handling)
- Minimum tier: 2 (command sequences)

**For AGGREGATOR Agent:**
- Needs: High context (10% weight), planning (20% weight)
- Best models: qwen3:30b-a3b (93.3 context, 94.6 planning)
- Minimum tier: 2 (synthesizing multiple inputs)

---

## Integration Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│              mcp_client_for_ollama                      │
│                                                         │
│  ┌──────────────┐         ┌─────────────────┐         │
│  │   Agent      │────────>│  Model Selector │         │
│  │  Delegation  │         │    Engine       │         │
│  │   System     │         └─────────┬───────┘         │
│  └──────────────┘                   │                  │
│                                     │                  │
│                          ┌──────────▼──────────┐       │
│                          │  Performance Store  │       │
│                          │  (Test Suite Data)  │       │
│                          └─────────────────────┘       │
└─────────────────────────────────────────────────────────┘
                                   │
                                   │ Updates
                                   ▼
                    ┌──────────────────────────┐
                    │  os_llm_testing_suite    │
                    │  (External Test Runner)  │
                    └──────────────────────────┘
```

### Data Flow

1. **Initialization**: Load test suite results into performance store
2. **Agent Request**: PLANNER agent needs model for task decomposition
3. **Model Selection**:
   - Query performance store for models matching requirements
   - Score models based on dimension weights and tier requirements
   - Select optimal model with fallbacks
4. **Execution**: Agent uses selected model
5. **Performance Tracking**: Monitor success/failure, update preferences
6. **Periodic Testing**: Re-run test suite, update performance data

---

## Phase 1: Foundation (Weeks 1-3)

### 1.1 Performance Store Implementation

**Goal:** Create a local database of model performance metrics from test suite results.

**Implementation:**

```python
# New module: mcp_client_for_ollama/models/performance_store.py

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class ModelPerformance:
    """Model performance metrics from test suite"""
    model: str
    overall_score: float
    passed: bool
    tier_scores: Dict[str, float]  # {"1": 94.2, "2": 86.7, "3": 84.8}
    dimension_scores: Dict[str, float]  # {"tool_selection": 100.0, ...}
    test_count: int
    timestamp: str
    temperature: float

    # Computed fields
    max_tier: int = 1  # Highest tier passed
    strengths: List[str] = None  # Dimensions with score > 70
    weaknesses: List[str] = None  # Dimensions with score < 40

    def __post_init__(self):
        """Calculate derived fields"""
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

class PerformanceStore:
    """Store and query model performance data"""

    def __init__(self, test_suite_path: str = None):
        """
        Initialize performance store

        Args:
            test_suite_path: Path to os_llm_testing_suite results directory
        """
        self.test_suite_path = test_suite_path or "~/project/os_llm_testing_suite/results"
        self.models: Dict[str, ModelPerformance] = {}
        self.last_update: Optional[datetime] = None

        self.load_test_results()

    def load_test_results(self):
        """Load all test results from test suite"""
        results_dir = Path(self.test_suite_path).expanduser()

        if not results_dir.exists():
            print(f"Warning: Test suite results not found at {results_dir}")
            return

        # Find all JSON report files
        for json_file in results_dir.rglob("report_*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # Create ModelPerformance object
                perf = ModelPerformance(
                    model=data["model"],
                    overall_score=data["summary"]["overall_score"],
                    passed=data["summary"]["passed"],
                    tier_scores={
                        str(k): v["average_score"]
                        for k, v in data["tier_details"].items()
                    },
                    dimension_scores=data["summary"]["dimension_averages"],
                    test_count=sum(
                        v["total_tests"]
                        for v in data["tier_details"].values()
                    ),
                    timestamp=data["timestamp"],
                    temperature=data.get("temperature", 0.2)
                )

                # Store best result per model (highest overall score)
                model_name = perf.model
                if (model_name not in self.models or
                    perf.overall_score > self.models[model_name].overall_score):
                    self.models[model_name] = perf

            except Exception as e:
                print(f"Error loading {json_file}: {e}")

        self.last_update = datetime.now()
        print(f"Loaded performance data for {len(self.models)} models")

    def get_model_performance(self, model: str) -> Optional[ModelPerformance]:
        """Get performance data for specific model"""
        return self.models.get(model)

    def list_models(self,
                   min_score: float = 0.0,
                   min_tier: int = 1,
                   required_dimensions: List[str] = None) -> List[ModelPerformance]:
        """
        List models matching criteria

        Args:
            min_score: Minimum overall score
            min_tier: Minimum tier passed
            required_dimensions: Dimensions that must be strengths (>70)
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
        """Get best model for specific agent type"""
        # Agent requirements defined below
        requirements = AGENT_REQUIREMENTS.get(agent_type)
        if not requirements:
            return None

        candidates = self.list_models(
            min_score=requirements["min_score"],
            min_tier=requirements["min_tier"],
            required_dimensions=requirements["critical_dimensions"]
        )

        if not candidates:
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
        return candidates[0]

    def get_fallbacks(self,
                     primary_model: str,
                     count: int = 2,
                     max_score_delta: float = 10.0) -> List[ModelPerformance]:
        """Get fallback models similar to primary"""
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
        return [c[0] for c in candidates[:count]]

    def export_summary(self) -> Dict:
        """Export summary statistics"""
        if not self.models:
            return {}

        scores = [m.overall_score for m in self.models.values()]
        return {
            "total_models": len(self.models),
            "passing_models": len([m for m in self.models.values() if m.passed]),
            "average_score": sum(scores) / len(scores),
            "top_model": max(self.models.values(), key=lambda x: x.overall_score).model,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }

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
    "TOOL_FORM_AGENT": {
        "min_score": 65.0,
        "min_tier": 1,
        "critical_dimensions": ["tool_selection", "parameters"],
        "important_dimensions": ["context"]
    }
}
```

**Files to Create:**
- `mcp_client_for_ollama/models/performance_store.py`
- `mcp_client_for_ollama/models/agent_requirements.py` (optional split)

**Testing:**
- Unit tests for performance store
- Test with sample test suite results
- Verify model ranking accuracy

**Timeline:** 1 week

---

### 1.2 Model Selector Engine

**Goal:** Implement intelligent model selection logic based on agent requirements and performance data.

**Implementation:**

```python
# New module: mcp_client_for_ollama/models/selector.py

from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
import logging

from .performance_store import PerformanceStore, ModelPerformance

@dataclass
class SelectionContext:
    """Context for model selection"""
    agent_type: str
    task_complexity: int  # 1-3 (tier)
    required_tools: List[str] = None
    context_length: int = 0
    previous_failures: List[str] = None  # Models that failed
    performance_requirements: Dict[str, float] = None  # Custom dimension thresholds

class ModelSelector:
    """Intelligent model selection engine"""

    def __init__(self, performance_store: PerformanceStore):
        self.store = performance_store
        self.logger = logging.getLogger(__name__)

        # Selection history for learning
        self.selection_history: List[Dict] = []
        self.failure_count: Dict[str, int] = {}

    def select_model(self,
                    context: SelectionContext,
                    available_models: List[str] = None) -> Tuple[str, List[str]]:
        """
        Select optimal model for agent task

        Args:
            context: Selection context with agent type and requirements
            available_models: Models available for selection (None = all)

        Returns:
            (primary_model, fallback_models)
        """
        self.logger.info(f"Selecting model for {context.agent_type} (tier {context.task_complexity})")

        # Get base recommendation
        primary = self.store.get_best_for_agent(context.agent_type)

        if not primary:
            self.logger.warning(f"No models meet requirements for {context.agent_type}")
            return self._get_default_model(), []

        # Filter by available models
        if available_models and primary.model not in available_models:
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
            else:
                return self._get_default_model(), []

        # Exclude previous failures
        if context.previous_failures and primary.model in context.previous_failures:
            self.logger.info(f"{primary.model} previously failed, finding alternative")
            candidates = self.store.list_models(
                min_score=60.0,
                min_tier=context.task_complexity
            )
            for candidate in candidates:
                if candidate.model not in context.previous_failures:
                    primary = candidate
                    break

        # Apply custom performance requirements
        if context.performance_requirements:
            if not self._meets_requirements(primary, context.performance_requirements):
                self.logger.warning(f"{primary.model} doesn't meet custom requirements")
                # Find model that does
                candidates = self.store.list_models(min_score=60.0)
                for candidate in candidates:
                    if self._meets_requirements(candidate, context.performance_requirements):
                        primary = candidate
                        break

        # Get fallbacks
        fallbacks = self.store.get_fallbacks(primary.model, count=2)
        fallback_names = [f.model for f in fallbacks]

        # Record selection
        self.selection_history.append({
            "agent_type": context.agent_type,
            "primary": primary.model,
            "fallbacks": fallback_names,
            "timestamp": datetime.now().isoformat()
        })

        self.logger.info(f"Selected {primary.model} (score: {primary.overall_score:.1f})")
        return primary.model, fallback_names

    def _meets_requirements(self,
                          perf: ModelPerformance,
                          requirements: Dict[str, float]) -> bool:
        """Check if model meets custom dimension requirements"""
        for dim, min_score in requirements.items():
            if perf.dimension_scores.get(dim, 0) < min_score:
                return False
        return True

    def _get_default_model(self) -> str:
        """Get default fallback model"""
        # Return highest scoring model overall
        if self.store.models:
            best = max(self.store.models.values(), key=lambda x: x.overall_score)
            return best.model
        return "qwen2.5:7b"  # Hardcoded ultimate fallback

    def report_failure(self, model: str, agent_type: str, reason: str = None):
        """Report model failure for learning"""
        self.failure_count[model] = self.failure_count.get(model, 0) + 1
        self.logger.warning(f"Failure reported for {model} on {agent_type}: {reason}")

    def report_success(self, model: str, agent_type: str, metrics: Dict = None):
        """Report model success for learning"""
        self.logger.info(f"Success reported for {model} on {agent_type}")

    def get_recommendations(self, agent_type: str, top_k: int = 3) -> List[Dict]:
        """Get top K model recommendations for agent type"""
        requirements = AGENT_REQUIREMENTS.get(agent_type)
        if not requirements:
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
        """Generate human-readable explanation for recommendation"""
        requirements = AGENT_REQUIREMENTS.get(agent_type, {})
        critical = requirements.get("critical_dimensions", [])

        reasons = []
        reasons.append(f"Overall score: {perf.overall_score:.1f}")
        reasons.append(f"Max tier: {perf.max_tier}")

        for dim in critical:
            score = perf.dimension_scores.get(dim, 0)
            reasons.append(f"{dim}: {score:.1f}")

        return " | ".join(reasons)

    def optimize_for_speed(self, agent_type: str) -> str:
        """Select fastest model that meets minimum requirements"""
        requirements = AGENT_REQUIREMENTS.get(agent_type)
        if not requirements:
            return self._get_default_model()

        # Get all models that meet requirements
        candidates = self.store.list_models(
            min_score=requirements["min_score"] - 5,  # Slightly lower threshold
            min_tier=requirements["min_tier"],
            required_dimensions=requirements["critical_dimensions"]
        )

        if not candidates:
            return self._get_default_model()

        # Prefer smaller models (faster inference)
        # Parse model size from name (e.g., "qwen2.5:7b" -> 7)
        def get_size(model_name: str) -> float:
            parts = model_name.split(':')
            if len(parts) > 1:
                size_str = parts[1].replace('b', '').replace('B', '')
                try:
                    return float(size_str)
                except:
                    return 999.0  # Unknown size, deprioritize
            return 999.0

        candidates.sort(key=lambda x: get_size(x.model))
        return candidates[0].model

    def optimize_for_quality(self, agent_type: str) -> str:
        """Select highest quality model regardless of speed"""
        requirements = AGENT_REQUIREMENTS.get(agent_type)
        if not requirements:
            return self._get_default_model()

        candidates = self.store.list_models(
            min_score=requirements["min_score"],
            min_tier=requirements["min_tier"],
            required_dimensions=requirements["critical_dimensions"]
        )

        if not candidates:
            return self._get_default_model()

        # Return highest scoring
        return candidates[0].model
```

**Files to Create:**
- `mcp_client_for_ollama/models/selector.py`

**Testing:**
- Test selection for each agent type
- Test fallback logic
- Test custom requirements
- Test speed vs quality optimization

**Timeline:** 1 week

---

### 1.3 Integration with Agent Delegation

**Goal:** Connect model selector to existing agent delegation system.

**Implementation:**

```python
# Modification to: mcp_client_for_ollama/agents/delegation_client.py

from ..models.performance_store import PerformanceStore
from ..models.selector import ModelSelector, SelectionContext

class DelegationClient:
    """Existing delegation client with intelligent model selection"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize model intelligence
        self.perf_store = PerformanceStore()
        self.model_selector = ModelSelector(self.perf_store)

        # Configuration
        self.use_intelligent_selection = True  # Feature flag
        self.available_models = self._get_available_models()

    def _get_available_models(self) -> List[str]:
        """Get list of models available on Ollama server"""
        # Query Ollama API for available models
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except:
            return []  # Fall back to config

    async def delegate_task(self,
                          agent_type: str,
                          task: str,
                          context: Dict = None) -> Dict:
        """Delegate task with intelligent model selection"""

        # Determine task complexity (heuristic for now)
        task_complexity = self._estimate_complexity(task)

        # Select model intelligently
        if self.use_intelligent_selection:
            selection_context = SelectionContext(
                agent_type=agent_type,
                task_complexity=task_complexity,
                previous_failures=context.get("failed_models", []) if context else None
            )

            primary_model, fallbacks = self.model_selector.select_model(
                selection_context,
                available_models=self.available_models
            )
        else:
            # Use default from agent config
            primary_model = self.agents[agent_type].get("model", self.default_model)
            fallbacks = []

        # Execute with primary model
        try:
            result = await self._execute_agent(
                agent_type=agent_type,
                task=task,
                model=primary_model,
                context=context
            )

            # Report success
            self.model_selector.report_success(
                model=primary_model,
                agent_type=agent_type
            )

            return result

        except Exception as e:
            self.logger.error(f"Agent {agent_type} failed with {primary_model}: {e}")

            # Report failure
            self.model_selector.report_failure(
                model=primary_model,
                agent_type=agent_type,
                reason=str(e)
            )

            # Try fallbacks
            for fallback_model in fallbacks:
                try:
                    self.logger.info(f"Retrying with fallback: {fallback_model}")
                    result = await self._execute_agent(
                        agent_type=agent_type,
                        task=task,
                        model=fallback_model,
                        context=context
                    )

                    self.model_selector.report_success(
                        model=fallback_model,
                        agent_type=agent_type
                    )

                    return result

                except Exception as e2:
                    self.model_selector.report_failure(
                        model=fallback_model,
                        agent_type=agent_type,
                        reason=str(e2)
                    )
                    continue

            # All failed
            raise Exception(f"All models failed for {agent_type}")

    def _estimate_complexity(self, task: str) -> int:
        """Estimate task complexity (1-3) based on heuristics"""
        # Simple heuristics for now
        if any(word in task.lower() for word in ["analyze", "compare", "synthesize"]):
            return 3
        elif any(word in task.lower() for word in ["list", "find", "search"]):
            return 2
        else:
            return 1
```

**Files to Modify:**
- `mcp_client_for_ollama/agents/delegation_client.py`

**Timeline:** 1 week

---

## Phase 2: Enhanced Selection (Weeks 4-6)

### 2.1 Performance Prediction

**Goal:** Predict success probability for model-task combinations.

**Implementation:**

```python
# Extension to: mcp_client_for_ollama/models/selector.py

class ModelSelector:
    """Enhanced with performance prediction"""

    def predict_success(self,
                       model: str,
                       agent_type: str,
                       task_complexity: int) -> float:
        """
        Predict probability of success for model on task

        Returns: probability 0.0-1.0
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
        critical_strength = sum(
            perf.dimension_scores.get(dim, 0)
            for dim in critical_dims
        ) / (len(critical_dims) * 100.0) if critical_dims else 1.0

        # Weighted average
        predicted_prob = (base_prob * 0.6) + (critical_strength * 0.4)

        # Adjust based on historical failures
        failure_rate = self.failure_count.get(model, 0) / max(1, len(self.selection_history))
        predicted_prob *= (1.0 - (failure_rate * 0.3))  # Max 30% penalty

        return max(0.0, min(1.0, predicted_prob))

    def explain_prediction(self,
                          model: str,
                          agent_type: str,
                          task_complexity: int) -> Dict:
        """Explain prediction with breakdown"""
        prob = self.predict_success(model, agent_type, task_complexity)
        perf = self.store.get_model_performance(model)

        if not perf:
            return {"probability": prob, "explanation": "Unknown model"}

        requirements = AGENT_REQUIREMENTS.get(agent_type, {})
        critical_dims = requirements.get("critical_dimensions", [])

        explanation = {
            "probability": prob,
            "confidence": "high" if abs(prob - 0.5) > 0.3 else "medium",
            "factors": {
                "tier_score": perf.tier_scores.get(str(task_complexity), 0),
                "overall_score": perf.overall_score,
                "critical_dimensions": {
                    dim: perf.dimension_scores.get(dim, 0)
                    for dim in critical_dims
                },
                "historical_failures": self.failure_count.get(model, 0)
            },
            "recommendation": "recommended" if prob > 0.7 else "not recommended"
        }

        return explanation
```

**Timeline:** 1 week

---

### 2.2 Dynamic Model Optimization

**Goal:** Automatically adjust model selection based on runtime performance.

**Implementation:**

```python
# New module: mcp_client_for_ollama/models/optimizer.py

class ModelOptimizer:
    """Optimize model selection based on runtime metrics"""

    def __init__(self, selector: ModelSelector):
        self.selector = selector
        self.runtime_metrics: Dict[str, List[float]] = {}  # model -> [execution_times]
        self.success_rates: Dict[str, Tuple[int, int]] = {}  # model -> (successes, total)

    def record_execution(self,
                        model: str,
                        agent_type: str,
                        execution_time: float,
                        success: bool,
                        tokens_used: int = 0):
        """Record execution metrics"""
        # Track execution time
        if model not in self.runtime_metrics:
            self.runtime_metrics[model] = []
        self.runtime_metrics[model].append(execution_time)

        # Track success rate
        if model not in self.success_rates:
            self.success_rates[model] = (0, 0)

        successes, total = self.success_rates[model]
        if success:
            successes += 1
        total += 1
        self.success_rates[model] = (successes, total)

    def get_optimization_recommendation(self, agent_type: str) -> Dict:
        """Recommend model optimization for agent"""
        current_model = self.selector.get_recommendations(agent_type, top_k=1)[0]["model"]

        # Get current performance
        if current_model not in self.success_rates:
            return {"recommendation": "insufficient_data"}

        successes, total = self.success_rates[current_model]
        success_rate = successes / total if total > 0 else 0

        avg_time = sum(self.runtime_metrics.get(current_model, [0])) / max(1, len(self.runtime_metrics.get(current_model, [1])))

        # Check if optimization is needed
        if success_rate < 0.7:
            # Need better quality
            better_model = self.selector.optimize_for_quality(agent_type)
            return {
                "recommendation": "upgrade_quality",
                "current_model": current_model,
                "suggested_model": better_model,
                "reason": f"Success rate too low: {success_rate:.2%}"
            }

        if success_rate > 0.95 and avg_time > 5.0:
            # Can use faster model
            faster_model = self.selector.optimize_for_speed(agent_type)
            return {
                "recommendation": "optimize_speed",
                "current_model": current_model,
                "suggested_model": faster_model,
                "reason": f"High success rate ({success_rate:.2%}), slow execution ({avg_time:.1f}s)"
            }

        return {
            "recommendation": "maintain",
            "current_model": current_model,
            "success_rate": success_rate,
            "avg_execution_time": avg_time
        }
```

**Timeline:** 1 week

---

### 2.3 Test Suite Integration (Periodic Updates)

**Goal:** Automatically update performance data when new models are added or retested.

**Implementation:**

```python
# New module: mcp_client_for_ollama/models/test_integration.py

import subprocess
import os
from pathlib import Path

class TestSuiteIntegration:
    """Integration with os_llm_testing_suite for automatic testing"""

    def __init__(self,
                 test_suite_path: str = "~/project/os_llm_testing_suite",
                 performance_store: PerformanceStore = None):
        self.test_suite_path = Path(test_suite_path).expanduser()
        self.performance_store = performance_store

    def test_model(self, model: str, temperature: float = 0.2) -> bool:
        """
        Run test suite on model

        Returns: True if test completed successfully
        """
        if not self.test_suite_path.exists():
            print(f"Test suite not found at {self.test_suite_path}")
            return False

        # Run test suite
        cmd = [
            "python", "-m", "llm_test_suite",
            "--model", model,
            "--temperature", str(temperature),
            "--base-url", "http://localhost:11434/v1"
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.test_suite_path,
                capture_output=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                print(f"Successfully tested {model}")
                # Reload performance store
                if self.performance_store:
                    self.performance_store.load_test_results()
                return True
            else:
                print(f"Test failed: {result.stderr.decode()}")
                return False

        except subprocess.TimeoutExpired:
            print(f"Test timeout for {model}")
            return False
        except Exception as e:
            print(f"Error testing {model}: {e}")
            return False

    def test_all_available(self, temperature: float = 0.2) -> Dict[str, bool]:
        """Test all models available on Ollama server"""
        # Get available models
        try:
            response = requests.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in response.json().get("models", [])]
        except:
            print("Failed to get available models")
            return {}

        results = {}
        for model in models:
            print(f"Testing {model}...")
            results[model] = self.test_model(model, temperature)

        return results

    def schedule_periodic_testing(self, interval_hours: int = 24):
        """Schedule periodic retesting of models"""
        # Implementation with APScheduler (Phase 1.2 from main roadmap)
        pass
```

**Timeline:** 1 week

---

## Phase 3: Advanced Features (Weeks 7-10)

### 3.1 Web UI for Model Management

**Goal:** Add web UI for viewing model performance and managing selection.

**Implementation:**

```python
# Extension to: mcp_client_for_ollama/web/app.py

from flask import Blueprint, jsonify, request
from ..models.performance_store import PerformanceStore
from ..models.selector import ModelSelector

model_bp = Blueprint('models', __name__)

@model_bp.route('/api/models/performance', methods=['GET'])
def get_model_performance():
    """Get performance data for all models"""
    store = get_performance_store()  # From app context

    models = []
    for model_name, perf in store.models.items():
        models.append({
            "model": perf.model,
            "overall_score": perf.overall_score,
            "tier_scores": perf.tier_scores,
            "dimension_scores": perf.dimension_scores,
            "strengths": perf.strengths,
            "weaknesses": perf.weaknesses,
            "max_tier": perf.max_tier
        })

    return jsonify({"models": models})

@model_bp.route('/api/models/recommendations/<agent_type>', methods=['GET'])
def get_recommendations(agent_type):
    """Get model recommendations for agent type"""
    selector = get_model_selector()
    recommendations = selector.get_recommendations(agent_type, top_k=5)
    return jsonify({"recommendations": recommendations})

@model_bp.route('/api/models/predict', methods=['POST'])
def predict_success():
    """Predict success for model-agent-task combination"""
    data = request.json
    selector = get_model_selector()

    prediction = selector.explain_prediction(
        model=data["model"],
        agent_type=data["agent_type"],
        task_complexity=data.get("task_complexity", 2)
    )

    return jsonify(prediction)

@model_bp.route('/api/models/test', methods=['POST'])
def test_model():
    """Trigger test suite for model"""
    data = request.json
    integration = get_test_integration()

    # Run in background
    result = integration.test_model(
        model=data["model"],
        temperature=data.get("temperature", 0.2)
    )

    return jsonify({"success": result})
```

**UI Components:**

1. **Model Performance Dashboard**
   - Table of all models with scores
   - Dimension radar charts
   - Tier performance bars
   - Sortable/filterable

2. **Agent-Model Matrix**
   - Show recommended models per agent
   - Success predictions
   - Historical performance

3. **Model Testing Interface**
   - Trigger tests for new models
   - View test progress
   - Test history

4. **Optimization Recommendations**
   - Automatic suggestions
   - Speed vs quality tradeoffs
   - Performance trends

**Timeline:** 2 weeks

---

### 3.2 Custom Test Integration

**Goal:** Allow users to define custom tests for their specific use cases.

**Implementation:**

```python
# New module: mcp_client_for_ollama/models/custom_tests.py

class CustomTestRunner:
    """Run custom tests on models"""

    def __init__(self):
        self.custom_tests: Dict[str, Dict] = {}

    def register_test(self,
                     test_id: str,
                     name: str,
                     prompt: str,
                     expected_tools: List[str],
                     grading_criteria: Dict):
        """Register custom test"""
        self.custom_tests[test_id] = {
            "name": name,
            "prompt": prompt,
            "expected_tools": expected_tools,
            "grading": grading_criteria
        }

    async def run_test(self,
                      test_id: str,
                      model: str) -> Dict:
        """Run custom test on model"""
        test = self.custom_tests.get(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")

        # Execute test (similar to main test suite)
        # ... implementation
        pass
```

**Timeline:** 1 week

---

### 3.3 Performance Monitoring & Alerts

**Goal:** Monitor model performance in production and alert on degradation.

**Implementation:**

```python
# New module: mcp_client_for_ollama/models/monitoring.py

class PerformanceMonitor:
    """Monitor model performance over time"""

    def __init__(self, optimizer: ModelOptimizer):
        self.optimizer = optimizer
        self.alerts: List[Dict] = []

    def check_performance(self, agent_type: str):
        """Check if performance has degraded"""
        recommendation = self.optimizer.get_optimization_recommendation(agent_type)

        if recommendation["recommendation"] == "upgrade_quality":
            self.alerts.append({
                "severity": "warning",
                "agent_type": agent_type,
                "message": recommendation["reason"],
                "action": f"Consider switching to {recommendation['suggested_model']}"
            })

    def get_alerts(self) -> List[Dict]:
        """Get all active alerts"""
        return self.alerts
```

**Timeline:** 1 week

---

## Phase 4: Machine Learning Enhancement (Weeks 11-14)

### 4.1 Learning from Execution History

**Goal:** Train simple ML model to improve selection based on historical data.

**Implementation:**

```python
# New module: mcp_client_for_ollama/models/learning.py

from sklearn.ensemble import RandomForestClassifier
import numpy as np

class SelectionLearner:
    """Learn optimal model selection from history"""

    def __init__(self, selector: ModelSelector):
        self.selector = selector
        self.model = RandomForestClassifier()
        self.is_trained = False

    def train(self):
        """Train on historical selection data"""
        history = self.selector.selection_history

        if len(history) < 50:
            print("Insufficient history for training")
            return

        # Feature engineering
        X = []
        y = []

        for entry in history:
            # Features: agent type (one-hot), task complexity, etc.
            features = self._extract_features(entry)
            X.append(features)

            # Label: was this selection successful?
            y.append(entry.get("success", True))

        # Train model
        self.model.fit(np.array(X), np.array(y))
        self.is_trained = True

    def predict_best_model(self, context: SelectionContext) -> str:
        """Predict best model using ML"""
        if not self.is_trained:
            # Fall back to rule-based
            return self.selector.select_model(context)[0]

        # Use ML model
        # ... implementation
        pass
```

**Timeline:** 2 weeks

---

### 4.2 A/B Testing Framework

**Goal:** Compare model performance with controlled experiments.

**Implementation:**

```python
# New module: mcp_client_for_ollama/models/ab_testing.py

class ABTester:
    """A/B test different models"""

    def __init__(self):
        self.experiments: Dict[str, Dict] = {}

    def create_experiment(self,
                         name: str,
                         agent_type: str,
                         model_a: str,
                         model_b: str,
                         traffic_split: float = 0.5):
        """Create A/B test"""
        self.experiments[name] = {
            "agent_type": agent_type,
            "model_a": model_a,
            "model_b": model_b,
            "split": traffic_split,
            "results_a": [],
            "results_b": []
        }

    def select_variant(self, experiment_name: str) -> str:
        """Select model variant for request"""
        exp = self.experiments[experiment_name]
        return exp["model_a"] if random.random() < exp["split"] else exp["model_b"]

    def record_result(self, experiment_name: str, model: str, success: bool):
        """Record experiment result"""
        exp = self.experiments[experiment_name]
        if model == exp["model_a"]:
            exp["results_a"].append(success)
        else:
            exp["results_b"].append(success)

    def analyze_experiment(self, experiment_name: str) -> Dict:
        """Analyze experiment results"""
        exp = self.experiments[experiment_name]

        success_rate_a = sum(exp["results_a"]) / len(exp["results_a"])
        success_rate_b = sum(exp["results_b"]) / len(exp["results_b"])

        # Statistical significance test
        # ... implementation

        return {
            "model_a": exp["model_a"],
            "model_b": exp["model_b"],
            "success_rate_a": success_rate_a,
            "success_rate_b": success_rate_b,
            "winner": exp["model_a"] if success_rate_a > success_rate_b else exp["model_b"]
        }
```

**Timeline:** 2 weeks

---

## Configuration & Usage

### Configuration File

```yaml
# config/model_intelligence.yaml

model_intelligence:
  enabled: true
  test_suite_path: "~/project/os_llm_testing_suite"

  selection:
    strategy: "intelligent"  # or "manual", "round_robin"
    use_fallbacks: true
    max_fallbacks: 2

  optimization:
    enabled: true
    auto_adjust: true  # Automatically switch models based on performance
    speed_priority: 0.3  # 0.0 = quality only, 1.0 = speed only

  monitoring:
    enabled: true
    alert_threshold: 0.7  # Alert if success rate drops below 70%

  testing:
    auto_test_new_models: true
    periodic_retest: true
    retest_interval_hours: 168  # 1 week

  learning:
    enabled: false  # Experimental
    min_history: 100
    retrain_interval: 50  # Retrain every 50 selections
```

### CLI Commands

```bash
# Show model performance
ollmcp models list
ollmcp models show qwen3:30b-a3b

# Get recommendations
ollmcp models recommend CODER
ollmcp models recommend PLANNER --top 5

# Test model
ollmcp models test qwen2.5:32b
ollmcp models test-all

# View selection history
ollmcp models history
ollmcp models history --agent CODER

# Optimization
ollmcp models optimize RESEARCHER --strategy speed
ollmcp models optimize CODER --strategy quality

# A/B testing
ollmcp models ab-test create \
  --name "coder_test" \
  --agent CODER \
  --model-a qwen3:30b-a3b \
  --model-b qwen2.5:32b \
  --split 0.5

ollmcp models ab-test analyze coder_test
```

### Web UI Commands

From web interface:
- View model performance dashboard
- See real-time recommendations
- Monitor selection history
- Trigger model tests
- View optimization suggestions
- Manage A/B experiments

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ Performance data loaded for all tested models (32+)
- ✅ Model selector returns appropriate model for each agent type
- ✅ Fallback logic works when primary model fails
- ✅ Integration with delegation system is seamless
- ✅ No performance regression for existing users

### Phase 2 Success Criteria
- ✅ Success prediction accuracy > 70%
- ✅ Automatic optimization reduces failures by 20%+
- ✅ New models automatically tested and added
- ✅ Performance data stays current (<1 week old)

### Phase 3 Success Criteria
- ✅ Web UI shows clear model recommendations
- ✅ Users can trigger custom tests
- ✅ Monitoring alerts catch performance degradation
- ✅ 50%+ of users engage with model management UI

### Phase 4 Success Criteria
- ✅ ML-based selection improves success rate by 10%+
- ✅ A/B testing identifies optimal models per agent
- ✅ System continuously learns and improves

---

## Risk Assessment

### High-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Test suite data format changes | High | Medium | Version pinning, schema validation |
| Models not available locally | High | High | Graceful fallback to default model |
| Performance overhead | Medium | Medium | Lazy loading, caching |
| Test suite execution time | Medium | High | Background testing, result caching |

### Low-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Incorrect recommendations | Medium | Low | Extensive testing, user feedback |
| UI complexity | Low | Medium | Progressive disclosure, good UX |
| Storage requirements | Low | Low | Periodic cleanup, compression |

---

## Implementation Checklist

### Phase 1
- [ ] Create PerformanceStore class
- [ ] Load test suite results
- [ ] Define agent requirements
- [ ] Create ModelSelector class
- [ ] Implement selection logic
- [ ] Add fallback mechanism
- [ ] Integrate with DelegationClient
- [ ] Add feature flag
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update documentation

### Phase 2
- [ ] Add success prediction
- [ ] Implement ModelOptimizer
- [ ] Add runtime metrics tracking
- [ ] Create TestSuiteIntegration
- [ ] Add periodic testing scheduler
- [ ] Write tests
- [ ] Update documentation

### Phase 3
- [ ] Create model performance API endpoints
- [ ] Build web UI dashboard
- [ ] Add model testing interface
- [ ] Implement custom tests
- [ ] Add performance monitoring
- [ ] Create alerts system
- [ ] Write tests
- [ ] Update documentation

### Phase 4
- [ ] Implement SelectionLearner
- [ ] Add ML model training
- [ ] Create ABTester
- [ ] Add experiment analysis
- [ ] Write tests
- [ ] Update documentation
- [ ] User acceptance testing

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|-----------------|
| Phase 1 | 3 weeks | Performance store, model selector, agent integration |
| Phase 2 | 3 weeks | Success prediction, optimization, auto-testing |
| Phase 3 | 4 weeks | Web UI, monitoring, custom tests |
| Phase 4 | 4 weeks | ML enhancement, A/B testing |
| **Total** | **14 weeks** | **Full intelligent model selection system** |

---

## Integration with Main Roadmap

This model intelligence system complements the main Agent Zero integration roadmap:

**Synergies:**
1. **Phase 1.1 (Multi-Provider)**: Model intelligence helps select optimal provider per agent
2. **Phase 2 (Autonomous Capabilities)**: Complex tasks benefit from intelligent model matching
3. **Phase 3 (Advanced Features)**: Docker/SSH execution needs quality models for reliability

**Dependencies:**
- Model intelligence is independent and can proceed in parallel
- Recommend implementing after Phase 1.1 (Multi-Provider) for maximum benefit
- Web UI (Phase 3) should integrate both roadmaps

---

## Conclusion

This roadmap transforms mcp_client_for_ollama's model selection from manual/static to **intelligent and adaptive**. By leveraging the os_llm_testing_suite's empirical performance data, the system will:

1. **Automatically match optimal models to agent roles** based on 6 performance dimensions
2. **Predict success probability** before execution, reducing failures
3. **Adapt over time** through monitoring and learning
4. **Provide transparency** via web UI and explanations

**Expected Outcomes:**
- **20-30% reduction in agent failures** through better model selection
- **Improved task completion rates** by matching model capabilities to task complexity
- **User confidence** via transparent recommendations and predictions
- **Continuous improvement** through automatic testing and learning

**Key Differentiator:** No other AI agent framework uses empirical, multi-dimensional performance data for intelligent model selection. This positions mcp_client_for_ollama as the most sophisticated and reliable agent system.

---

**Document Version:** 1.0
**Date:** 2026-01-26
**Author:** Development Team
**Review Date:** Bi-weekly during implementation
