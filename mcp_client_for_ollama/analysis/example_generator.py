"""Example Generator - Creates few-shot examples from chat successes."""

import logging
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentExample:
    """A training example for agent model."""
    input: str  # User query
    expected_output: str  # What the agent should produce
    reasoning: str  # Step-by-step reasoning
    tools_used: List[str]  # Tools involved
    output_format: str  # Expected format (tool_call, code, command, etc.)
    model: str  # Original model that produced this
    success_indicators: List[str]  # Why this was successful


class ExampleGenerator:
    """Creates few-shot examples from chat successes."""

    def __init__(self):
        """Initialize the example generator."""
        self.agent_examples: List[AgentExample] = []
        self.format_templates: Dict[str, str] = self._initialize_format_templates()

    def generate_agent_examples(
        self,
        chat_examples: List[Dict[str, Any]],
        target_agent_type: Optional[str] = None
    ) -> List[AgentExample]:
        """
        Transform chat interactions into agent-friendly examples.

        Args:
            chat_examples: List of successful chat interactions
            target_agent_type: Optional filter for specific agent types

        Returns:
            List of AgentExample objects ready for training
        """
        logger.info(f"Generating {len(chat_examples)} agent examples...")

        for chat_example in chat_examples:
            # Convert chat response to agent tool-calling format
            agent_example = self._convert_to_agent_format(chat_example)

            if agent_example:
                self.agent_examples.append(agent_example)

        logger.info(f"Generated {len(self.agent_examples)} agent examples")
        return self.agent_examples

    def _convert_to_agent_format(self, chat_example: Dict[str, Any]) -> Optional[AgentExample]:
        """Convert a single chat interaction to agent format."""
        try:
            user_query = chat_example.get("user_message", {}).get("content", "")
            assistant_response = chat_example.get("assistant_message", {}).get("content", "")
            models = chat_example.get("assistant_message", {}).get("models", ["unknown"])

            if not user_query or not assistant_response:
                return None

            # Extract reasoning from response
            reasoning = self._extract_reasoning(assistant_response)

            # Infer tools from response
            tools_used = self._infer_tools(assistant_response)

            # Determine output format
            output_format = self._determine_output_format(assistant_response)

            # Extract success indicators
            success_indicators = self._extract_success_indicators(assistant_response)

            # Format the expected output for agent
            formatted_output = self._format_agent_output(
                assistant_response,
                tools_used,
                output_format
            )

            return AgentExample(
                input=user_query,
                expected_output=formatted_output,
                reasoning=reasoning,
                tools_used=tools_used,
                output_format=output_format,
                model=models[0] if models else "unknown",
                success_indicators=success_indicators
            )

        except Exception as e:
            logger.warning(f"Failed to convert chat example: {e}")
            return None

    def _extract_reasoning(self, response: str) -> str:
        """Extract step-by-step reasoning from the response."""
        # Look for numbered steps or reasoning markers
        lines = response.split('\n')
        reasoning_lines = []

        for i, line in enumerate(lines[:10]):  # First 10 lines usually contain reasoning
            line_lower = line.lower()
            if any(marker in line_lower for marker in ["step", "first", "then", "next", "because", "reason"]):
                reasoning_lines.append(line.strip())

            # Also include lines that look like steps
            if re.match(r'^\d+\.\s|^-\s|^\*\s', line.strip()):
                reasoning_lines.append(line.strip())

        return " ".join(reasoning_lines[:5]) if reasoning_lines else "See response for detailed explanation"

    def _infer_tools(self, response: str) -> List[str]:
        """Infer which tools were used based on response content."""
        tools = []

        # Check for command-line tools
        tool_patterns = {
            "bash": r"```\s*bash|```\s*shell|\$\s",
            "python": r"```\s*python|import\s|def\s",
            "javascript": r"```\s*javascript|```\s*js|function\s|const\s",
            "curl": r"curl\s+",
            "git": r"git\s+\w+",
            "docker": r"docker\s+\w+",
            "npm": r"npm\s+",
            "sql": r"```\s*sql|SELECT|INSERT|UPDATE",
            "json": r"```\s*json|\{.*\}",
        }

        for tool, pattern in tool_patterns.items():
            if re.search(pattern, response, re.IGNORECASE | re.DOTALL):
                tools.append(tool)

        return tools if tools else ["text"]

    def _determine_output_format(self, response: str) -> str:
        """Determine what kind of output this is."""
        response_lower = response.lower()

        if "```" in response:
            # Determine code type
            if "python" in response[:200]:
                return "python_code"
            elif "bash" in response[:200] or "shell" in response[:200]:
                return "bash_script"
            elif "javascript" in response[:200] or re.search(r"```\s*js", response[:200]):
                return "javascript_code"
            else:
                return "code_block"
        elif "```" not in response and any(cmd in response_lower for cmd in ["systemctl", "docker", "npm", "python", "bash", "$"]):
            return "command_sequence"
        elif re.search(r'\{.*\}', response, re.DOTALL):
            return "json_response"
        else:
            return "explanation"

    def _extract_success_indicators(self, response: str) -> List[str]:
        """Extract indicators of successful response."""
        indicators = []

        if len(response) > 300:
            indicators.append("detailed_response")
        if "```" in response:
            indicators.append("includes_code")
        if any(word in response.lower() for word in ["step", "first", "then", "next"]):
            indicators.append("step_by_step")
        if len(response.split('\n')) > 5:
            indicators.append("well_structured")
        if any(word in response.lower() for word in ["example", "for instance", "such as"]):
            indicators.append("includes_examples")

        return indicators

    def _format_agent_output(
        self,
        response: str,
        tools_used: List[str],
        output_format: str
    ) -> str:
        """Format the response for agent output."""
        # For now, keep the original response
        # In real implementation, would convert to tool-calling format

        formatted = response

        # If tools were used, add tool call markers
        if tools_used and tools_used != ["text"]:
            formatted = f"TOOLS: {', '.join(tools_used)}\n\n{formatted}"

        return formatted

    def generate_few_shot_prompts(self, num_examples: int = 5) -> Dict[str, Any]:
        """Generate few-shot prompt examples for agent prompting."""
        if not self.agent_examples:
            logger.warning("No agent examples available for few-shot generation")
            return {}

        # Select diverse examples
        selected = self._select_diverse_examples(num_examples)

        few_shot_prompt = """Here are some examples of successfully completing similar tasks:

"""
        for i, example in enumerate(selected, 1):
            few_shot_prompt += f"""Example {i}:
User Query: {example.input[:150]}...
Expected Approach: {example.reasoning[:100]}...
Tools to use: {', '.join(example.tools_used)}
Output format: {example.output_format}

"""

        return {
            "few_shot_prompt": few_shot_prompt,
            "num_examples": len(selected),
            "examples": [asdict(ex) for ex in selected]
        }

    def _select_diverse_examples(self, num_examples: int) -> List[AgentExample]:
        """Select diverse examples covering different output formats."""
        selected = []
        formats_covered = set()

        # First, pick examples with different output formats
        for example in self.agent_examples:
            if example.output_format not in formats_covered and len(selected) < num_examples:
                selected.append(example)
                formats_covered.add(example.output_format)

        # Fill remaining with any examples
        for example in self.agent_examples:
            if len(selected) < num_examples and example not in selected:
                selected.append(example)

        return selected

    def export_examples_to_jsonl(self, output_path: Optional[str] = None) -> str:
        """
        Export examples in JSONL format for fine-tuning.

        Args:
            output_path: Path to save JSONL file

        Returns:
            Path to saved file
        """
        if output_path is None:
            output_path = str(Path.home() / "Nextcloud/DEV/ollmcp/mcp-client-for-ollama/data/agent_training_examples.jsonl")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            for example in self.agent_examples:
                # Format as OpenAI fine-tuning format
                training_entry = {
                    "messages": [
                        {
                            "role": "user",
                            "content": example.input
                        },
                        {
                            "role": "assistant",
                            "content": example.expected_output
                        }
                    ],
                    "metadata": {
                        "reasoning": example.reasoning,
                        "tools": example.tools_used,
                        "format": example.output_format,
                        "source_model": example.model,
                        "success_indicators": example.success_indicators
                    }
                }
                f.write(json.dumps(training_entry) + '\n')

        logger.info(f"Exported {len(self.agent_examples)} examples to {output_path}")
        return output_path

    def get_examples_summary(self) -> Dict[str, Any]:
        """Get summary statistics about generated examples."""
        if not self.agent_examples:
            return {"total_examples": 0}

        formats = {}
        for example in self.agent_examples:
            fmt = example.output_format
            formats[fmt] = formats.get(fmt, 0) + 1

        return {
            "total_examples": len(self.agent_examples),
            "formats": formats,
            "models_represented": list(set(e.model for e in self.agent_examples)),
            "avg_input_length": sum(len(e.input) for e in self.agent_examples) / len(self.agent_examples),
        }

    def _initialize_format_templates(self) -> Dict[str, str]:
        """Initialize templates for different output formats."""
        return {
            "tool_call": "CALL_TOOL: {tool_name}\nARGS: {args}",
            "code": "```{language}\n{code}\n```",
            "command": "$ {command}",
            "json": "```json\n{json_content}\n```",
        }
