"""
Collapsible output utility for displaying large blocks of text in the terminal.

Provides a way to collapse large outputs into a single line summary that can be
expanded by the user if they want to see the full content.
"""

from typing import Optional
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm


class CollapsibleOutput:
    """
    Manages collapsible output blocks in the terminal.

    Large outputs are shown as a summary line with the option to expand.
    Users can configure the threshold for what constitutes "large" output.
    """

    def __init__(
        self,
        console: Console,
        line_threshold: int = 20,
        char_threshold: int = 1000,
        auto_collapse: bool = True
    ):
        """
        Initialize collapsible output manager.

        Args:
            console: Rich console instance
            line_threshold: Number of lines before auto-collapsing
            char_threshold: Number of characters before auto-collapsing
            auto_collapse: Whether to auto-collapse large outputs
        """
        self.console = console
        self.line_threshold = line_threshold
        self.char_threshold = char_threshold
        self.auto_collapse = auto_collapse

    def should_collapse(self, content: str) -> bool:
        """
        Determine if content should be collapsed.

        Args:
            content: The text content to check

        Returns:
            True if content exceeds thresholds, False otherwise
        """
        if not self.auto_collapse:
            return False

        lines = content.splitlines()
        return (
            len(lines) > self.line_threshold or
            len(content) > self.char_threshold
        )

    def print_collapsible(
        self,
        content: str,
        title: str,
        summary: Optional[str] = None,
        style: str = "cyan",
        interactive: bool = False
    ):
        """
        Print content with optional collapsing.

        Args:
            content: The full content to display
            title: Title for the output block
            summary: Optional custom summary (auto-generated if None)
            style: Style for the panel border
            interactive: If True, prompt user to expand collapsed content
        """
        if not content:
            self.console.print(f"[{style}]{title}[/{style}]: [dim](empty)[/dim]")
            return

        should_collapse = self.should_collapse(content)

        if not should_collapse:
            # Show full content
            self.console.print(Panel(
                content,
                title=title,
                border_style=style,
                expand=False
            ))
            return

        # Generate summary if not provided
        if summary is None:
            summary = self._generate_summary(content)

        # Show collapsed version
        lines = content.splitlines()
        self.console.print(
            f"[{style}]▶ {title}[/{style}] "
            f"[dim]({len(lines)} lines, {len(content)} chars)[/dim]"
        )
        self.console.print(f"  [dim]{summary}[/dim]")

        # Optionally allow expansion
        if interactive:
            expand = Confirm.ask(
                f"  [dim]Expand {title}?[/dim]",
                default=False,
                console=self.console
            )
            if expand:
                self.console.print(Panel(
                    content,
                    title=f"{title} (expanded)",
                    border_style=style,
                    expand=False
                ))

    def print_with_preview(
        self,
        content: str,
        title: str,
        preview_lines: int = 5,
        style: str = "cyan"
    ):
        """
        Print content with a preview of first few lines if collapsed.

        Args:
            content: The full content
            title: Title for the output
            preview_lines: Number of lines to show in preview
            style: Style for the panel border
        """
        if not content:
            self.console.print(f"[{style}]{title}[/{style}]: [dim](empty)[/dim]")
            return

        lines = content.splitlines()
        should_collapse = self.should_collapse(content)

        if not should_collapse:
            # Show full content
            self.console.print(Panel(
                content,
                title=title,
                border_style=style,
                expand=False
            ))
            return

        # Show preview
        preview = "\n".join(lines[:preview_lines])
        remaining = len(lines) - preview_lines

        self.console.print(
            f"[{style}]▶ {title}[/{style}] "
            f"[dim]({len(lines)} lines total)[/dim]"
        )
        self.console.print(Panel(
            f"{preview}\n\n[dim]... ({remaining} more lines hidden)[/dim]",
            border_style="dim",
            expand=False
        ))

    def _generate_summary(self, content: str, max_length: int = 100) -> str:
        """
        Generate a one-line summary of the content.

        Args:
            content: The full content
            max_length: Maximum length of summary

        Returns:
            Summary string
        """
        # Try to get the first meaningful line
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        if not lines:
            return "(empty)"

        first_line = lines[0]

        if len(first_line) <= max_length:
            return first_line

        # Truncate with ellipsis
        return first_line[:max_length-3] + "..."


class TaskOutputCollector:
    """
    Collects and manages output from agent tasks.

    Allows for intelligent display of task results with collapsing
    for long outputs.
    """

    def __init__(self, console: Console, collapsible: CollapsibleOutput):
        """
        Initialize task output collector.

        Args:
            console: Rich console instance
            collapsible: CollapsibleOutput instance
        """
        self.console = console
        self.collapsible = collapsible

    def print_task_result(
        self,
        task_id: str,
        agent_type: str,
        description: str,
        result: str,
        status: str = "completed"
    ):
        """
        Print the result of a task execution.

        Args:
            task_id: Task identifier
            agent_type: Type of agent that executed the task
            description: Task description
            result: Task execution result
            status: Task status (completed/failed)
        """
        # Create title
        status_icon = "✓" if status == "completed" else "✗"
        status_color = "green" if status == "completed" else "red"

        title = f"[{status_color}]{status_icon}[/{status_color}] {task_id} ({agent_type})"

        # Generate summary from description
        summary = f"{description[:80]}..." if len(description) > 80 else description

        # Print with collapsing
        self.collapsible.print_with_preview(
            content=result,
            title=title,
            preview_lines=3,
            style=status_color
        )

    def print_aggregated_results(
        self,
        results: list[tuple[str, str, str]],
        original_query: str
    ):
        """
        Print aggregated results from multiple tasks.

        Args:
            results: List of (task_id, agent_type, result) tuples
            original_query: Original user query
        """
        self.console.print("\n[bold yellow]📊 Aggregated Results[/bold yellow]")
        self.console.print(f"[dim]Original query: {original_query}[/dim]\n")

        for task_id, agent_type, result in results:
            self.print_task_result(
                task_id=task_id,
                agent_type=agent_type,
                description="",
                result=result,
                status="completed"
            )
