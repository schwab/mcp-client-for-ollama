"""Chat History Analyzer - Ingests and analyzes successful chat interactions."""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Categories of tasks that can be analyzed from chat history."""
    COMMAND_EXECUTION = "command_execution"
    CODE_GENERATION = "code_generation"
    TOOL_SELECTION = "tool_selection"
    PARAMETER_FORMATTING = "parameter_formatting"
    SYSTEM_INTERACTION = "system_interaction"
    UNKNOWN = "unknown"


@dataclass
class ChatMessage:
    """Represents a single chat message with metadata."""
    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: int
    models: List[str]
    parent_id: Optional[str] = None
    children_ids: Optional[List[str]] = None


@dataclass
class ConversationChain:
    """Represents a user-assistant exchange."""
    user_message: ChatMessage
    assistant_response: ChatMessage
    task_type: TaskType
    success_indicators: List[str]


class ChatHistoryAnalyzer:
    """
    Processes chat logs from Open Web UI, extracting successful patterns
    and organizing them by task type for transfer to agent mode.
    """

    def __init__(self, chat_history_path: Optional[str] = None):
        """
        Initialize the analyzer.

        Args:
            chat_history_path: Path to the chat history JSON export.
                               If None, uses default data directory.
        """
        self.chat_history_path = Path(chat_history_path) if chat_history_path else self._get_default_path()
        self.conversations: List[Dict[str, Any]] = []
        self.patterns: Dict[TaskType, List[ConversationChain]] = {t: [] for t in TaskType}
        self.model_success_rates: Dict[str, Dict[TaskType, float]] = {}
        self._load_chat_history()

    def _get_default_path(self) -> Path:
        """Get the default chat history export path."""
        return Path.home() / "Nextcloud/DEV/ollmcp/mcp-client-for-ollama/data/folder-Dev-export-1769875679739.json"

    def _load_chat_history(self) -> None:
        """Load and parse the chat history JSON file."""
        if not self.chat_history_path.exists():
            logger.warning(f"Chat history file not found: {self.chat_history_path}")
            return

        try:
            with open(self.chat_history_path, 'r') as f:
                self.conversations = json.load(f)
            logger.info(f"Loaded {len(self.conversations)} conversations")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            self.conversations = []

    def analyze_all(self) -> Dict[str, Any]:
        """
        Analyze all conversations and extract patterns.

        Returns:
            Dictionary containing analysis results
        """
        logger.info("Starting comprehensive chat history analysis...")

        # Extract conversation chains and classify them
        for conversation in self.conversations:
            self._analyze_conversation(conversation)

        # Calculate success rates by model
        self._calculate_success_rates()

        return {
            "total_conversations": len(self.conversations),
            "patterns_by_type": {t.value: len(patterns) for t, patterns in self.patterns.items()},
            "model_success_rates": self.model_success_rates,
        }

    def _analyze_conversation(self, conversation: Dict[str, Any]) -> None:
        """
        Analyze a single conversation to extract successful patterns.

        Args:
            conversation: A single conversation object from the export
        """
        title = conversation.get('title', 'Unknown')
        messages_dict = conversation.get('chat', {}).get('history', {}).get('messages', {})

        # Organize messages by parent-child relationships
        message_map = self._build_message_map(messages_dict)

        # Extract conversation chains (user -> assistant pairs)
        chains = self._extract_conversation_chains(message_map)

        # Classify each chain
        for chain in chains:
            task_type = self._classify_task(chain)
            success_indicators = self._detect_success_indicators(chain)

            conv_chain = ConversationChain(
                user_message=chain[0],
                assistant_response=chain[1],
                task_type=task_type,
                success_indicators=success_indicators
            )
            self.patterns[task_type].append(conv_chain)

    def _build_message_map(self, messages_dict: Dict[str, Dict]) -> Dict[str, ChatMessage]:
        """Convert raw message dict to ChatMessage objects with relationships."""
        message_map = {}

        for msg_id, msg_data in messages_dict.items():
            chat_msg = ChatMessage(
                id=msg_id,
                role=msg_data.get('role', 'unknown'),
                content=msg_data.get('content', ''),
                timestamp=msg_data.get('timestamp', 0),
                models=msg_data.get('models', []),
                parent_id=msg_data.get('parentId'),
                children_ids=msg_data.get('childrenIds', [])
            )
            message_map[msg_id] = chat_msg

        return message_map

    def _extract_conversation_chains(self, message_map: Dict[str, ChatMessage]) -> List[Tuple[ChatMessage, ChatMessage]]:
        """Extract user-assistant message pairs."""
        chains = []

        # Find root messages (no parent)
        root_messages = [msg for msg in message_map.values() if not msg.parent_id]

        # For each user message, find the corresponding assistant response
        for user_msg in root_messages:
            if user_msg.role != 'user':
                continue

            # Walk down the tree to find the first assistant response
            current = user_msg
            for child_id in (current.children_ids or []):
                if child_id in message_map:
                    child = message_map[child_id]
                    if child.role == 'assistant':
                        chains.append((user_msg, child))
                        break

        return chains

    def _classify_task(self, chain: Tuple[ChatMessage, ChatMessage]) -> TaskType:
        """Classify the type of task based on user input and response."""
        user_msg, assistant_msg = chain
        user_content = user_msg.content.lower()
        assistant_content = assistant_msg.content.lower()

        # Command execution patterns
        if any(keyword in user_content for keyword in ['systemctl', 'service', 'start', 'stop', 'restart', 'docker', 'npm run', 'python', 'bash']):
            return TaskType.COMMAND_EXECUTION

        # Code generation patterns
        if any(keyword in user_content for keyword in ['script', 'write', 'code', 'function', 'class', 'create', 'implement']):
            if any(lang in user_content for lang in ['python', 'javascript', 'typescript', 'bash', 'shell', 'sql']):
                return TaskType.CODE_GENERATION

        # Tool selection patterns
        if any(keyword in user_content for keyword in ['curl', 'wget', 'api', 'request', 'fetch', 'tool']):
            return TaskType.TOOL_SELECTION

        # Parameter formatting patterns
        if any(keyword in user_content for keyword in ['path', 'format', 'parameter', 'argument', 'flag', 'option']):
            return TaskType.PARAMETER_FORMATTING

        # System interaction patterns
        if any(keyword in user_content for keyword in ['folder', 'file', 'directory', 'flatten', 'organize', 'copy', 'move']):
            return TaskType.SYSTEM_INTERACTION

        return TaskType.UNKNOWN

    def _detect_success_indicators(self, chain: Tuple[ChatMessage, ChatMessage]) -> List[str]:
        """Detect indicators that this exchange was successful."""
        user_msg, assistant_msg = chain
        response = assistant_msg.content.lower()

        indicators = []

        # Success signals
        if 'here' in response and ('script' in response or 'code' in response or 'command' in response):
            indicators.append("provided_solution")
        if 'done' in response or 'complete' in response or 'finished' in response:
            indicators.append("task_completed")
        if len(assistant_msg.content) > 200:
            indicators.append("detailed_response")
        if '```' in assistant_msg.content:
            indicators.append("code_block_provided")
        if any(char in assistant_msg.content for char in ['#', '$', '>', '```']):
            indicators.append("formatted_code_or_commands")

        # Check for typical successful patterns
        if 'would' in response and 'this' in response:
            indicators.append("explanatory_response")

        return indicators

    def _calculate_success_rates(self) -> None:
        """Calculate success rates by model and task type."""
        model_stats: Dict[str, Dict[TaskType, Tuple[int, int]]] = {}

        for task_type, chains in self.patterns.items():
            for chain in chains:
                models = chain.assistant_response.models
                for model in models:
                    if model not in model_stats:
                        model_stats[model] = {t: (0, 0) for t in TaskType}

                    # Count as attempt
                    current = model_stats[model][task_type]
                    model_stats[model][task_type] = (current[0] + 1, current[1] + 1)

                    # Count as success if indicators present
                    if chain.success_indicators:
                        current = model_stats[model][task_type]
                        model_stats[model][task_type] = (current[0] + 1, current[1])

        # Convert to rates
        for model, stats in model_stats.items():
            self.model_success_rates[model] = {}
            for task_type, (successes, attempts) in stats.items():
                rate = (successes / attempts * 100) if attempts > 0 else 0
                self.model_success_rates[model][task_type.value] = round(rate, 1)

    def get_patterns_by_type(self, task_type: TaskType) -> List[ConversationChain]:
        """Get all patterns for a specific task type."""
        return self.patterns.get(task_type, [])

    def get_patterns_by_model(self, model_name: str) -> Dict[TaskType, List[ConversationChain]]:
        """Get all patterns produced by a specific model."""
        result = {t: [] for t in TaskType}

        for task_type, chains in self.patterns.items():
            for chain in chains:
                if model_name in chain.assistant_response.models:
                    result[task_type].append(chain)

        return result

    def get_successful_examples(self, task_type: TaskType, limit: int = 5) -> List[ConversationChain]:
        """Get successful examples of a specific task type."""
        patterns = self.get_patterns_by_type(task_type)
        # Sort by number of success indicators
        sorted_patterns = sorted(patterns, key=lambda p: len(p.success_indicators), reverse=True)
        return sorted_patterns[:limit]

    def export_patterns(self, output_path: Optional[str] = None) -> str:
        """
        Export analyzed patterns to a JSON file.

        Args:
            output_path: Path to save patterns. If None, uses default.

        Returns:
            Path to exported file
        """
        if output_path is None:
            output_path = str(Path.home() / "Nextcloud/DEV/ollmcp/mcp-client-for-ollama/data/extracted_patterns.json")

        export_data = {
            "analysis_timestamp": self._get_timestamp(),
            "total_conversations": len(self.conversations),
            "patterns_by_type": {}
        }

        for task_type, chains in self.patterns.items():
            export_data["patterns_by_type"][task_type.value] = [
                {
                    "user_query": chain.user_message.content,
                    "assistant_response": chain.assistant_response.content[:500],  # Truncate long responses
                    "models_used": chain.assistant_response.models,
                    "success_indicators": chain.success_indicators,
                    "timestamp": chain.assistant_response.timestamp,
                }
                for chain in chains
            ]

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Patterns exported to {output_path}")
        return output_path

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the analysis."""
        return {
            "total_conversations": len(self.conversations),
            "patterns_extracted": sum(len(p) for p in self.patterns.values()),
            "by_type": {t.value: len(p) for t, p in self.patterns.items()},
            "models_analyzed": list(self.model_success_rates.keys()),
            "success_rates_by_model": self.model_success_rates,
        }
