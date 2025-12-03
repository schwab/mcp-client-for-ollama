import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from ollama._types import Message

from .base_tool_parser import BaseToolParser


class ClineToolParser(BaseToolParser):
    """
    A parser for extracting tool calls from Cline-style XML format.

    Cline syntax format:
    <server_name.tool_name>
      <argument_name>argument_value</argument_name>
      <another_arg>value</another_arg>
    </server_name.tool_name>
    """

    def parse(self, text: str) -> List[Message.ToolCall]:
        """
        Parses a text response to extract tool calls in Cline XML format.

        Cline syntax requires at least one dot in the tag name (e.g., <server.tool>),
        which distinguishes it from generic XML tags.

        Args:
            text: The text response from the LLM.

        Returns:
            A list of Message.ToolCall objects found in the text.
        """
        tool_calls: List[Message.ToolCall] = []

        # Pattern to match Cline-style tool calls: <server.tool>...</server.tool>
        # Tool name format: server_name.tool_name (must contain at least one dot)
        # This distinguishes Cline syntax from generic XML tags like <tool_request>
        pattern = re.compile(r"<([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)>(.*?)</\1>", re.DOTALL)
        matches = pattern.finditer(text)

        for match in matches:
            tool_name = match.group(1)
            content = match.group(2)

            # Parse arguments from XML content
            arguments = self._parse_arguments(content)
            if arguments is not None:
                tool_call = Message.ToolCall(
                    function=Message.ToolCall.Function(
                        name=tool_name,
                        arguments=arguments,
                    )
                )
                tool_calls.append(tool_call)

        return tool_calls

    def _parse_arguments(self, xml_content: str) -> Dict[str, Any]:
        """
        Parses arguments from XML content.

        Args:
            xml_content: The content between opening and closing tags.

        Returns:
            A dictionary of arguments, or None if parsing fails.
        """
        arguments = {}

        # Try to parse as XML structure
        try:
            # Wrap content in a root element to make it valid XML
            wrapped = f"<root>{xml_content}</root>"
            root = ET.fromstring(wrapped)

            for child in root:
                tag_name = child.tag
                text_value = child.text.strip() if child.text else ""

                # Try to parse the value as JSON, int, float, or bool
                value = self._convert_value(text_value)
                arguments[tag_name] = value

            return arguments if arguments else {}
        except ET.ParseError:
            # If XML parsing fails, try simple line-based parsing
            return self._parse_simple_arguments(xml_content)

    def _parse_simple_arguments(self, content: str) -> Dict[str, Any]:
        """
        Simple fallback parsing for arguments using regex.
        Looks for <key>value</key> patterns.

        Args:
            content: The content to parse.

        Returns:
            A dictionary of arguments.
        """
        arguments = {}

        # Pattern: <tag_name>content</tag_name>
        pattern = re.compile(r"<([a-zA-Z0-9_]+)>(.*?)</\1>", re.DOTALL)
        matches = pattern.finditer(content)

        for match in matches:
            tag_name = match.group(1)
            text_value = match.group(2).strip()

            # Try to convert the value
            value = self._convert_value(text_value)
            arguments[tag_name] = value

        return arguments

    def _convert_value(self, value_str: str) -> Any:
        """
        Converts a string value to the appropriate Python type.

        Handles:
        - JSON values (objects, arrays)
        - Boolean values (true, false)
        - Numbers (integers and floats)
        - Strings (default fallback)

        Args:
            value_str: The string representation of the value.

        Returns:
            The converted value.
        """
        value_str = value_str.strip()

        # Try JSON first (handles objects, arrays, null)
        if value_str.startswith('{') or value_str.startswith('['):
            try:
                import json
                return json.loads(value_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # Boolean values
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False
        elif value_str.lower() == 'null':
            return None

        # Try numeric values
        try:
            # Check if it's an integer
            if '.' not in value_str:
                return int(value_str)
            else:
                return float(value_str)
        except ValueError:
            pass

        # Default to string
        return value_str
