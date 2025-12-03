from typing import List
from ollama._types import Message

from .base_tool_parser import BaseToolParser
from .json_tool_parser import JsonToolParser
from .python_tool_parser import PythonToolParser
from .xml_tool_parser import XmlToolParser
from .cline_tool_parser import ClineToolParser

class ToolParser:
    """
    Composite parser that combines multiple tool parsing strategies.
    It iterates through a list of sub-parsers and aggregates their results.
    """

    def __init__(self):
        """Initializes the ToolParser with default sub-parsers.

        The order matters: more specific parsers should come first to avoid
        conflicts. Cline syntax is specific and should be parsed before JSON
        to prevent false positives.
        """
        self.sub_parsers: List[BaseToolParser] = [
            ClineToolParser(),     # Most specific format (XML with dot notation)
            JsonToolParser(),      # Standard JSON format
            PythonToolParser(),    # Python code execution
            XmlToolParser(),       # Generic XML tool requests
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
