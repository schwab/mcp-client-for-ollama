
## This file implements a parser for extracting tool calls 
# from LLM text responses.

import abc
from typing import List
from ollama._types import Message

class BaseToolParser(abc.ABC):
    """Abstract base class for parsing tool calls from LLM text responses."""

    @abc.abstractmethod
    def parse(self, text: str) -> List[Message.ToolCall]:
        """
        Parses a text response to extract tool calls.
        
        Args:
            text: The text response from the LLM.
            
        Returns:
            A list of Message.ToolCall objects found in the text.
        """
        pass

