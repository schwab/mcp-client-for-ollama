"""Fine-Tuning Dataset Creator - Creates targeted training datasets."""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """A single training example."""
    user_message: str
    assistant_message: str
    metadata: Dict[str, Any]


@dataclass
class DatasetMetrics:
    """Metrics about a dataset."""
    total_examples: int
    average_input_length: int
    average_output_length: int
    task_distribution: Dict[str, int]
    quality_score: float  # 0-100


class FineTuningDatasetCreator:
    """
    Creates targeted fine-tuning datasets from chat knowledge.
    Focuses on specific weaknesses identified from test failures.
    """

    def __init__(self):
        """Initialize the dataset creator."""
        self.datasets: Dict[str, List[TrainingExample]] = {}

    def create_tool_calling_dataset(
        self,
        model_name: str,
        chat_examples: List[Dict[str, Any]],
        agent_type: Optional[str] = None
    ) -> List[TrainingExample]:
        """
        Create dataset to improve tool calling.

        Args:
            model_name: Name of model to create dataset for
            chat_examples: Successful chat interactions
            agent_type: Optional filter for specific agent type

        Returns:
            List of training examples for tool calling
        """
        logger.info(f"Creating tool-calling dataset for {model_name}")

        dataset_key = f"{model_name}_tool_calling"
        examples: List[TrainingExample] = []

        for chat_example in chat_examples:
            user_msg = chat_example.get("user_message", {})
            assistant_msg = chat_example.get("assistant_message", {})

            if not user_msg or not assistant_msg:
                continue

            # Check if this example involves tool usage
            if not self._involves_tool_usage(assistant_msg.get("content", "")):
                continue

            # Convert to explicit tool calling format
            user_content = user_msg.get("content", "")
            response_content = assistant_msg.get("content", "")

            # Extract tool calls from response
            tool_calls = self._extract_tool_calls(response_content)

            if not tool_calls:
                continue

            # Create explicit tool calling format
            explicit_format = self._create_explicit_tool_format(tool_calls, response_content)

            models = assistant_msg.get("models", ["unknown"])
            original_model = models[0] if models else "unknown"

            example = TrainingExample(
                user_message=user_content,
                assistant_message=explicit_format,
                metadata={
                    "task_type": "tool_calling",
                    "original_model": original_model,
                    "tools_involved": [t.get("tool", "unknown") for t in tool_calls],
                    "success_indicators": chat_example.get("success_indicators", []),
                }
            )
            examples.append(example)

        self.datasets[dataset_key] = examples
        logger.info(f"Created tool-calling dataset with {len(examples)} examples")
        return examples

    def create_format_fixing_dataset(
        self,
        model_name: str,
        chat_examples: List[Dict[str, Any]],
        failure_examples: Optional[List[Dict[str, Any]]] = None
    ) -> List[TrainingExample]:
        """
        Create dataset to fix common formatting issues.

        Args:
            model_name: Name of model
            chat_examples: Successful formatted responses
            failure_examples: Examples of formatting failures to learn from

        Returns:
            List of formatting training examples
        """
        logger.info(f"Creating format-fixing dataset for {model_name}")

        dataset_key = f"{model_name}_formatting"
        examples: List[TrainingExample] = []

        for chat_example in chat_examples:
            user_msg = chat_example.get("user_message", {})
            assistant_msg = chat_example.get("assistant_message", {})

            if not user_msg or not assistant_msg:
                continue

            # Check if response has good formatting
            response = assistant_msg.get("content", "")
            if not self._has_good_formatting(response):
                continue

            models = assistant_msg.get("models", ["unknown"])
            original_model = models[0] if models else "unknown"

            example = TrainingExample(
                user_message=user_msg.get("content", ""),
                assistant_message=response,
                metadata={
                    "task_type": "formatting",
                    "formatting_features": self._identify_formatting_features(response),
                    "original_model": original_model,
                }
            )
            examples.append(example)

        self.datasets[dataset_key] = examples
        logger.info(f"Created formatting dataset with {len(examples)} examples")
        return examples

    def create_reasoning_dataset(
        self,
        model_name: str,
        chat_examples: List[Dict[str, Any]]
    ) -> List[TrainingExample]:
        """
        Create dataset to improve step-by-step reasoning.

        Args:
            model_name: Name of model
            chat_examples: Examples with good reasoning patterns

        Returns:
            List of reasoning training examples
        """
        logger.info(f"Creating reasoning dataset for {model_name}")

        dataset_key = f"{model_name}_reasoning"
        examples: List[TrainingExample] = []

        for chat_example in chat_examples:
            user_msg = chat_example.get("user_message", {})
            assistant_msg = chat_example.get("assistant_message", {})

            if not user_msg or not assistant_msg:
                continue

            response = assistant_msg.get("content", "")

            # Check if response has good reasoning structure
            if not self._has_good_reasoning(response):
                continue

            # Extract and enhance reasoning
            enhanced_response = self._enhance_reasoning_format(response)

            models = assistant_msg.get("models", ["unknown"])
            original_model = models[0] if models else "unknown"

            example = TrainingExample(
                user_message=user_msg.get("content", ""),
                assistant_message=enhanced_response,
                metadata={
                    "task_type": "reasoning",
                    "original_model": original_model,
                    "reasoning_quality": self._assess_reasoning_quality(response),
                }
            )
            examples.append(example)

        self.datasets[dataset_key] = examples
        logger.info(f"Created reasoning dataset with {len(examples)} examples")
        return examples

    def create_error_recovery_dataset(
        self,
        model_name: str,
        failure_examples: List[Dict[str, Any]],
        chat_successes: List[Dict[str, Any]]
    ) -> List[TrainingExample]:
        """
        Create dataset to help model recover from errors.

        Args:
            model_name: Name of model
            failure_examples: Examples of failures
            chat_successes: Successful approaches to similar problems

        Returns:
            List of error recovery training examples
        """
        logger.info(f"Creating error-recovery dataset for {model_name}")

        dataset_key = f"{model_name}_error_recovery"
        examples: List[TrainingExample] = []

        for failure in failure_examples[:10]:  # Limit to 10 failures
            # Find similar successful example
            failure_task = failure.get("task_description", "")
            success = self._find_similar_success(failure_task, chat_successes)

            if not success:
                continue

            # Create example showing error -> recovery
            user_msg = f"{failure_task}\n[Previous error: {failure.get('error', 'unknown')}]\nPlease retry with a different approach."

            example = TrainingExample(
                user_message=user_msg,
                assistant_message=success.get("assistant_message", {}).get("content", ""),
                metadata={
                    "task_type": "error_recovery",
                    "error_type": failure.get("error_type", "unknown"),
                    "recovery_strategy": "use_alternative_approach",
                }
            )
            examples.append(example)

        self.datasets[dataset_key] = examples
        logger.info(f"Created error-recovery dataset with {len(examples)} examples")
        return examples

    def create_combined_dataset(
        self,
        model_name: str,
        datasets: Optional[List[str]] = None
    ) -> List[TrainingExample]:
        """
        Combine multiple datasets into one comprehensive dataset.

        Args:
            model_name: Name of model
            datasets: Optional list of dataset keys to combine

        Returns:
            Combined list of training examples
        """
        if datasets is None:
            # Use all datasets for this model
            datasets = [k for k in self.datasets.keys() if k.startswith(model_name)]

        logger.info(f"Combining {len(datasets)} datasets for {model_name}")

        combined = []
        for dataset_key in datasets:
            if dataset_key in self.datasets:
                combined.extend(self.datasets[dataset_key])

        logger.info(f"Combined dataset contains {len(combined)} examples")
        return combined

    def export_to_jsonl(
        self,
        examples: List[TrainingExample],
        output_path: Optional[str] = None,
        format_type: str = "openai"
    ) -> str:
        """
        Export training examples to JSONL format.

        Args:
            examples: List of training examples
            output_path: Path to save JSONL file
            format_type: Format type (openai, huggingface, etc.)

        Returns:
            Path to exported file
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(
                Path.home() / f"Nextcloud/DEV/ollmcp/mcp-client-for-ollama/data/training_data_{timestamp}.jsonl"
            )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            for example in examples:
                if format_type == "openai":
                    entry = {
                        "messages": [
                            {"role": "user", "content": example.user_message},
                            {"role": "assistant", "content": example.assistant_message}
                        ]
                    }
                elif format_type == "huggingface":
                    entry = {
                        "text": f"<USER>{example.user_message}<ASSISTANT>{example.assistant_message}"
                    }
                else:
                    entry = {
                        "input": example.user_message,
                        "output": example.assistant_message
                    }

                entry["metadata"] = example.metadata
                f.write(json.dumps(entry) + '\n')

        logger.info(f"Exported {len(examples)} examples to {output_path}")
        return output_path

    def get_dataset_metrics(self, examples: List[TrainingExample]) -> DatasetMetrics:
        """Calculate metrics about a dataset."""
        if not examples:
            return DatasetMetrics(
                total_examples=0,
                average_input_length=0,
                average_output_length=0,
                task_distribution={},
                quality_score=0.0
            )

        # Calculate averages
        avg_input = sum(len(e.user_message) for e in examples) // len(examples)
        avg_output = sum(len(e.assistant_message) for e in examples) // len(examples)

        # Calculate task distribution
        task_counts: Dict[str, int] = {}
        for example in examples:
            task = example.metadata.get("task_type", "unknown")
            task_counts[task] = task_counts.get(task, 0) + 1

        # Calculate quality score (simplified)
        quality_score = min(
            100.0,
            (len(examples) / 100) * 50 +  # More examples = better
            (min(avg_output, 1000) / 1000) * 30 +  # Better if responses are detailed
            20  # Base score
        )

        return DatasetMetrics(
            total_examples=len(examples),
            average_input_length=avg_input,
            average_output_length=avg_output,
            task_distribution=task_counts,
            quality_score=round(quality_score, 1)
        )

    # Helper methods

    def _involves_tool_usage(self, content: str) -> bool:
        """Check if response involves tool usage."""
        tool_indicators = ["curl", "docker", "python", "bash", "git", "npm", "```"]
        return any(indicator in content.lower() for indicator in tool_indicators)

    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract tool calls from response."""
        tools = []

        if "```bash" in content or "$ " in content:
            tools.append({"tool": "bash", "type": "command"})
        if "```python" in content or "import " in content:
            tools.append({"tool": "python", "type": "code"})
        if "curl" in content.lower():
            tools.append({"tool": "curl", "type": "api"})
        if "docker" in content.lower():
            tools.append({"tool": "docker", "type": "container"})

        return tools

    def _create_explicit_tool_format(self, tool_calls: List[Dict[str, Any]], response: str) -> str:
        """Create explicit tool calling format."""
        formatted = "REASONING:\nBased on the task, I need to use the following tools:\n\n"

        for tool_call in tool_calls:
            formatted += f"TOOL: {tool_call['tool']}\n"

        formatted += f"\nDETAILED RESPONSE:\n{response}"
        return formatted

    def _has_good_formatting(self, response: str) -> bool:
        """Check if response has good formatting."""
        good_formatting_indicators = ["```", "- ", "\n", "**"]
        return sum(indicator in response for indicator in good_formatting_indicators) >= 2

    def _identify_formatting_features(self, response: str) -> List[str]:
        """Identify formatting features in response."""
        features = []

        if "```" in response:
            features.append("code_blocks")
        if "- " in response or "* " in response:
            features.append("bullet_points")
        if "**" in response or "__" in response:
            features.append("emphasis")
        if "\n" in response:
            features.append("structured_layout")

        return features

    def _has_good_reasoning(self, response: str) -> bool:
        """Check if response has good reasoning structure."""
        reasoning_indicators = ["because", "therefore", "first", "then", "next", "step"]
        return sum(indicator in response.lower() for indicator in reasoning_indicators) >= 2

    def _enhance_reasoning_format(self, response: str) -> str:
        """Enhance reasoning with explicit step formatting."""
        # If not already formatted, add step numbering
        if not any(f"{i}." in response for i in range(1, 10)):
            lines = response.split('\n')
            enhanced_lines = []

            for i, line in enumerate(lines[:10], 1):
                if line.strip():
                    enhanced_lines.append(f"Step {i}: {line.strip()}")

            return '\n'.join(enhanced_lines)

        return response

    def _assess_reasoning_quality(self, response: str) -> str:
        """Assess quality of reasoning in response."""
        indicators = sum(
            indicator in response.lower()
            for indicator in ["because", "therefore", "first", "step", "reason"]
        )

        if indicators >= 5:
            return "excellent"
        elif indicators >= 3:
            return "good"
        else:
            return "fair"

    def _find_similar_success(
        self,
        task_description: str,
        chat_successes: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find a successful example similar to the given task."""
        # Simple similarity based on keywords
        task_words = set(task_description.lower().split())

        best_match = None
        best_score = 0

        for success in chat_successes:
            user_msg = success.get("user_message", {}).get("content", "").lower()
            success_words = set(user_msg.split())

            # Calculate Jaccard similarity
            overlap = len(task_words & success_words)
            similarity = overlap / len(task_words | success_words) if task_words or success_words else 0

            if similarity > best_score:
                best_score = similarity
                best_match = success

        return best_match if best_score > 0.3 else None
