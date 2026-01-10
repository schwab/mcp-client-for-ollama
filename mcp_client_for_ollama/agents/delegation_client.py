"""
Delegation client for agent-based task execution.

This module provides the main DelegationClient class that orchestrates
the delegation workflow: planning, task execution, and result aggregation.
"""

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .task import Task, TaskStatus
from .agent_config import AgentConfig
from .model_pool import ModelPool
from ..utils.collapsible_output import CollapsibleOutput, TaskOutputCollector
from ..utils.trace_logger import TraceLogger, TraceLoggerFactory, TraceLevel
from ..memory import (
    MemoryInitializer,
    InitializerPromptBuilder,
    DomainMemory,
    MemoryStorage,
    BootRitual,
    MemoryTools,
)


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
                - context_depth: Number of previous exchanges to include for context (default: 3)
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
                'model': mcp_client.model_manager.get_current_model() or 'qwen2.5:7b',
                'max_concurrent': 1
            }]
        self.model_pool = ModelPool(model_pool_config)

        # Parallelism control
        max_parallel = config.get('max_parallel_tasks', 3)
        self._parallelism_semaphore = asyncio.Semaphore(max_parallel)

        # Task tracking
        self.tasks: Dict[str, Task] = {}
        self.task_counter = 0

        # Chat history for context (passed per-request)
        self.chat_history: List[Dict] = []

        # Load planning examples for few-shot learning
        self.planner_examples = self._load_planner_examples()

        # Initialize trace logger
        self.trace_logger = TraceLoggerFactory.from_config(config)

        # Initialize collapsible output
        collapsible_config = config.get('collapsible_output', {})
        self.collapsible = CollapsibleOutput(
            console=self.console,
            line_threshold=collapsible_config.get('line_threshold', 20),
            char_threshold=collapsible_config.get('char_threshold', 1000),
            auto_collapse=collapsible_config.get('auto_collapse', True)
        )
        self.task_output = TaskOutputCollector(self.console, self.collapsible)

        # Initialize memory system (Phase 2 & 3)
        memory_config = config.get('memory', {})
        self.memory_enabled = memory_config.get('enabled', False)
        if self.memory_enabled:
            self.memory_storage = MemoryStorage(
                base_dir=Path(memory_config.get('storage_dir', '~/.mcp-memory')).expanduser()
            )
            self.memory_initializer = MemoryInitializer(self.memory_storage)
            self.memory_tools = MemoryTools(self.memory_storage)
            self.current_memory: Optional[DomainMemory] = None
            self.default_domain = memory_config.get('default_domain', 'coding')
        else:
            self.memory_storage = None
            self.memory_initializer = None
            self.memory_tools = None
            self.current_memory = None

    @staticmethod
    def _load_shared_prompt(filename: str) -> str:
        """
        Load a shared prompt component from the shared_prompts directory.

        Args:
            filename: Name of the shared prompt file (e.g., 'tool_protocol.txt')

        Returns:
            Content of the shared prompt file, or empty string if not found
        """
        try:
            prompt_path = Path(__file__).parent / "shared_prompts" / filename
            if not prompt_path.exists():
                return ""
            return prompt_path.read_text()
        except Exception:
            # Silently fail - shared prompts are optional enhancements
            return ""

    def _load_planner_examples(self) -> List[Dict[str, Any]]:
        """
        Load planning examples from the examples directory for few-shot learning.

        Returns:
            List of example planning scenarios, or empty list if file not found
        """
        try:
            examples_path = Path(__file__).parent / "examples" / "planner_examples.json"
            if not examples_path.exists():
                return []

            with open(examples_path, 'r') as f:
                data = json.load(f)
                return data.get('examples', [])
        except Exception as e:
            # Don't fail if examples can't be loaded, just log and continue
            self.console.print(f"[dim yellow]Note: Could not load planner examples: {e}[/dim yellow]")
            return []

    def _select_relevant_examples(self, query: str, max_examples: int = 2) -> List[Dict[str, Any]]:
        """
        Select the most relevant planning examples for the given query.

        Uses keyword matching to find examples from similar task categories.

        Args:
            query: The user's query
            max_examples: Maximum number of examples to return

        Returns:
            List of relevant example dictionaries
        """
        if not self.planner_examples:
            return []

        # Category keywords for matching
        category_keywords = {
            'multi-file-read': ['read', 'scan', 'list', 'show', 'summarize', 'files', 'all'],
            'code-modification': ['add', 'modify', 'update', 'change', 'implement', 'create'],
            'debugging': ['fix', 'bug', 'error', 'issue', 'broken', 'debug', 'investigate'],
            'refactoring': ['refactor', 'restructure', 'reorganize', 'clean', 'improve'],
            'testing': ['test', 'verify', 'check', 'validate', 'coverage'],
            'research': ['understand', 'how does', 'explain', 'analyze', 'find', 'search'],
            'documentation': ['document', 'doc', 'readme', 'api doc', 'write doc'],
            'feature-implementation': ['add feature', 'implement', 'new feature'],
            'music-creation': ['song', 'lyrics', 'music', 'suno', 'write song'],
            'note-taking': ['obsidian', 'note', 'markdown note', 'create note'],
            'analysis-with-execution': ['profile', 'benchmark', 'performance', 'analyze'],
            'simple-read': ['what does', 'what is', 'show me', 'read'],
            'simple-execute': ['run', 'execute', 'test suite'],
            'bug-investigation': ['investigate', 'debug', 'error', '500', 'failure'],
            'parallel-independent': ['and', 'both', 'generate and', 'write and'],
            'mcp-tool-with-specific-data': ['append', 'add to', 'update with', 'insert', 'get note', 'modify note'],
            'bulk-file-processing': ['all files', 'multiple files', 'each file', 'list files', 'all .md', 'all .py', 'check files']
        }

        # Score each example by keyword relevance
        query_lower = query.lower()
        query_words = set(query_lower.split())
        scored_examples = []

        for example in self.planner_examples:
            score = 0
            category = example.get('category', '')

            # Exact category match bonus
            if category in query_lower:
                score += 10

            # Keyword matching
            keywords = category_keywords.get(category, [])
            for keyword in keywords:
                if keyword in query_lower:
                    score += 2
                # Partial word match
                if any(keyword in word for word in query_words):
                    score += 1

            scored_examples.append((score, example))

        # Sort by score (highest first) and take top examples
        scored_examples.sort(reverse=True, key=lambda x: x[0])

        # Filter to only examples with score > 0, or take simple examples as fallback
        relevant = [ex for score, ex in scored_examples if score > 0][:max_examples]

        # If no relevant examples found, provide simple examples as fallback
        if not relevant and self.planner_examples:
            simple_categories = ['simple-read', 'simple-execute']
            relevant = [ex for ex in self.planner_examples
                       if ex.get('category') in simple_categories][:max_examples]

        return relevant

    async def process_with_delegation(self, user_query: str, chat_history: List[Dict] = None) -> str:
        """
        Process a query using the agent delegation system.

        This is the main entry point for delegated execution.

        Args:
            user_query: The user's question or request
            chat_history: Optional list of previous chat exchanges for context

        Returns:
            Final aggregated response from all tasks

        Raises:
            Exception: If planning or execution fails
        """
        # Store chat history for use in planning
        self.chat_history = chat_history or []
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

            # Note: Trace summary is now printed at the end with memory progress summary
            return final_answer

        except Exception as e:
            self.console.print(f"[bold red]❌ Delegation failed: {e}[/bold red]")
            self.console.print("[yellow]Falling back to direct execution...[/yellow]")

            # Note: Trace summary is printed at the end with memory progress summary
            return await self._fallback_direct_execution(user_query)

    async def process_with_memory(
        self,
        user_query: str,
        chat_history: List[Dict] = None,
        session_id: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> str:
        """
        Process a query with persistent domain memory (Phase 2).

        This method implements the Anthropic memory pattern:
        1. If new session: Use INITIALIZER agent to bootstrap memory
        2. If resuming: Load existing memory
        3. Execute tasks with memory context (Phase 3 - future)
        4. Update memory after execution (Phase 3 - future)

        Args:
            user_query: The user's question or request
            chat_history: Optional list of previous chat exchanges
            session_id: Optional session ID to resume
            domain: Optional domain type (coding, research, etc.). Defaults to config.

        Returns:
            Final aggregated response

        Raises:
            Exception: If initialization or execution fails
        """
        if not self.memory_enabled:
            # Memory not enabled, fall back to regular delegation
            return await self.process_with_delegation(user_query, chat_history)

        domain = domain or self.default_domain
        self.chat_history = chat_history or []

        self.console.print("\n[bold cyan]🧠 Memory-Aware Agent Mode[/bold cyan]")
        self.console.print(f"[dim]Domain: {domain}[/dim]")
        self.console.print(f"[dim]Query: {user_query}[/dim]\n")

        try:
            # Phase 0: Memory Setup
            self.console.print("[bold magenta]🔮 Memory Setup Phase[/bold magenta]")

            # Try to resume existing session or detect if new
            if session_id:
                # Explicit session ID provided - try to resume
                if self.memory_storage.session_exists(session_id, domain):
                    self.current_memory = self.memory_storage.load_memory(session_id, domain)
                    self.console.print(f"[green]✓[/green] Resumed session: {session_id}")
                    self.console.print(f"[dim]  {len(self.current_memory.goals)} goals, "
                                     f"{self.current_memory.get_completion_percentage():.1f}% complete[/dim]\n")
                else:
                    self.console.print(f"[yellow]⚠️  Session {session_id} not found. Creating new session.[/yellow]")
                    session_id = None

            if not self.current_memory:
                # New session - use INITIALIZER to bootstrap memory
                self.console.print("[yellow]Initializing new memory session...[/yellow]")

                # Build prompt for INITIALIZER
                initializer_prompt = InitializerPromptBuilder.build_prompt(
                    user_query=user_query,
                    domain=domain,
                )

                # Run INITIALIZER agent
                initializer_output = await self._run_initializer(initializer_prompt)

                if not initializer_output:
                    self.console.print("[yellow]⚠️  Memory initialization failed. Falling back to regular delegation.[/yellow]")
                    return await self.process_with_delegation(user_query, chat_history)

                # Bootstrap memory from INITIALIZER output
                self.current_memory = self.memory_initializer.initialize_and_save(
                    initializer_output,
                    session_id=session_id,
                )

                session_id = self.current_memory.metadata.session_id
                self.console.print(f"[green]✓[/green] Created session: {session_id}")
                self.console.print(f"[dim]  {len(self.current_memory.goals)} goals, "
                                 f"{len(self.current_memory.get_all_features())} features[/dim]\n")

            # Store session ID for reference
            self.console.print(f"[bold]Session ID:[/bold] {self.current_memory.metadata.session_id}")
            self.console.print(f"[bold]Domain:[/bold] {self.current_memory.metadata.domain}")
            self.console.print(f"[bold]Description:[/bold] {self.current_memory.metadata.description}\n")

            # Phase 3: Set current session for memory tools
            self.memory_tools.set_current_session(
                self.current_memory.metadata.session_id,
                self.current_memory.metadata.domain
            )

            # Phase 3: Worker agents will now read memory context before acting
            result = await self.process_with_delegation(user_query, chat_history)

            # Phase 3: Save updated memory after execution
            self.memory_storage.save_memory(self.current_memory)

            return result

        except Exception as e:
            self.console.print(f"[bold red]❌ Memory-aware processing failed: {e}[/bold red]")
            self.console.print("[yellow]Falling back to regular delegation...[/yellow]")
            return await self.process_with_delegation(user_query, chat_history)

    async def _run_initializer(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Run the INITIALIZER agent to bootstrap domain memory.

        Args:
            prompt: The prompt for INITIALIZER

        Returns:
            Parsed JSON output from INITIALIZER, or None if failed
        """
        try:
            # Get INITIALIZER agent config
            initializer_config = self.agent_configs.get("INITIALIZER")
            if not initializer_config:
                self.console.print("[red]ERROR: INITIALIZER agent not found[/red]")
                return None

            # Build context for INITIALIZER
            context = [
                {"role": "system", "content": initializer_config.system_prompt},
                {"role": "user", "content": prompt}
            ]

            # Get available tools for INITIALIZER
            # Build list of all available tool names
            available_tool_names = []

            # Add builtin tools
            if self.mcp_client.builtin_tool_manager:
                builtin_tools = self.mcp_client.builtin_tool_manager.get_builtin_tools()
                available_tool_names.extend([tool.name for tool in builtin_tools])

            # Add MCP server tools
            if self.mcp_client.tool_manager:
                mcp_tools = self.mcp_client.tool_manager.get_enabled_tool_objects()
                available_tool_names.extend([tool.name for tool in mcp_tools])

            # Get the effective tools for this agent (filtered by agent config)
            tool_names = initializer_config.get_effective_tools(available_tool_names)

            # Convert tool names to Tool objects
            tools = []

            # Get builtin tool objects
            if self.mcp_client.builtin_tool_manager:
                builtin_tools = self.mcp_client.builtin_tool_manager.get_builtin_tools()
                for tool in builtin_tools:
                    if tool.name in tool_names:
                        tools.append(tool)

            # Get MCP tool objects
            if self.mcp_client.tool_manager:
                mcp_tools = self.mcp_client.tool_manager.get_enabled_tool_objects()
                for tool in mcp_tools:
                    if tool.name in tool_names:
                        tools.append(tool)

            # Get model for INITIALIZER
            initializer_model = initializer_config.model or self.mcp_client.model_manager.get_current_model()

            # Execute with tools
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task("Running INITIALIZER agent...", total=None)

                result = await self._execute_with_tools(
                    messages=context,
                    model=initializer_model,
                    temperature=initializer_config.temperature,
                    tools=tools,
                    loop_limit=initializer_config.loop_limit,
                    task_id=None,
                    agent_type="INITIALIZER",
                    quiet=True  # Suppress verbose output for cleaner UX
                )

                progress.update(task, completed=True)

            if not result:
                self.console.print("[yellow]⚠️  INITIALIZER returned empty response[/yellow]")
                return None

            # Parse JSON response
            try:
                parsed = InitializerPromptBuilder.parse_initializer_response(result)
                return parsed
            except ValueError as e:
                self.console.print(f"[red]INITIALIZER execution failed: {e}[/red]")
                self.console.print(f"[dim]Raw response (first 1000 chars):[/dim]")
                self.console.print(f"[dim]{result[:1000]}[/dim]")
                return None

        except Exception as e:
            self.console.print(f"[red]INITIALIZER execution failed: {e}[/red]")
            return None

    def _extract_key_entities(self, text: str) -> List[str]:
        """
        Extract key entities from text (file paths, IDs, names).

        Args:
            text: Text to extract entities from

        Returns:
            List of extracted key entities
        """
        import re
        entities = []

        # Extract file paths (common patterns)
        file_patterns = [
            r'[\'"]([a-zA-Z0-9_./\-]+\.(py|js|json|md|txt|yaml|yml|toml|conf|config))[\'"]',
            r'(?:file|path|directory):\s*([a-zA-Z0-9_./\-]+)',
            r'`([a-zA-Z0-9_./\-]+\.[a-zA-Z0-9]+)`'
        ]
        for pattern in file_patterns:
            entities.extend(re.findall(pattern, text))

        # Extract IDs (common patterns like abc-123, id_123, etc.)
        id_patterns = [
            r'\b(?:id|ID|Id):\s*([a-zA-Z0-9_-]+)',
            r'\b([a-zA-Z0-9]{8,})\b',  # Long alphanumeric strings
        ]
        for pattern in id_patterns:
            matches = re.findall(pattern, text)
            # Filter out very common words
            entities.extend([m for m in matches if len(str(m)) > 5])

        # Deduplicate and return
        return list(set([str(e) if isinstance(e, tuple) else e for e in entities]))[:10]

    def _build_context_section(self) -> str:
        """
        Build a context section from chat history for the planner.

        Returns:
            Formatted context string to add to planning prompt
        """
        if not self.chat_history:
            return ""

        # Get context depth from config (default: 3)
        context_depth = self.config.get('context_depth', 3)

        # Get last N exchanges
        recent_history = self.chat_history[-context_depth:] if len(self.chat_history) > context_depth else self.chat_history

        # Build context section
        context_section = "\n\nPREVIOUS CONVERSATION CONTEXT:\n"
        context_section += "=" * 60 + "\n"

        for i, entry in enumerate(recent_history, 1):
            query = entry.get('query', '')
            response = entry.get('response', '')

            # Truncate very long responses
            if len(response) > 500:
                response = response[:500] + "...[truncated]"

            context_section += f"\nExchange {i}:\n"
            context_section += f"User: {query}\n"
            context_section += f"Assistant: {response}\n"

        # Extract key entities from all responses
        all_entities = []
        for entry in recent_history:
            response = entry.get('response', '')
            all_entities.extend(self._extract_key_entities(response))

        if all_entities:
            context_section += "\nKEY FACTS FROM PREVIOUS WORK:\n"
            for entity in all_entities[:15]:  # Limit to top 15
                context_section += f"- {entity}\n"

        context_section += "=" * 60 + "\n"

        return context_section

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

        # Build planning context with descriptions and hints
        available_agents = []
        for agent_type, config in self.agent_configs.items():
            if agent_type == 'PLANNER':
                continue

            agent_info = f"- {agent_type}: {config.description}"

            # Add planning hints if available (helps planner know when to use this agent)
            if config.planning_hints:
                agent_info += f"\n  Usage: {config.planning_hints}"

            available_agents.append(agent_info)

        # Select relevant examples for few-shot learning
        relevant_examples = self._select_relevant_examples(query, max_examples=2)

        # Build few-shot examples section
        examples_section = ""
        if relevant_examples:
            examples_section = "\n\nHERE ARE EXAMPLE TASK PLANS TO GUIDE YOU:\n"
            for i, example in enumerate(relevant_examples, 1):
                examples_section += f"\nExample {i}:\n"
                examples_section += f"Query: \"{example['query']}\"\n"
                examples_section += f"Plan:\n{json.dumps(example['plan'], indent=2)}\n"

        # Get available MCP tools and build tools section
        available_tools = self._get_available_tool_descriptions()
        tools_section = ""
        if available_tools:
            tools_section = "\n\nAvailable MCP Tools (agents can use these):\n"

            # Categorize by server if more than 20 tools to avoid prompt bloat
            if len(available_tools) > 20:
                # Group by server prefix
                tools_by_server = {}
                for tool in available_tools:
                    server = tool['name'].split('.')[0] if '.' in tool['name'] else 'other'
                    if server not in tools_by_server:
                        tools_by_server[server] = []
                    tools_by_server[server].append(tool)

                for server, tools in tools_by_server.items():
                    tools_section += f"\n{server} server:\n"
                    for tool in tools[:5]:  # Limit per server
                        tools_section += f"  - {tool['name']}: {tool['description']}\n"
                    if len(tools) > 5:
                        tools_section += f"  ... and {len(tools)-5} more tools\n"
            else:
                # List all tools if under 20
                for tool in available_tools:
                    tools_section += f"- {tool['name']}: {tool['description']}\n"

        # Build context section from chat history
        context_section = self._build_context_section()

        # Build memory-aware planning instructions if memory is enabled
        memory_instructions = ""
        if self.memory_enabled and self.current_memory:
            memory_instructions = """
IMPORTANT - MEMORY-AWARE PLANNING:
You have access to the current memory state (see MEMORY CONTEXT above).
- Review current goals and their status before planning
- Check which features are pending, in_progress, or completed
- Build on work that's already been completed
- Continue work that's in progress

CRITICAL - STATUS UPDATES REQUIRED:
Your plan MUST include tasks to update memory status. For each feature worked on:
1. Create a task to do the work (EXECUTOR/CODER/etc.)
2. Create a task to update feature status using builtin.update_feature_status
3. Create a task to log progress using builtin.log_progress

Memory tools available:
  * builtin.update_feature_status - Update feature status (pending/in_progress/completed/failed/blocked)
  * builtin.log_progress - Record what was accomplished
  * builtin.add_test_result - Record test results for features
  * builtin.get_memory_state - Get current memory state
  * builtin.get_feature_details - Get details about a specific feature

Example task plan with memory updates:
{
  "tasks": [
    {"agent_type": "EXECUTOR", "description": "Work on Feature X using tool Y"},
    {"agent_type": "EXECUTOR", "description": "Use builtin.update_feature_status to mark Feature X as completed"},
    {"agent_type": "EXECUTOR", "description": "Use builtin.log_progress to record what was accomplished"}
  ]
}
"""

        planning_prompt = f"""
{planner_config.system_prompt}

===== AVAILABLE AGENTS (USE ONLY THESE) =====
The ONLY valid agent types you can use are:
{chr(10).join(available_agents)}

CRITICAL CONSTRAINT: You MUST use ONLY the agent types listed above. Do NOT invent, hallucinate, or use any other agent type names. If you need functionality that doesn't match these agents, use the closest available agent or break the task differently.
===== END AVAILABLE AGENTS =====
{tools_section}
{examples_section}
{context_section}
{memory_instructions}

When planning tasks, consider:
1. What MCP tools are available that could solve this task directly
2. Which agent type is best suited to use those tools (usually EXECUTOR)
3. Prefer using MCP tools over writing custom Python code when available
4. MCP tools are called by name (e.g., osm-mcp-server.geocode_address)
5. If previous context exists, consider it when planning - the user may be asking follow-up questions

CRITICAL: The agent_type field must ONLY contain agent names from the AVAILABLE AGENTS list above, NEVER MCP tool names.
- CORRECT: "agent_type": "EXECUTOR", "description": "Use nextcloud-api.nc_notes_create_note to create a note"
- INCORRECT: "agent_type": "nextcloud-api.nc_notes_create_note"
- INCORRECT: "agent_type": "ARCHITECT" (not in available agents list)
- INCORRECT: "agent_type": "TESTER" (not in available agents list)

Now create a plan for this user request:
{query}

Remember: Output ONLY valid JSON following the format shown above. Use ONLY agent types from the AVAILABLE AGENTS list. No markdown, no additional text.
"""

        # Get planner model (agent config -> global config -> fallback to current)
        planner_model = planner_config.model or self.config.get('planner_model') or self.mcp_client.model_manager.get_current_model()

        # Retry loop for plan validation
        max_retries = 2
        task_plan = None
        validation_error = None

        for attempt in range(max_retries + 1):
            # Build retry feedback if this is a retry
            retry_feedback = ""
            if attempt > 0 and validation_error:
                retry_feedback = f"""

🚨 PREVIOUS PLAN WAS REJECTED 🚨

Your previous plan was invalid. Error:
{validation_error}

Please create a NEW plan that fixes this issue. Pay careful attention to the MANDATORY PRE-PROCESSING step at the top of your instructions.
"""

            # Execute planning with minimal tools
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                ) as progress:
                    retry_msg = f" (attempt {attempt+1}/{max_retries+1})" if attempt > 0 else ""
                    task = progress.add_task(f"Planning with {planner_model}{retry_msg}... (Ctrl+C to cancel)", total=None)

                    # Build messages for planner
                    messages = []

                    # Inject memory context if memory system is enabled
                    if self.memory_enabled and self.current_memory:
                        from ..memory.boot_ritual import BootRitual
                        memory_context = BootRitual.build_memory_context(
                            memory=self.current_memory,
                            agent_type="PLANNER",
                            task_description=query,
                        )
                        messages.append({
                            "role": "system",
                            "content": memory_context
                        })

                    # Add planning prompt with retry feedback if applicable
                    messages.append({"role": "user", "content": planning_prompt + retry_feedback})

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
                        loop_limit=planner_config.loop_limit,
                        task_id=None,  # Planning phase
                        agent_type=None,  # Will be logged as PLANNER
                        quiet=True  # Suppress verbose output for cleaner UX
                    )

                    progress.update(task, completed=True)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]⚠️  Planning interrupted by user (Ctrl+C)[/yellow]")
                self.console.print("[dim]   Returning to main prompt...[/dim]")
                raise Exception("Planning cancelled by user")

            # Parse JSON from response
            task_plan = self._extract_json_from_response(response_text)

            # Validate plan structure
            if not isinstance(task_plan, dict) or 'tasks' not in task_plan:
                validation_error = f"Invalid plan structure. Expected dict with 'tasks' key, got: {type(task_plan)}"
                if attempt < max_retries:
                    self.console.print(f"[yellow]⚠️  {validation_error}. Retrying...[/yellow]")
                    continue
                else:
                    raise Exception(validation_error)

            # Log planning phase
            example_categories = [ex.get('category', '') for ex in relevant_examples]
            self.trace_logger.log_planning_phase(
                query=query,
                plan=task_plan,
                available_agents=list(self.agent_configs.keys()),
                examples_used=example_categories
            )

            # Validate plan quality
            is_valid, error_msg = self._validate_plan_quality(task_plan)
            if not is_valid:
                validation_error = error_msg
                if attempt < max_retries:
                    self.console.print(f"[yellow]⚠️  Plan validation failed: {error_msg}[/yellow]")
                    self.console.print(f"[yellow]   Retrying... (attempt {attempt+2}/{max_retries+1})[/yellow]")
                    continue
                else:
                    self.console.print(f"[red]❌ Plan validation failed after {max_retries+1} attempts: {error_msg}[/red]")
                    raise Exception(f"Invalid task plan: {error_msg}")

            # Plan is valid, break out of retry loop
            break

        # Display plan
        self._display_plan(task_plan)

        return task_plan

    def _validate_plan_quality(self, plan: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that the plan meets quality standards.

        Args:
            plan: The task plan dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        tasks = plan.get('tasks', [])

        # Check 1: Reasonable task count (should have at least 1, max 12 tasks)
        if len(tasks) == 0:
            return False, "Plan has no tasks"
        if len(tasks) > 12:
            return False, f"Plan too complex - has {len(tasks)} tasks (recommend max 8)"

        # Check 2: All tasks have required fields
        required_fields = ['id', 'description', 'agent_type']
        for i, task in enumerate(tasks):
            for field in required_fields:
                if field not in task or not task[field]:
                    return False, f"Task {i+1} missing required field: {field}"

        # Check 3: Valid agent types
        valid_agents = set(self.agent_configs.keys())
        valid_agents.discard('PLANNER')  # PLANNER shouldn't be used in execution
        for i, task in enumerate(tasks):
            agent_type = task.get('agent_type', '')
            if agent_type not in valid_agents:
                return False, f"Task {i+1} has invalid agent_type: {agent_type} (valid: {', '.join(sorted(valid_agents))})"

        # Check 4: No circular dependencies
        if self._has_circular_dependencies(tasks):
            return False, "Plan has circular dependencies"

        # Check 5: Dependencies reference valid task IDs
        task_ids = {task['id'] for task in tasks}
        for i, task in enumerate(tasks):
            deps = task.get('dependencies', [])
            for dep_id in deps:
                if dep_id not in task_ids:
                    return False, f"Task {i+1} depends on non-existent task: {dep_id}"

        # Check 6: Detect "list + process each" anti-pattern
        # This pattern should be ONE Python batch task, not split into two
        if len(tasks) >= 2:
            task_1_desc = tasks[0].get('description', '').lower()
            task_2_desc = tasks[1].get('description', '') if len(tasks) > 1 else ''

            # Pattern: task_1 lists files, task_2 processes "each"
            if any(word in task_1_desc for word in ['list', 'get', 'find']) and \
               any(word in task_1_desc for word in ['file', 'pdf', 'document']) and \
               any(word in task_2_desc.lower() for word in ['each', 'every', 'all']):

                # Check if task_2 has filenames in description
                # If not, it's the anti-pattern
                if '/' not in task_2_desc and '.pdf' not in task_2_desc.lower():
                    return False, (
                        "Invalid plan: 'list files + process each' must be ONE Python batch task using SHELL_EXECUTOR. "
                        "Create a single task with builtin.execute_python_code that lists files AND processes them in a loop. "
                        "See MANDATORY PRE-PROCESSING in PLANNER instructions."
                    )

        # Check 7: Detect unwanted memory tasks
        # User must explicitly request memory operations
        if len(tasks) >= 2:
            last_tasks_desc = [tasks[i].get('description', '').lower() for i in range(max(0, len(tasks)-2), len(tasks))]

            has_memory_task = any(
                'update_feature_status' in desc or 'log_progress' in desc
                for desc in last_tasks_desc
            )

            if has_memory_task:
                # This is likely a violation - return warning but allow (too risky to block)
                # The actual user query should have requested this
                pass  # Could add warning here but not blocking

        return True, ""

    def _has_circular_dependencies(self, tasks: List[Dict[str, Any]]) -> bool:
        """
        Check if the task plan has circular dependencies.

        Args:
            tasks: List of task dictionaries

        Returns:
            True if circular dependencies exist, False otherwise
        """
        # Build dependency graph
        graph = {task['id']: task.get('dependencies', []) for task in tasks}

        # DFS to detect cycles
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            # Check all dependencies
            for dep in graph.get(node, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        # Check each task
        for task_id in graph.keys():
            if task_id not in visited:
                if has_cycle(task_id):
                    return True

        return False

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

            # Execute task (execution message printed inside execute_single_task with model info)
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
                # Execution message printed inside execute_single_task with model info
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
        start_time = time.time()

        # Log task start
        self.trace_logger.log_task_start(
            task_id=task.id,
            agent_type=task.agent_type,
            description=task.description,
            dependencies=task.dependencies
        )

        try:
            # Get tools for this agent first (needed for context building)
            available_tool_names = self._get_available_tool_names()
            agent_tool_names = agent_config.get_effective_tools(available_tool_names)

            # Get actual tool objects
            agent_tools = self._get_tool_objects(agent_tool_names)

            # Build task context (include available tools so agent knows what it has)
            messages = self._build_task_context(task, agent_config, agent_tools)

            # Execute with tool support enabled
            # Use agent-specific model if configured, otherwise use endpoint model
            model_to_use = agent_config.model or endpoint.model

            # Display execution with model info and emoji
            agent_emoji = agent_config.emoji if hasattr(agent_config, 'emoji') and agent_config.emoji else ""
            agent_display = f"{agent_emoji} {task.agent_type}" if agent_emoji else task.agent_type
            self.console.print(f"\n[cyan]▶️  Executing {task.id} ({agent_display}) <{model_to_use}>[/cyan]")
            self.console.print(f"[dim]   {task.description}[/dim]")

            response_text = await self._execute_with_tools(
                messages=messages,
                model=model_to_use,
                temperature=agent_config.temperature,
                tools=agent_tools,
                loop_limit=agent_config.loop_limit,
                task_id=task.id,
                agent_type=task.agent_type
            )

            # Store result
            task.mark_completed(response_text)

            # Log task completion
            duration_ms = (time.time() - start_time) * 1000
            self.trace_logger.log_task_end(
                task_id=task.id,
                agent_type=task.agent_type,
                status="completed",
                result=response_text,
                duration_ms=duration_ms
            )

            # Display result with collapsing
            self.task_output.print_task_result(
                task_id=task.id,
                agent_type=task.agent_type,
                description=task.description,
                result=response_text,
                status="completed"
            )

        except Exception as e:
            task.mark_failed(str(e))

            # Log task failure
            duration_ms = (time.time() - start_time) * 1000
            self.trace_logger.log_task_end(
                task_id=task.id,
                agent_type=task.agent_type,
                status="failed",
                error=str(e),
                duration_ms=duration_ms
            )

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

        # Use AGGREGATOR agent to synthesize results into a coherent answer
        try:
            aggregator_config = self.agent_configs["AGGREGATOR"]

            # Build prompt for aggregator
            results_text = "\n\n".join(successful_results)
            aggregator_prompt = f"""
USER'S ORIGINAL QUESTION:
{original_query}

TASK RESULTS TO SYNTHESIZE:
{results_text}

Please synthesize these task results into a clear, direct answer to the user's original question.
"""

            # Execute aggregator with no tools
            messages = [
                {"role": "system", "content": aggregator_config.system_prompt},
                {"role": "user", "content": aggregator_prompt}
            ]

            synthesized_response = await self._execute_with_tools(
                messages=messages,
                model=aggregator_config.model or self.mcp_client.model_manager.get_current_model(),
                temperature=aggregator_config.temperature,
                tools=[],  # No tools for aggregator
                loop_limit=aggregator_config.loop_limit,
                task_id="aggregation",
                agent_type="AGGREGATOR",
                quiet=True
            )

            self.console.print("[green]✓[/green] Results synthesized by AGGREGATOR")
            return synthesized_response

        except (KeyError, Exception) as e:
            # Fallback to simple concatenation if AGGREGATOR fails
            self.console.print(f"[yellow]⚠[/yellow] Aggregator failed ({e}), using fallback")
            aggregated = f"""
Based on the delegated task execution, here are the results:

{chr(10).join(successful_results)}

---
Summary: {len(successful_results)} of {len(tasks)} tasks completed successfully.
"""
            return aggregated

    def _build_task_context(self, task: Task, agent_config: AgentConfig, available_tools: List = None) -> List[Dict[str, str]]:
        """
        Build the message context for a task.

        Includes:
        - Agent's system prompt
        - List of available tools (if provided)
        - Results from dependency tasks (shared read)
        - Task description

        Args:
            task: The task to build context for
            agent_config: Agent configuration
            available_tools: List of tool objects available to this agent

        Returns:
            List of message dictionaries
        """
        messages = []

        # Build enhanced system prompt with shared components
        system_prompt_parts = [agent_config.system_prompt]

        # Inject shared tool protocol (for all agents)
        tool_protocol = self._load_shared_prompt("tool_protocol.txt")
        if tool_protocol:
            system_prompt_parts.append("\n\n" + tool_protocol)

        # Inject memory workflow if memory is active (for worker agents)
        if self.memory_enabled and self.current_memory and task.agent_type not in ["PLANNER", "INITIALIZER"]:
            memory_workflow = self._load_shared_prompt("memory_workflow.txt")
            if memory_workflow:
                system_prompt_parts.append("\n\n" + memory_workflow)

        # Combine all parts
        enhanced_prompt = "".join(system_prompt_parts)

        # System prompt
        messages.append({
            "role": "system",
            "content": enhanced_prompt
        })

        # Add available tools information
        if available_tools:
            tools_info = "\n\nAVAILABLE TOOLS:\n"
            tools_info += "You have access to the following tools (call them by name):\n"
            for tool in available_tools:
                tool_desc = f"- {tool.name}: {tool.description}"
                tools_info += tool_desc + "\n"
            tools_info += "\nUse these tools to complete your task. Call them using the standard function call format."

            messages.append({
                "role": "system",
                "content": tools_info
            })

        # Phase 3: Inject memory context for worker agents (boot ritual)
        if self.memory_enabled and self.current_memory and task.agent_type not in ["PLANNER", "INITIALIZER"]:
            memory_context = BootRitual.build_memory_context(
                memory=self.current_memory,
                agent_type=task.agent_type,
                task_description=task.description,
            )
            messages.append({
                "role": "system",
                "content": memory_context
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
        loop_limit: int,
        task_id: str = None,
        agent_type: str = None,
        quiet: bool = False
    ) -> str:
        """
        Execute a query with tool support (full agent capabilities).

        Args:
            messages: Message history
            model: Model name to use
            temperature: Sampling temperature
            tools: List of tool objects available to this agent
            loop_limit: Maximum tool call iterations
            task_id: Optional task ID for trace logging
            agent_type: Optional agent type for trace logging
            quiet: If True, suppress debug output (for background agents like INITIALIZER)

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
        response_text, tool_calls, _metrics = await self.mcp_client.streaming_manager.process_streaming_response(
            stream,
            thinking_mode=False,
            show_thinking=False,
            show_metrics=False
        )

        # Log the LLM call
        prompt_text = "\n".join([msg.get("content", "") for msg in messages])
        tool_names = [tc.function.name for tc in (tool_calls or [])]
        self.trace_logger.log_llm_call(
            task_id=task_id,
            agent_type=agent_type,
            prompt=prompt_text,
            response=response_text,
            model=model,
            temperature=temperature,
            loop_iteration=0,
            tools_used=tool_names
        )

        # Debug: Check if tool calls were detected (suppress in quiet mode)
        if not quiet:
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

        # Build set of allowed tool names for validation
        allowed_tool_names = set(tool.name for tool in tools) if tools else set()

        while pending_tool_calls and loop_count < loop_limit:
            loop_count += 1

            for tool_call in pending_tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments

                # CRITICAL: Validate tool is in allowed list before executing
                if allowed_tool_names and tool_name not in allowed_tool_names:
                    tool_response = f"Error: Tool '{tool_name}' is not available to this agent. This tool may be forbidden or not in the agent's tool list."
                    tool_success = False
                else:
                    # Execute tool
                    try:
                        tool_response = await self._execute_tool(tool_name, tool_args)
                        tool_success = True
                    except Exception as e:
                        tool_response = f"Error: {str(e)}"
                        tool_success = False

                # Log tool call
                self.trace_logger.log_tool_call(
                    task_id=task_id,
                    agent_type=agent_type,
                    tool_name=tool_name,
                    arguments=tool_args,
                    result=tool_response,
                    success=tool_success
                )

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
            response_text, tool_calls, _metrics = await self.mcp_client.streaming_manager.process_streaming_response(
                stream,
                thinking_mode=False,
                show_thinking=False,
                show_metrics=False
            )

            # Log subsequent LLM call
            prompt_text = "\n".join([msg.get("content", "") for msg in messages])
            tool_names = [tc.function.name for tc in (tool_calls or [])]
            self.trace_logger.log_llm_call(
                task_id=task_id,
                agent_type=agent_type,
                prompt=prompt_text,
                response=response_text,
                model=model,
                temperature=temperature,
                loop_iteration=loop_count,
                tools_used=tool_names
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
                # Combine all content items (MCP can return multiple)
                response_parts = []
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        response_parts.append(content_item.text)
                return "\n".join(response_parts) if response_parts else "No text content in result."
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

    def _get_available_tool_descriptions(self) -> List[Dict[str, str]]:
        """
        Get descriptions of all available MCP tools for the planner.

        Returns:
            List of dicts with 'name' and 'description' keys
        """
        tool_descriptions = []

        # Get MCP server tools (not builtin tools - those are agent capabilities)
        if self.mcp_client.tool_manager:
            enabled_tool_objects = self.mcp_client.tool_manager.get_enabled_tool_objects()
            for tool in enabled_tool_objects:
                tool_descriptions.append({
                    "name": tool.name,
                    "description": tool.description or "No description available"
                })

        return tool_descriptions

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
            agent_type = task_def['agent_type']
            # Get emoji from agent config
            agent_config = self.agent_configs.get(agent_type)
            agent_emoji = ""
            if agent_config and hasattr(agent_config, 'emoji') and agent_config.emoji:
                agent_emoji = agent_config.emoji + " "

            deps = task_def.get('dependencies', [])
            deps_str = f" (depends on: {', '.join(deps)})" if deps else ""
            plan_text += f"{i}. [{agent_emoji}{agent_type}] {task_def['description']}{deps_str}\n"

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

    def show_agent_models(self):
        """
        Display current model configuration for all agents.
        
        Shows:
        - Agent type
        - Configured model (if set in agent definition)
        - Effective model (what will actually be used)
        - Source (agent config, global config, or default)
        """
        from rich.table import Table
        from rich.text import Text
        
        # Get current global model
        global_model = self.mcp_client.model_manager.get_current_model()
        global_planner = self.config.get('planner_model')
        
        # Create table
        table = Table(title="🧠 Agent Model Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Agent Type", style="cyan", width=15)
        table.add_column("Configured Model", style="yellow", width=25)
        table.add_column("Effective Model", style="green", width=25)
        table.add_column("Source", style="dim", width=20)
        
        # Sort agents by type
        sorted_agents = sorted(self.agent_configs.items(), key=lambda x: x[0])
        
        for agent_type, config in sorted_agents:
            # Determine configured model
            configured = config.model if config.model else "-"
            
            # Determine effective model (what will actually be used)
            if agent_type == "PLANNER":
                effective = config.model or global_planner or global_model
                source = "agent config" if config.model else ("global planner" if global_planner else "global default")
            else:
                effective = config.model or global_model
                source = "agent config" if config.model else "global default"
            
            # Add row with color coding
            configured_text = Text(configured, style="yellow" if config.model else "dim")
            effective_text = Text(effective, style="green bold" if config.model else "green")
            
            table.add_row(agent_type, str(configured_text), str(effective_text), source)
        
        # Display table
        self.console.print()
        self.console.print(table)
        self.console.print()
        self.console.print(f"[dim]Global default model: {global_model}[/dim]")
        if global_planner:
            self.console.print(f"[dim]Global planner model: {global_planner}[/dim]")
        self.console.print()

    async def select_agent_model_interactive(self, clear_console_func=None):
        """
        Interactive UI to select models for individual agents.
        
        Allows users to:
        - View current model for each agent
        - Select a specific model for any agent
        - Clear agent-specific model (use global default)
        - Save changes to agent definition files
        
        Args:
            clear_console_func: Function to clear the console (optional)
        """
        from rich.prompt import Prompt, Confirm
        from rich.table import Table
        from rich.text import Text
        
        # Check if Ollama is running
        if not await self.mcp_client.model_manager.check_ollama_running():
            self.console.print(Panel(
                "[bold red]Ollama is not running![/bold red]\n\n"
                "Please start Ollama before trying to configure agent models.",
                title="Error", border_style="red", expand=False
            ))
            return
        
        # Get available models
        with self.console.status("[cyan]Getting available models from Ollama...[/cyan]"):
            models = await self.mcp_client.model_manager.list_ollama_models()
        
        if not models:
            self.console.print("[yellow]No models available. Try pulling a model with 'ollama pull <model>'[/yellow]")
            return
        
        # Extract model names
        model_names = sorted([m.get("name", "") for m in models])
        
        # Track changes
        changes_made = {}
        result_message = None
        result_style = "green"
        
        # Main selection loop
        while True:
            if clear_console_func:
                clear_console_func()
            
            # Display header
            self.console.print(Panel(Text.from_markup("[bold]🎯 Configure Agent Models[/bold]", justify="center"), 
                                    expand=True, border_style="green"))
            
            # Create table of agents
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=3)
            table.add_column("Agent Type", style="cyan", width=15)
            table.add_column("Current Model", style="yellow", width=30)
            table.add_column("Status", style="dim", width=15)
            
            sorted_agents = sorted(self.agent_configs.items(), key=lambda x: x[0])
            
            for i, (agent_type, config) in enumerate(sorted_agents, 1):
                # Check if there are unsaved changes
                if agent_type in changes_made:
                    current_model = changes_made[agent_type] if changes_made[agent_type] else "[dim](use global)[/dim]"
                    status = "[yellow]*modified*[/yellow]"
                else:
                    current_model = config.model if config.model else "[dim](use global)[/dim]"
                    status = ""
                
                table.add_row(str(i), agent_type, current_model, status)
            
            self.console.print(table)
            self.console.print()
            
            # Show result message if any
            if result_message:
                self.console.print(Panel(result_message, border_style=result_style, expand=False))
                result_message = None
            
            # Show commands
            self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
            self.console.print("• Enter [bold magenta]number[/bold magenta] to configure agent model")
            self.console.print("• [bold]s[/bold] or [bold]save[/bold] - Save changes and return")
            self.console.print("• [bold]q[/bold] or [bold]quit[/bold] - Cancel and return")
            self.console.print()
            
            selection = Prompt.ask("> ").strip().lower()
            
            if selection in ['s', 'save']:
                if not changes_made:
                    result_message = "[yellow]No changes to save[/yellow]"
                    result_style = "yellow"
                    continue
                
                # Save changes to agent definition files
                saved_count = 0
                for agent_type, new_model in changes_made.items():
                    try:
                        # Get agent config
                        config = self.agent_configs[agent_type]
                        
                        # Find the definition file
                        def_file = Path(__file__).parent / "definitions" / f"{agent_type.lower()}.json"
                        
                        # Load current definition
                        with open(def_file, 'r') as f:
                            data = json.load(f)
                        
                        # Update model field
                        if new_model:
                            data['model'] = new_model
                        else:
                            # Remove model field to use global default
                            if 'model' in data:
                                del data['model']
                        
                        # Save back
                        with open(def_file, 'w') as f:
                            json.dump(data, f, indent=2)
                        
                        # Update in-memory config
                        config.model = new_model
                        saved_count += 1
                    
                    except Exception as e:
                        self.console.print(f"[red]Error saving {agent_type}: {e}[/red]")
                
                self.console.print(f"\n[green]✓ Saved {saved_count} agent model configuration(s)[/green]")
                self.console.print("[dim]Press Enter to continue...[/dim]")
                input()
                return
            
            elif selection in ['q', 'quit']:
                if changes_made:
                    if Confirm.ask("[yellow]Discard unsaved changes?[/yellow]"):
                        return
                    else:
                        continue
                return
            
            elif selection.isdigit():
                index = int(selection) - 1
                if 0 <= index < len(sorted_agents):
                    agent_type, config = sorted_agents[index]
                    
                    # Show model selection for this agent
                    if clear_console_func:
                        clear_console_func()
                    
                    self.console.print(Panel(f"[bold]Select Model for {agent_type}[/bold]", border_style="cyan"))
                    self.console.print()
                    
                    # Show available models
                    for i, model_name in enumerate(model_names, 1):
                        current_indicator = ""
                        if agent_type in changes_made:
                            if changes_made[agent_type] == model_name:
                                current_indicator = " [green]← selected[/green]"
                        elif config.model == model_name:
                            current_indicator = " [yellow]← current[/yellow]"
                        
                        self.console.print(f"{i}. {model_name}{current_indicator}")
                    
                    self.console.print()
                    self.console.print("[bold]0.[/bold] Clear (use global default)")
                    self.console.print("[bold]c.[/bold] Cancel")
                    self.console.print()
                    
                    model_selection = Prompt.ask("> ").strip().lower()
                    
                    if model_selection == 'c':
                        continue
                    elif model_selection == '0':
                        changes_made[agent_type] = None
                        result_message = f"[green]{agent_type} will use global default model[/green]"
                        result_style = "green"
                    elif model_selection.isdigit():
                        model_index = int(model_selection) - 1
                        if 0 <= model_index < len(model_names):
                            selected_model = model_names[model_index]
                            changes_made[agent_type] = selected_model
                            result_message = f"[green]{agent_type} model set to {selected_model}[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Invalid model number[/red]"
                            result_style = "red"
                    else:
                        result_message = "[red]Invalid selection[/red]"
                        result_style = "red"
                else:
                    result_message = "[red]Invalid agent number[/red]"
                    result_style = "red"
            else:
                result_message = "[red]Invalid command[/red]"
                result_style = "red"
