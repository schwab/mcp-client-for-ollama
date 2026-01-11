"""Artifact context management for LLM integration."""

from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from uuid import uuid4
import re


@dataclass
class ArtifactExecution:
    """Record of an artifact interaction."""

    execution_id: str
    timestamp: datetime
    artifact_type: str
    artifact_title: str
    tool_name: str
    tool_args: Dict[str, Any]
    tool_result: str
    user_id: Optional[str] = None
    interaction_type: str = "form_submit"
    result_type: str = "success"
    result_summary: str = ""
    result_size: int = 0
    is_referenceable: bool = True
    context_ttl: int = 10


@dataclass
class ArtifactContext:
    """Manages artifact execution history and context."""

    session_id: str
    executions: List[ArtifactExecution] = field(default_factory=list)
    max_context_items: int = 10
    max_result_size: int = 50000
    auto_summarize_threshold: int = 10000
    auto_inject: bool = True

    @property
    def last_execution(self) -> Optional[ArtifactExecution]:
        """Get the most recent execution."""
        return self.executions[-1] if self.executions else None

    @property
    def recent_files(self) -> List[str]:
        """Get recently accessed file paths."""
        files = []
        for exec in reversed(self.executions):
            if 'path' in exec.tool_args:
                path = exec.tool_args['path']
                if path not in files:
                    files.append(path)
        return files[:10]

    @property
    def recent_tools(self) -> List[str]:
        """Get recently used tools."""
        tools = []
        for exec in reversed(self.executions):
            if exec.tool_name not in tools:
                tools.append(exec.tool_name)
        return tools[:10]

    def add_execution(self, execution: ArtifactExecution):
        """Add an execution record."""
        self.executions.append(execution)

        # Prune old executions (keep last 50)
        if len(self.executions) > 50:
            self.executions = self.executions[-50:]

    def get_recent_executions(self, limit: int = 5) -> List[ArtifactExecution]:
        """Get N most recent executions."""
        return list(reversed(self.executions[-limit:]))

    def get_execution(self, execution_id: str) -> Optional[ArtifactExecution]:
        """Get execution by ID."""
        for exec in self.executions:
            if exec.execution_id == execution_id:
                return exec
        return None


class ArtifactContextManager:
    """Manages artifact context for LLM integration."""

    def __init__(self):
        self.contexts: Dict[str, ArtifactContext] = {}
        self.reference_resolvers: List[Callable] = [
            self._resolve_temporal_reference,
            self._resolve_content_reference,
            self._resolve_tool_reference,
        ]

    def get_or_create_context(self, session_id: str) -> ArtifactContext:
        """Get or create context for a session."""
        if session_id not in self.contexts:
            self.contexts[session_id] = ArtifactContext(session_id=session_id)
        return self.contexts[session_id]

    def record_execution(
        self,
        session_id: str,
        artifact_type: str,
        artifact_title: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: str,
        **kwargs
    ) -> ArtifactExecution:
        """
        Record a new artifact execution.

        Args:
            session_id: The session ID
            artifact_type: Type of artifact (e.g., "toolform")
            artifact_title: Display title
            tool_name: Name of the tool executed
            tool_args: Arguments passed to the tool
            tool_result: Result from tool execution
            **kwargs: Additional execution metadata

        Returns:
            The created ArtifactExecution record
        """
        context = self.get_or_create_context(session_id)

        # Create execution record
        execution = ArtifactExecution(
            execution_id=str(uuid4()),
            timestamp=datetime.now(),
            artifact_type=artifact_type,
            artifact_title=artifact_title,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            result_size=len(tool_result),
            result_summary=self._create_summary(tool_name, tool_args, tool_result),
            **kwargs
        )

        context.add_execution(execution)
        return execution

    def build_context_message(
        self,
        session_id: str,
        user_query: Optional[str] = None,
        include_recent: int = 3
    ) -> Optional[Dict[str, str]]:
        """
        Build a context message for the LLM.

        This creates a system message containing recent artifact executions
        and their results, which will be injected into the LLM context.

        Args:
            session_id: The session ID
            user_query: Optional user query to resolve references
            include_recent: Number of recent executions to include

        Returns:
            A system message dict with artifact context, or None if no context
        """
        context = self.get_or_create_context(session_id)

        if not context.executions:
            return None

        # Don't inject if disabled
        if not context.auto_inject:
            return None

        # Get executions to include
        executions_to_include = []

        # 1. Always include recent executions
        recent = context.get_recent_executions(limit=include_recent)
        executions_to_include.extend(recent)

        # 2. If user query provided, resolve references and include
        if user_query:
            referenced = self.resolve_references(session_id, user_query)
            for exec in referenced:
                if exec not in executions_to_include:
                    executions_to_include.append(exec)

        if not executions_to_include:
            return None

        # Build context message
        content_parts = ["**Artifact Context:**\n"]
        content_parts.append("The user recently executed the following tools via artifacts:\n")

        for i, execution in enumerate(executions_to_include, 1):
            content_parts.append(f"\n{i}. **{execution.artifact_title}**")
            content_parts.append(f"   Time: {self._format_time_ago(execution.timestamp)}")
            content_parts.append(f"   Tool: {execution.tool_name}")
            content_parts.append(f"   Arguments: {execution.tool_args}")

            # Include result (with size management)
            result = execution.tool_result
            if execution.result_size > context.auto_summarize_threshold:
                result = self._truncate_result(result, max_size=5000)
                content_parts.append(f"   Result (truncated): {result}")
            else:
                content_parts.append(f"   Result:\n   ```\n{result}\n   ```")

        content_parts.append("\nYou can reference these results when answering the user's questions.")

        return {
            "role": "system",
            "content": "\n".join(content_parts)
        }

    def resolve_references(
        self,
        session_id: str,
        query: str
    ) -> List[ArtifactExecution]:
        """
        Resolve references in user query to artifact executions.

        Uses multiple resolution strategies (temporal, content-based, tool-based)
        to find artifact executions that the user is referring to.

        Args:
            session_id: The session ID
            query: User's query text

        Returns:
            List of referenced executions
        """
        context = self.get_or_create_context(session_id)
        referenced = []

        for resolver in self.reference_resolvers:
            results = resolver(context, query)
            for result in results:
                if result not in referenced:
                    referenced.append(result)

        return referenced

    def _resolve_temporal_reference(
        self,
        context: ArtifactContext,
        query: str
    ) -> List[ArtifactExecution]:
        """Resolve time-based references like 'just', 'last', 'earlier'."""
        query_lower = query.lower()

        # "just", "last", "latest", "recent"
        if any(word in query_lower for word in ["just", "last", "latest", "recent"]):
            if context.last_execution:
                return [context.last_execution]

        # "earlier", "previous", "before"
        if any(word in query_lower for word in ["earlier", "previous", "before"]):
            recent = context.get_recent_executions(limit=2)
            if len(recent) > 1:
                return [recent[1]]  # Second to last

        return []

    def _resolve_content_reference(
        self,
        context: ArtifactContext,
        query: str
    ) -> List[ArtifactExecution]:
        """Resolve content-based references (file names, paths, etc.)."""
        referenced = []

        # Extract potential file names/paths
        # Matches: word.ext, path/to/file.ext, "quoted/file.ext"
        file_patterns = [
            r'\b(\w+\.\w+)\b',           # Simple file.ext
            r'\b([\w/.-]+\.\w+)\b',       # path/file.ext
            r'"([^"]+)"',                 # "quoted path"
            r"'([^']+)'",                 # 'quoted path'
        ]

        mentioned_items = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, query)
            mentioned_items.update(matches)

        # Find executions involving these items
        for exec in reversed(context.executions):
            # Check path argument
            if 'path' in exec.tool_args:
                path = exec.tool_args['path']
                if any(item in path for item in mentioned_items):
                    referenced.append(exec)
                    continue

            # Check other string arguments
            for arg_value in exec.tool_args.values():
                if isinstance(arg_value, str):
                    if any(item in arg_value for item in mentioned_items):
                        referenced.append(exec)
                        break

        return referenced[:5]  # Limit to 5 matches

    def _resolve_tool_reference(
        self,
        context: ArtifactContext,
        query: str
    ) -> List[ArtifactExecution]:
        """Resolve tool-based references like 'what I listed', 'the code I ran'."""
        query_lower = query.lower()

        tool_keywords = {
            "list": ["builtin.list_files", "builtin.list_directories"],
            "listed": ["builtin.list_files", "builtin.list_directories"],
            "read": ["builtin.read_file"],
            "loaded": ["builtin.read_file"],
            "opened": ["builtin.read_file"],
            "wrote": ["builtin.write_file", "builtin.patch_file"],
            "written": ["builtin.write_file", "builtin.patch_file"],
            "executed": ["builtin.execute_python_code", "builtin.execute_bash_command"],
            "ran": ["builtin.execute_python_code", "builtin.execute_bash_command", "builtin.run_pytest"],
            "test": ["builtin.run_pytest"],
            "tested": ["builtin.run_pytest"],
        }

        for keyword, tools in tool_keywords.items():
            if keyword in query_lower:
                matches = [
                    exec for exec in reversed(context.executions)
                    if exec.tool_name in tools
                ]
                if matches:
                    return matches[:3]  # Return up to 3 most recent

        return []

    def _create_summary(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: str
    ) -> str:
        """Create a brief summary of the execution."""
        # Tool-specific summaries
        if "read_file" in tool_name:
            path = tool_args.get('path', 'unknown')
            size_kb = len(tool_result) / 1024
            return f"Loaded {path} ({size_kb:.1f} KB)"

        elif "write_file" in tool_name or "patch_file" in tool_name:
            path = tool_args.get('path', 'unknown')
            return f"Wrote to {path}"

        elif "list_files" in tool_name or "list_directories" in tool_name:
            path = tool_args.get('path', '.')
            lines = tool_result.split('\n')
            count = len([line for line in lines if line.strip()])
            return f"Listed {count} items in {path}"

        elif "execute_python" in tool_name:
            return "Executed Python code"

        elif "execute_bash" in tool_name:
            command = tool_args.get('command', '')
            cmd_preview = command[:30] + '...' if len(command) > 30 else command
            return f"Executed command: {cmd_preview}"

        elif "run_pytest" in tool_name:
            return "Ran pytest tests"

        else:
            # Generic summary
            tool_display = tool_name.replace('builtin.', '').replace('_', ' ').title()
            return f"Executed {tool_display}"

    def _format_time_ago(self, timestamp: datetime) -> str:
        """Format timestamp as 'X ago' string."""
        delta = datetime.now() - timestamp

        if delta < timedelta(seconds=10):
            return "just now"
        elif delta < timedelta(minutes=1):
            secs = int(delta.total_seconds())
            return f"{secs} seconds ago"
        elif delta < timedelta(hours=1):
            mins = int(delta.total_seconds() / 60)
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = delta.days
            return f"{days} day{'s' if days != 1 else ''} ago"

    def _truncate_result(self, result: str, max_size: int = 5000) -> str:
        """Truncate large results."""
        if len(result) <= max_size:
            return result

        # Show first portion with ellipsis
        keep_size = max_size - 100  # Leave room for message
        truncated = result[:keep_size]
        total_size_kb = len(result) / 1024

        return f"{truncated}\n\n... (truncated, total size: {total_size_kb:.1f} KB)"

    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of the current context.

        Useful for debugging or displaying context status in UI.

        Args:
            session_id: The session ID

        Returns:
            Dictionary with context summary
        """
        context = self.get_or_create_context(session_id)

        return {
            "session_id": session_id,
            "total_executions": len(context.executions),
            "recent_files": context.recent_files,
            "recent_tools": context.recent_tools,
            "last_execution": {
                "execution_id": context.last_execution.execution_id,
                "tool": context.last_execution.tool_name,
                "summary": context.last_execution.result_summary,
                "timestamp": context.last_execution.timestamp.isoformat(),
            } if context.last_execution else None,
        }

    def clear_context(self, session_id: str):
        """Clear all context for a session."""
        if session_id in self.contexts:
            del self.contexts[session_id]
