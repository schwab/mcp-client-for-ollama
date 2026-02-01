"""Model Optimizer - Specializes models for different agent roles."""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OptimizationProfile:
    """Optimization profile for a model-agent combination."""
    model_name: str
    agent_type: str  # CODER, EXECUTOR, PLANNER, DEBUGGER, etc.
    optimized_prompt: str
    few_shot_examples: List[Dict[str, str]]
    temperature: float
    top_p: float
    max_tokens: int
    stop_sequences: List[str]
    description: str


class ModelOptimizer:
    """
    Optimizes different models for different agent roles.
    Creates specialized prompts and configurations for each model-agent combination.
    """

    def __init__(self):
        """Initialize the model optimizer."""
        self.agent_requirements = self._initialize_agent_requirements()
        self.model_characteristics = self._initialize_model_characteristics()
        self.optimization_profiles: Dict[str, Dict[str, OptimizationProfile]] = {}

    def optimize_model_for_agent(
        self,
        model_name: str,
        agent_type: str,
        chat_examples: Optional[List[Dict[str, Any]]] = None
    ) -> OptimizationProfile:
        """
        Create a specialized optimization profile for a model-agent pair.

        Args:
            model_name: Name of the model to optimize
            agent_type: Type of agent (CODER, EXECUTOR, etc.)
            chat_examples: Optional successful examples from chat mode

        Returns:
            OptimizationProfile with specialized configuration
        """
        logger.info(f"Optimizing {model_name} for {agent_type} agent")

        # Get requirements for this agent type
        requirements = self.agent_requirements.get(agent_type, {})

        # Get characteristics of this model
        model_chars = self.model_characteristics.get(model_name, {})

        # Create optimized prompt
        optimized_prompt = self._create_optimized_prompt(
            model_name,
            agent_type,
            requirements,
            chat_examples
        )

        # Create tool usage examples
        tool_examples = self._create_tool_examples(
            agent_type,
            chat_examples
        ) if chat_examples else []

        # Optimize parameters
        temp = self._optimize_temperature(model_name, agent_type)
        top_p = self._optimize_top_p(model_name, agent_type)
        max_tokens = self._optimize_max_tokens(model_name, agent_type)
        stop_seqs = self._get_stop_sequences(agent_type)

        profile = OptimizationProfile(
            model_name=model_name,
            agent_type=agent_type,
            optimized_prompt=optimized_prompt,
            few_shot_examples=tool_examples,
            temperature=temp,
            top_p=top_p,
            max_tokens=max_tokens,
            stop_sequences=stop_seqs,
            description=f"Optimized for {agent_type} tasks"
        )

        # Store profile
        if model_name not in self.optimization_profiles:
            self.optimization_profiles[model_name] = {}
        self.optimization_profiles[model_name][agent_type] = profile

        return profile

    def _create_optimized_prompt(
        self,
        model_name: str,
        agent_type: str,
        requirements: Dict[str, Any],
        chat_examples: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Create a specialized prompt for this model-agent combination."""

        base_prompt = self._get_base_prompt(agent_type)
        task_focus = requirements.get("task_focus", "")
        tools = requirements.get("tools", [])

        prompt = f"""{base_prompt}

AGENT TYPE: {agent_type}
MODEL: {model_name}

PRIMARY RESPONSIBILITIES:
{task_focus}

TOOLS AVAILABLE:
{self._format_tools_list(tools)}

GUIDELINES:
1. Follow instructions precisely
2. Use available tools appropriately
3. Provide clear reasoning for decisions
4. Handle errors gracefully
"""

        # Add few-shot examples if provided
        if chat_examples:
            prompt += "\nEXAMPLES OF SUCCESSFUL APPROACHES:\n"
            for i, example in enumerate(chat_examples[:3], 1):
                prompt += f"\nExample {i}:\n"
                prompt += f"Task: {example.get('user_message', {}).get('content', '')[:100]}...\n"
                prompt += f"Approach: {example.get('approach', 'Follow guidelines above')}\n"

        return prompt

    def _get_base_prompt(self, agent_type: str) -> str:
        """Get base prompt template for agent type."""
        base_prompts = {
            "CODER": """You are an expert programming assistant. Your role is to:
- Write high-quality, efficient code
- Follow best practices and patterns
- Provide clear explanations
- Handle edge cases appropriately""",

            "EXECUTOR": """You are a task execution specialist. Your role is to:
- Execute commands and operations
- Select appropriate tools for tasks
- Handle failures and retry when needed
- Provide clear output and status updates""",

            "PLANNER": """You are a strategic planner. Your role is to:
- Break down complex tasks into steps
- Identify dependencies and resources
- Create efficient plans
- Adapt plans based on feedback""",

            "DEBUGGER": """You are a debugging expert. Your role is to:
- Identify and isolate problems
- Provide systematic troubleshooting steps
- Suggest solutions with explanations
- Verify fixes are working""",

            "READER": """You are an information extraction specialist. Your role is to:
- Read and understand documentation
- Extract relevant information
- Summarize key points
- Answer specific questions accurately""",
        }

        return base_prompts.get(agent_type, "You are a helpful assistant.")

    def _format_tools_list(self, tools: List[str]) -> str:
        """Format tools list for prompt."""
        if not tools:
            return "- Check available tools dynamically"

        return "\n".join(f"- {tool}" for tool in tools)

    def _create_tool_examples(
        self,
        agent_type: str,
        chat_examples: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Create tool usage examples relevant to agent type."""
        examples = []

        for example in chat_examples[:5]:
            assistant_response = example.get("assistant_message", {}).get("content", "")

            # Extract if this example is relevant to agent type
            if self._is_relevant_to_agent(assistant_response, agent_type):
                examples.append({
                    "user": example.get("user_message", {}).get("content", "")[:150],
                    "approach": self._extract_approach(assistant_response),
                    "tools_used": self._extract_tools(assistant_response),
                })

        return examples

    def _is_relevant_to_agent(self, response: str, agent_type: str) -> bool:
        """Check if example is relevant to agent type."""
        response_lower = response.lower()

        relevance_keywords = {
            "CODER": ["code", "function", "class", "python", "javascript", "script"],
            "EXECUTOR": ["command", "execute", "run", "bash", "shell", "docker"],
            "PLANNER": ["step", "plan", "organize", "sequence", "strategy"],
            "DEBUGGER": ["error", "debug", "fix", "issue", "problem"],
            "READER": ["documentation", "read", "understand", "extract", "summary"],
        }

        keywords = relevance_keywords.get(agent_type, [])
        return any(keyword in response_lower for keyword in keywords)

    def _extract_approach(self, response: str) -> str:
        """Extract the approach/strategy from a response."""
        lines = response.split('\n')
        # Get first non-empty line or first 100 chars
        for line in lines:
            if line.strip():
                return line.strip()[:150]
        return response[:150]

    def _extract_tools(self, response: str) -> List[str]:
        """Extract tools mentioned in response."""
        tools = []

        tool_keywords = {
            "curl": ["curl", "http request"],
            "git": ["git ", "repository"],
            "docker": ["docker", "container"],
            "python": ["python", "import", "def"],
            "bash": ["bash", "shell script", "#!/bin/bash"],
            "sql": ["SELECT", "INSERT", "database"],
        }

        response_lower = response.lower()
        for tool, keywords in tool_keywords.items():
            if any(kw in response_lower for kw in keywords):
                tools.append(tool)

        return tools if tools else ["text"]

    def _optimize_temperature(self, model_name: str, agent_type: str) -> float:
        """Optimize temperature parameter for model-agent combination."""
        # Higher temp = more creative, lower = more deterministic
        # Executors/Debuggers: low temp (0.2-0.4)
        # Coders: medium temp (0.5-0.7)
        # Planners: medium-high temp (0.7-0.9)

        base_temps = {
            "EXECUTOR": 0.3,
            "DEBUGGER": 0.2,
            "CODER": 0.6,
            "PLANNER": 0.8,
            "READER": 0.3,
        }

        # Adjust based on model
        base = base_temps.get(agent_type, 0.5)

        # Some models work better with different temperatures
        if "3b" in model_name or "small" in model_name:
            base += 0.1  # Smaller models: slightly higher creativity
        elif "large" in model_name or "34b" in model_name:
            base -= 0.1  # Larger models: slightly lower temperature

        return max(0.0, min(2.0, base))  # Clamp to valid range

    def _optimize_top_p(self, model_name: str, agent_type: str) -> float:
        """Optimize nucleus sampling parameter."""
        # More deterministic agents: lower top_p
        # More creative agents: higher top_p

        base_top_p = {
            "EXECUTOR": 0.8,
            "DEBUGGER": 0.7,
            "CODER": 0.85,
            "PLANNER": 0.9,
            "READER": 0.7,
        }

        return base_top_p.get(agent_type, 0.8)

    def _optimize_max_tokens(self, model_name: str, agent_type: str) -> int:
        """Optimize max tokens for agent type."""
        # Executors: shorter responses
        # Coders: longer responses
        # Planners: medium responses

        base_max_tokens = {
            "EXECUTOR": 1000,
            "DEBUGGER": 1500,
            "CODER": 2000,
            "PLANNER": 1500,
            "READER": 1000,
        }

        # Adjust based on model context window
        max_tokens = base_max_tokens.get(agent_type, 1500)

        if "32b" in model_name or "large" in model_name:
            max_tokens = min(max_tokens * 2, 4000)  # Can handle more
        elif "3b" in model_name or "small" in model_name:
            max_tokens = min(max_tokens, 1000)  # Limited context

        return max_tokens

    def _get_stop_sequences(self, agent_type: str) -> List[str]:
        """Get stop sequences for agent type."""
        base_stops = ["\n\nUser:", "\n\nAssistant:", "---"]

        # Add agent-specific stops
        if agent_type == "EXECUTOR":
            base_stops.extend(["$", ">>>"])
        elif agent_type == "CODER":
            base_stops.extend(["```\n\n", "# End of code"])

        return base_stops

    def _initialize_agent_requirements(self) -> Dict[str, Dict[str, Any]]:
        """Define requirements for each agent type."""
        return {
            "CODER": {
                "task_focus": "Write, review, and debug code. Understand requirements and implement solutions.",
                "tools": ["language_models", "code_execution", "file_operations", "debugging"],
                "key_skills": ["syntax_accuracy", "logic_design", "error_handling"],
            },
            "EXECUTOR": {
                "task_focus": "Execute commands, manage systems, handle operations. Take action on requests.",
                "tools": ["shell_commands", "package_managers", "service_management", "file_operations"],
                "key_skills": ["reliability", "error_recovery", "status_reporting"],
            },
            "PLANNER": {
                "task_focus": "Plan complex tasks, break them into steps, coordinate execution.",
                "tools": ["task_analysis", "dependency_analysis", "resource_planning"],
                "key_skills": ["strategic_thinking", "sequencing", "adaptation"],
            },
            "DEBUGGER": {
                "task_focus": "Identify problems, troubleshoot issues, verify solutions.",
                "tools": ["error_analysis", "logging", "testing", "verification"],
                "key_skills": ["problem_analysis", "systematic_approach", "verification"],
            },
            "READER": {
                "task_focus": "Read documentation, extract information, answer questions.",
                "tools": ["document_reading", "information_extraction", "summarization"],
                "key_skills": ["comprehension", "extraction", "clarity"],
            },
        }

    def _initialize_model_characteristics(self) -> Dict[str, Dict[str, Any]]:
        """Define characteristics of known models."""
        return {
            "qwen2.5-coder:32b": {
                "strengths": ["code_generation", "multi_turn", "reasoning"],
                "weaknesses": ["tool_calling", "parameter_accuracy"],
                "context_window": 32000,
                "native_tools": False,
            },
            "qwen2.5-coder:14b": {
                "strengths": ["code_generation", "practical_coding"],
                "weaknesses": ["complex_reasoning", "tool_calling"],
                "context_window": 32000,
                "native_tools": False,
            },
            "granite-3.1-8b-instruct": {
                "strengths": ["instruction_following", "command_execution"],
                "weaknesses": ["complex_code", "tool_calling"],
                "context_window": 8000,
                "native_tools": False,
            },
        }

    def export_profile(self, profile: OptimizationProfile, output_path: Optional[str] = None) -> str:
        """Export optimization profile to JSON file."""
        if output_path is None:
            output_dir = Path.home() / "Nextcloud/DEV/ollmcp/mcp-client-for-ollama/data/optimization_profiles"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / f"{profile.model_name}_{profile.agent_type}.json")

        with open(output_path, 'w') as f:
            json.dump({
                "model_name": profile.model_name,
                "agent_type": profile.agent_type,
                "optimized_prompt": profile.optimized_prompt,
                "few_shot_examples": profile.few_shot_examples,
                "temperature": profile.temperature,
                "top_p": profile.top_p,
                "max_tokens": profile.max_tokens,
                "stop_sequences": profile.stop_sequences,
                "description": profile.description,
            }, f, indent=2)

        logger.info(f"Exported profile to {output_path}")
        return output_path

    def get_profile(self, model_name: str, agent_type: str) -> Optional[OptimizationProfile]:
        """Retrieve a stored optimization profile."""
        if model_name in self.optimization_profiles:
            return self.optimization_profiles[model_name].get(agent_type)
        return None
