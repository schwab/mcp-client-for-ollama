import re
from typing import List
from ollama._types import Message

from .base_tool_parser import BaseToolParser

class PythonToolParser(BaseToolParser):
    """Parses Python code blocks from a model's text response and converts them into tool calls."""

    def parse(self, text: str) -> List[Message.ToolCall]:
        """
        Parses a text response to extract Python code blocks.
        
        Looks for code blocks fenced with ```python and converts them into
        Message.ToolCall objects for the 'builtin.execute_python_code' tool.
        
        Args:
            text: The text response from the LLM.
            
        Returns:
            A list of Message.ToolCall objects for Python code execution.
        """
        tool_calls: List[Message.ToolCall] = []
        
        # Regex to find Python code blocks fenced with ```python
        python_blocks = re.findall(r"""```\s*python\n(.*?)```""", text, re.DOTALL)
        
        for code_block in python_blocks:
            # Create a ToolCall object for each Python code block
            tool_call = Message.ToolCall(
                function=Message.ToolCall.Function(
                    name="builtin.execute_python_code",
                    arguments={"code": code_block.strip()}
                )
            )
            tool_calls.append(tool_call)
            
        return tool_calls

