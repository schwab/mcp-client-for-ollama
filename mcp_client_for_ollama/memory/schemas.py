"""
JSON schema definitions and domain-specific memory schemas.

This module defines domain-specific memory schemas for different agent contexts
(coding, research, operations, etc.) and provides validation.
"""

from enum import Enum
from typing import Dict, Any, Optional


class DomainType(str, Enum):
    """Types of domains for agent memory."""
    CODING = "coding"
    RESEARCH = "research"
    OPERATIONS = "operations"
    CONTENT = "content"
    GENERAL = "general"


class MemorySchema:
    """
    Schema definitions and validation for domain memory.

    Provides JSON schemas for validation and domain-specific defaults.
    """

    # Base schema for all domain memory
    BASE_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["metadata", "goals", "state", "progress_log", "artifacts"],
        "properties": {
            "metadata": {
                "type": "object",
                "required": ["session_id", "domain", "description", "created_at", "updated_at"],
                "properties": {
                    "session_id": {"type": "string"},
                    "domain": {"type": "string"},
                    "description": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "version": {"type": "string"},
                },
            },
            "goals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "description", "features", "status"],
                    "properties": {
                        "id": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "failed", "cancelled"],
                        },
                        "features": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "description", "status"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "description": {"type": "string"},
                                    "status": {
                                        "type": "string",
                                        "enum": ["pending", "in_progress", "completed", "failed", "blocked"],
                                    },
                                    "criteria": {"type": "array", "items": {"type": "string"}},
                                    "tests": {"type": "array", "items": {"type": "string"}},
                                    "notes": {"type": "string"},
                                },
                            },
                        },
                        "constraints": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "state": {"type": "object"},
            "progress_log": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["timestamp", "agent_type", "action", "outcome", "details"],
                    "properties": {
                        "timestamp": {"type": "string", "format": "date-time"},
                        "agent_type": {"type": "string"},
                        "action": {"type": "string"},
                        "outcome": {
                            "type": "string",
                            "enum": ["success", "failure", "partial", "blocked"],
                        },
                        "details": {"type": "string"},
                        "feature_id": {"type": "string"},
                        "artifacts_changed": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "artifacts": {"type": "object"},
        },
    }

    @staticmethod
    def get_domain_defaults(domain: DomainType) -> Dict[str, Any]:
        """Get default state structure for a specific domain."""
        if domain == DomainType.CODING:
            return {
                "test_harness": {
                    "framework": "pytest",
                    "test_dirs": ["tests/"],
                    "run_command": "pytest -v",
                    "coverage_enabled": False,
                },
                "scaffolding": {
                    "git_enabled": True,
                    "auto_commit": False,
                    "required_files": ["README.md"],
                    "language": None,  # Auto-detect
                },
                "build": {
                    "build_command": None,
                    "clean_command": None,
                },
            }

        elif domain == DomainType.RESEARCH:
            return {
                "hypothesis_tracking": {
                    "active_hypotheses": [],
                    "confirmed_hypotheses": [],
                    "rejected_hypotheses": [],
                },
                "experiment_registry": [],
                "evidence_log": [],
                "decision_journal": [],
                "literature_review": {
                    "papers_reviewed": [],
                    "key_findings": [],
                },
            }

        elif domain == DomainType.OPERATIONS:
            return {
                "runbooks": [],
                "incidents": {
                    "active": [],
                    "resolved": [],
                },
                "tickets": {
                    "open": [],
                    "in_progress": [],
                    "closed": [],
                },
                "sla_metrics": {
                    "uptime": 100.0,
                    "response_time": 0.0,
                    "resolution_time": 0.0,
                },
                "monitoring": {
                    "alerts": [],
                    "health_checks": [],
                },
            }

        elif domain == DomainType.CONTENT:
            return {
                "content_calendar": [],
                "drafts": {},
                "style_guide": {
                    "voice": "professional",
                    "tone": "informative",
                    "guidelines": [],
                },
                "publication_log": [],
                "audience_feedback": {
                    "engagement_metrics": {},
                    "comments": [],
                },
            }

        else:  # GENERAL
            return {
                "notes": [],
                "references": [],
            }

    @staticmethod
    def get_domain_artifact_templates(domain: DomainType) -> Dict[str, str]:
        """
        Get template paths for domain-specific artifacts.

        Returns a mapping of artifact names to their expected locations
        relative to the session directory.
        """
        if domain == DomainType.CODING:
            return {
                "features": "features.json",
                "progress": "progress.log",
                "tests": "test_results.json",
                "readme": "README.md",
            }

        elif domain == DomainType.RESEARCH:
            return {
                "hypotheses": "hypotheses.json",
                "experiments": "experiments.json",
                "evidence": "evidence.log",
                "decisions": "decisions.md",
                "literature": "literature.md",
            }

        elif domain == DomainType.OPERATIONS:
            return {
                "runbooks": "runbooks/",
                "incidents": "incidents.json",
                "tickets": "tickets.json",
                "metrics": "metrics.json",
            }

        elif domain == DomainType.CONTENT:
            return {
                "calendar": "calendar.json",
                "drafts": "drafts/",
                "style_guide": "style_guide.md",
                "publications": "publications.json",
            }

        else:  # GENERAL
            return {
                "notes": "notes.md",
            }

    @staticmethod
    def get_feature_criteria_templates(domain: DomainType) -> Dict[str, list]:
        """Get common feature criteria templates for a domain."""
        if domain == DomainType.CODING:
            return {
                "implementation": [
                    "Code implements the specified functionality",
                    "Code follows project style guidelines",
                    "Code is properly documented",
                ],
                "testing": [
                    "Unit tests written and passing",
                    "Integration tests passing",
                    "Code coverage meets threshold",
                ],
                "quality": [
                    "No linting errors",
                    "No type errors",
                    "No security vulnerabilities",
                ],
            }

        elif domain == DomainType.RESEARCH:
            return {
                "hypothesis": [
                    "Hypothesis clearly stated",
                    "Testable prediction defined",
                    "Success criteria specified",
                ],
                "experiment": [
                    "Methodology documented",
                    "Data collection plan defined",
                    "Analysis approach specified",
                ],
                "validation": [
                    "Results analyzed",
                    "Conclusions drawn",
                    "Limitations documented",
                ],
            }

        elif domain == DomainType.OPERATIONS:
            return {
                "incident_response": [
                    "Issue identified and documented",
                    "Root cause determined",
                    "Resolution implemented",
                    "Postmortem completed",
                ],
                "runbook": [
                    "Steps clearly documented",
                    "Prerequisites specified",
                    "Rollback procedure defined",
                ],
            }

        elif domain == DomainType.CONTENT:
            return {
                "draft": [
                    "Outline completed",
                    "First draft written",
                    "Edited and revised",
                    "Style guide followed",
                ],
                "publication": [
                    "Content finalized",
                    "Metadata added",
                    "Published to platform",
                    "Promotion scheduled",
                ],
            }

        else:  # GENERAL
            return {
                "task": [
                    "Task completed as specified",
                    "Documentation updated",
                ],
            }

    @staticmethod
    def validate_memory_structure(memory_dict: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate memory structure against schema.

        Returns:
            (is_valid, error_message)
        """
        try:
            # Check required top-level keys
            required_keys = ["metadata", "goals", "state", "progress_log", "artifacts"]
            missing_keys = [k for k in required_keys if k not in memory_dict]
            if missing_keys:
                return False, f"Missing required keys: {', '.join(missing_keys)}"

            # Check metadata
            metadata = memory_dict.get("metadata", {})
            required_metadata = ["session_id", "domain", "description", "created_at", "updated_at"]
            missing_metadata = [k for k in required_metadata if k not in metadata]
            if missing_metadata:
                return False, f"Missing metadata keys: {', '.join(missing_metadata)}"

            # Check goals structure
            goals = memory_dict.get("goals", [])
            if not isinstance(goals, list):
                return False, "Goals must be a list"

            for i, goal in enumerate(goals):
                if not isinstance(goal, dict):
                    return False, f"Goal {i} must be a dictionary"
                if "id" not in goal or "description" not in goal:
                    return False, f"Goal {i} missing required fields (id, description)"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"
