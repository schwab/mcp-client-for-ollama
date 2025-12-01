
""" FZF-style command completer for interactive mode using prompt_toolkit """
import json
import re
import os
from prompt_toolkit.completion import Completion, FuzzyCompleter, WordCompleter, Completer
from .constants import INTERACTIVE_COMMANDS

class FZFStyleCompleter(Completer):
    """Simple FZF-style completer with fuzzy matching."""

    def __init__(self, sessions=None, console=None):
        self.sessions = sessions if sessions is not None else {}
        self.console = console
        # Just wrap a WordCompleter with FuzzyCompleter
        self.completer = FuzzyCompleter(WordCompleter(
            list(INTERACTIVE_COMMANDS.keys()),
            ignore_case=True
        ))

    def get_completions(self, document, complete_event):
        """
        This is the synchronous version of get_completions.
        Because our completer is async, we don't implement this.
        Instead, we have get_completions_async.
        This is required to satisfy the abstract base class.
        """
        return
        yield

    async def get_completions_async(self, document, complete_event):
        text_before_cursor = document.text_before_cursor
        
        if text_before_cursor.startswith('@'):
            # Handle @-commands
            async for completion in self._get_at_command_completions(document, complete_event):
                yield completion
        else:
            # Only complete if cursor is in the first word (commands only)
            if " " in text_before_cursor:
                return
            # Get fuzzy completions for regular commands
            for i, completion in enumerate(self.completer.get_completions(document, complete_event)):
                cmd = completion.text
                description = INTERACTIVE_COMMANDS.get(cmd, "")

                # Add arrow to first match
                display = f"▶ {cmd}" if i == 0 else f"  {cmd}"

                yield Completion(
                    cmd,
                    start_position=completion.start_position,
                    display=display,
                    display_meta=description
                )

    async def _get_at_command_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor
        at_command_text = text_before_cursor[1:] # Text after '@'
        
        # For now, assume @-command is for filesystem paths
        if 'filesystem' in self.sessions:
            try:
                # Determine the directory to list and the search term
                path_parts = at_command_text.split('/')
                if len(path_parts) > 1 and at_command_text.endswith('/'):
                    # If ends with '/', list that directory
                    dir_to_list = '/' + '/'.join(path_parts[:-1])
                    search_term = ''
                elif len(path_parts) > 1:
                    # List parent directory and filter by last part
                    dir_to_list = '/' + '/'.join(path_parts[:-1])
                    search_term = path_parts[-1]
                else:
                    # List root and filter by current text
                    dir_to_list = '/'
                    search_term = at_command_text

                # Ensure dir_to_list is absolute and normalized
                dir_to_list = os.path.normpath(dir_to_list)
                if not dir_to_list.startswith('/'):
                    dir_to_list = '/' + dir_to_list
                
                # Call list_directory tool
                list_result = await self.sessions['filesystem']['session'].call_tool(
                    'list_directory',
                    {'path': dir_to_list}
                )
                
                session_items = []
                if list_result.content and isinstance(list_result.content[0].text, str):
                    content_text = list_result.content[0].text.strip()
                    try:
                        list_data = json.loads(content_text)
                        if isinstance(list_data, dict) and 'items' in list_data:
                            session_items = [
                                item for item in list_data['items']
                                if item.get('type') in ['file', 'directory']
                            ]
                        elif isinstance(list_data, list):
                            session_items = [{'name': s, 'type': 'file'} for s in list_data if isinstance(s, str)]
                    except json.JSONDecodeError:
                        filenames = [line.strip() for line in content_text.split('\n') if line.strip()]
                        session_items = [{'name': f, 'type': 'file'} for f in filenames]

                # Filter and yield completions
                for item in session_items:
                    clean_name = re.sub(r'\[.*?\]\s*', '', item['name']).strip()
                    
                    # Construct the full path for completion
                    # Handle root directory case to avoid double slashes
                    if dir_to_list == '/':
                        full_path = '/' + clean_name
                    else:
                        full_path = os.path.join(dir_to_list, clean_name)
                    
                    # Fuzzy match against the search term
                    if not search_term or search_term.lower() in clean_name.lower():
                        display_meta = f"[{item.get('type', 'file').upper()}]"
                        yield Completion(
                            full_path,
                            start_position=-len(text_before_cursor), # Replace the whole @-command
                            display=full_path,
                            display_meta=display_meta
                        )
            except Exception as e:
                if self.console:
                    self.console.print(f"[red]Error fetching filesystem completions: {e}[/red]")
        else:
            if self.console:
                self.console.print("[yellow]Filesystem tool not available for @-commands.[/yellow]")

