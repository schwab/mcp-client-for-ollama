
## This file implements a parser for extracting tool calls 
# from LLM text responses.

import json
import re
from typing import List, Dict, Any, Optional
from ollama._types import Message

class ToolParser:
    """Parses tool calls from a model's text response."""

    def parse(self, text: str) -> List[Message.ToolCall]:
        """
        Parses a text response to extract tool calls.
        
        It uses multiple strategies to find tool calls:
        1. Find all markdown JSON blocks.
        2. If none, fall back to parsing the entire text as a single JSON object or array.
        
        Returns:
            A list of Message.ToolCall objects found in the text.
        """
        tool_calls: List[Message.ToolCall] = []
        potential_tool_jsons = self._parse_markdown_blocks(text)

        if not potential_tool_jsons:
            potential_tool_jsons = self._parse_full_text(text)

        if potential_tool_jsons:
            for tc_json in potential_tool_jsons:
                tool_call = self._convert_json_to_tool_call(tc_json)
                if tool_call:
                    tool_calls.append(tool_call)
        
        return tool_calls

    def _parse_markdown_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Strategy 1: Find and parse all markdown JSON blocks."""
        potential_tool_calls = []
        json_blocks = re.findall(r"""```json\n(.*?)\n```""", text, re.DOTALL)
        if json_blocks:
            for block in json_blocks:
                try:
                    parsed_json = json.loads(block)
                    if isinstance(parsed_json, list):
                        potential_tool_calls.extend(parsed_json)
                    else:
                        potential_tool_calls.append(parsed_json)
                except json.JSONDecodeError:
                    continue
        return potential_tool_calls
    
    def _parse_full_text(self, text: str) -> List[Dict[str, Any]]:
        """Strategy 2: Parse the entire text as a single JSON object or array."""
        potential_tool_calls = []
        try:
            text_to_parse = text.strip()
            if text_to_parse.startswith("```json"):
                text_to_parse = text_to_parse[7:]
                if text_to_parse.endswith("```"):
                    text_to_parse = text_to_parse[:-3]
                text_to_parse = text_to_parse.strip()

            parsed_json = json.loads(text_to_parse)
            if isinstance(parsed_json, list):
                potential_tool_calls = parsed_json
            elif isinstance(parsed_json, dict):
                if 'tool_calls' in parsed_json and isinstance(parsed_json['tool_calls'], list):
                    potential_tool_calls = parsed_json['tool_calls']
                else:
                    potential_tool_calls.append(parsed_json)
        except json.JSONDecodeError:
            pass
        return potential_tool_calls

    def _convert_json_to_tool_call(self, tc_json: Dict[str, Any]) -> Optional[Message.ToolCall]:
        """Converts a JSON dictionary to a Message.ToolCall object."""
        # Case 1: Standard format {'function': {'name': ..., 'arguments': ...}}
        if (isinstance(tc_json, dict) and 'function' in tc_json and 
            isinstance(tc_json['function'], dict) and 'name' in tc_json['function'] and 
            'arguments' in tc_json['function']):
            
            return Message.ToolCall(
                function=Message.ToolCall.Function(
                    name=tc_json['function']['name'],
                    arguments=tc_json['function']['arguments']
                )
            )
        # Case 2: Flattened format {'name': ..., 'arguments': ...}
        elif (isinstance(tc_json, dict) and 'name' in tc_json and 'arguments' in tc_json):
            return Message.ToolCall(
                function=Message.ToolCall.Function(
                    name=tc_json['name'],
                    arguments=tc_json['arguments']
                )
            )
        return None

