"""Artifact detection system for LLM outputs."""

import re
import json
from typing import List, Dict, Any, Optional
from .types import ArtifactType, ArtifactData


class ArtifactDetector:
    """Detects and parses artifacts from LLM output."""

    # Regex pattern to match artifact blocks
    ARTIFACT_PATTERN = re.compile(
        r'```artifact:(\w+)\n(.*?)\n```',
        re.DOTALL
    )

    # Alternative pattern for JSON-only artifacts (no code fence)
    JSON_ARTIFACT_PATTERN = re.compile(
        r'<artifact:(\w+)>(.*?)</artifact:\1>',
        re.DOTALL
    )

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the artifact detector.

        Args:
            strict_mode: If True, raise exceptions on parse errors.
                        If False, silently skip malformed artifacts.
        """
        self.strict_mode = strict_mode
        self._supported_types = {t.value for t in ArtifactType}

    def detect(self, llm_output: str) -> List[ArtifactData]:
        """
        Detect all artifacts in LLM output.

        Args:
            llm_output: The raw output text from the LLM

        Returns:
            List of parsed artifact data dictionaries
        """
        artifacts = []

        # Check for code fence format
        for match in self.ARTIFACT_PATTERN.finditer(llm_output):
            artifact = self._parse_match(match.group(1), match.group(2))
            if artifact:
                artifacts.append(artifact)

        # Check for XML tag format
        for match in self.JSON_ARTIFACT_PATTERN.finditer(llm_output):
            artifact = self._parse_match(match.group(1), match.group(2))
            if artifact:
                artifacts.append(artifact)

        return artifacts

    def _parse_match(self, artifact_type: str, artifact_data: str) -> Optional[ArtifactData]:
        """
        Parse a matched artifact.

        Args:
            artifact_type: The type identifier from the match
            artifact_data: The JSON data string

        Returns:
            Parsed ArtifactData or None if parsing failed
        """
        # Validate artifact type
        if artifact_type not in self._supported_types:
            if self.strict_mode:
                raise ValueError(f"Unsupported artifact type: {artifact_type}")
            return None

        # Parse JSON data
        try:
            parsed = json.loads(artifact_data.strip())

            # Ensure required fields
            if not isinstance(parsed, dict):
                if self.strict_mode:
                    raise ValueError("Artifact data must be a JSON object")
                return None

            # Build artifact data structure
            artifact: ArtifactData = {
                'type': f"artifact:{artifact_type}",
                'version': parsed.get('version', '1.0'),
                'title': parsed.get('title', 'Untitled'),
                'data': parsed.get('data', {}),
            }

            # Add optional metadata
            if 'metadata' in parsed:
                artifact['metadata'] = parsed['metadata']

            return artifact

        except json.JSONDecodeError as e:
            if self.strict_mode:
                raise ValueError(f"Invalid JSON in artifact: {e}")
            return None

    def has_artifacts(self, llm_output: str) -> bool:
        """
        Quick check if output contains any artifacts.

        Args:
            llm_output: The raw output text from the LLM

        Returns:
            True if at least one artifact is detected
        """
        return bool(
            self.ARTIFACT_PATTERN.search(llm_output) or
            self.JSON_ARTIFACT_PATTERN.search(llm_output)
        )

    def extract_text_without_artifacts(self, llm_output: str) -> str:
        """
        Extract regular text from output, removing artifact blocks.

        Args:
            llm_output: The raw output text from the LLM

        Returns:
            Text with artifact blocks removed
        """
        # Remove code fence artifacts
        text = self.ARTIFACT_PATTERN.sub('', llm_output)

        # Remove XML tag artifacts
        text = self.JSON_ARTIFACT_PATTERN.sub('', text)

        return text.strip()

    def validate_artifact(self, artifact: ArtifactData) -> tuple[bool, Optional[str]]:
        """
        Validate an artifact data structure.

        Args:
            artifact: The artifact data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if 'type' not in artifact:
            return False, "Missing required field 'type'"

        if 'data' not in artifact:
            return False, "Missing required field 'data'"

        # Validate type format
        if not artifact['type'].startswith('artifact:'):
            return False, "Type must start with 'artifact:'"

        artifact_type = artifact['type'].replace('artifact:', '')
        if artifact_type not in self._supported_types:
            return False, f"Unsupported artifact type: {artifact_type}"

        # Type-specific validation
        validation_result = self._validate_type_specific(artifact_type, artifact['data'])
        if not validation_result[0]:
            return validation_result

        return True, None

    def _validate_type_specific(self, artifact_type: str, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Perform type-specific validation on artifact data.

        Args:
            artifact_type: The artifact type
            data: The artifact data

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Add type-specific validation rules here
        validators = {
            'spreadsheet': self._validate_spreadsheet,
            'chart': self._validate_chart,
            'toolform': self._validate_toolform,
            'querybuilder': self._validate_querybuilder,
            'toolwizard': self._validate_toolwizard,
        }

        validator = validators.get(artifact_type)
        if validator:
            return validator(data)

        # Default: accept if data is a dict
        return True, None

    def _validate_spreadsheet(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate spreadsheet artifact data."""
        if 'columns' not in data:
            return False, "Spreadsheet artifact missing 'columns'"
        if 'rows' not in data:
            return False, "Spreadsheet artifact missing 'rows'"
        return True, None

    def _validate_chart(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate chart artifact data."""
        if 'chart_type' not in data:
            return False, "Chart artifact missing 'chart_type'"
        if 'data' not in data:
            return False, "Chart artifact missing 'data'"
        return True, None

    def _validate_toolform(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate toolform artifact data."""
        if 'tool_name' not in data:
            return False, "Toolform artifact missing 'tool_name'"
        if 'schema' not in data:
            return False, "Toolform artifact missing 'schema'"
        return True, None

    def _validate_querybuilder(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate querybuilder artifact data."""
        if 'available_tools' not in data:
            return False, "Querybuilder artifact missing 'available_tools'"
        return True, None

    def _validate_toolwizard(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate toolwizard artifact data."""
        if 'tool_name' not in data:
            return False, "Toolwizard artifact missing 'tool_name'"
        if 'steps' not in data:
            return False, "Toolwizard artifact missing 'steps'"
        return True, None
