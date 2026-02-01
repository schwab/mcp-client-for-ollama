"""Claude Code provider for emergency fallback and supervision.

This module provides integration with Claude Code API to act as a fallback
when Ollama models fail repeatedly, ensuring high success rates while
minimizing paid API usage.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from rich.console import Console

logger = logging.getLogger(__name__)


@dataclass
class ClaudeUsageRecord:
    """Record of Claude API usage."""
    timestamp: str
    task_type: str
    reason: str  # "fallback", "critical", "user_requested"
    input_tokens: int
    output_tokens: int
    cost_estimate: float
    success: bool


class ClaudeUsageTracker:
    """Tracks Claude API usage and enforces limits."""

    def __init__(self, usage_file: Optional[Path] = None):
        """Initialize usage tracker.

        Args:
            usage_file: Path to store usage records. Defaults to ~/.ollmcp/claude_usage.json
        """
        if usage_file is None:
            usage_file = Path.home() / ".ollmcp" / "claude_usage.json"

        self.usage_file = usage_file
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        self.records: List[ClaudeUsageRecord] = []
        self._load_usage()

    def _load_usage(self):
        """Load usage records from file."""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    self.records = [ClaudeUsageRecord(**r) for r in data]
            except Exception as e:
                logger.warning(f"Failed to load Claude usage records: {e}")
                self.records = []

    def _save_usage(self):
        """Save usage records to file."""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump([asdict(r) for r in self.records], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save Claude usage records: {e}")

    def record_usage(self, task_type: str, reason: str, input_tokens: int,
                    output_tokens: int, success: bool = True, model: str = "claude-3-5-sonnet-20241022"):
        """Record a Claude API usage.

        Args:
            task_type: Type of task (e.g., "PLANNER", "SHELL_EXECUTOR")
            reason: Why Claude was used ("fallback", "critical", "user_requested")
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            success: Whether the call succeeded
            model: Claude model used (for accurate pricing)
        """
        # Get pricing for the model (fallback to Sonnet 3.5 if unknown)
        pricing = self.model_pricing.get(model, (3.00, 15.00))
        cost = (input_tokens / 1_000_000 * pricing[0]) + (output_tokens / 1_000_000 * pricing[1])

        record = ClaudeUsageRecord(
            timestamp=datetime.now().isoformat(),
            task_type=task_type,
            reason=reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_estimate=cost,
            success=success
        )

        self.records.append(record)
        self._save_usage()

        logger.info(f"Claude usage recorded: {reason} for {task_type}, "
                   f"cost ~${cost:.4f} ({input_tokens}in/{output_tokens}out tokens)")

    def get_usage_last_hour(self) -> int:
        """Get number of Claude calls in the last hour."""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        return sum(1 for r in self.records
                  if datetime.fromisoformat(r.timestamp) > one_hour_ago)

    def get_usage_today(self) -> Dict[str, Any]:
        """Get usage statistics for today.

        Returns:
            Dictionary with call count, token usage, and cost estimate
        """
        today = datetime.now().date()
        today_records = [r for r in self.records
                        if datetime.fromisoformat(r.timestamp).date() == today]

        if not today_records:
            return {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_estimate": 0.0,
                "by_reason": {}
            }

        by_reason = {}
        for r in today_records:
            if r.reason not in by_reason:
                by_reason[r.reason] = {"calls": 0, "cost": 0.0}
            by_reason[r.reason]["calls"] += 1
            by_reason[r.reason]["cost"] += r.cost_estimate

        return {
            "calls": len(today_records),
            "input_tokens": sum(r.input_tokens for r in today_records),
            "output_tokens": sum(r.output_tokens for r in today_records),
            "cost_estimate": sum(r.cost_estimate for r in today_records),
            "by_reason": by_reason
        }

    def can_use_claude(self, max_per_hour: int = 50) -> bool:
        """Check if we're within usage limits.

        Args:
            max_per_hour: Maximum Claude calls allowed per hour

        Returns:
            True if within limits, False otherwise
        """
        usage = self.get_usage_last_hour()
        return usage < max_per_hour


class ClaudeProvider:
    """Provider for Claude Code API integration.

    This provider acts as an emergency fallback when Ollama models fail,
    ensuring high success rates while minimizing paid API usage.
    """

    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None,
                 console: Optional[Console] = None):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key. If None, will try to load from config or env
            config: Configuration dictionary with Claude settings
            console: Rich console for output
        """
        self.console = console or Console()
        self.config = config or {}
        self.enabled = self.config.get("enabled", False)
        self.api_key = api_key or self.config.get("api_key")

        # Usage settings
        self.escalation_threshold = self.config.get("escalation_threshold", 2)
        self.max_calls_per_hour = self.config.get("max_calls_per_hour", 50)
        self.critical_tasks = set(self.config.get("critical_tasks", [
            "batch_process", "code_generation", "file_write"
        ]))

        # Model selection (supports multiple Claude models)
        self.model = self.config.get("model", "claude-3-5-sonnet-20241022")
        # Supported models with pricing (input/output per million tokens)
        self.model_pricing = {
            "claude-opus-4-5-20250514": (15.00, 75.00),  # Opus 4.5 - most powerful, most expensive
            "claude-opus-4-20250514": (5.00, 25.00),     # Opus 4 - 3x cheaper than 4.5
            "claude-3-5-sonnet-20241022": (3.00, 15.00), # Sonnet 3.5 - best value
            "claude-3-5-haiku-20241022": (1.00, 5.00),   # Haiku 3.5 - fastest, cheapest
        }

        # Usage tracker
        self.usage_tracker = ClaudeUsageTracker()

        # Anthropic client (lazy loaded)
        self._client = None

        if self.enabled and not self.api_key:
            logger.warning("Claude integration enabled but no API key provided")
            self.enabled = False

    @property
    def client(self):
        """Lazy load Anthropic client."""
        if self._client is None and self.enabled:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.error("anthropic package not installed. Install with: pip install anthropic")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self.enabled = False
        return self._client

    def should_use_claude(self, task, ollama_failures: int = 0,
                         user_requested: bool = False) -> tuple[bool, str]:
        """Decide if Claude should handle this task.

        Args:
            task: Task object with agent_type and description
            ollama_failures: Number of times Ollama models have failed on this task
            user_requested: Whether user explicitly requested Claude

        Returns:
            Tuple of (should_use, reason)
        """
        if not self.enabled:
            return False, "disabled"

        # Check usage limits
        if not self.usage_tracker.can_use_claude(self.max_calls_per_hour):
            logger.warning(f"Claude usage limit reached ({self.max_calls_per_hour}/hour)")
            return False, "rate_limit"

        # User explicitly requested Claude
        if user_requested:
            return True, "user_requested"

        # Critical task types
        task_type = getattr(task, 'agent_type', '').lower()
        if any(critical in task_type for critical in self.critical_tasks):
            # Only use Claude for critical tasks if they're complex
            # (avoid using for every simple critical operation)
            if ollama_failures >= 1:
                return True, "critical"

        # Fallback after repeated failures
        if ollama_failures >= self.escalation_threshold:
            return True, "fallback"

        return False, "not_needed"

    async def execute_task(self, task, context: Dict, reason: str = "fallback") -> str:
        """Execute a task using Claude Code API.

        Args:
            task: Task object with description and agent_type
            context: Context dictionary with conversation history, tools, etc.
            reason: Reason for using Claude ("fallback", "critical", "user_requested")

        Returns:
            Claude's response text
        """
        if not self.enabled or self.client is None:
            raise RuntimeError("Claude provider is not enabled or configured")

        self.console.print(f"[yellow]🤖 Escalating to Claude Code ({reason})...[/yellow]")

        # Build prompt
        system_prompt = self._build_system_prompt(task, context)
        user_message = self._build_user_message(task, context)

        try:
            # Call Claude API with configured model
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                temperature=0.3,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": user_message
                }]
            )

            # Extract response text
            response_text = response.content[0].text

            # Record usage with model info for accurate pricing
            self.usage_tracker.record_usage(
                task_type=getattr(task, 'agent_type', 'unknown'),
                reason=reason,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                success=True,
                model=self.model
            )

            # Show usage summary
            usage = self.usage_tracker.get_usage_today()
            self.console.print(
                f"[green]✓[/green] Claude completed task. "
                f"Today's usage: {usage['calls']} calls, "
                f"~${usage['cost_estimate']:.4f}"
            )

            return response_text

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")

            # Record failed usage
            self.usage_tracker.record_usage(
                task_type=getattr(task, 'agent_type', 'unknown'),
                reason=reason,
                input_tokens=0,
                output_tokens=0,
                success=False
            )

            raise RuntimeError(f"Claude API call failed: {e}")

    def _build_system_prompt(self, task, context: Dict) -> str:
        """Build system prompt for Claude.

        Args:
            task: Task object
            context: Context dictionary

        Returns:
            System prompt string
        """
        agent_type = getattr(task, 'agent_type', 'EXECUTOR')

        # Get agent-specific system prompt if available
        agent_definitions = context.get('agent_definitions', {})
        agent_def = agent_definitions.get(agent_type, {})
        base_prompt = agent_def.get('system_prompt', '')

        # Add Claude-specific instructions
        claude_additions = f"""

You are Claude, acting as a fallback for local Ollama models that have failed.
You have been called because the Ollama models were unable to complete this task successfully.

Your goal: Complete this task definitively and correctly.

Agent Type: {agent_type}
Working Directory: {context.get('working_directory', 'unknown')}

Be direct, thorough, and ensure the task is fully completed.
"""

        return base_prompt + claude_additions

    def _build_user_message(self, task, context: Dict) -> str:
        """Build user message for Claude.

        Args:
            task: Task object
            context: Context dictionary

        Returns:
            User message string
        """
        description = getattr(task, 'description', 'No description provided')

        # Include information about previous failures
        previous_attempts = context.get('previous_attempts', [])
        failure_info = ""
        if previous_attempts:
            failure_info = "\n\nPrevious attempts by Ollama models:\n"
            for i, attempt in enumerate(previous_attempts[-3:], 1):  # Last 3 attempts
                model = attempt.get('model', 'unknown')
                error = attempt.get('error', 'unknown error')
                failure_info += f"  Attempt {i} ({model}): {error}\n"

        message = f"""Task: {description}

{failure_info}

Please complete this task. Available tools will be provided via tool calling.
Ensure you complete the entire task and provide a summary of what was done.
"""

        return message

    def get_usage_summary(self) -> str:
        """Get formatted usage summary.

        Returns:
            Formatted string with usage statistics
        """
        usage = self.usage_tracker.get_usage_today()

        if usage['calls'] == 0:
            return "No Claude usage today"

        summary = f"""Claude Usage Today:
  Total Calls: {usage['calls']}
  Input Tokens: {usage['input_tokens']:,}
  Output Tokens: {usage['output_tokens']:,}
  Estimated Cost: ${usage['cost_estimate']:.4f}

  Breakdown by Reason:"""

        for reason, stats in usage['by_reason'].items():
            summary += f"\n    {reason}: {stats['calls']} calls (${stats['cost']:.4f})"

        return summary


class ClaudeQualityValidator:
    """Phase 2: Quality validation of Ollama outputs using Claude.

    Validates critical task outputs before marking complete, catching mistakes
    early and reducing escalation rate through feedback loop.
    """

    def __init__(self, claude_provider: ClaudeProvider):
        """Initialize validator with Claude provider.

        Args:
            claude_provider: ClaudeProvider instance for API calls
        """
        self.claude_provider = claude_provider
        self.validation_rules = {
            "CODER": {
                "checks": ["syntax", "security", "completeness"],
                "priority": "high",
            },
            "FILE_EXECUTOR": {
                "checks": ["file_exists", "content_correctness"],
                "priority": "high",
            },
            "SHELL_EXECUTOR": {
                "checks": ["command_success", "output_validity"],
                "priority": "medium",
            },
            "PLANNER": {
                "checks": ["task_decomposition", "logical_flow"],
                "priority": "medium",
            },
        }

    def should_validate(self, task_type: str, task_description: str) -> bool:
        """Determine if task output should be validated.

        Args:
            task_type: Agent type (CODER, FILE_EXECUTOR, etc.)
            task_description: Task description

        Returns:
            True if validation should occur
        """
        # Only validate configured task types
        if task_type not in self.validation_rules:
            return False

        # Check if Claude is enabled
        if not self.claude_provider.enabled:
            return False

        # Check usage limits (validation is cheaper than execution)
        if not self.claude_provider.usage_tracker.can_use_claude(
            self.claude_provider.max_calls_per_hour * 2  # More lenient for validation
        ):
            logger.warning("Claude usage limit reached for validation")
            return False

        return True

    def build_validation_prompt(self, task_type: str, task_description: str,
                                output: str) -> str:
        """Build validation prompt based on task type.

        Args:
            task_type: Agent type
            task_description: What was supposed to be done
            output: Output to validate

        Returns:
            Validation prompt for Claude
        """
        rules = self.validation_rules.get(task_type, {})
        checks = rules.get("checks", [])

        if task_type == "CODER":
            return f"""Review this code output for correctness:

TASK: {task_description}

OUTPUT:
```
{output}
```

VALIDATION CHECKS:
1. Syntax: Is the code syntactically correct? Any parse errors?
2. Security: Are there any security vulnerabilities (SQL injection, XSS, etc.)?
3. Completeness: Does it fully implement the requested functionality?

RESPONSE FORMAT:
If validation PASSES:
✅ VALID: [brief explanation of why code is correct]

If validation FAILS:
❌ INVALID: [explanation of what's wrong]
FEEDBACK: [specific corrections needed]"""

        elif task_type == "FILE_EXECUTOR":
            return f"""Review this file operation output:

TASK: {task_description}

OUTPUT:
{output}

VALIDATION CHECKS:
1. File Existence: Does the file exist after operation?
2. Content Correctness: Is the file content correct?
3. Format: Is it in the expected format?

RESPONSE FORMAT:
If validation PASSES:
✅ VALID: [brief explanation]

If validation FAILS:
❌ INVALID: [what's wrong]
FEEDBACK: [corrections needed]"""

        elif task_type == "SHELL_EXECUTOR":
            return f"""Review this shell execution output:

TASK: {task_description}

OUTPUT:
{output}

VALIDATION CHECKS:
1. Success: Did the command succeed?
2. Output Validity: Is the output in expected format?
3. Completeness: Are all files/tasks processed?

RESPONSE FORMAT:
If validation PASSES:
✅ VALID: [brief explanation]

If validation FAILS:
❌ INVALID: [what's wrong]
FEEDBACK: [corrections needed]"""

        else:  # Generic validation
            return f"""Review this task output:

TASK: {task_description}

OUTPUT:
{output}

Is this output correct and complete?

RESPONSE FORMAT:
✅ VALID if correct, ❌ INVALID with feedback if not."""

    async def validate_output(self, task_type: str, task_description: str,
                             output: str) -> tuple[bool, str]:
        """Validate Ollama output using Claude.

        Args:
            task_type: Agent type
            task_description: Task description
            output: Output to validate

        Returns:
            Tuple of (is_valid, feedback)
        """
        if not self.should_validate(task_type, task_description):
            return True, "Validation skipped (not configured)"

        if not self.claude_provider.client:
            logger.warning("Claude client not available for validation")
            return True, "Claude not available"

        try:
            logger.info(f"Validating {task_type} output with Claude")

            prompt = self.build_validation_prompt(task_type, task_description, output)

            response = self.claude_provider.client.messages.create(
                model=self.claude_provider.model,
                max_tokens=1024,  # Validation responses are short
                temperature=0.2,  # Lower temperature for strict validation
                system="You are a code quality and output validator. Provide strict validation feedback.",
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            feedback = response.content[0].text

            # Record validation usage
            self.claude_provider.usage_tracker.record_usage(
                task_type=task_type,
                reason="validation",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                success=True,
                model=self.claude_provider.model
            )

            # Parse validation result
            is_valid = feedback.strip().startswith("✅")

            return is_valid, feedback

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            # On validation error, treat as valid to avoid breaking workflow
            return True, f"Validation error: {e}"

    def extract_feedback(self, validation_response: str) -> str:
        """Extract actionable feedback from validation response.

        Args:
            validation_response: Full validation response from Claude

        Returns:
            Extracted feedback for retry
        """
        if "FEEDBACK:" in validation_response:
            feedback = validation_response.split("FEEDBACK:", 1)[1].strip()
            return feedback
        elif "feedback:" in validation_response.lower():
            lines = validation_response.split("\n")
            for i, line in enumerate(lines):
                if "feedback" in line.lower():
                    return "\n".join(lines[i+1:]).strip()

        # If no explicit feedback, extract the explanation
        if "❌" in validation_response:
            return validation_response.split("❌")[1].strip()

        return validation_response
