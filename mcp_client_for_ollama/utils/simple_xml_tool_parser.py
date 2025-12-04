import re
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from ollama._types import Message

from .base_tool_parser import BaseToolParser


class SimpleXmlToolParser(BaseToolParser):
    """
    A parser for extracting tool calls from a simple XML format.

    This parser looks for pairs of <tool_name> and <arguments> tags:

    <tool_name>builtin.list_files</tool_name>
    <arguments>{"path": "/some/path"}</arguments>

    or with nested XML arguments:

    <tool_name>builtin.list_files</tool_name>
    <arguments>
      <path>/some/path</path>
    </arguments>
    """

    def parse(self, text: str) -> List[Message.ToolCall]:
        """
        Parses a text response to extract tool calls in simple XML format.

        Args:
            text: The text response from the LLM.

        Returns:
            A list of Message.ToolCall objects found in the text.
        """
        tool_calls: List[Message.ToolCall] = []

        # Pattern to match <tool_name>...</tool_name> followed optionally by <arguments>...</arguments>
        # We need to be careful to match these in pairs
        tool_name_pattern = re.compile(r"<tool_name>(.*?)</tool_name>", re.DOTALL)

        # Find all tool_name occurrences
        tool_name_matches = list(tool_name_pattern.finditer(text))

        for tool_name_match in tool_name_matches:
            tool_name = tool_name_match.group(1).strip()

            # Look for an <arguments> tag following this tool_name
            # Search from the end of the tool_name tag
            start_pos = tool_name_match.end()

            # Find the next <arguments> tag (if any) within a reasonable distance
            # We'll limit the search to avoid matching arguments from a different tool call
            search_window = text[start_pos:start_pos + 5000]  # Look ahead up to 5000 chars

            arguments_pattern = re.compile(r"<arguments>(.*?)</arguments>", re.DOTALL)
            arguments_match = arguments_pattern.search(search_window)

            if arguments_match:
                arguments_content = arguments_match.group(1).strip()
                arguments = self._parse_arguments(arguments_content)
            else:
                # No arguments provided
                arguments = {}

            # Create the tool call
            tool_call = Message.ToolCall(
                function=Message.ToolCall.Function(
                    name=tool_name,
                    arguments=arguments,
                )
            )
            tool_calls.append(tool_call)

        return tool_calls

    def _parse_arguments(self, arguments_content: str) -> Dict[str, Any]:
        """
        Parses the content of an <arguments> tag.

        Supports both JSON and nested XML formats.

        Args:
            arguments_content: The content inside the <arguments> tag.

        Returns:
            A dictionary of arguments.
        """
        if not arguments_content:
            return {}

        # Try parsing as JSON first
        try:
            parsed = json.loads(arguments_content)
            if isinstance(parsed, dict):
                return parsed
            # If it's not a dict, wrap it
            return {"value": parsed}
        except json.JSONDecodeError:
            pass

        # Try parsing as nested XML
        try:
            # Wrap content in a root element to make it valid XML
            wrapped = f"<root>{arguments_content}</root>"
            root = ET.fromstring(wrapped)

            arguments = {}
            for child in root:
                tag_name = child.tag

                # Check if this element has children (nested structure)
                if len(child) > 0:
                    # Recursively parse nested elements
                    arguments[tag_name] = self._parse_xml_element(child)
                else:
                    # Simple text value
                    text_value = child.text.strip() if child.text else ""
                    arguments[tag_name] = self._convert_value(text_value)

            return arguments
        except ET.ParseError:
            pass

        # If all else fails, return the raw content as a single "value" argument
        return {"value": arguments_content}

    def _parse_xml_element(self, element: ET.Element) -> Any:
        """
        Recursively parses an XML element into a Python data structure.

        Args:
            element: The XML element to parse.

        Returns:
            A dictionary, list, or primitive value.
        """
        # If element has no children, return its text value
        if len(element) == 0:
            text_value = element.text.strip() if element.text else ""
            return self._convert_value(text_value)

        # If element has children, parse them into a dict
        result = {}
        for child in element:
            tag_name = child.tag

            if len(child) > 0:
                # Nested structure
                result[tag_name] = self._parse_xml_element(child)
            else:
                # Simple text value
                text_value = child.text.strip() if child.text else ""
                result[tag_name] = self._convert_value(text_value)

        return result

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

        if not value_str:
            return ""

        # Try JSON first (handles objects, arrays, null)
        if value_str.startswith('{') or value_str.startswith('['):
            try:
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
