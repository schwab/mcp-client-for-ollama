from typing import List
from ollama._types import Message

from .base_tool_parser import BaseToolParser
from .json_tool_parser import JsonToolParser
from .python_tool_parser import PythonToolParser

class ToolParser:
    """
    Composite parser that combines multiple tool parsing strategies.
    It iterates through a list of sub-parsers and aggregates their results.
    """

    def __init__(self):
        """Initializes the ToolParser with default sub-parsers."""
        self.sub_parsers: List[BaseToolParser] = [
            JsonToolParser(),
            PythonToolParser(),
        ]

    def parse(self, text: str) -> List[Message.ToolCall]:
        """
        Parses a text response using all registered sub-parsers.
        
        Args:
            text: The text response from the LLM.
            
        Returns:
            A list of all Message.ToolCall objects found by the sub-parsers.
        """
        all_tool_calls: List[Message.ToolCall] = []
        for parser in self.sub_parsers:
            tool_calls = parser.parse(text)
            all_tool_calls.extend(tool_calls)
        return all_tool_calls
