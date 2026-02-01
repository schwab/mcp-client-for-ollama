#!/usr/bin/env python3
"""
Main improvement pipeline orchestrator.

Runs the complete chat-to-agent knowledge transfer pipeline:
1. Analyze chat history
2. Extract patterns and knowledge
3. Generate improvements
4. Test improvements
5. Apply fine-tuning
6. Generate reports
"""

import asyncio
import argparse
import logging
from pathlib import Path
import json
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_client_for_ollama.analysis.chat_analyzer import ChatHistoryAnalyzer
from mcp_client_for_ollama.analysis.knowledge_extractor import KnowledgeExtractor
from mcp_client_for_ollama.analysis.example_generator import ExampleGenerator
from mcp_client_for_ollama.analysis.differential_analyzer import DifferentialAnalyzer
from mcp_client_for_ollama.optimization.improvement_loop import ImprovementLoop
from mcp_client_for_ollama.optimization.model_optimizer import ModelOptimizer
from mcp_client_for_ollama.training.dataset_creator import FineTuningDatasetCreator
from mcp_client_for_ollama.training.fine_tuner import TargetedFineTuner
from mcp_client_for_ollama.monitoring.dashboard import ImprovementDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImprovementPipelineOrchestrator:
    """Orchestrates the complete improvement pipeline."""

    def __init__(self, config_path: str = None):
        """Initialize the orchestrator."""
        self.config = self._load_config(config_path) if config_path else self._get_default_config()
        self.chat_analyzer = ChatHistoryAnalyzer()
        self.knowledge_extractor = KnowledgeExtractor()
        self.example_generator = ExampleGenerator()
        self.differential_analyzer = DifferentialAnalyzer()
        self.improvement_loop = ImprovementLoop()
        self.model_optimizer = ModelOptimizer()
        self.dataset_creator = FineTuningDatasetCreator()
        self.fine_tuner = TargetedFineTuner()
        self.dashboard = ImprovementDashboard()

    def _load_config(self, path: str) -> dict:
        """Load configuration from file."""
        with open(path, 'r') as f:
            return json.load(f)

    def _get_default_config(self) -> dict:
        """Get default configuration."""
        return {
            "models_to_optimize": [
                "qwen2.5-coder:32b",
                "qwen2.5-coder:14b",
                "granite-3.1-8b-instruct"
            ],
            "agent_types": ["CODER", "EXECUTOR", "PLANNER", "DEBUGGER", "READER"],
            "enable_fine_tuning": True,
            "fine_tuning_targets": ["tool_calling", "formatting", "reasoning"],
            "max_improvement_cycles": 3,
        }

    async def run_full_pipeline(self, verbose: bool = False) -> dict:
        """
        Run the complete improvement pipeline.

        Returns:
            Dictionary with results and summary
        """
        logger.info("Starting complete improvement pipeline")
        results = {}

        try:
            # Phase 1: Analyze chat history
            logger.info("=" * 60)
            logger.info("PHASE 1: Analyzing Chat History")
            logger.info("=" * 60)
            results["chat_analysis"] = await self._phase1_analyze_chat()

            # Phase 2: Extract knowledge
            logger.info("=" * 60)
            logger.info("PHASE 2: Extracting Knowledge")
            logger.info("=" * 60)
            results["knowledge_extraction"] = await self._phase2_extract_knowledge()

            # Phase 3: Run improvement cycles
            logger.info("=" * 60)
            logger.info("PHASE 3: Running Improvement Cycles")
            logger.info("=" * 60)
            results["improvements"] = await self._phase3_improvement_cycles()

            # Phase 4: Create and apply fine-tuning
            if self.config.get("enable_fine_tuning"):
                logger.info("=" * 60)
                logger.info("PHASE 4: Fine-Tuning Datasets & Training")
                logger.info("=" * 60)
                results["fine_tuning"] = await self._phase4_fine_tuning()

            # Phase 5: Generate reports
            logger.info("=" * 60)
            logger.info("PHASE 5: Generating Reports")
            logger.info("=" * 60)
            results["reports"] = await self._phase5_reporting()

            logger.info("=" * 60)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            results["error"] = str(e)

        return results

    async def _phase1_analyze_chat(self) -> dict:
        """Phase 1: Analyze chat history."""
        logger.info("Loading and analyzing chat history...")

        # Run analysis
        analysis_results = self.chat_analyzer.analyze_all()

        # Export patterns
        patterns_file = self.chat_analyzer.export_patterns()

        logger.info(f"Chat analysis complete: {analysis_results['total_conversations']} conversations analyzed")
        logger.info(f"Patterns exported to: {patterns_file}")

        return {
            "total_conversations": analysis_results["total_conversations"],
            "patterns_by_type": analysis_results["patterns_by_type"],
            "models_analyzed": list(self.chat_analyzer.model_success_rates.keys()),
            "patterns_file": patterns_file,
            "summary": self.chat_analyzer.get_summary(),
        }

    async def _phase2_extract_knowledge(self) -> dict:
        """Phase 2: Extract transferable knowledge."""
        logger.info("Extracting transferable knowledge from chat successes...")

        # Get successful patterns from chat analyzer
        successful_patterns = []
        for task_type, patterns in self.chat_analyzer.patterns.items():
            successful_patterns.extend([
                {
                    "user_message": {"content": p.user_message.content},
                    "assistant_message": {"content": p.assistant_response.content},
                    "success_indicators": p.success_indicators,
                }
                for p in patterns[:3]  # Top 3 per type
            ])

        # Extract knowledge
        knowledge = self.knowledge_extractor.extract_transferable_knowledge(successful_patterns)

        logger.info(f"Extracted {len(knowledge)} knowledge items")

        # Generate training examples
        examples = self.example_generator.generate_agent_examples(successful_patterns)

        logger.info(f"Generated {len(examples)} agent training examples")

        # Export examples
        examples_file = self.example_generator.export_examples_to_jsonl()

        return {
            "knowledge_items": len(knowledge),
            "training_examples": len(examples),
            "examples_file": examples_file,
            "knowledge_summary": self.knowledge_extractor.get_knowledge_summary(),
        }

    async def _phase3_improvement_cycles(self) -> dict:
        """Phase 3: Run improvement cycles."""
        logger.info("Running improvement cycles for configured models...")

        cycle_results = []

        for model in self.config.get("models_to_optimize", [])[:2]:  # Test with 2 models
            logger.info(f"Running improvement cycle for {model}")

            cycle = await self.improvement_loop.improvement_cycle(
                model,
                chat_analyzer=self.chat_analyzer,
                knowledge_extractor=self.knowledge_extractor
            )

            cycle_results.append({
                "model": cycle.model_name,
                "baseline": cycle.baseline_score,
                "improvement": cycle.improvement,
                "improvement_percentage": cycle.improvement_percentage,
                "validation_passed": cycle.validation_passed,
            })

            logger.info(
                f"  Baseline: {cycle.baseline_score:.1f}% -> "
                f"New: {cycle.new_score:.1f}% (Improvement: {cycle.improvement_percentage:.1f}%)"
            )

        # Export cycle results
        cycles_file = self.improvement_loop.export_cycle_results()

        return {
            "cycles_completed": len(cycle_results),
            "results": cycle_results,
            "cycles_file": cycles_file,
            "metrics": self.improvement_loop.get_improvement_metrics(),
        }

    async def _phase4_fine_tuning(self) -> dict:
        """Phase 4: Create fine-tuning datasets and train models."""
        logger.info("Creating fine-tuning datasets...")

        fine_tuning_results = []

        models = self.config.get("models_to_optimize", [])[:1]  # Focus on top model
        targets = self.config.get("fine_tuning_targets", [])

        for model in models:
            for weakness in targets:
                logger.info(f"Creating {weakness} dataset for {model}...")

                # Create appropriate dataset
                if weakness == "tool_calling":
                    examples = self.dataset_creator.create_tool_calling_dataset(
                        model,
                        self._get_chat_examples()
                    )
                elif weakness == "formatting":
                    examples = self.dataset_creator.create_format_fixing_dataset(
                        model,
                        self._get_chat_examples()
                    )
                elif weakness == "reasoning":
                    examples = self.dataset_creator.create_reasoning_dataset(
                        model,
                        self._get_chat_examples()
                    )
                else:
                    continue

                logger.info(f"Created {len(examples)} training examples for {weakness}")

                # Export dataset
                dataset_file = self.dataset_creator.export_to_jsonl(examples)
                logger.info(f"Dataset exported to: {dataset_file}")

                # Run fine-tuning
                logger.info(f"Fine-tuning {model} for {weakness}...")
                result = await self.fine_tuner.fine_tune_for_weakness(
                    model,
                    weakness,
                    dataset_file,
                    baseline_score=65.0
                )

                fine_tuning_results.append({
                    "model": result.model_name,
                    "weakness": result.weakness,
                    "improvement": result.improvement_percentage,
                    "new_model": result.new_model_name,
                })

                logger.info(f"  Fine-tuning result: {result.improvement_percentage:.1f}% improvement")

        # Export fine-tuning results
        results_file = self.fine_tuner.export_results()

        return {
            "datasets_created": len(fine_tuning_results),
            "results": fine_tuning_results,
            "results_file": results_file,
            "summary": self.fine_tuner.get_summary(),
        }

    async def _phase5_reporting(self) -> dict:
        """Phase 5: Generate comprehensive reports."""
        logger.info("Generating improvement reports...")

        # Generate dashboard metrics
        metrics = self.dashboard.get_improvement_metrics(
            self.improvement_loop,
            self.fine_tuner,
            self.chat_analyzer
        )

        # Generate comprehensive report
        report = self.dashboard.generate_improvement_report(
            self.improvement_loop,
            self.fine_tuner,
            self.chat_analyzer
        )

        # Export report
        report_file = self.dashboard.export_report(report)

        logger.info(f"Improvement report exported to: {report_file}")

        return {
            "metrics": {
                "models_analyzed": metrics.models_analyzed,
                "agents_tested": metrics.agents_tested,
                "total_test_runs": metrics.total_test_runs,
                "average_agent_success_rate": metrics.average_agent_success_rate,
                "chat_agent_gap": metrics.chat_agent_performance_gap,
                "claude_reduction_potential": metrics.estimated_claude_reduction,
            },
            "top_improvements": metrics.top_improvements,
            "recommendations": report.get("recommendations", []),
            "report_file": report_file,
        }

    def _get_chat_examples(self) -> list:
        """Get chat examples for training data creation."""
        examples = []

        for task_type, patterns in self.chat_analyzer.patterns.items():
            for pattern in patterns[:2]:  # Get a few examples per type
                examples.append({
                    "user_message": {"content": pattern.user_message.content},
                    "assistant_message": {
                        "content": pattern.assistant_response.content,
                        "models": pattern.assistant_response.models,
                    },
                    "success_indicators": pattern.success_indicators,
                })

        return examples


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the complete Chat-to-Agent improvement pipeline"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file",
        default=None
    )
    parser.add_argument(
        "--phase",
        choices=["all", "1", "2", "3", "4", "5"],
        default="all",
        help="Which phase(s) to run"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = ImprovementPipelineOrchestrator(args.config)

    # Run pipeline
    results = await orchestrator.run_full_pipeline(verbose=args.verbose)

    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE RESULTS SUMMARY")
    print("=" * 60)
    print(json.dumps(results, indent=2, default=str))

    return 0 if "error" not in results else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
