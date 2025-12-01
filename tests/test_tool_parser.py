def test_parse_markdown_with_space_before_json_tag(self):
        """Test parsing markdown where there is a space before the json language tag."""
        test_text = '''Let's try the function call again with the correct formatting.

``` json
{"name": "filesystem.list_directory", "arguments": {"path": "/projects/journal/book"}}
```

If this doesn't work, there might be an issue with accessing the directory. We can also check which directories are allowed to ensure that `/projects/journal/book` is accessible.

Let's first verify the list of allowed directories:

``` json
{"name": "filesystem.list_allowed_directories", "arguments": {}}
```'''
        tool_calls = self.parser.parse(test_text)
        self.assertEqual(len(tool_calls), 2)
        self.assertEqual(tool_calls[0].function.name, "filesystem.list_directory")
        self.assertEqual(tool_calls[1].function.name, "filesystem.list_allowed_directories")