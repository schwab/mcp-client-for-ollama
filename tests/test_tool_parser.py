import unittest
from mcp_client_for_ollama.utils.tool_parser import ToolParser

class TestToolParser(unittest.TestCase):

    def setUp(self):
        self.parser = ToolParser()

    def test_parse_multiple_markdown_blocks(self):
        """Test parsing of multiple tool calls each in their own markdown JSON block."""
        test_text = '''```json
{
  "name": "builtin.get_system_prompt",
  "arguments": {}
}
```

```json
{
  "name": "filesystem.read_file",
  "arguments": {
    "path": "test.md"
  }
}
```'''
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 2)
        self.assertEqual(tool_calls[0].function.name, "builtin.get_system_prompt")
        self.assertEqual(tool_calls[1].function.name, "filesystem.read_file")
        self.assertEqual(tool_calls[1].function.arguments, {"path": "test.md"})

    def test_parse_single_json_no_markdown(self):
        """Test parsing a single tool call without markdown fences."""
        test_text = '{"name": "test.tool", "arguments": {"arg1": "val1"}}'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "test.tool")
        self.assertEqual(tool_calls[0].function.arguments, {"arg1": "val1"})

    def test_parse_json_array_no_markdown(self):
        """Test parsing a JSON array of tool calls without markdown fences."""
        test_text = '[{"name": "test.tool1", "arguments": {}}, {"name": "test.tool2", "arguments": {}}]'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 2)
        self.assertEqual(tool_calls[0].function.name, "test.tool1")
        self.assertEqual(tool_calls[1].function.name, "test.tool2")

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
        self.assertEqual(tool_calls[0].function.name, "test.tool1")
        self.assertEqual(tool_calls[1].function.name, "test.tool2")

    def test_parse_openai_format(self):
        """Test parsing the standard {'function': {'name': ...}} format."""
        test_text = '{"function": {"name": "test.tool", "arguments": {"arg1": "val1"}}}'
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "test.tool")
        self.assertEqual(tool_calls[0].function.arguments, {"arg1": "val1"})

if __name__ == '__main__':
    unittest.main()
