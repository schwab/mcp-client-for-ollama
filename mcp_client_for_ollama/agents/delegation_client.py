"""
Delegation client for agent-based task execution.

This module provides the main DelegationClient class that orchestrates
the delegation workflow: planning, task execution, and result aggregation.
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Set
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .task import Task, TaskStatus
from .agent_config import AgentConfig
from .model_pool import ModelPool


class DelegationClient:
    """
    Main orchestrator for the agent delegation system.

    The DelegationClient wraps an MCPClient instance and provides
    agent-based task delegation capabilities. It breaks down complex
    queries into subtasks, executes them with specialized agents,
    and aggregates the results.

    Phase 1 (MVP): Sequential task execution
    Future phases: Parallel execution with dependency resolution

    Usage:
        delegation_client = DelegationClient(mcp_client, config)
        result = await delegation_client.process_with_delegation(user_query)
    """

    def __init__(self, mcp_client, config: Dict[str, Any]):
        """
        Initialize the delegation client.

        Args:
            mcp_client: The MCPClient instance to use for model interactions
            config: Delegation configuration containing:
                - planner_model: Optional model name for planning (falls back to current)
                - model_pool: List of model endpoint configurations
                - execution_mode: "sequential" or "parallel" (default: "parallel")
                - max_parallel_tasks: Maximum concurrent LLM calls (default: 3)
                - task_timeout: Task execution timeout in seconds (default: 300)
        """
        self.mcp_client = mcp_client
        self.config = config
        self.console = Console()

        # Load agent definitions from JSON files
        self.agent_configs = AgentConfig.load_all_definitions()

        # Initialize model pool (even for sequential execution)
        model_pool_config = config.get('model_pool', [])
        if not model_pool_config:
            # Default to current client's Ollama instance
            model_pool_config = [{
                'url': mcp_client.host,
                'model': mcp_client.model_manager.current_model or 'qwen2.5:7b',
                'max_concurrent': 1
            }]
        self.model_pool = ModelPool(model_pool_config)

        # Parallelism control
        max_parallel = config.get('max_parallel_tasks', 3)
        self._parallelism_semaphore = asyncio.Semaphore(max_parallel)

        # Task tracking
        self.tasks: Dict[str, Task] = {}
        self.task_counter = 0

    async def process_with_delegation(self, user_query: str) -> str:
        """
        Process a query using the agent delegation system.

        This is the main entry point for delegated execution.

        Args:
            user_query: The user's question or request

        Returns:
            Final aggregated response from all tasks

        Raises:
            Exception: If planning or execution fails
        """
        self.console.print("\n[bold cyan]🤖 Agent Delegation Mode[/bold cyan]")
        self.console.print(f"[dim]Query: {user_query}[/dim]\n")

        try:
            # Phase 1: Planning
            self.console.print("[bold yellow]📋 Planning Phase[/bold yellow]")
            task_plan = await self.create_plan(user_query)

            if not task_plan or not task_plan.get('tasks'):
                self.console.print("[yellow]⚠️  Planner returned no tasks. Falling back to direct execution.[/yellow]")
                return await self._fallback_direct_execution(user_query)

            # Phase 2: Create task objects
            tasks = self.create_tasks_from_plan(task_plan)
            self.console.print(f"[green]✓[/green] Created {len(tasks)} tasks\n")

            # Phase 3: Execute tasks (parallel by default, fallback to sequential)
            self.console.print("[bold yellow]⚙️  Execution Phase[/bold yellow]")
            execution_mode = self.config.get('execution_mode', 'parallel')

            if execution_mode == 'parallel':
                results = await self.execute_tasks_parallel(tasks)
            else:
                results = await self.execute_tasks_sequential(tasks)

            # Phase 4: Aggregate results
            self.console.print("\n[bold yellow]📊 Aggregation Phase[/bold yellow]")
            final_answer = await self.aggregate_results(user_query, results)

            return final_answer

        except Exception as e:
            self.console.print(f"[bold red]❌ Delegation failed: {e}[/bold red]")
            self.console.print("[yellow]Falling back to direct execution...[/yellow]")
            return await self._fallback_direct_execution(user_query)

    async def create_plan(self, query: str) -> Dict[str, Any]:
        """
        Use the planner agent to decompose the query into tasks.

        Args:
            query: User's original query

        Returns:
            Task plan as a dictionary with 'tasks' key containing task definitions

        Raises:
            Exception: If planning fails or planner output is invalid
        """
        planner_config = self.agent_configs.get('PLANNER')
        if not planner_config:
            raise Exception("PLANNER agent configuration not found")

        # Build planning context
        available_agents = [
            f"- {agent_type}: {config.description}"
            for agent_type, config in self.agent_configs.items()
            if agent_type != 'PLANNER'
        ]

        planning_prompt = f"""
{planner_config.system_prompt}

Available agents:
{chr(10).join(available_agents)}

User request:
{query}

Please break this down into focused subtasks. Output valid JSON only.
"""

        # Get planner model (configurable or fallback to current)
        planner_model = self.config.get('planner_model') or self.mcp_client.model_manager.get_current_model()

        # Execute planning with minimal tools
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Planning with {planner_model}...", total=None)

            # Build messages for planner
            messages = [{"role": "user", "content": planning_prompt}]

            # Get available tools for planner
            available_tool_names = self._get_available_tool_names()
            planner_tool_names = planner_config.get_effective_tools(available_tool_names)
            planner_tool_objects = self._get_tool_objects(planner_tool_names)

            # Execute planning (planner usually doesn't need tools, just JSON output)
            response_text = await self._execute_with_tools(
                messages=messages,
                model=planner_model,
                temperature=planner_config.temperature,
                tools=planner_tool_objects,
                loop_limit=planner_config.loop_limit
            )

            progress.update(task, completed=True)

        # Parse JSON from response
        task_plan = self._extract_json_from_response(response_text)

        # Validate plan structure
        if not isinstance(task_plan, dict) or 'tasks' not in task_plan:
            raise Exception(f"Invalid plan structure. Expected dict with 'tasks' key, got: {type(task_plan)}")

        # Display plan
        self._display_plan(task_plan)

        return task_plan

    def create_tasks_from_plan(self, task_plan: Dict[str, Any]) -> List[Task]:
        """
        Convert task plan JSON into Task objects.

        Args:
            task_plan: Dictionary containing 'tasks' array

        Returns:
            List of Task objects ready for execution
        """
        tasks = []

        for task_def in task_plan['tasks']:
            task_id = task_def.get('id', f"task_{self.task_counter}")
            self.task_counter += 1

            task = Task(
                id=task_id,
                description=task_def['description'],
                agent_type=task_def['agent_type'],
                dependencies=task_def.get('dependencies', []),
            )

            tasks.append(task)
            self.tasks[task_id] = task

        return tasks

    async def execute_tasks_sequential(self, tasks: List[Task]) -> List[Task]:
        """
        Execute tasks sequentially, respecting dependencies.

        MVP implementation: Simple sequential execution in dependency order.

        Args:
            tasks: List of tasks to execute

        Returns:
            List of completed tasks (some may have failed)
        """
        completed_ids = set()
        failed_ids = set()

        # Sort tasks by dependencies (topological sort)
        sorted_tasks = self._topological_sort(tasks)

        for task in sorted_tasks:
            # Check if dependencies are satisfied
            if not task.can_execute(completed_ids):
                self.console.print(f"[yellow]⏸️  Task {task.id} blocked by failed dependencies[/yellow]")
                task.mark_blocked()
                continue

            # Execute task
            self.console.print(f"\n[cyan]▶️  Executing {task.id} ({task.agent_type})[/cyan]")
            self.console.print(f"[dim]   {task.description}[/dim]")

            try:
                await self.execute_single_task(task)
                completed_ids.add(task.id)
                self.console.print(f"[green]✓[/green] {task.id} completed")

            except Exception as e:
                failed_ids.add(task.id)
                task.mark_failed(str(e))
                self.console.print(f"[red]✗[/red] {task.id} failed: {e}")

        return sorted_tasks

    async def execute_tasks_parallel(self, tasks: List[Task]) -> List[Task]:
        """
        Execute tasks in parallel, respecting dependencies and concurrency limits.

        Tasks are executed in "waves" where each wave contains independent tasks
        that can run concurrently. The max_parallel_tasks config limits how many
        LLM calls can run simultaneously.

        Args:
            tasks: List of tasks to execute

        Returns:
            List of completed tasks (some may have failed)
        """
        completed_ids: Set[str] = set()
        failed_ids: Set[str] = set()
        pending_tasks = list(tasks)  # Use list, not set (Tasks aren't hashable)

        # Sort tasks by dependencies for efficient wave detection
        sorted_tasks = self._topological_sort(tasks)

        wave_number = 1

        while pending_tasks:
            # Find tasks that can execute in this wave
            ready_tasks = [
                t for t in pending_tasks
                if t.can_execute(completed_ids)
            ]

            if not ready_tasks:
                # No tasks can execute - remaining tasks are blocked
                for task in pending_tasks:
                    task.mark_blocked()
                    self.console.print(
                        f"[yellow]⏸️  Task {task.id} blocked by failed dependencies[/yellow]"
                    )
                break

            # Display wave info
            if len(ready_tasks) > 1:
                self.console.print(
                    f"\n[bold magenta]🌊 Wave {wave_number}: Executing {len(ready_tasks)} tasks in parallel[/bold magenta]"
                )
            else:
                self.console.print(f"\n[bold magenta]🌊 Wave {wave_number}[/bold magenta]")

            # Execute ready tasks in parallel with semaphore limiting concurrency
            wave_results = await self._execute_wave(ready_tasks)

            # Process results
            for task, success in wave_results:
                pending_tasks.remove(task)

                if success:
                    completed_ids.add(task.id)
                    self.console.print(f"[green]✓[/green] {task.id} completed")
                else:
                    failed_ids.add(task.id)
                    self.console.print(f"[red]✗[/red] {task.id} failed")

            wave_number += 1

        return sorted_tasks

    async def _execute_wave(self, ready_tasks: List[Task]) -> List[tuple[Task, bool]]:
        """
        Execute a wave of independent tasks in parallel with concurrency control.

        Args:
            ready_tasks: Tasks that are ready to execute (dependencies satisfied)

        Returns:
            List of (task, success) tuples
        """
        async def execute_with_semaphore(task: Task) -> tuple[Task, bool]:
            """Execute a single task with semaphore-controlled concurrency."""
            async with self._parallelism_semaphore:
                self.console.print(f"\n[cyan]▶️  Executing {task.id} ({task.agent_type})[/cyan]")
                self.console.print(f"[dim]   {task.description}[/dim]")

                try:
                    await self.execute_single_task(task)
                    return (task, True)
                except Exception as e:
                    task.mark_failed(str(e))
                    self.console.print(f"[red]   Error: {e}[/red]")
                    return (task, False)

        # Execute all tasks in this wave concurrently (semaphore limits actual parallelism)
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in ready_tasks],
            return_exceptions=False
        )

        return results

    async def execute_single_task(self, task: Task):
        """
        Execute a single task with the appropriate agent configuration.

        Args:
            task: The task to execute

        Raises:
            Exception: If task execution fails
        """
        # Get agent configuration
        agent_config = self.agent_configs.get(task.agent_type)
        if not agent_config:
            raise Exception(f"Unknown agent type: {task.agent_type}")

        # Acquire model from pool
        endpoint = await self.model_pool.wait_for_available(
            timeout=self.config.get('task_timeout', 300)
        )

        task.mark_started(endpoint.url)

        try:
            # Build task context
            messages = self._build_task_context(task, agent_config)

            # Get tools for this agent
            available_tool_names = self._get_available_tool_names()
            agent_tool_names = agent_config.get_effective_tools(available_tool_names)

            # Get actual tool objects
            agent_tools = self._get_tool_objects(agent_tool_names)

            # Execute with tool support enabled
            response_text = await self._execute_with_tools(
                messages=messages,
                model=endpoint.model,
                temperature=agent_config.temperature,
                tools=agent_tools,
                loop_limit=agent_config.loop_limit
            )

            # Store result
            task.mark_completed(response_text)

        except Exception as e:
            task.mark_failed(str(e))
            raise

        finally:
            # Release endpoint back to pool
            success = task.status == TaskStatus.COMPLETED
            await self.model_pool.release(endpoint, success=success)

    async def aggregate_results(self, original_query: str, tasks: List[Task]) -> str:
        """
        Aggregate results from all tasks into a final answer.

        Args:
            original_query: The user's original question
            tasks: List of executed tasks with results

        Returns:
            Final synthesized response
        """
        # Collect successful task results
        successful_results = [
            f"**{task.id}** ({task.agent_type}):\n{task.result}"
            for task in tasks
            if task.status == TaskStatus.COMPLETED and task.result
        ]

        if not successful_results:
            return "No tasks completed successfully. Unable to provide a response."

        # For MVP: Simple concatenation
        # Future: Use an aggregator agent to synthesize
        aggregated = f"""
Based on the delegated task execution, here are the results:

{chr(10).join(successful_results)}

---
Summary: {len(successful_results)} of {len(tasks)} tasks completed successfully.
"""

        self.console.print("[green]✓[/green] Results aggregated")
        return aggregated

    def _build_task_context(self, task: Task, agent_config: AgentConfig) -> List[Dict[str, str]]:
        """
        Build the message context for a task.

        Includes:
        - Agent's system prompt
        - Results from dependency tasks (shared read)
        - Task description

        Args:
            task: The task to build context for
            agent_config: Agent configuration

        Returns:
            List of message dictionaries
        """
        messages = []

        # System prompt
        messages.append({
            "role": "system",
            "content": agent_config.system_prompt
        })

        # Add dependency results (shared read strategy)
        dependency_results = task.get_dependency_results(self.tasks)
        if dependency_results:
            context_text = "Context from previous tasks:\n\n" + "\n".join(dependency_results)
            messages.append({
                "role": "user",
                "content": context_text
            })

        # Task description
        messages.append({
            "role": "user",
            "content": f"Your task:\n{task.description}"
        })

        return messages

    async def _execute_with_tools(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        tools: List,
        loop_limit: int
    ) -> str:
        """
        Execute a query with tool support (full agent capabilities).

        Args:
            messages: Message history
            model: Model name to use
            temperature: Sampling temperature
            tools: List of tool objects available to this agent
            loop_limit: Maximum tool call iterations

        Returns:
            Final response text from the model
        """
        # Format tools for Ollama API
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in tools] if tools else []

        # Ollama options
        options = {
            "temperature": temperature,
            "num_ctx": self.config.get('max_context_tokens', 8192),
        }

        # Initial call with tools
        stream = await self.mcp_client.ollama.chat(
            model=model,
            messages=messages,
            stream=True,
            tools=available_tools,
            options=options
        )

        # Process streaming response
        response_text, tool_calls, metrics = await self.mcp_client.streaming_manager.process_streaming_response(
            stream,
            thinking_mode=False,
            show_thinking=False,
            show_metrics=False
        )

        # Debug: Check if tool calls were detected
        if tool_calls:
            self.console.print(f"[dim cyan]🔧 Detected {len(tool_calls)} tool call(s)[/dim cyan]")
        elif response_text and ("builtin." in response_text or "arguments" in response_text):
            self.console.print(f"[yellow]⚠️  Model generated tool-like text but no tool_calls detected[/yellow]")
            self.console.print(f"[dim]Response preview: {response_text[:200]}...[/dim]")

        # Add assistant response to messages
        messages.append({
            "role": "assistant",
            "content": response_text,
            "tool_calls": tool_calls
        })

        # Handle tool calls in a loop
        loop_count = 0
        pending_tool_calls = tool_calls

        while pending_tool_calls and loop_count < loop_limit:
            loop_count += 1

            for tool_call in pending_tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments

                # Execute tool
                tool_response = await self._execute_tool(tool_name, tool_args)

                # Add tool response to messages
                messages.append({
                    "role": "tool",
                    "content": tool_response,
                    "tool_name": tool_name
                })

            # Get next response from model
            stream = await self.mcp_client.ollama.chat(
                model=model,
                messages=messages,
                stream=True,
                tools=available_tools,
                options=options
            )

            # Process response
            response_text, tool_calls, metrics = await self.mcp_client.streaming_manager.process_streaming_response(
                stream,
                thinking_mode=False,
                show_thinking=False,
                show_metrics=False
            )

            # Add to messages
            messages.append({
                "role": "assistant",
                "content": response_text,
                "tool_calls": tool_calls
            })

            pending_tool_calls = tool_calls

        return response_text.strip()

    async def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        """
        Execute a tool call (builtin or MCP server tool).

        Args:
            tool_name: Fully qualified tool name (e.g., "builtin.read_file")
            tool_args: Tool arguments

        Returns:
            Tool execution result
        """
        # Parse server name and actual tool name
        server_name, actual_tool_name = tool_name.split('.', 1) if '.' in tool_name else (None, tool_name)

        # Handle builtin tools
        if server_name == "builtin":
            return self.mcp_client.builtin_tool_manager.execute_tool(actual_tool_name, tool_args)

        # Handle MCP server tools
        if server_name and server_name in self.mcp_client.sessions:
            result = await self.mcp_client.sessions[server_name]["session"].call_tool(actual_tool_name, tool_args)
            if result.content:
                return result.content[0].text
            return "No tool response found."

        return f"Error: Unknown tool {tool_name}"

    def _get_available_tool_names(self) -> List[str]:
        """Get list of all available tool names from MCP client."""
        available_tools = []

        # Get builtin tools
        if self.mcp_client.builtin_tool_manager:
            builtin_tool_objects = self.mcp_client.builtin_tool_manager.get_builtin_tools()
            available_tools.extend([tool.name for tool in builtin_tool_objects])

        # Get MCP server tools
        if self.mcp_client.tool_manager:
            enabled_tools = self.mcp_client.tool_manager.get_enabled_tools()
            available_tools.extend(enabled_tools.keys())

        return available_tools

    def _get_tool_objects(self, tool_names: List[str]) -> List:
        """
        Get actual Tool objects for the given tool names.

        Args:
            tool_names: List of tool names to get objects for

        Returns:
            List of Tool objects
        """
        tool_objects = []

        # Get builtin tools
        if self.mcp_client.builtin_tool_manager:
            builtin_tools = self.mcp_client.builtin_tool_manager.get_builtin_tools()
            for tool in builtin_tools:
                if tool.name in tool_names:
                    tool_objects.append(tool)

        # Get MCP server tools
        if self.mcp_client.tool_manager:
            enabled_tool_objects = self.mcp_client.tool_manager.get_enabled_tool_objects()
            for tool in enabled_tool_objects:
                if tool.name in tool_names:
                    tool_objects.append(tool)

        return tool_objects

    def _extract_json_from_response(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON object from model response.

        Handles cases where JSON is wrapped in markdown code blocks or
        surrounded by extra text.

        Args:
            text: Response text potentially containing JSON

        Returns:
            Parsed JSON object

        Raises:
            Exception: If no valid JSON found
        """
        # Try to find JSON in code blocks first
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_block_pattern, text, re.DOTALL)

        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        brace_start = text.find('{')
        brace_end = text.rfind('}')

        if brace_start != -1 and brace_end != -1:
            json_str = text[brace_start:brace_end + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Last resort: try parsing the whole thing
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise Exception(f"Could not extract valid JSON from response: {text[:200]}...")

    def _topological_sort(self, tasks: List[Task]) -> List[Task]:
        """
        Sort tasks by dependencies using topological sort.

        Args:
            tasks: List of tasks to sort

        Returns:
            Tasks sorted such that dependencies come before dependents

        Raises:
            Exception: If circular dependencies detected
        """
        # Build dependency graph
        graph = {task.id: task.dependencies for task in tasks}
        task_map = {task.id: task for task in tasks}

        # Kahn's algorithm for topological sort
        in_degree = {task_id: 0 for task_id in graph}
        for task_id, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[task_id] += 1

        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        sorted_ids = []

        while queue:
            task_id = queue.pop(0)
            sorted_ids.append(task_id)

            # Reduce in-degree for dependent tasks
            for other_id, deps in graph.items():
                if task_id in deps:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)

        if len(sorted_ids) != len(tasks):
            raise Exception("Circular dependencies detected in task plan")

        return [task_map[task_id] for task_id in sorted_ids]

    def _display_plan(self, task_plan: Dict[str, Any]):
        """Display the task plan in a formatted panel."""
        plan_text = ""
        for i, task_def in enumerate(task_plan['tasks'], 1):
            deps = task_def.get('dependencies', [])
            deps_str = f" (depends on: {', '.join(deps)})" if deps else ""
            plan_text += f"{i}. [{task_def['agent_type']}] {task_def['description']}{deps_str}\n"

        self.console.print(Panel(
            plan_text.strip(),
            title="[bold]Task Plan[/bold]",
            border_style="cyan"
        ))

    async def _fallback_direct_execution(self, query: str) -> str:
        """
        Fallback to direct MCPClient execution if delegation fails.

        Args:
            query: User's original query

        Returns:
            Response from direct execution
        """
        return await self.mcp_client.process_query(query)
