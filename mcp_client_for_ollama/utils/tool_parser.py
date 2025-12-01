
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
        2. If none, find JSON objects embedded directly in the text.
        3. If none, fall back to parsing the entire text as a single JSON object or array.
        
        Returns:
            A list of Message.ToolCall objects found in the text.
        """
        tool_calls: List[Message.ToolCall] = []
        potential_tool_jsons = self._parse_markdown_blocks(text)

        if not potential_tool_jsons:
            potential_tool_jsons = self._parse_embedded_json(text)

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
        json_blocks = re.findall(r"""```\s*json
(.*?)```""", text, re.DOTALL)
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
    
    def _parse_embedded_json(self, text: str) -> List[Dict[str, Any]]:
        """Strategy 2: Find and parse JSON objects embedded in the text."""
        potential_tool_calls = []
        
        # Clean up special tokens that might interfere with parsing
        cleaned_text = re.sub(r'<\|im_start\|>', '', text)
        cleaned_text = re.sub(r'<\|im_end\|>', '', cleaned_text)

        # Find all possible start indices of a JSON object
        start_indices = [m.start() for m in re.finditer(r'\{', cleaned_text)]
        
        for start_index in start_indices:
            balance = 1
            for i in range(start_index + 1, len(cleaned_text)):
                if cleaned_text[i] == '{':
                    balance += 1
                elif cleaned_text[i] == '}':
                    balance -= 1
                
                if balance == 0:
                    potential_json_str = cleaned_text[start_index : i + 1]
                    try:
                        parsed = json.loads(potential_json_str)
                        if isinstance(parsed, dict):
                            # Basic validation to see if it looks like a tool call
                            has_name = 'name' in parsed or 'function_name' in parsed or 'function' in parsed
                            has_args = 'arguments' in parsed or 'function_args' in parsed
                            if has_name and has_args:
                                potential_tool_calls.append(parsed)
                    except json.JSONDecodeError:
                        pass  # Not a valid JSON object, ignore
                    # Break from inner loop to continue searching from the next start index
                    break
        
        return potential_tool_calls

    def _parse_full_text(self, text: str) -> List[Dict[str, Any]]:
        """Strategy 3: Parse the entire text as a single JSON object or array."""
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
        if not isinstance(tc_json, dict):
            return None

        name = None
        args = None

        # Check for standard format {'function': {...}}
        if 'function' in tc_json and isinstance(tc_json['function'], dict):
            func_dict = tc_json['function']
            name = func_dict.get('name') or func_dict.get('function_name')
            # Use a more careful check for arguments to handle cases where it's present but None
            if 'arguments' in func_dict:
                args = func_dict['arguments']
            elif 'function_args' in func_dict:
                args = func_dict['function_args']
        
        # If not found, check for flattened format
        if name is None:
            name = tc_json.get('name') or tc_json.get('function_name')
        if args is None:
            if 'arguments' in tc_json:
                args = tc_json['arguments']
            elif 'function_args' in tc_json:
                args = tc_json['function_args']

        # We must have a name and args (even if args is an empty dict)
        if name is not None and args is not None:
            return Message.ToolCall(
                function=Message.ToolCall.Function(name=name, arguments=args)
            )
            
        return None

