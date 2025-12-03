import re
import json
from typing import List
from ollama._types import Message

from .base_tool_parser import BaseToolParser

class XmlToolParser(BaseToolParser):
    """
    A parser for extracting tool calls from an XML-like format in a text response.
    This parser looks for content within <tool_request> ... </tool_request> blocks.
    """

    def parse(self, text: str) -> List[Message.ToolCall]:
        """
        Parses a text response to extract tool calls enclosed in <tool_request> blocks.

        Args:
            text: The text response from the LLM.

        Returns:
            A list of Message.ToolCall objects found in the text.
        """
        tool_calls: List[Message.ToolCall] = []
        pattern = re.compile(r"<tool_request>(.*?)</tool_request>", re.DOTALL)
        matches = pattern.findall(text)

        for match in matches:
            try:
                tool_call_data = json.loads(match.strip())
                if isinstance(tool_call_data, list):
                    for tool_call_item in tool_call_data:
                        tool_calls.append(self._create_tool_call_from_dict(tool_call_item))
                else:
                    tool_calls.append(self._create_tool_call_from_dict(tool_call_data))
            except json.JSONDecodeError:
                # Ignore blocks that are not valid JSON
                pass
        return tool_calls

    def _create_tool_call_from_dict(self, tool_call_dict: dict) -> Message.ToolCall:
        """
        Creates a Message.ToolCall object from a dictionary.

        Args:
            tool_call_dict: The dictionary containing the tool call information.

        Returns:
            A Message.ToolCall object.
        """
        return Message.ToolCall(
            function=Message.ToolCall.Function(
                name=tool_call_dict.get("function", {}).get("name"),
                arguments=tool_call_dict.get("function", {}).get("arguments", {}),
            )
        )
