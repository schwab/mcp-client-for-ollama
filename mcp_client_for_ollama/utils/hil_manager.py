"""Human-in-the-Loop (HIL) manager for tool execution confirmations.

This module manages HIL confirmations for tool calls, allowing users to review,
approve, or skip tool executions before they are performed.
"""

import copy
from rich.prompt import Prompt
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from typing import Dict, Any, Optional, Callable, List

class HumanInTheLoopManager:
    """Manages Human-in-the-Loop confirmations for tool execution with granular control."""

    def __init__(self, console: Console, tool_manager: Any = None):
        """Initialize the HIL manager.

        Args:
            console: Rich console for output
            tool_manager: Reference to the ToolManager to get available tools.
        """
        self.console = console
        self.tool_manager = tool_manager
        self._hil_config: Dict[str, Any] = self._get_default_hil_config()

    def _get_default_hil_config(self) -> Dict[str, Any]:
        """Returns the default HIL configuration."""
        return {
            "global_enabled": True,
            "servers": {} # Populated dynamically
        }

    def get_config(self) -> Dict[str, Any]:
        """Returns the current HIL configuration."""
        return self._hil_config

    def set_config(self, config: Dict[str, Any]) -> None:
        """Sets the HIL configuration."""
        self._hil_config = config

    def _initialize_server_configs(self) -> None:
        """Initializes HIL configuration for newly discovered servers/tools."""
        if not self.tool_manager:
            return

        available_tools = self.tool_manager.get_available_tools()
        
        # Group tools by server name
        server_tools: Dict[str, List[str]] = {}
        for tool in available_tools:
            server_name, _ = tool.name.split('.', 1) if '.' in tool.name else ("default", tool.name)
            if server_name not in server_tools:
                server_tools[server_name] = []
            server_tools[server_name].append(tool.name)

        if "servers" not in self._hil_config:
            self._hil_config["servers"] = {}

        for server_name, tools_in_server in server_tools.items():
            if server_name not in self._hil_config["servers"]:
                self._hil_config["servers"][server_name] = {
                    "enabled": True, # Default to enabled for new servers
                    "tools": {}
                }
            for tool_name in tools_in_server:
                if tool_name not in self._hil_config["servers"][server_name]["tools"]:
                    self._hil_config["servers"][server_name]["tools"][tool_name] = True # Default to enabled for new tools

    def is_enabled(self, tool_name: str) -> bool:
        """
        Checks if HIL confirmation is enabled for a specific tool.

        Args:
            tool_name: The fully qualified name of the tool (e.g., "builtin.set_system_prompt").

        Returns:
            True if HIL is enabled for this tool, False otherwise.
        """
        if not self._hil_config["global_enabled"]:
            return False

        server_name, _ = tool_name.split('.', 1) if '.' in tool_name else ("default", tool_name)

        server_config = self._hil_config["servers"].get(server_name)
        if not server_config or not server_config["enabled"]:
            return False

        return server_config["tools"].get(tool_name, True) # Default to True if tool not explicitly configured

    def toggle_global(self) -> None:
        """Toggles global HIL confirmations."""
        self._hil_config["global_enabled"] = not self._hil_config["global_enabled"]
        status = "enabled" if self._hil_config["global_enabled"] else "disabled"
        self.console.print(f"[green]Global HIL confirmations {status}![/green]")
        self.console.print("[dim]Use 'hil-config' to manage granular settings.[/dim]")

    def _set_global_enabled(self, enabled: bool) -> None:
        """Sets global HIL enabled state (used when loading from config)."""
        self._hil_config["global_enabled"] = enabled

    def _set_server_enabled(self, server_name: str, enabled: bool) -> None:
        """Sets HIL enabled state for all tools on a specific server."""
        if server_name in self._hil_config["servers"]:
            self._hil_config["servers"][server_name]["enabled"] = enabled
            for tool_name in self._hil_config["servers"][server_name]["tools"]:
                self._hil_config["servers"][server_name]["tools"][tool_name] = enabled
            status = "enabled" if enabled else "disabled"
            self.console.print(f"[green]HIL for server '{server_name}' {status}![/green]")
        else:
            self.console.print(f"[red]Server '{server_name}' not found in HIL configuration.[/red]")

    def _set_tool_enabled(self, tool_name: str, enabled: bool) -> None:
        """Sets HIL enabled state for a specific tool."""
        server_name, _ = tool_name.split('.', 1) if '.' in tool_name else ("default", tool_name)
        if server_name in self._hil_config["servers"]:
            if tool_name in self._hil_config["servers"][server_name]["tools"]:
                self._hil_config["servers"][server_name]["tools"][tool_name] = enabled
                status = "enabled" if enabled else "disabled"
                self.console.print(f"[green]HIL for tool '{tool_name}' {status}![/green]")
            else:
                self.console.print(f"[red]Tool '{tool_name}' not found in server '{server_name}'.[/red]")
        else:
            self.console.print(f"[red]Server '{server_name}' not found for tool '{tool_name}'.[/red]")

    async def request_tool_confirmation(self, tool_name: str, tool_args: dict) -> bool:
        """
        Request user confirmation for tool execution.

        Args:
            tool_name: Name of the tool to execute.
            tool_args: Arguments for the tool.

        Returns:
            True if the tool should be executed, False otherwise.
        """
        # Ensure HIL config is up-to-date with available tools
        self._initialize_server_configs()

        if not self.is_enabled(tool_name):
            return True # Execute if HIL is disabled for this tool/server/globally

        server_name, _ = tool_name.split('.', 1) if '.' in tool_name else ("default", tool_name)

        self.console.print("[bold yellow]🧑‍💻 Human-in-the-Loop Confirmation[/bold yellow]")

        # Show tool information
        self.console.print(f"[cyan]Tool to execute:[/cyan] [bold]{tool_name}[/bold]")

        # Show arguments
        if tool_args:
            self.console.print("[cyan]Arguments:[/cyan]")
            for key, value in tool_args.items():
                # Truncate long values for display
                display_value = str(value)
                if len(display_value) > 50:
                    display_value = display_value[:47] + "..."
                self.console.print(f"  • {key}: {display_value}")
        else:
            self.console.print("[cyan]Arguments:[/cyan] [dim]None[/dim]")

        self.console.print()

        # Display options
        self._display_confirmation_options(tool_name, server_name)

        choice = Prompt.ask(
            "[bold]What would you like to do?[/bold]",
            choices=["y", "yes", "n", "no", "disable-tool", "disable-server", "disable-all", "config"],
            default="y",
            show_choices=False
        ).lower()

        return self._handle_user_choice(choice, tool_name, server_name)

    def _display_confirmation_options(self, tool_name: str, server_name: str) -> None:
        """Display available confirmation options."""
        self.console.print("[bold cyan]Options:[/bold cyan]")
        self.console.print("  [green]y/yes[/green] - Execute the tool call")
        self.console.print("  [red]n/no[/red] - Skip this tool call")
        self.console.print(f"  [yellow]disable-tool[/yellow] - Disable HIL for '[bold]{tool_name}[/bold]' permanently")
        self.console.print(f"  [yellow]disable-server[/yellow] - Disable HIL for all tools on '[bold]{server_name}[/bold]' permanently")
        self.console.print("  [yellow]disable-all[/yellow] - Disable HIL globally permanently")
        self.console.print("  [blue]config[/blue] - Open HIL configuration menu")
        self.console.print()

    def _handle_user_choice(self, choice: str, tool_name: str, server_name: str) -> bool:
        """
        Handle user's confirmation choice.

        Args:
            choice: User's choice string.
            tool_name: The name of the tool being confirmed.
            server_name: The name of the server the tool belongs to.

        Returns:
            True if the tool should be executed, False otherwise.
        """
        if choice == "disable-tool":
            self._set_tool_enabled(tool_name, False)
            self.console.print(f"[dim]HIL for '{tool_name}' disabled. This tool will now execute automatically.[/dim]")
            return True # Execute current tool call after disabling HIL for it
        elif choice == "disable-server":
            self._set_server_enabled(server_name, False)
            self.console.print(f"[dim]HIL for server '{server_name}' disabled. All tools on this server will now execute automatically.[/dim]")
            return True # Execute current tool call after disabling HIL for its server
        elif choice == "disable-all":
            self._set_global_enabled(False)
            self.console.print("[dim]Global HIL disabled. All tools will now execute automatically.[/dim]")
            return True # Execute current tool call after disabling HIL globally
        elif choice == "config":
            self.configure_hil_interactive(None) # Pass None for clear_console_func as it's handled by client
            return False # Do not execute current tool, user is in config menu
        elif choice in ["n", "no"]:
            self.console.print("[yellow]⏭️  Tool call skipped[/yellow]")
            return False
        else:  # y/yes
            return True

    def _display_hil_menu(self, sorted_server_names: List[str], result_message: Optional[str], result_style: str) -> None:
        """Displays the HIL configuration menu."""
        self.console.print(Panel(Text.from_markup("[bold]🧑‍💻 HIL Configuration[/bold]", justify="center"),
                                 expand=True, border_style="yellow"))

        # Display Global HIL Status
        global_status = self._get_status_indicator(self._hil_config["global_enabled"])
        self.console.print(f"[bold magenta]1. Global HIL: {global_status}[/bold magenta]")
        self.console.print()

        # Display Server HIL Settings
        self.console.print("[bold]Server HIL Settings:[/bold]")
        for i, server_name in enumerate(sorted_server_names):
            server_config = self._hil_config["servers"][server_name]
            server_status = self._get_status_indicator(server_config["enabled"])
            self.console.print(f"  [cyan]{i+2}. {server_name}: {server_status}[/cyan]")
        self.console.print()

        # Display result message if any
        if result_message:
            self.console.print(Panel(result_message, border_style=result_style, expand=False))

        self._display_hil_config_commands()

    def _handle_hil_menu_selection(self, selection: str, sorted_server_names: List[str]) -> tuple[bool, Optional[str], str]:
        """
        Handles a user's selection in the HIL configuration menu.
        Returns (should_exit, result_message, result_style).
        """
        result_message = None
        result_style = "green"
        should_exit = False

        if selection == '1':
            self.toggle_global()
            result_message = f"[green]Global HIL toggled.[/green]"
        elif selection.startswith('s') and len(selection) > 1 and selection[1:].isdigit():
            server_idx = int(selection[1:]) - 2 # Adjust for global option
            if 0 <= server_idx < len(sorted_server_names):
                server_name = sorted_server_names[server_idx]
                current_state = self._hil_config["servers"][server_name]["enabled"]
                self._set_server_enabled(server_name, not current_state)
                result_message = f"[green]HIL for server '{server_name}' toggled.[/green]"
            else:
                result_message, result_style = "[red]Invalid server selection.[/red]", "red"
        elif selection.startswith('t') and len(selection) > 1 and selection[1:].isdigit():
            # This is more complex, requires another sub-menu or direct tool name input
            # For now, let's just allow direct tool name input
            tool_name_input = Prompt.ask("Enter full tool name to toggle (e.g., builtin.execute_python_code)").strip()
            if tool_name_input:
                server_name, _ = tool_name_input.split('.', 1) if '.' in tool_name_input else ("default", tool_name_input)
                if server_name in self._hil_config["servers"] and tool_name_input in self._hil_config["servers"][server_name]["tools"]:
                    current_state = self._hil_config["servers"][server_name]["tools"][tool_name_input]
                    self._set_tool_enabled(tool_name_input, not current_state)
                    result_message = f"[green]HIL for tool '{tool_name_input}' toggled.[/green]"
                else:
                    result_message, result_style = "[red]Tool not found or invalid tool name.[/red]", "red"
            else:
                result_message, result_style = "[yellow]No tool name entered.[/yellow]", "yellow"
        else:
            result_message, result_style = "[red]Invalid selection.[/red]", "red"
        
        return should_exit, result_message, result_style

    def configure_hil_interactive(self, clear_console_func: Optional[Callable]) -> None:
        """
        Interactive interface for configuring HIL settings.
        Allows users to enable/disable HIL at global, server, and tool levels.
        """
        # Ensure HIL config is up-to-date with available tools
        self._initialize_server_configs()

        original_config = copy.deepcopy(self._hil_config) # For 'quit' option
        result_message = None
        result_style = "green"

        while True:
            if clear_console_func:
                clear_console_func()
            
            sorted_server_names = sorted(self._hil_config["servers"].keys())
            self._display_hil_menu(sorted_server_names, result_message, result_style)
            result_message = None # Clear message after display

            selection = Prompt.ask("> ").strip().lower()

            if selection in ['s', 'save']:
                if clear_console_func:
                    clear_console_func()
                self.console.print("[green]HIL configuration saved.[/green]")
                return
            elif selection in ['q', 'quit']:
                self._hil_config = original_config # Revert changes
                if clear_console_func:
                    clear_console_func()
                self.console.print("[yellow]HIL configuration changes cancelled.[/yellow]")
                return
            else:
                should_exit, result_message, result_style = self._handle_hil_menu_selection(selection, sorted_server_names)
                if should_exit:
                    return

    def _display_hil_config_commands(self) -> None:
        """Displays commands for the HIL configuration menu."""
        self.console.print("[bold yellow]Commands:[/bold yellow]")
        self.console.print("  [bold magenta]1[/bold magenta] - Toggle Global HIL")
        self.console.print("  [bold cyan]S + number[/bold cyan] - Toggle HIL for a specific server (e.g., [bold]S2[/bold])")
        self.console.print("  [bold green]T + number[/bold green] - Toggle HIL for a specific tool (e.g., [bold]T3[/bold]) - [dim]Not yet implemented for direct selection[/dim]")
        self.console.print("  [bold]s/save[/bold] - Save changes and return")
        self.console.print("  [bold]q/quit[/bold] - Cancel changes and return")
        self.console.print()

    def _get_status_indicator(self, enabled: bool) -> str:
        """Get a formatted status indicator based on enabled state."""
        return "[green]✓[/green]" if enabled else "[red]✗[/red]"
