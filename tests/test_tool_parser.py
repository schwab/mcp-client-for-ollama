import unittest
from mcp_client_for_ollama.utils.tool_parser import ToolParser

class TestToolParser(unittest.TestCase):

    def setUp(self):
        self.parser = ToolParser()

    def test_parse_multiple_markdown_blocks(self):
        """Test parsing of multiple tool calls each in their own markdown JSON block."""
        test_text = '''```json
{
  "name": "tool1",
  "arguments": {}
}
```
```json
{
  "name": "tool2",
  "arguments": {"arg": "val"}
}
```'''
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 2)
        self.assertEqual(tool_calls[0].function.name, "tool1")
        self.assertEqual(tool_calls[1].function.name, "tool2")

    def test_parse_single_json_no_markdown(self):
        """Test parsing a single tool call without markdown fences."""
        test_text = '{"name": "test.tool", "arguments": {"arg1": "val1"}}'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "test.tool")

    def test_parse_json_array_no_markdown(self):
        """Test parsing a JSON array of tool calls without markdown fences."""
        test_text = '[{"name": "test.tool1", "arguments": {}}, {"name": "test.tool2", "arguments": {}}]'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 2)

    def test_parse_no_json(self):
        """Test that it returns an empty list for text with no tool calls."""
        test_text = "This is just a regular sentence."
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 0)

    def test_parse_mixed_valid_invalid_blocks(self):
        """Test that it correctly parses valid blocks and ignores invalid ones."""
        test_text = '''```json
{"name": "test.tool1", "arguments": {}}
```
This is some text in between.
```json
{not a valid json}
```
```json
{"name": "test.tool2", "arguments": {}}
```'''
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 2)

    def test_parse_openai_format(self):
        """Test parsing the standard {'function': {'name': ...}} format."""
        test_text = '{"function": {"name": "test.tool", "arguments": {"arg1": "val1"}}}'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "test.tool")

    def test_parse_flattened_aliases(self):
        """Test parsing flattened format with aliased keys."""
        test_text = '{"function_name": "test.tool", "function_args": {"arg1": "val1"}}'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "test.tool")

    def test_parse_nested_aliases(self):
        """Test parsing nested format with aliased keys."""
        test_text = '{"function": {"function_name": "test.tool", "function_args": {"arg1": "val1"}}}'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "test.tool")

    def test_parse_markdown_with_space_before_json_tag(self):
        """Test parsing markdown where there is a space before the json language tag."""
        test_text = '''``` json
{"name": "filesystem.list_directory", "arguments": {}}
```'''
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "filesystem.list_directory")

    def test_parse_embedded_json(self):
        """Test parsing JSON embedded directly in text without markdown fences."""
        test_text = 'Some text here: {"name": "filesystem.read_file", "arguments": {"path":"file.md"}}'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "filesystem.read_file")

    def test_parse_embedded_json_with_special_tokens(self):
        """Test parsing embedded JSON with special model tokens that should be ignored."""
        test_text = '<|im_start|>{"name": "filesystem.read_file", "arguments": {"path":"file.md"}}<|im_end|>'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "filesystem.read_file")

if __name__ == '__main__':
    unittest.main()