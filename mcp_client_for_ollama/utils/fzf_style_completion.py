
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
        self.allowed_dirs = None # Initialize allowed directories to None
        # Just wrap a WordCompleter with FuzzyCompleter
        self.completer = FuzzyCompleter(WordCompleter(
            list(INTERACTIVE_COMMANDS.keys()),
            ignore_case=True
        ))

    def update_sessions(self, new_sessions):
        """Update the sessions dictionary for the completer."""
        self.sessions = new_sessions
        self.allowed_dirs = None # Reset allowed_dirs when sessions are updated

    async def _fetch_allowed_directories(self):
        """Fetch allowed directories from the filesystem tool."""
        if 'filesystem' not in self.sessions:
            self.allowed_dirs = []
            return

        try:
            list_result = await self.sessions['filesystem']['session'].call_tool(
                'list_allowed_directories', {}
            )
            if list_result.content and isinstance(list_result.content[0].text, str):
                content_text = list_result.content[0].text.strip()
                try:
                    list_data = json.loads(content_text)
                    if isinstance(list_data, dict) and 'items' in list_data:
                        self.allowed_dirs = [item['name'] for item in list_data['items'] if item.get('type') == 'directory']
                    elif isinstance(list_data, list):
                        self.allowed_dirs = [s for s in list_data if isinstance(s, str)]
                    else:
                        self.allowed_dirs = []
                except json.JSONDecodeError:
                    # Attempt to parse if it's a string like "Allowed directories: [ '/path1', '/path2' ]"
                    match = re.search(r"\[\s*'(.*?)'\s*\]", content_text)
                    if match:
                        # Extract paths, splitting by "', '" and stripping quotes
                        parsed_dirs = [p.strip("'") for p in match.group(1).split("', '")]
                        self.allowed_dirs = [d for d in parsed_dirs if d.startswith('/')] # Filter to ensure they are paths
                    else:
                        # Fallback to splitting by newline if no specific pattern found
                        parsed_dirs = [line.strip() for line in content_text.split('\n') if line.strip()]
                        self.allowed_dirs = [d for d in parsed_dirs if d.startswith('/')] # Filter to ensure they are paths
            else:
                self.allowed_dirs = []
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error fetching allowed directories: {e}[/red]")
            self.allowed_dirs = []

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
            if self.allowed_dirs is None:
                await self._fetch_allowed_directories()

            if not self.allowed_dirs:
                if self.console:
                    self.console.print("[yellow]No allowed directories configured for filesystem tool.[/yellow]")
                return

            try:
                # Determine the directory to list and the search term
                # Handle cases like "@", "@/", "@foo", "@foo/", "@foo/bar"
                if not at_command_text:
                    # If no path is typed yet, suggest allowed root directories
                    for allowed_dir in self.allowed_dirs:
                        yield Completion(
                            allowed_dir,
                            start_position=-len(text_before_cursor),
                            display=allowed_dir,
                            display_meta="[DIRECTORY]"
                        )
                    return
                
                # Normalize path to handle cases like "//" or "/./"
                normalized_at_command_text = os.path.normpath(at_command_text)
                
                # If the command text ends with a slash, it means we want to list that directory
                if at_command_text.endswith('/'):
                    dir_to_list = normalized_at_command_text
                    search_term = ''
                else:
                    # Otherwise, the last part is the search term, and the rest is the directory
                    # Special case for root directory
                    if normalized_at_command_text == '/':
                        dir_to_list = '/'
                        search_term = ''
                    else:
                        dir_to_list = os.path.dirname(normalized_at_command_text)
                        search_term = os.path.basename(normalized_at_command_text)
                        
                        # If dirname returns empty for a path like "foo", it means it's in the current dir
                        if dir_to_list == '':
                            dir_to_list = '/'

                # Ensure dir_to_list is absolute and normalized
                if not dir_to_list.startswith('/'):
                    dir_to_list = '/' + dir_to_list
                
                # Validate if the requested directory is within allowed directories
                is_allowed = False
                for allowed_path in self.allowed_dirs:
                    if dir_to_list.startswith(allowed_path):
                        is_allowed = True
                        break
                
                if not is_allowed:
                    if self.console:
                        self.console.print(f"[red]Error: Access denied - path outside allowed directories: {dir_to_list} not in {self.allowed_dirs}[/red]")
                    return

                # Call list_directory tool
                list_result = await self.sessions['filesystem']['session'].call_tool(
                    'list_directory',
                    {'path': dir_to_list}
                )
                
                # Debugging: Print the raw output from list_directory
                if self.console:
                    self.console.print(f"[yellow]DEBUG: list_directory('{dir_to_list}') raw result: {list_result.content}[/yellow]")

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
                    
                    # Fuzzy match against the search term
                    if not search_term or clean_name.lower().startswith(search_term.lower()):
                        # Construct the full path for display
                        if dir_to_list == '/':
                            display_path = '/' + clean_name
                        else:
                            display_path = os.path.join(dir_to_list, clean_name)
                        
                        # The text to insert is just the clean_name, not the full path
                        # If it's a directory, add a '/' to make it easier to continue typing
                        text_to_insert = clean_name
                        if item.get('type') == 'directory':
                            text_to_insert += '/'

                        display_meta = f"[{item.get('type', 'file').upper()}]"
                        yield Completion(
                            text_to_insert,
                            start_position=-len(search_term), # Replace only the search term part
                            display=display_path,
                            display_meta=display_meta
                        )
            except Exception as e:
                if self.console:
                    self.console.print(f"[red]Error fetching filesystem completions: {e}[/red]")
        else:
            if self.console:
                self.console.print("[yellow]Filesystem tool not available for @-commands.[/yellow]")

