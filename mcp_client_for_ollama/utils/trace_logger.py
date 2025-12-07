"""
Trace logging system for agent LLM calls.

Provides detailed logging of prompts, responses, and tool calls for debugging
the agent delegation system.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum


class TraceLevel(Enum):
    """Trace logging levels."""
    OFF = 0      # No tracing
    SUMMARY = 1  # Log only summaries (task start/end)
    BASIC = 2    # Log prompts and responses (truncated)
    FULL = 3     # Log everything including full prompts/responses
    DEBUG = 4    # Maximum verbosity including tool calls


@dataclass
class TraceEntry:
    """A single trace log entry."""
    timestamp: str
    entry_type: str  # "task_start", "llm_call", "tool_call", "task_end", etc.
    task_id: Optional[str]
    agent_type: Optional[str]
    data: Dict[str, Any]


class TraceLogger:
    """
    Manages trace logging for agent delegation system.

    Logs all LLM interactions to help debug planning and execution issues.
    """

    def __init__(
        self,
        level: TraceLevel = TraceLevel.OFF,
        log_dir: Optional[Path] = None,
        console_output: bool = False,
        truncate_length: int = 500
    ):
        """
        Initialize trace logger.

        Args:
            level: Trace logging level
            log_dir: Directory for log files (default: ./.trace/)
            console_output: Whether to also print traces to console
            truncate_length: Max length for truncated outputs
        """
        self.level = level
        self.console_output = console_output
        self.truncate_length = truncate_length

        # Set up log directory
        if log_dir is None:
            log_dir = Path(".trace")

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create session log file
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"trace_{self.session_id}.jsonl"

        # Track entries
        self.entries: List[TraceEntry] = []

    def is_enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self.level != TraceLevel.OFF

    def log_task_start(
        self,
        task_id: str,
        agent_type: str,
        description: str,
        dependencies: List[str]
    ):
        """
        Log the start of a task.

        Args:
            task_id: Task identifier
            agent_type: Type of agent executing the task
            description: Task description
            dependencies: List of dependency task IDs
        """
        if not self.is_enabled():
            return

        entry = TraceEntry(
            timestamp=self._get_timestamp(),
            entry_type="task_start",
            task_id=task_id,
            agent_type=agent_type,
            data={
                "description": description,
                "dependencies": dependencies
            }
        )

        self._write_entry(entry)

    def log_llm_call(
        self,
        task_id: Optional[str],
        agent_type: Optional[str],
        prompt: str,
        response: str,
        model: str,
        temperature: float,
        loop_iteration: int = 0,
        tools_used: Optional[List[str]] = None
    ):
        """
        Log an LLM call with its prompt and response.

        Args:
            task_id: Task identifier (None for planning phase)
            agent_type: Agent type (None for planner)
            prompt: Full prompt sent to LLM
            response: Full response from LLM
            model: Model name/ID
            temperature: Temperature setting
            loop_iteration: Tool loop iteration number
            tools_used: List of tool names used in this call
        """
        if self.level == TraceLevel.OFF:
            return

        # Truncate if not in FULL or DEBUG mode
        if self.level in [TraceLevel.SUMMARY, TraceLevel.BASIC]:
            prompt = self._truncate(prompt)
            response = self._truncate(response)

        entry = TraceEntry(
            timestamp=self._get_timestamp(),
            entry_type="llm_call",
            task_id=task_id,
            agent_type=agent_type or "PLANNER",
            data={
                "model": model,
                "temperature": temperature,
                "loop_iteration": loop_iteration,
                "prompt": prompt,
                "response": response,
                "prompt_length": len(prompt),
                "response_length": len(response),
                "tools_used": tools_used or []
            }
        )

        self._write_entry(entry)

    def log_tool_call(
        self,
        task_id: Optional[str],
        agent_type: Optional[str],
        tool_name: str,
        arguments: Dict[str, Any],
        result: str,
        success: bool
    ):
        """
        Log a tool call and its result.

        Args:
            task_id: Task identifier
            agent_type: Agent type
            tool_name: Name of the tool called
            arguments: Tool arguments
            result: Tool execution result
            success: Whether tool call succeeded
        """
        if self.level not in [TraceLevel.FULL, TraceLevel.DEBUG]:
            return

        # Truncate result if not in DEBUG mode
        if self.level != TraceLevel.DEBUG:
            result = self._truncate(result)

        entry = TraceEntry(
            timestamp=self._get_timestamp(),
            entry_type="tool_call",
            task_id=task_id,
            agent_type=agent_type,
            data={
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
                "result_length": len(result),
                "success": success
            }
        )

        self._write_entry(entry)

    def log_task_end(
        self,
        task_id: str,
        agent_type: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """
        Log the completion of a task.

        Args:
            task_id: Task identifier
            agent_type: Agent type
            status: Task status (completed/failed)
            result: Task result (if successful)
            error: Error message (if failed)
            duration_ms: Task execution duration in milliseconds
        """
        if not self.is_enabled():
            return

        # Truncate result/error if not in FULL mode
        if self.level not in [TraceLevel.FULL, TraceLevel.DEBUG]:
            if result:
                result = self._truncate(result)
            if error:
                error = self._truncate(error)

        entry = TraceEntry(
            timestamp=self._get_timestamp(),
            entry_type="task_end",
            task_id=task_id,
            agent_type=agent_type,
            data={
                "status": status,
                "result": result,
                "error": error,
                "duration_ms": duration_ms,
                "result_length": len(result) if result else 0
            }
        )

        self._write_entry(entry)

    def log_planning_phase(
        self,
        query: str,
        plan: Dict[str, Any],
        available_agents: List[str],
        examples_used: List[str]
    ):
        """
        Log the planning phase details.

        Args:
            query: User query
            plan: Generated task plan
            available_agents: List of available agent types
            examples_used: List of example categories used
        """
        if not self.is_enabled():
            return

        entry = TraceEntry(
            timestamp=self._get_timestamp(),
            entry_type="planning_phase",
            task_id=None,
            agent_type="PLANNER",
            data={
                "query": query,
                "plan": plan,
                "available_agents": available_agents,
                "examples_used": examples_used,
                "task_count": len(plan.get("tasks", []))
            }
        )

        self._write_entry(entry)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the trace session.

        Returns:
            Dictionary with session statistics
        """
        llm_calls = [e for e in self.entries if e.entry_type == "llm_call"]
        tool_calls = [e for e in self.entries if e.entry_type == "tool_call"]
        tasks = [e for e in self.entries if e.entry_type == "task_end"]

        completed_tasks = [t for t in tasks if t.data.get("status") == "completed"]
        failed_tasks = [t for t in tasks if t.data.get("status") == "failed"]

        return {
            "session_id": self.session_id,
            "log_file": str(self.log_file),
            "total_entries": len(self.entries),
            "llm_calls": len(llm_calls),
            "tool_calls": len(tool_calls),
            "tasks_total": len(tasks),
            "tasks_completed": len(completed_tasks),
            "tasks_failed": len(failed_tasks)
        }

    def print_summary(self, console):
        """
        Print a summary of the trace session to console.

        Args:
            console: Rich console instance
        """
        summary = self.get_summary()

        console.print("\n[bold cyan]🔍 Trace Session Summary[/bold cyan]")
        console.print(f"[dim]Session ID: {summary['session_id']}[/dim]")
        console.print(f"[dim]Log file: {summary['log_file']}[/dim]\n")

        console.print(f"Total trace entries: {summary['total_entries']}")
        console.print(f"LLM calls: {summary['llm_calls']}")
        console.print(f"Tool calls: {summary['tool_calls']}")
        console.print(f"Tasks completed: {summary['tasks_completed']}")
        console.print(f"Tasks failed: {summary['tasks_failed']}\n")

    def _write_entry(self, entry: TraceEntry):
        """Write a trace entry to the log file."""
        self.entries.append(entry)

        # Write to JSONL file
        with open(self.log_file, 'a') as f:
            json_data = asdict(entry)
            f.write(json.dumps(json_data) + "\n")

        # Optionally print to console
        if self.console_output and self.level == TraceLevel.DEBUG:
            print(f"[TRACE] {entry.entry_type}: {entry.task_id or 'N/A'}")

    def _truncate(self, text: str) -> str:
        """Truncate text to configured length."""
        if len(text) <= self.truncate_length:
            return text
        return text[:self.truncate_length] + f"... ({len(text) - self.truncate_length} chars truncated)"

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()


class TraceLoggerFactory:
    """Factory for creating trace loggers with configuration."""

    @staticmethod
    def from_config(config: Dict[str, Any]) -> TraceLogger:
        """
        Create a trace logger from configuration.

        Args:
            config: Configuration dictionary with keys:
                - trace_enabled: bool
                - trace_level: str ("off", "summary", "basic", "full", "debug")
                - trace_dir: Optional[str]
                - trace_console: bool

        Returns:
            Configured TraceLogger instance
        """
        if not config.get("trace_enabled", False):
            return TraceLogger(level=TraceLevel.OFF)

        # Parse level
        level_str = config.get("trace_level", "basic").upper()
        level = TraceLevel[level_str] if level_str in TraceLevel.__members__ else TraceLevel.BASIC

        # Get directory
        trace_dir = config.get("trace_dir")
        if trace_dir:
            trace_dir = Path(trace_dir)

        return TraceLogger(
            level=level,
            log_dir=trace_dir,
            console_output=config.get("trace_console", False),
            truncate_length=config.get("trace_truncate", 500)
        )
