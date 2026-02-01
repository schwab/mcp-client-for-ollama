"""Knowledge Extractor - Extracts transferable knowledge from chat successes."""

import logging
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TransferableKnowledge:
    """Represents knowledge that can be transferred from chat to agents."""
    knowledge_type: str  # "prompt_pattern", "tool_usage", "reasoning", "formatting"
    content: str
    confidence: float  # 0-1
    applicable_to_agents: List[str]  # List of agent types that could use this
    examples: List[Dict[str, str]]  # Examples of this pattern


class KnowledgeExtractor:
    """Extracts transferable knowledge from chat successes."""

    def __init__(self):
        """Initialize the knowledge extractor."""
        self.extracted_knowledge: List[TransferableKnowledge] = []
        self.prompt_patterns: Set[str] = set()
        self.tool_patterns: Dict[str, List[str]] = {}
        self.reasoning_patterns: List[Dict[str, Any]] = []
        self.formatting_patterns: Dict[str, str] = {}

    def extract_transferable_knowledge(
        self,
        chat_successes: List[Dict[str, Any]],
        agent_failures: Optional[List[Dict[str, Any]]] = None
    ) -> List[TransferableKnowledge]:
        """
        Identify what chat does differently that could help agents.

        Args:
            chat_successes: List of successful chat interactions
            agent_failures: Optional list of agent failures to target

        Returns:
            List of transferable knowledge items
        """
        logger.info(f"Extracting knowledge from {len(chat_successes)} successful chat interactions...")

        # Extract different types of patterns
        self._extract_prompt_patterns(chat_successes)
        self._extract_tool_patterns(chat_successes)
        self._extract_reasoning_patterns(chat_successes)
        self._extract_formatting_patterns(chat_successes)

        # If agent failures provided, prioritize knowledge that addresses them
        if agent_failures:
            self._prioritize_for_failures(agent_failures)

        return self.extracted_knowledge

    def _extract_prompt_patterns(self, chat_successes: List[Dict[str, Any]]) -> None:
        """Extract effective prompt patterns from successful chats."""
        logger.debug("Extracting prompt patterns...")

        for success in chat_successes:
            user_query = success.get("user_message", {}).get("content", "")
            assistant_response = success.get("assistant_message", {}).get("content", "")

            if not user_query or not assistant_response:
                continue

            # Extract patterns: instructions that appear in successful queries
            patterns = self._identify_prompt_instructions(user_query)
            self.prompt_patterns.update(patterns)

            # Create knowledge item
            knowledge = TransferableKnowledge(
                knowledge_type="prompt_pattern",
                content=f"Use explicit instructions: {patterns}",
                confidence=self._calculate_confidence(assistant_response),
                applicable_to_agents=["CODER", "EXECUTOR", "PLANNER"],
                examples=[{
                    "user": user_query[:200],
                    "response": assistant_response[:200]
                }]
            )
            self.extracted_knowledge.append(knowledge)

    def _identify_prompt_instructions(self, query: str) -> Set[str]:
        """Identify effective instruction patterns in a query."""
        patterns = set()

        # Look for imperative verbs
        imperatives = ["create", "write", "build", "generate", "show", "provide", "explain", "list"]
        for verb in imperatives:
            if verb in query.lower():
                patterns.add(f"start_with_{verb}")

        # Look for structured requests
        if ":" in query or "\n" in query:
            patterns.add("structured_request")

        if "step" in query.lower() or "how to" in query.lower():
            patterns.add("step_by_step_guidance")

        if "example" in query.lower():
            patterns.add("request_examples")

        return patterns

    def _extract_tool_patterns(self, chat_successes: List[Dict[str, Any]]) -> None:
        """Extract tool usage patterns from successful chats."""
        logger.debug("Extracting tool patterns...")

        for success in chat_successes:
            response = success.get("assistant_message", {}).get("content", "")
            user_query = success.get("user_message", {}).get("content", "")

            if not response:
                continue

            # Identify tools mentioned in response
            tools = self._identify_tools_in_response(response, user_query)

            for tool in tools:
                if tool not in self.tool_patterns:
                    self.tool_patterns[tool] = []
                self.tool_patterns[tool].append(response[:500])

                # Create knowledge item
                knowledge = TransferableKnowledge(
                    knowledge_type="tool_usage",
                    content=f"Tool '{tool}' effectively used in context",
                    confidence=0.8,
                    applicable_to_agents=["EXECUTOR", "CODER"],
                    examples=[{
                        "tool": tool,
                        "context": user_query[:100]
                    }]
                )
                self.extracted_knowledge.append(knowledge)

    def _identify_tools_in_response(self, response: str, context: str) -> Set[str]:
        """Identify tools (commands, APIs, etc.) mentioned in response."""
        tools = set()

        # Look for common tool patterns
        tool_patterns = {
            "curl": r"curl\s+",
            "git": r"git\s+\w+",
            "docker": r"docker\s+\w+",
            "npm": r"npm\s+\w+",
            "python": r"python.*\.py",
            "bash": r"bash\s+",
            "jq": r"jq\s+",
            "grep": r"grep\s+",
            "find": r"find\s+",
            "awk": r"awk\s+",
        }

        for tool_name, pattern in tool_patterns.items():
            if re.search(pattern, response, re.IGNORECASE):
                tools.add(tool_name)

        # Also check context for what the user asked for
        if "api" in context.lower() or "request" in context.lower():
            tools.add("api_call")
        if "file" in context.lower() or "path" in context.lower():
            tools.add("file_operations")

        return tools

    def _extract_reasoning_patterns(self, chat_successes: List[Dict[str, Any]]) -> None:
        """Extract reasoning and explanation patterns."""
        logger.debug("Extracting reasoning patterns...")

        for success in chat_successes:
            response = success.get("assistant_message", {}).get("content", "")

            if not response:
                continue

            # Check if response contains reasoning markers
            reasoning_markers = ["because", "therefore", "first", "then", "next", "however", "note that"]
            has_reasoning = any(marker in response.lower() for marker in reasoning_markers)

            if has_reasoning:
                # Extract first few steps/sentences
                sentences = response.split(".")[:3]
                reasoning_text = ". ".join(sentences)

                pattern = {
                    "structure": "step_by_step",
                    "content": reasoning_text[:300],
                    "marker_count": sum(response.lower().count(m) for m in reasoning_markers)
                }
                self.reasoning_patterns.append(pattern)

                knowledge = TransferableKnowledge(
                    knowledge_type="reasoning",
                    content="Include step-by-step reasoning and explanations",
                    confidence=min(0.9, (pattern["marker_count"] / 5) * 0.9),
                    applicable_to_agents=["PLANNER", "DEBUGGER", "CODER"],
                    examples=[{"reasoning": reasoning_text[:200]}]
                )
                self.extracted_knowledge.append(knowledge)

    def _extract_formatting_patterns(self, chat_successes: List[Dict[str, Any]]) -> None:
        """Extract output formatting patterns."""
        logger.debug("Extracting formatting patterns...")

        for success in chat_successes:
            response = success.get("assistant_message", {}).get("content", "")

            if not response:
                continue

            # Check for formatting elements
            formatting_patterns = {
                "code_blocks": "```" in response,
                "bullet_points": "- " in response or "* " in response,
                "numbered_list": re.search(r"\d+\.", response) is not None,
                "bold_text": "**" in response or "__" in response,
                "inline_code": "`" in response,
            }

            for fmt_type, present in formatting_patterns.items():
                if present:
                    if fmt_type not in self.formatting_patterns:
                        self.formatting_patterns[fmt_type] = "effective"

                    knowledge = TransferableKnowledge(
                        knowledge_type="formatting",
                        content=f"Use {fmt_type} for better readability",
                        confidence=0.85,
                        applicable_to_agents=["CODER", "EXECUTOR"],
                        examples=[{"format": fmt_type}]
                    )
                    self.extracted_knowledge.append(knowledge)

    def _calculate_confidence(self, response: str) -> float:
        """Calculate confidence score for knowledge based on response quality."""
        score = 0.5

        # Longer responses tend to be more detailed
        if len(response) > 500:
            score += 0.15
        if len(response) > 1000:
            score += 0.15

        # Responses with code blocks are usually high quality
        if "```" in response:
            score += 0.1

        return min(1.0, score)

    def _prioritize_for_failures(self, agent_failures: List[Dict[str, Any]]) -> None:
        """Re-prioritize extracted knowledge to address agent failures."""
        logger.debug(f"Prioritizing knowledge to address {len(agent_failures)} agent failures...")

        # Analyze failure patterns and boost confidence of relevant knowledge
        for failure in agent_failures:
            failure_type = failure.get("error_type", "unknown")

            # Boost confidence for knowledge relevant to this failure type
            for knowledge in self.extracted_knowledge:
                if failure_type == "tool_calling" and knowledge.knowledge_type in ["tool_usage", "prompt_pattern"]:
                    knowledge.confidence = min(1.0, knowledge.confidence + 0.2)
                elif failure_type == "parameter" and knowledge.knowledge_type == "formatting":
                    knowledge.confidence = min(1.0, knowledge.confidence + 0.2)
                elif failure_type == "reasoning" and knowledge.knowledge_type == "reasoning":
                    knowledge.confidence = min(1.0, knowledge.confidence + 0.2)

    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary of extracted knowledge."""
        return {
            "total_knowledge_items": len(self.extracted_knowledge),
            "by_type": {
                "prompt_patterns": len([k for k in self.extracted_knowledge if k.knowledge_type == "prompt_pattern"]),
                "tool_usage": len([k for k in self.extracted_knowledge if k.knowledge_type == "tool_usage"]),
                "reasoning": len([k for k in self.extracted_knowledge if k.knowledge_type == "reasoning"]),
                "formatting": len([k for k in self.extracted_knowledge if k.knowledge_type == "formatting"]),
            },
            "unique_tools_identified": list(self.tool_patterns.keys()),
            "prompt_patterns": list(self.prompt_patterns),
        }

    def get_high_confidence_knowledge(self, min_confidence: float = 0.8) -> List[TransferableKnowledge]:
        """Get knowledge items with confidence above threshold."""
        return [k for k in self.extracted_knowledge if k.confidence >= min_confidence]
