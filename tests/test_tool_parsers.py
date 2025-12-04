import pytest
from typing import List
from ollama._types import Message

from mcp_client_for_ollama.utils.json_tool_parser import JsonToolParser
from mcp_client_for_ollama.utils.python_tool_parser import PythonToolParser
from mcp_client_for_ollama.utils.xml_tool_parser import XmlToolParser
from mcp_client_for_ollama.utils.cline_tool_parser import ClineToolParser
from mcp_client_for_ollama.utils.simple_xml_tool_parser import SimpleXmlToolParser
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
def cline_tool_parser():
    return ClineToolParser()

@pytest.fixture
def simple_xml_tool_parser():
    return SimpleXmlToolParser()

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

def test_json_tool_parser_tool_request_format(json_tool_parser):
    """Test parsing tool_request format with thoughts and parameters."""
    text = """```json
{
  "thoughts": "To load the Writing Style Guide and apply it as my instructions, I need to follow these steps.",
  "tool_request": {
    "name": "builtin.list_files",
    "parameters": {
      "path": "/root"
    }
  }
}
```"""
    tool_calls = json_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("builtin.list_files", {"path": "/root"})

def test_json_tool_parser_tool_request_embedded(json_tool_parser):
    """Test parsing embedded tool_request format in text."""
    text = """I need to read a file. Here's my request:
{
  "thoughts": "Reading the configuration file",
  "tool_request": {
    "name": "builtin.read_file",
    "parameters": {
      "path": "config.json"
    }
  }
}
Let me know what you find."""
    tool_calls = json_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("builtin.read_file", {"path": "config.json"})

def test_json_tool_parser_tool_request_with_arguments(json_tool_parser):
    """Test tool_request format also works with 'arguments' key."""
    text = """```json
{
  "tool_request": {
    "name": "builtin.write_file",
    "arguments": {
      "path": "output.txt",
      "content": "Hello"
    }
  }
}
```"""
    tool_calls = json_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("builtin.write_file", {"path": "output.txt", "content": "Hello"})

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


# --- ClineToolParser Tests ---
def test_cline_tool_parser_single_tool_call_simple(cline_tool_parser):
    text = """<filesystem.read_file>
  <path>/root/CLAUDE.md</path>
</filesystem.read_file>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("filesystem.read_file", {"path": "/root/CLAUDE.md"})


def test_cline_tool_parser_single_tool_call_multiple_args(cline_tool_parser):
    text = """<web.search>
  <query>Claude AI</query>
  <max_results>10</max_results>
</web.search>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.name == "web.search"
    assert tool_calls[0].function.arguments["query"] == "Claude AI"
    assert tool_calls[0].function.arguments["max_results"] == 10


def test_cline_tool_parser_multiple_tool_calls(cline_tool_parser):
    text = """<filesystem.read_file>
  <path>/etc/config</path>
</filesystem.read_file>
Some text in between.
<filesystem.write_file>
  <path>/tmp/output.txt</path>
  <content>Hello World</content>
</filesystem.write_file>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 2
    assert tool_calls[0] == create_tool_call("filesystem.read_file", {"path": "/etc/config"})
    assert tool_calls[1] == create_tool_call("filesystem.write_file", {
        "path": "/tmp/output.txt",
        "content": "Hello World"
    })


def test_cline_tool_parser_with_numeric_args(cline_tool_parser):
    text = """<math.calculate>
  <operation>add</operation>
  <a>5</a>
  <b>3</b>
  <precision>2.5</precision>
  <enabled>true</enabled>
</math.calculate>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.name == "math.calculate"
    assert tool_calls[0].function.arguments["a"] == 5
    assert tool_calls[0].function.arguments["b"] == 3
    assert tool_calls[0].function.arguments["precision"] == 2.5
    assert tool_calls[0].function.arguments["enabled"] is True


def test_cline_tool_parser_with_boolean_args(cline_tool_parser):
    text = """<config.set>
  <key>debug_mode</key>
  <value>true</value>
  <force>false</force>
  <nullable_value>null</nullable_value>
</config.set>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 1
    args = tool_calls[0].function.arguments
    assert args["value"] is True
    assert args["force"] is False
    assert args["nullable_value"] is None


def test_cline_tool_parser_with_json_arg(cline_tool_parser):
    text = """<api.call>
  <endpoint>/users</endpoint>
  <payload>{"name": "John", "age": 30}</payload>
</api.call>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.arguments["endpoint"] == "/users"
    assert tool_calls[0].function.arguments["payload"] == {"name": "John", "age": 30}


def test_cline_tool_parser_with_json_array_arg(cline_tool_parser):
    text = """<data.process>
  <items>[1, 2, 3, 4, 5]</items>
</data.process>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.arguments["items"] == [1, 2, 3, 4, 5]


def test_cline_tool_parser_no_tool_calls(cline_tool_parser):
    text = "This is just plain text with no tool calls."
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 0


def test_cline_tool_parser_underscore_in_name(cline_tool_parser):
    text = """<my_server.my_tool>
  <param>value</param>
</my_server.my_tool>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.name == "my_server.my_tool"


def test_cline_tool_parser_with_whitespace_variations(cline_tool_parser):
    text = """<tool.action>
  <arg1>value1</arg1>
<arg2>value2</arg2>
  <arg3>  value3  </arg3>
</tool.action>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.arguments["arg1"] == "value1"
    assert tool_calls[0].function.arguments["arg2"] == "value2"
    assert tool_calls[0].function.arguments["arg3"] == "value3"


def test_cline_tool_parser_empty_arguments(cline_tool_parser):
    text = """<tool.action>
</tool.action>"""
    tool_calls = cline_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.arguments == {}


def test_composite_tool_parser_with_cline_syntax(composite_tool_parser):
    text = """I'll call the filesystem tool using Cline syntax:
<filesystem.read_file>
  <path>/root/README.md</path>
</filesystem.read_file>
And also JSON format:
```json
{"function": {"name": "web.search", "arguments": {"query": "test"}}}
```"""
    tool_calls = composite_tool_parser.parse(text)
    assert len(tool_calls) == 2
    assert tool_calls[0] == create_tool_call("filesystem.read_file", {"path": "/root/README.md"})
    assert tool_calls[1] == create_tool_call("web.search", {"query": "test"})


# --- SimpleXmlToolParser Tests ---
def test_simple_xml_tool_parser_tool_name_only(simple_xml_tool_parser):
    """Test tool call with only a tool name, no arguments."""
    text = """<tool_name>builtin.list_files</tool_name>"""
    tool_calls = simple_xml_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("builtin.list_files", {})


def test_simple_xml_tool_parser_with_json_arguments(simple_xml_tool_parser):
    """Test tool call with JSON arguments."""
    text = """<tool_name>builtin.read_file</tool_name>
<arguments>{"path": "/root/config.json", "encoding": "utf-8"}</arguments>"""
    tool_calls = simple_xml_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("builtin.read_file", {"path": "/root/config.json", "encoding": "utf-8"})


def test_simple_xml_tool_parser_with_xml_arguments(simple_xml_tool_parser):
    """Test tool call with nested XML arguments."""
    text = """<tool_name>filesystem.write_file</tool_name>
<arguments>
  <path>/tmp/output.txt</path>
  <content>Hello World</content>
</arguments>"""
    tool_calls = simple_xml_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("filesystem.write_file", {
        "path": "/tmp/output.txt",
        "content": "Hello World"
    })


def test_simple_xml_tool_parser_multiple_calls(simple_xml_tool_parser):
    """Test multiple tool calls in the same text."""
    text = """First call:
<tool_name>builtin.list_files</tool_name>
<arguments>{"path": "/root"}</arguments>

Then another call:
<tool_name>builtin.read_file</tool_name>
<arguments>
  <path>/root/README.md</path>
</arguments>"""
    tool_calls = simple_xml_tool_parser.parse(text)
    assert len(tool_calls) == 2
    assert tool_calls[0] == create_tool_call("builtin.list_files", {"path": "/root"})
    assert tool_calls[1] == create_tool_call("builtin.read_file", {"path": "/root/README.md"})


def test_simple_xml_tool_parser_with_numeric_xml_args(simple_xml_tool_parser):
    """Test XML arguments with numeric values."""
    text = """<tool_name>math.calculate</tool_name>
<arguments>
  <a>5</a>
  <b>10</b>
  <precision>2.5</precision>
</arguments>"""
    tool_calls = simple_xml_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0].function.arguments["a"] == 5
    assert tool_calls[0].function.arguments["b"] == 10
    assert tool_calls[0].function.arguments["precision"] == 2.5


def test_simple_xml_tool_parser_with_boolean_xml_args(simple_xml_tool_parser):
    """Test XML arguments with boolean values."""
    text = """<tool_name>config.set</tool_name>
<arguments>
  <enabled>true</enabled>
  <debug>false</debug>
  <optional>null</optional>
</arguments>"""
    tool_calls = simple_xml_tool_parser.parse(text)
    assert len(tool_calls) == 1
    args = tool_calls[0].function.arguments
    assert args["enabled"] is True
    assert args["debug"] is False
    assert args["optional"] is None


def test_simple_xml_tool_parser_no_tool_calls(simple_xml_tool_parser):
    """Test text with no tool calls."""
    text = "This is just regular text without any tool calls."
    tool_calls = simple_xml_tool_parser.parse(text)
    assert len(tool_calls) == 0


def test_simple_xml_tool_parser_with_surrounding_text(simple_xml_tool_parser):
    """Test tool call embedded in regular text."""
    text = """I need to list files in the directory.

<tool_name>builtin.list_files</tool_name>
<arguments>{"path": "/"}</arguments>

Let me know what files you find."""
    tool_calls = simple_xml_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("builtin.list_files", {"path": "/"})


def test_simple_xml_tool_parser_empty_arguments_tag(simple_xml_tool_parser):
    """Test tool call with empty arguments tag."""
    text = """<tool_name>builtin.get_system_prompt</tool_name>
<arguments></arguments>"""
    tool_calls = simple_xml_tool_parser.parse(text)
    assert len(tool_calls) == 1
    assert tool_calls[0] == create_tool_call("builtin.get_system_prompt", {})


def test_composite_tool_parser_with_simple_xml_syntax(composite_tool_parser):
    """Test that composite parser can handle simple XML format."""
    text = """I'll use the simple XML format:
<tool_name>builtin.list_files</tool_name>
<arguments>{"path": "/root"}</arguments>

And also JSON:
```json
{"function": {"name": "web.search", "arguments": {"query": "test"}}}
```"""
    tool_calls = composite_tool_parser.parse(text)
    assert len(tool_calls) == 2
    assert tool_calls[0] == create_tool_call("web.search", {"query": "test"})
    assert tool_calls[1] == create_tool_call("builtin.list_files", {"path": "/root"})
