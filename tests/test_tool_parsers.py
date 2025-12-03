import pytest
from typing import List
from ollama._types import Message

from mcp_client_for_ollama.utils.json_tool_parser import JsonToolParser
from mcp_client_for_ollama.utils.python_tool_parser import PythonToolParser
from mcp_client_for_ollama.utils.xml_tool_parser import XmlToolParser
from mcp_client_for_ollama.utils.tool_parser import ToolParser as CompositeToolParser

# --- Fixtures ---
@pytest.fixture
def json_tool_parser():
    return JsonToolParser()

@pytest.fixture
def python_tool_parser():
    return PythonToolParser()

@pytest.fixture
def xml_tool_parser():
    return XmlToolParser()

@pytest.fixture
def composite_tool_parser():
    return CompositeToolParser()

# --- Helper for creating ToolCall objects ---
def create_tool_call(name: str, args: dict) -> Message.ToolCall:
    return Message.ToolCall(function=Message.ToolCall.Function(name=name, arguments=args))

# --- JsonToolParser Tests ---
def test_json_tool_parser_markdown_json_single(json_tool_parser):
    text = """```json
{"function": {"name": "tool1", "arguments": {"arg1": "value1"}}}
```"""
    tool_calls = json_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("tool1", {"arg1": "value1"})

def test_json_tool_parser_markdown_json_multiple(json_tool_parser):
    text = """```json
[
    {"function": {"name": "tool1", "arguments": {"arg1": "value1"}}},
    {"function": {"name": "tool2", "arguments": {"arg2": "value2"}}}
]
```"""
    tool_calls = json_tool_parser.parse(text)
    assert len(tool_calls) == 2
    assert tool_calls[0] == create_tool_call("tool1", {"arg1": "value1"})
    assert tool_calls[1] == create_tool_call("tool2", {"arg2": "value2"})

def test_json_tool_parser_embedded_json(json_tool_parser):
    text = """Some text before. {"function": {"name": "tool_embedded", "arguments": {"data": 123}}} text after."""
    tool_calls = json_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("tool_embedded", {"data": 123})

def test_json_tool_parser_full_text_json(json_tool_parser):
    text = '{"function": {"name": "tool_full", "arguments": {"key": "val"}}}'
    tool_calls = json_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("tool_full", {"key": "val"})

def test_json_tool_parser_no_tool_calls(json_tool_parser):
    text = "Just a regular sentence with no tool calls."
    tool_calls = json_tool_parser.parse(text)
    assert len(tool_calls) == 0

# --- PythonToolParser Tests ---
def test_python_tool_parser_single_block(python_tool_parser):
    text = """Some text.
```python
print("Hello")
x = 1 + 1
```
More text."""
    tool_calls = python_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.name == "builtin.execute_python_code"
    assert tool_calls[0].function.arguments["code"].strip() == 'print("Hello")\nx = 1 + 1'

def test_python_tool_parser_multiple_blocks(python_tool_parser):
    text = """```python
import os
```
Some intermediate text.
```python
print(os.getcwd())
```"""
    tool_calls = python_tool_parser.parse(text)
    assert len(tool_calls) == 2
    assert tool_calls[0].function.name == "builtin.execute_python_code"
    assert tool_calls[0].function.arguments["code"].strip() == 'import os'
    assert tool_calls[1].function.name == "builtin.execute_python_code"
    assert tool_calls[1].function.arguments["code"].strip() == 'print(os.getcwd())'

def test_python_tool_parser_no_python_blocks(python_tool_parser):
    text = """```json
{"tool": "test"}
```
Just some code in another language.
```javascript
console.log("hello");
```"""
    tool_calls = python_tool_parser.parse(text)
    assert len(tool_calls) == 0

def test_python_tool_parser_empty_block(python_tool_parser):
    text = """```python
```"""
    tool_calls = python_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.name == "builtin.execute_python_code"
    assert tool_calls[0].function.arguments["code"].strip() == ''

# --- XmlToolParser Tests ---
def test_xml_tool_parser_single_tool_call(xml_tool_parser):
    text = """Some text before.
<tool_request>{"function": {"name": "xml_tool_single", "arguments": {"data": "test"}}}</tool_request>
More text after."""
    tool_calls = xml_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("xml_tool_single", {"data": "test"})

def test_xml_tool_parser_multiple_tool_calls(xml_tool_parser):
    text = """<tool_request>{"function": {"name": "xml_tool_1", "arguments": {"id": 1}}}</tool_request>
<tool_request>{"function": {"name": "xml_tool_2", "arguments": {"id": 2}}}</tool_request>"""
    tool_calls = xml_tool_parser.parse(text)
    assert len(tool_calls) == 2
    assert tool_calls[0] == create_tool_call("xml_tool_1", {"id": 1})
    assert tool_calls[1] == create_tool_call("xml_tool_2", {"id": 2})

def test_xml_tool_parser_invalid_json(xml_tool_parser):
    text = """<tool_request>{invalid json}</tool_request>"""
    tool_calls = xml_tool_parser.parse(text)
    assert len(tool_calls) == 0

def test_xml_tool_parser_no_tool_calls(xml_tool_parser):
    text = """Just some regular text without any tool requests."""
    tool_calls = xml_tool_parser.parse(text)
    assert len(tool_calls) == 0

def test_xml_tool_parser_list_of_tool_calls(xml_tool_parser):
    text = """<tool_request>[{"function": {"name": "xml_tool_list_1", "arguments": {}}}, {"function": {"name": "xml_tool_list_2", "arguments": {}}}]</tool_request>"""
    tool_calls = xml_tool_parser.parse(text)
    assert len(tool_calls) == 2
    assert tool_calls[0] == create_tool_call("xml_tool_list_1", {})
    assert tool_calls[1] == create_tool_call("xml_tool_list_2", {})

# --- CompositeToolParser Tests ---
def test_composite_tool_parser_json_only(composite_tool_parser):
    text = """```json
{"function": {"name": "json_tool", "arguments": {}}}
```"""
    tool_calls = composite_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("json_tool", {})

def test_composite_tool_parser_python_only(composite_tool_parser):
    text = """```python
print('hello')
```"""
    tool_calls = composite_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.name == "builtin.execute_python_code"
    assert tool_calls[0].function.arguments["code"].strip() == "print('hello')"

def test_composite_tool_parser_xml_only(composite_tool_parser):
    text = """<tool_request>{"function": {"name": "xml_tool", "arguments": {"param": "value"}}}</tool_request>"""
    tool_calls = composite_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("xml_tool", {"param": "value"})

def test_composite_tool_parser_all_types_mixed(composite_tool_parser):
    text = """```json
{"function": {"name": "json_tool", "arguments": {"id": 1}}}
```
Some text.
<tool_request>{"function": {"name": "xml_tool", "arguments": {"param": "value"}}}</tool_request>
```python
result = 1 + 1
```
More text.
```json
{"function": {"name": "another_json_tool", "arguments": {"value": "abc"}}}
```"""
    tool_calls = composite_tool_parser.parse(text)
    assert len(tool_calls) == 4
    # Order depends on the order of sub-parsers in CompositeToolParser
    assert tool_calls[0] == create_tool_call("json_tool", {"id": 1})
    assert tool_calls[1] == create_tool_call("another_json_tool", {"value": "abc"})
    assert tool_calls[2].function.name == "builtin.execute_python_code"
    assert tool_calls[2].function.arguments["code"].strip() == "result = 1 + 1"
    assert tool_calls[3] == create_tool_call("xml_tool", {"param": "value"})

def test_composite_tool_parser_no_tool_calls(composite_tool_parser):
    text = "No tool calls here."
    tool_calls = composite_tool_parser.parse(text)
    assert len(tool_calls) == 0

def test_composite_tool_parser_mixed_invalid_and_valid(composite_tool_parser):
    text = """```json
{invalid json
```
<tool_request>{invalid xml json}</tool_request>
```python
print('valid python')
```
```json
{"function": {"name": "valid_json", "arguments": {}}}
```
<tool_request>{"function": {"name": "valid_xml", "arguments": {}}}</tool_request>"""
    tool_calls = composite_tool_parser.parse(text)
    assert len(tool_calls) == 3
    # JsonToolParser will ignore invalid JSON, PythonToolParser will find its block
    assert tool_calls[0] == create_tool_call("valid_json", {})
    assert tool_calls[1].function.name == "builtin.execute_python_code"
    assert tool_calls[1].function.arguments["code"].strip() == "print('valid python')"
    assert tool_calls[2] == create_tool_call("valid_xml", {})
