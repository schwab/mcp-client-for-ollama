"""Targeted Fine-Tuner - Implements focused fine-tuning on specific weaknesses."""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FineTuningJob:
    """Configuration for a fine-tuning job."""
    job_id: str
    model_name: str
    weakness: str
    dataset_path: str
    learning_rate: float
    num_epochs: int
    batch_size: int
    status: str  # pending, running, completed, failed
    created_at: str
    completed_at: Optional[str] = None


@dataclass
class FineTuningResult:
    """Result of a fine-tuning job."""
    job_id: str
    model_name: str
    weakness: str
    success: bool
    original_score: float
    fine_tuned_score: float
    improvement: float
    improvement_percentage: float
    new_model_name: str
    training_loss: float
    validation_loss: Optional[float] = None
    completed_at: str = ""


class TargetedFineTuner:
    """
    Implements focused fine-tuning on specific weaknesses.
    Targets particular model deficiencies with curated datasets.
    """

    def __init__(self):
        """Initialize the targeted fine-tuner."""
        self.jobs: Dict[str, FineTuningJob] = {}
        self.results: List[FineTuningResult] = []

    async def fine_tune_for_weakness(
        self,
        model_name: str,
        weakness: str,
        dataset_path: str,
        baseline_score: float
    ) -> FineTuningResult:
        """
        Fine-tune model on specific weakness.

        Args:
            model_name: Name of model to fine-tune
            weakness: Type of weakness (tool_calling, formatting, reasoning, etc.)
            dataset_path: Path to training dataset
            baseline_score: Baseline performance score

        Returns:
            FineTuningResult with results
        """
        logger.info(f"Starting fine-tuning for {model_name} on weakness: {weakness}")

        # Create fine-tuning job
        job_id = self._generate_job_id(model_name, weakness)
        job = FineTuningJob(
            job_id=job_id,
            model_name=model_name,
            weakness=weakness,
            dataset_path=dataset_path,
            learning_rate=self._get_learning_rate(weakness),
            num_epochs=self._get_num_epochs(weakness),
            batch_size=32,
            status="pending",
            created_at=datetime.now().isoformat()
        )

        self.jobs[job_id] = job

        # Get fine-tuning parameters for this weakness
        params = self._get_fine_tuning_params(model_name, weakness)

        # Run fine-tuning (in real implementation, would call actual fine-tuning service)
        training_loss = await self._run_fine_tuning(job, params)

        # Validate improvement
        improvement_result = await self._validate_improvement(
            model_name,
            weakness,
            baseline_score
        )

        # Create result
        result = FineTuningResult(
            job_id=job_id,
            model_name=model_name,
            weakness=weakness,
            success=improvement_result["success"],
            original_score=baseline_score,
            fine_tuned_score=improvement_result["new_score"],
            improvement=improvement_result["new_score"] - baseline_score,
            improvement_percentage=(
                ((improvement_result["new_score"] - baseline_score) / baseline_score * 100)
                if baseline_score > 0 else 0
            ),
            new_model_name=improvement_result["new_model_name"],
            training_loss=training_loss,
            validation_loss=improvement_result.get("validation_loss"),
            completed_at=datetime.now().isoformat()
        )

        self.results.append(result)
        job.status = "completed"
        job.completed_at = result.completed_at

        logger.info(
            f"Fine-tuning completed. Improvement: {result.improvement_percentage:.1f}% "
            f"({result.original_score:.1f} -> {result.fine_tuned_score:.1f})"
        )

        return result

    def _get_fine_tuning_params(self, model_name: str, weakness: str) -> Dict[str, Any]:
        """Get optimized fine-tuning parameters for weakness type."""
        base_params = {
            "tool_calling": {
                "learning_rate": 2e-5,
                "epochs": 3,
                "batch_size": 16,
                "warmup_steps": 100,
                "gradient_accumulation_steps": 2,
            },
            "formatting": {
                "learning_rate": 5e-5,
                "epochs": 2,
                "batch_size": 32,
                "warmup_steps": 50,
                "gradient_accumulation_steps": 1,
            },
            "reasoning": {
                "learning_rate": 2e-5,
                "epochs": 4,
                "batch_size": 16,
                "warmup_steps": 150,
                "gradient_accumulation_steps": 2,
            },
            "error_recovery": {
                "learning_rate": 1e-5,
                "epochs": 3,
                "batch_size": 16,
                "warmup_steps": 100,
                "gradient_accumulation_steps": 2,
            },
        }

        params = base_params.get(weakness, base_params["formatting"])

        # Adjust based on model size
        if "3b" in model_name:
            params["learning_rate"] *= 2  # Smaller models need higher LR
            params["batch_size"] = 8
        elif "34b" in model_name:
            params["learning_rate"] *= 0.5  # Larger models need lower LR

        return params

    def _get_learning_rate(self, weakness: str) -> float:
        """Get initial learning rate for weakness type."""
        rates = {
            "tool_calling": 2e-5,
            "formatting": 5e-5,
            "reasoning": 2e-5,
            "error_recovery": 1e-5,
        }
        return rates.get(weakness, 3e-5)

    def _get_num_epochs(self, weakness: str) -> int:
        """Get number of epochs for weakness type."""
        epochs = {
            "tool_calling": 3,
            "formatting": 2,
            "reasoning": 4,
            "error_recovery": 3,
        }
        return epochs.get(weakness, 3)

    async def _run_fine_tuning(
        self,
        job: FineTuningJob,
        params: Dict[str, Any]
    ) -> float:
        """
        Run the actual fine-tuning job.

        In real implementation, would call fine-tuning service (e.g., OpenAI, HuggingFace).
        """
        logger.debug(f"Running fine-tuning job {job.job_id}")
        job.status = "running"

        # Simulate training by loading dataset and calculating loss
        training_loss = await self._simulate_training(
            job.dataset_path,
            params
        )

        return training_loss

    async def _simulate_training(
        self,
        dataset_path: str,
        params: Dict[str, Any]
    ) -> float:
        """Simulate training process (for demo purposes)."""
        # In real implementation, this would:
        # 1. Load dataset from dataset_path
        # 2. Initialize model
        # 3. Run training loop
        # 4. Calculate and return training loss

        # For now, simulate with a reasonable loss value
        import random
        base_loss = 0.8
        variance = random.uniform(-0.2, 0.1)
        return max(0.1, base_loss + variance)

    async def _validate_improvement(
        self,
        model_name: str,
        weakness: str,
        baseline_score: float
    ) -> Dict[str, Any]:
        """
        Validate improvement after fine-tuning.

        Returns:
            Dictionary with validation results
        """
        logger.debug(f"Validating improvement for {model_name}")

        # In real implementation, would:
        # 1. Run test suite on fine-tuned model
        # 2. Compare against baseline
        # 3. Validate on hold-out validation set

        # For now, simulate improvement
        improvement_factor = {
            "tool_calling": 1.3,  # 30% improvement
            "formatting": 1.25,   # 25% improvement
            "reasoning": 1.2,     # 20% improvement
            "error_recovery": 1.15,  # 15% improvement
        }.get(weakness, 1.2)

        new_score = min(100.0, baseline_score * improvement_factor)

        return {
            "success": new_score > baseline_score,
            "new_score": new_score,
            "new_model_name": f"{model_name}_ft_{weakness[:3]}",
            "validation_loss": 0.5,
        }

    def create_batch_fine_tuning_jobs(
        self,
        model_name: str,
        weaknesses: List[str],
        dataset_creator
    ) -> List[str]:
        """
        Create multiple fine-tuning jobs for different weaknesses.

        Args:
            model_name: Model to fine-tune
            weaknesses: List of weaknesses to target
            dataset_creator: DatasetCreator instance for generating datasets

        Returns:
            List of job IDs
        """
        job_ids = []

        for weakness in weaknesses:
            job_id = self._generate_job_id(model_name, weakness)
            job = FineTuningJob(
                job_id=job_id,
                model_name=model_name,
                weakness=weakness,
                dataset_path=f"datasets/{model_name}_{weakness}.jsonl",
                learning_rate=self._get_learning_rate(weakness),
                num_epochs=self._get_num_epochs(weakness),
                batch_size=32,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            self.jobs[job_id] = job
            job_ids.append(job_id)

        logger.info(f"Created {len(job_ids)} fine-tuning jobs for {model_name}")
        return job_ids

    def get_job_status(self, job_id: str) -> Optional[FineTuningJob]:
        """Get status of a fine-tuning job."""
        return self.jobs.get(job_id)

    def get_results_by_weakness(self, weakness: str) -> List[FineTuningResult]:
        """Get all fine-tuning results for a specific weakness."""
        return [r for r in self.results if r.weakness == weakness]

    def get_results_by_model(self, model_name: str) -> List[FineTuningResult]:
        """Get all fine-tuning results for a specific model."""
        return [r for r in self.results if r.model_name == model_name]

    def get_best_fine_tuned_model(self, model_name: str) -> Optional[FineTuningResult]:
        """Get the best fine-tuned version of a model."""
        results = self.get_results_by_model(model_name)
        if not results:
            return None
        return max(results, key=lambda r: r.fine_tuned_score)

    def export_results(self, output_path: Optional[str] = None) -> str:
        """Export all fine-tuning results to JSON."""
        if output_path is None:
            output_path = str(
                Path.home() / "Nextcloud/DEV/ollmcp/mcp-client-for-ollama/data/fine_tuning_results.json"
            )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        results_data = [
            {
                "job_id": r.job_id,
                "model_name": r.model_name,
                "weakness": r.weakness,
                "success": r.success,
                "original_score": r.original_score,
                "fine_tuned_score": r.fine_tuned_score,
                "improvement": round(r.improvement, 2),
                "improvement_percentage": round(r.improvement_percentage, 1),
                "new_model_name": r.new_model_name,
                "training_loss": round(r.training_loss, 4),
                "completed_at": r.completed_at,
            }
            for r in self.results
        ]

        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)

        logger.info(f"Exported {len(self.results)} fine-tuning results to {output_path}")
        return output_path

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all fine-tuning activities."""
        if not self.results:
            return {"total_jobs": 0}

        successful = sum(1 for r in self.results if r.success)
        total_improvement = sum(r.improvement_percentage for r in self.results)
        avg_improvement = total_improvement / len(self.results) if self.results else 0

        return {
            "total_jobs": len(self.results),
            "successful_jobs": successful,
            "success_rate": round((successful / len(self.results) * 100), 1) if self.results else 0,
            "total_improvement_percentage": round(total_improvement, 1),
            "average_improvement_per_job": round(avg_improvement, 1),
            "models_fine_tuned": list(set(r.model_name for r in self.results)),
            "weaknesses_addressed": list(set(r.weakness for r in self.results)),
        }

    def _generate_job_id(self, model_name: str, weakness: str) -> str:
        """Generate unique job ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{model_name}__{weakness}__{timestamp}"
