"""
Memory initialization utilities.

Converts INITIALIZER agent output into DomainMemory objects
and handles bootstrapping of new memory sessions.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .base_memory import (
    DomainMemory,
    Goal,
    Feature,
    MemoryMetadata,
    FeatureStatus,
    OutcomeType,
)
from .schemas import DomainType, MemorySchema
from .storage import MemoryStorage


class MemoryInitializer:
    """
    Handles initialization of domain memory from INITIALIZER agent output.

    Takes the structured JSON from INITIALIZER agent and converts it into
    a fully-formed DomainMemory object ready for use by worker agents.
    """

    def __init__(self, storage: Optional[MemoryStorage] = None):
        """
        Initialize the memory initializer.

        Args:
            storage: Optional MemoryStorage instance. If None, creates default.
        """
        self.storage = storage or MemoryStorage()

    def create_session_id(self, prefix: Optional[str] = None) -> str:
        """
        Generate a unique session ID.

        Args:
            prefix: Optional prefix for the session ID

        Returns:
            Unique session ID string
        """
        unique_id = uuid.uuid4().hex[:12]
        if prefix:
            return f"{prefix}_{unique_id}"
        return f"session_{unique_id}"

    def bootstrap_from_json(
        self,
        initializer_output: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> DomainMemory:
        """
        Create DomainMemory from INITIALIZER agent JSON output.

        Args:
            initializer_output: JSON output from INITIALIZER agent
            session_id: Optional custom session ID. If None, generates one.

        Returns:
            Initialized DomainMemory object

        Raises:
            ValueError: If initializer_output is invalid
        """
        # Validate required fields
        if "domain" not in initializer_output:
            raise ValueError("Missing required field: 'domain'")
        if "goals" not in initializer_output:
            raise ValueError("Missing required field: 'goals'")

        domain = initializer_output["domain"]
        session_description = initializer_output.get(
            "session_description",
            "Memory session"
        )

        # Generate session ID if not provided
        if session_id is None:
            session_id = self.create_session_id(prefix=domain)

        # Create metadata
        metadata = MemoryMetadata(
            session_id=session_id,
            domain=domain,
            description=session_description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Parse goals and features
        goals = self._parse_goals(initializer_output["goals"])

        # Get or merge state
        state = self._initialize_state(
            domain=domain,
            custom_state=initializer_output.get("state", {})
        )

        # Create memory
        memory = DomainMemory(
            metadata=metadata,
            goals=goals,
            state=state,
            progress_log=[],
            artifacts={},
        )

        # Add initial progress entry
        memory.add_progress_entry(
            agent_type="INITIALIZER",
            action="Created session",
            outcome=OutcomeType.SUCCESS,
            details=f"Initialized {domain} domain memory with {len(goals)} goal(s)",
        )

        # Handle initial artifacts
        if "initial_artifacts" in initializer_output:
            self._create_initial_artifacts(
                memory,
                initializer_output["initial_artifacts"]
            )

        return memory

    def _parse_goals(self, goals_data: list) -> list[Goal]:
        """Parse goals from initializer output."""
        goals = []

        for goal_data in goals_data:
            # Parse features
            features = []
            for feature_data in goal_data.get("features", []):
                feature = Feature(
                    id=feature_data["id"],
                    description=feature_data["description"],
                    status=FeatureStatus.PENDING,
                    criteria=feature_data.get("criteria", []),
                    tests=feature_data.get("tests", []),
                    notes=f"Priority: {feature_data.get('priority', 'medium')}",
                )
                features.append(feature)

            # Create goal
            goal = Goal(
                id=goal_data["id"],
                description=goal_data["description"],
                features=features,
                constraints=goal_data.get("constraints", []),
            )
            goals.append(goal)

        return goals

    def _initialize_state(
        self,
        domain: str,
        custom_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Initialize state by merging domain defaults with custom state."""
        try:
            domain_enum = DomainType(domain)
            default_state = MemorySchema.get_domain_defaults(domain_enum)
        except ValueError:
            # Unknown domain, use general defaults
            default_state = MemorySchema.get_domain_defaults(DomainType.GENERAL)

        # Merge custom state into defaults
        merged_state = {**default_state}
        self._deep_merge(merged_state, custom_state)

        return merged_state

    def _deep_merge(self, target: dict, source: dict) -> None:
        """Deep merge source dict into target dict."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _create_initial_artifacts(
        self,
        memory: DomainMemory,
        artifacts_data: Dict[str, Any]
    ) -> None:
        """
        Create initial artifact files.

        Args:
            memory: The memory object to update
            artifacts_data: Dictionary of artifact_name -> content
        """
        artifacts_dir = self.storage.get_artifacts_path(
            memory.metadata.session_id,
            memory.metadata.domain
        )
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        for name, content in artifacts_data.items():
            # Write artifact file
            artifact_path = artifacts_dir / name
            if isinstance(content, dict):
                # Write as JSON
                with open(artifact_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2)
            else:
                # Write as text
                with open(artifact_path, 'w', encoding='utf-8') as f:
                    f.write(str(content))

            # Track in memory
            memory.artifacts[name] = str(artifact_path.relative_to(artifacts_dir.parent))

    def initialize_and_save(
        self,
        initializer_output: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> DomainMemory:
        """
        Bootstrap memory and save to disk in one operation.

        Args:
            initializer_output: JSON output from INITIALIZER agent
            session_id: Optional custom session ID

        Returns:
            Initialized and persisted DomainMemory object
        """
        memory = self.bootstrap_from_json(initializer_output, session_id)
        self.storage.save_memory(memory, create_backup=False)
        return memory

    def resume_or_create(
        self,
        user_query: str,
        session_id: Optional[str] = None,
        domain: str = "coding",
    ) -> tuple[DomainMemory, bool]:
        """
        Resume existing session or flag for new initialization.

        Args:
            user_query: User's request
            session_id: Optional session ID to resume
            domain: Domain type if creating new session

        Returns:
            Tuple of (memory, is_new) where is_new indicates if memory needs initialization
        """
        # Try to resume existing session
        if session_id and self.storage.session_exists(session_id, domain):
            memory = self.storage.load_memory(session_id, domain)
            if memory:
                return memory, False

        # Create placeholder for new session
        # (actual initialization happens via INITIALIZER agent)
        metadata = MemoryMetadata(
            session_id=session_id or self.create_session_id(prefix=domain),
            domain=domain,
            description=user_query[:100],  # Truncate for preview
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        memory = DomainMemory(metadata=metadata)
        return memory, True


class InitializerPromptBuilder:
    """
    Builds prompts for the INITIALIZER agent based on domain and context.
    """

    @staticmethod
    def build_prompt(
        user_query: str,
        domain: str = "coding",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build a prompt for the INITIALIZER agent.

        Args:
            user_query: The user's request
            domain: Domain type (coding, research, operations, content, general)
            context: Optional additional context (existing files, constraints, etc.)

        Returns:
            Formatted prompt for INITIALIZER agent
        """
        prompt_parts = [
            f"Domain: {domain}",
            "",
            "User Request:",
            user_query,
            "",
        ]

        # Add context if provided
        if context:
            if "existing_files" in context:
                prompt_parts.extend([
                    "Existing Files:",
                    *[f"- {f}" for f in context["existing_files"]],
                    "",
                ])

            if "constraints" in context:
                prompt_parts.extend([
                    "Constraints:",
                    *[f"- {c}" for c in context["constraints"]],
                    "",
                ])

            if "preferences" in context:
                prompt_parts.extend([
                    "Preferences:",
                    *[f"- {k}: {v}" for k, v in context["preferences"].items()],
                    "",
                ])

        # Add domain-specific guidance
        domain_guidance = InitializerPromptBuilder._get_domain_guidance(domain)
        if domain_guidance:
            prompt_parts.extend([
                "Domain-Specific Guidance:",
                domain_guidance,
                "",
            ])

        prompt_parts.extend([
            "Please analyze this request and create a structured memory initialization",
            "that breaks it down into specific, testable goals and features.",
        ])

        return "\n".join(prompt_parts)

    @staticmethod
    def _get_domain_guidance(domain: str) -> str:
        """Get domain-specific guidance for INITIALIZER."""
        guidance_map = {
            "coding": (
                "- Identify programming language and framework\n"
                "- Specify test framework and test structure\n"
                "- Define build/run commands\n"
                "- List required dependencies\n"
                "- Consider git workflow if applicable"
            ),
            "research": (
                "- State clear, testable hypotheses\n"
                "- Define experiments and methodologies\n"
                "- Specify what evidence would confirm/reject hypotheses\n"
                "- Plan literature review if needed\n"
                "- Identify data collection requirements"
            ),
            "operations": (
                "- Identify runbooks and procedures needed\n"
                "- Define SLA targets and metrics\n"
                "- Plan incident response workflows\n"
                "- Set up monitoring and alerting\n"
                "- Document recovery procedures"
            ),
            "content": (
                "- Define content types and formats\n"
                "- Specify style guide requirements\n"
                "- Plan publication schedule\n"
                "- Set audience engagement targets\n"
                "- Outline content calendar"
            ),
        }
        return guidance_map.get(domain, "")

    @staticmethod
    def parse_initializer_response(response: str) -> Dict[str, Any]:
        """
        Parse INITIALIZER agent response (JSON).

        Args:
            response: Raw response from INITIALIZER agent

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If response is not valid JSON
        """
        if not response or not response.strip():
            raise ValueError("INITIALIZER returned empty response. The model may have only made tool calls without generating final JSON output.")

        # Strip whitespace
        response = response.strip()

        # Try to extract JSON from markdown code blocks
        if "```" in response:
            # Find JSON within code fences
            import re
            # Match ```json...``` or ```...```
            code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            matches = re.findall(code_block_pattern, response, re.DOTALL)
            if matches:
                response = matches[0].strip()

        # If response still has text before/after JSON, try to extract just the JSON
        if not response.startswith("{"):
            # Find first { and last }
            start_idx = response.find("{")
            end_idx = response.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                response = response[start_idx:end_idx + 1]

        try:
            parsed = json.loads(response)
            # Validate required fields
            if "domain" not in parsed or "goals" not in parsed:
                raise ValueError(f"INITIALIZER JSON missing required fields (domain, goals). Got: {list(parsed.keys())}")
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from INITIALIZER: {e}\n\nResponse preview (first 500 chars):\n{response[:500]}")
