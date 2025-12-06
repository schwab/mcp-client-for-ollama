"""
Agent configuration management for the delegation system.

This module handles loading and managing agent type configurations from
JSON definition files.
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class AgentConfig:
    """
    Configuration for a specialized agent type.

    Agent configurations are loaded from JSON files in the agents/definitions/
    directory. Each agent type has specific capabilities, tools, and constraints
    optimized for a particular kind of task.

    Attributes:
        agent_type: Unique identifier for this agent type (e.g., "READER", "CODER")
        display_name: Human-readable name for UI display
        description: Brief description of agent's purpose and capabilities
        system_prompt: System message that defines agent behavior
        default_tools: List of tool names this agent can use by default
        allowed_tool_categories: Categories of tools this agent can access
        forbidden_tools: Tools explicitly prohibited for this agent
        max_context_tokens: Maximum context window size for this agent
        loop_limit: Maximum number of tool-call iterations
        temperature: Sampling temperature for model responses
        planning_hints: Guidance for planner on when to use this agent
        output_format: Expected output format specification (optional)
    """

    agent_type: str
    display_name: str
    description: str
    system_prompt: str
    default_tools: List[str]
    allowed_tool_categories: List[str] = field(default_factory=list)
    forbidden_tools: List[str] = field(default_factory=list)
    max_context_tokens: int = 8192
    loop_limit: int = 2
    temperature: float = 0.5
    planning_hints: Optional[str] = None
    output_format: Optional[Dict[str, Any]] = None

    @classmethod
    def from_json_file(cls, file_path: str) -> 'AgentConfig':
        """
        Load agent configuration from a JSON definition file.

        Args:
            file_path: Path to the JSON definition file

        Returns:
            AgentConfig instance loaded from the file

        Raises:
            FileNotFoundError: If the definition file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
            KeyError: If required fields are missing
        """
        with open(file_path, 'r') as f:
            data = json.load(f)

        return cls(
            agent_type=data['agent_type'],
            display_name=data['display_name'],
            description=data['description'],
            system_prompt=data['system_prompt'],
            default_tools=data['default_tools'],
            allowed_tool_categories=data.get('allowed_tool_categories', []),
            forbidden_tools=data.get('forbidden_tools', []),
            max_context_tokens=data.get('max_context_tokens', 8192),
            loop_limit=data.get('loop_limit', 2),
            temperature=data.get('temperature', 0.5),
            planning_hints=data.get('planning_hints'),
            output_format=data.get('output_format'),
        )

    @classmethod
    def load_all_definitions(cls, definitions_dir: Optional[str] = None) -> Dict[str, 'AgentConfig']:
        """
        Load all agent definitions from the definitions directory.

        Args:
            definitions_dir: Path to definitions directory.
                           If None, uses default agents/definitions/ path.

        Returns:
            Dictionary mapping agent_type to AgentConfig instances

        Raises:
            FileNotFoundError: If definitions directory doesn't exist
        """
        if definitions_dir is None:
            # Default to agents/definitions/ relative to this file
            current_dir = Path(__file__).parent
            definitions_dir = current_dir / "definitions"

        definitions_path = Path(definitions_dir)
        if not definitions_path.exists():
            raise FileNotFoundError(f"Definitions directory not found: {definitions_dir}")

        configs = {}
        for json_file in definitions_path.glob("*.json"):
            try:
                config = cls.from_json_file(str(json_file))
                configs[config.agent_type] = config
            except Exception as e:
                # Log error but continue loading other definitions
                print(f"Warning: Failed to load {json_file.name}: {e}")

        return configs

    def get_effective_tools(self, available_tools: List[str]) -> List[str]:
        """
        Calculate the actual tools this agent can use.

        Combines default_tools with available_tools, respecting forbidden_tools.

        Args:
            available_tools: List of all tools available from MCP servers + builtin

        Returns:
            List of tool names this agent can actually use
        """
        # Start with default tools
        effective = set(self.default_tools)

        # Remove forbidden tools
        effective -= set(self.forbidden_tools)

        # Filter to only tools that are actually available
        effective = effective.intersection(set(available_tools))

        return list(effective)

    def matches_tool_category(self, tool_name: str, tool_categories: Dict[str, List[str]]) -> bool:
        """
        Check if a tool matches this agent's allowed categories.

        Args:
            tool_name: Name of the tool to check
            tool_categories: Dictionary mapping category names to lists of tool names

        Returns:
            True if tool is in an allowed category, False otherwise
        """
        if not self.allowed_tool_categories:
            # No category restrictions
            return True

        for category in self.allowed_tool_categories:
            if category in tool_categories and tool_name in tool_categories[category]:
                return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary for serialization.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            "agent_type": self.agent_type,
            "display_name": self.display_name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "default_tools": self.default_tools,
            "allowed_tool_categories": self.allowed_tool_categories,
            "forbidden_tools": self.forbidden_tools,
            "max_context_tokens": self.max_context_tokens,
            "loop_limit": self.loop_limit,
            "temperature": self.temperature,
            "planning_hints": self.planning_hints,
            "output_format": self.output_format,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"AgentConfig(agent_type={self.agent_type}, "
            f"display_name={self.display_name}, "
            f"tools={len(self.default_tools)}, "
            f"max_tokens={self.max_context_tokens})"
        )
