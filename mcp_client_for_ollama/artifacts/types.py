"""Type definitions for the artifact system."""

from enum import Enum
from typing import Dict, Any, List, Optional, TypedDict


class ArtifactType(str, Enum):
    """Supported artifact types."""

    # Base artifact types
    SPREADSHEET = "spreadsheet"
    CHART = "chart"
    GRAPH = "graph"
    TIMELINE = "timeline"
    KANBAN = "kanban"
    CODE = "code"
    MARKDOWN = "markdown"
    DIFF = "diff"
    FILETREE = "filetree"
    MAP = "map"
    SLIDES = "slides"
    CALENDAR = "calendar"
    DASHBOARD = "dashboard"
    FORM = "form"
    MINDMAP = "mindmap"

    # Tool-based artifact types
    TOOLFORM = "toolform"
    QUERYBUILDER = "querybuilder"
    TOOLWIZARD = "toolwizard"
    BATCHTOOL = "batchtool"
    TOOLPALETTE = "toolpalette"
    PARAMSUGGESTIONS = "paramsuggestions"


class ArtifactData(TypedDict, total=False):
    """Type definition for artifact data structure."""
    type: str
    version: str
    title: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]]


class UIWidget(str, Enum):
    """UI widget types for form generation."""
    TEXT = "text"
    NUMBER = "number"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    SELECT = "select"
    MULTISELECT = "multiselect"
    FILE_PICKER = "file_picker"
    DIRECTORY_PICKER = "directory_picker"
    CODE_EDITOR = "code_editor"
    JSON_EDITOR = "json_editor"
    TAG_INPUT = "tag_input"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    COLOR = "color"
    URL = "url"
    EMAIL = "email"
    PASSWORD = "password"
    SLIDER = "slider"
    RADIO = "radio"


class ToolFormData(TypedDict, total=False):
    """Type definition for tool form artifact data."""
    tool_name: str
    tool_description: str
    schema: Dict[str, Any]
    prefill: Dict[str, Any]
    submit_button: Dict[str, str]
    result_display: Dict[str, Any]
    validation_rules: Optional[List[Dict[str, Any]]]


class QueryBuilderData(TypedDict, total=False):
    """Type definition for query builder artifact data."""
    available_tools: List[str]
    tool_categories: Dict[str, List[str]]
    common_patterns: List[Dict[str, Any]]
    recent_queries: List[Dict[str, Any]]
    suggested_tools: List[str]


class ToolWizardData(TypedDict, total=False):
    """Type definition for tool wizard artifact data."""
    tool_name: str
    steps: List[Dict[str, Any]]
    current_step: int
    context: Dict[str, Any]
    navigation: Dict[str, bool]


class BatchToolData(TypedDict, total=False):
    """Type definition for batch tool artifact data."""
    tool_name: str
    schema: Dict[str, Any]
    input_method: str
    batch_inputs: List[Dict[str, Any]]
    execution_options: Dict[str, Any]
