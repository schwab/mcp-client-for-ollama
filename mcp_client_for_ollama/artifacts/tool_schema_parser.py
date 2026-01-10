"""Tool schema parser for generating interactive forms from MCP tools."""

import re
from typing import Dict, Any, List, Optional, Set
from .types import UIWidget, ToolFormData, QueryBuilderData, ToolWizardData, BatchToolData


class ToolSchemaParser:
    """Parse MCP tool schemas and generate artifact forms."""

    # Widget mapping based on JSON Schema types
    WIDGET_MAPPING = {
        'string': {
            'default': UIWidget.TEXT,
            'format': {
                'uri': UIWidget.URL,
                'email': UIWidget.EMAIL,
                'date': UIWidget.DATE,
                'time': UIWidget.TIME,
                'date-time': UIWidget.DATETIME,
                'password': UIWidget.PASSWORD,
                'color': UIWidget.COLOR,
            },
            'pattern': {
                r'^/.*': UIWidget.FILE_PICKER,  # Looks like file path
                r'^\w+://.*': UIWidget.URL,  # Looks like URL
            },
            'minLength_threshold': 100,  # Use textarea for long strings
        },
        'integer': UIWidget.NUMBER,
        'number': UIWidget.NUMBER,
        'boolean': UIWidget.CHECKBOX,
        'array': UIWidget.TAG_INPUT,
        'object': UIWidget.JSON_EDITOR,
    }

    # Keywords that suggest specific widgets
    KEYWORD_HINTS = {
        'path': UIWidget.FILE_PICKER,
        'file': UIWidget.FILE_PICKER,
        'file_path': UIWidget.FILE_PICKER,
        'filepath': UIWidget.FILE_PICKER,
        'directory': UIWidget.DIRECTORY_PICKER,
        'dir': UIWidget.DIRECTORY_PICKER,
        'folder': UIWidget.DIRECTORY_PICKER,
        'code': UIWidget.CODE_EDITOR,
        'script': UIWidget.CODE_EDITOR,
        'content': UIWidget.TEXTAREA,
        'description': UIWidget.TEXTAREA,
        'message': UIWidget.TEXTAREA,
        'text': UIWidget.TEXTAREA,
        'url': UIWidget.URL,
        'email': UIWidget.EMAIL,
        'password': UIWidget.PASSWORD,
        'color': UIWidget.COLOR,
        'colour': UIWidget.COLOR,
    }

    def __init__(self, tool_manager: Any = None):
        """
        Initialize the ToolSchemaParser.

        Args:
            tool_manager: Reference to the tool manager to access available tools
        """
        self.tool_manager = tool_manager

    def generate_form_artifact(
        self,
        tool_name: str,
        prefill: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a toolform artifact from a tool schema.

        Args:
            tool_name: The name of the tool
            prefill: Optional dictionary of prefilled values
            context: Optional context for generating suggestions

        Returns:
            Artifact data dictionary
        """
        # Get tool schema
        tool = self._get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        schema = tool.get('inputSchema', {})

        # Add UI hints based on schema analysis
        enhanced_schema = self._add_ui_hints(schema)

        # Generate parameter suggestions from context
        suggestions = {}
        if context:
            suggestions = self._generate_parameter_suggestions(tool_name, schema, context)

        # Merge prefill and suggestions
        prefill_data = {**suggestions, **(prefill or {})}

        artifact = {
            "type": "artifact:toolform",
            "version": "1.0",
            "title": self._format_tool_name(tool_name),
            "data": {
                "tool_name": tool_name,
                "tool_description": tool.get('description', ''),
                "schema": enhanced_schema,
                "prefill": prefill_data,
                "submit_button": {
                    "label": self._infer_action_label(tool_name),
                    "icon": self._infer_icon(tool_name)
                },
                "result_display": self._infer_result_display(tool_name, schema)
            }
        }
        return artifact

    def generate_query_builder_artifact(
        self,
        available_tools: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a querybuilder artifact.

        Args:
            available_tools: List of available tool names
            context: Optional context for generating suggestions

        Returns:
            Artifact data dictionary
        """
        if available_tools is None and self.tool_manager:
            available_tools = self._get_all_tool_names()

        # Categorize tools
        tool_categories = self._categorize_tools(available_tools or [])

        # Get common patterns (could be loaded from config or history)
        common_patterns = self._get_common_patterns()

        # Generate suggested tools based on context
        suggested_tools = []
        if context:
            suggested_tools = self._suggest_tools_from_context(context, available_tools or [])

        artifact = {
            "type": "artifact:querybuilder",
            "version": "1.0",
            "title": "Build a Query",
            "data": {
                "available_tools": available_tools or [],
                "tool_categories": tool_categories,
                "common_patterns": common_patterns,
                "recent_queries": context.get('recent_queries', []) if context else [],
                "suggested_tools": suggested_tools,
            }
        }
        return artifact

    def generate_wizard_artifact(
        self,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a toolwizard artifact with multi-step workflow.

        Args:
            tool_name: The name of the tool
            context: Optional context for the wizard

        Returns:
            Artifact data dictionary
        """
        tool = self._get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        schema = tool.get('inputSchema', {})

        # Break schema into logical steps
        steps = self._create_wizard_steps(schema, tool.get('description', ''))

        artifact = {
            "type": "artifact:toolwizard",
            "version": "1.0",
            "title": f"{self._format_tool_name(tool_name)} Wizard",
            "data": {
                "tool_name": tool_name,
                "steps": steps,
                "current_step": 0,
                "context": context or {},
                "navigation": {
                    "can_skip_optional": True,
                    "show_progress": True,
                    "allow_back": True,
                }
            }
        }
        return artifact

    def generate_batch_artifact(
        self,
        tool_name: str,
        batch_inputs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a batchtool artifact for executing a tool multiple times.

        Args:
            tool_name: The name of the tool
            batch_inputs: Optional list of input parameter sets

        Returns:
            Artifact data dictionary
        """
        tool = self._get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        schema = tool.get('inputSchema', {})
        enhanced_schema = self._add_ui_hints(schema)

        artifact = {
            "type": "artifact:batchtool",
            "version": "1.0",
            "title": f"Batch {self._format_tool_name(tool_name)}",
            "data": {
                "tool_name": tool_name,
                "schema": enhanced_schema,
                "input_method": "manual",  # manual, csv, json
                "batch_inputs": batch_inputs or [],
                "execution_options": {
                    "parallel": False,
                    "stop_on_error": True,
                    "show_progress": True,
                }
            }
        }
        return artifact

    def _get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool definition from tool manager."""
        if not self.tool_manager:
            return None

        # Try to get tool from manager
        if hasattr(self.tool_manager, 'get_tool'):
            return self.tool_manager.get_tool(tool_name)

        # Fallback: try to get from tools list
        if hasattr(self.tool_manager, 'get_builtin_tools'):
            tools = self.tool_manager.get_builtin_tools()
            for tool in tools:
                if tool.name == tool_name:
                    return {
                        'name': tool.name,
                        'description': tool.description,
                        'inputSchema': tool.inputSchema
                    }

        return None

    def _get_all_tool_names(self) -> List[str]:
        """Get list of all available tool names."""
        if not self.tool_manager:
            return []

        if hasattr(self.tool_manager, 'get_builtin_tools'):
            tools = self.tool_manager.get_builtin_tools()
            return [tool.name for tool in tools]

        return []

    def _add_ui_hints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add UI hints to schema properties.

        Args:
            schema: The JSON Schema object

        Returns:
            Enhanced schema with UI hints
        """
        enhanced = schema.copy()

        if 'properties' not in enhanced:
            return enhanced

        for prop_name, prop_schema in enhanced['properties'].items():
            # Infer widget from property name
            widget = self._infer_widget_from_name(prop_name)

            if not widget:
                # Infer from type and format
                widget = self._infer_widget_from_schema(prop_schema)

            if widget:
                prop_schema['ui_widget'] = widget.value

            # Add UI hints
            prop_schema['ui_hints'] = self._generate_ui_hints(
                prop_name, prop_schema, schema.get('required', [])
            )

        return enhanced

    def _infer_widget_from_name(self, prop_name: str) -> Optional[UIWidget]:
        """Infer UI widget from property name."""
        prop_lower = prop_name.lower()

        # Check keyword hints
        for keyword, widget in self.KEYWORD_HINTS.items():
            if keyword in prop_lower:
                return widget

        return None

    def _infer_widget_from_schema(self, prop_schema: Dict[str, Any]) -> Optional[UIWidget]:
        """Infer UI widget from schema definition."""
        schema_type = prop_schema.get('type')

        if not schema_type:
            return None

        # Check for enum (select dropdown)
        if 'enum' in prop_schema:
            return UIWidget.SELECT

        # Get base widget for type
        if schema_type not in self.WIDGET_MAPPING:
            return None

        type_mapping = self.WIDGET_MAPPING[schema_type]

        # Handle string type with special logic
        if schema_type == 'string':
            # Check format
            if 'format' in prop_schema:
                format_widget = type_mapping['format'].get(prop_schema['format'])
                if format_widget:
                    return format_widget

            # Check pattern
            if 'pattern' in prop_schema:
                pattern = prop_schema['pattern']
                for pattern_regex, widget in type_mapping['pattern'].items():
                    if re.match(pattern_regex, pattern):
                        return widget

            # Check length for textarea
            if 'minLength' in prop_schema:
                if prop_schema['minLength'] >= type_mapping['minLength_threshold']:
                    return UIWidget.TEXTAREA

            return type_mapping['default']

        # Return widget directly for other types
        if isinstance(type_mapping, UIWidget):
            return type_mapping

        return type_mapping.get('default')

    def _generate_ui_hints(
        self,
        prop_name: str,
        prop_schema: Dict[str, Any],
        required: List[str]
    ) -> Dict[str, Any]:
        """Generate UI hints for a property."""
        hints = {}

        # Placeholder from description or example
        if 'description' in prop_schema:
            hints['help_text'] = prop_schema['description']

        if 'examples' in prop_schema:
            hints['placeholder'] = str(prop_schema['examples'][0])
        elif 'default' in prop_schema:
            hints['placeholder'] = str(prop_schema['default'])

        # Required field
        hints['optional'] = prop_name not in required

        # Validation hints
        if 'minimum' in prop_schema:
            hints['min'] = prop_schema['minimum']
        if 'maximum' in prop_schema:
            hints['max'] = prop_schema['maximum']
        if 'minLength' in prop_schema:
            hints['minLength'] = prop_schema['minLength']
        if 'maxLength' in prop_schema:
            hints['maxLength'] = prop_schema['maxLength']
        if 'pattern' in prop_schema:
            hints['pattern'] = prop_schema['pattern']

        return hints

    def _generate_parameter_suggestions(
        self,
        tool_name: str,
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate parameter value suggestions from context."""
        suggestions = {}

        # Extract from chat history
        if 'chat_history' in context:
            # Look for mentioned files, paths, values in recent messages
            suggestions.update(self._extract_from_chat_history(schema, context['chat_history']))

        # Extract from memory state
        if 'memory_state' in context:
            suggestions.update(self._extract_from_memory(schema, context['memory_state']))

        return suggestions

    def _extract_from_chat_history(
        self,
        schema: Dict[str, Any],
        chat_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract parameter values from chat history."""
        suggestions = {}

        # Get recent messages (last 5)
        recent_messages = chat_history[-5:] if len(chat_history) > 5 else chat_history

        # Look for file paths mentioned
        for message in recent_messages:
            content = message.get('content', '')

            # Extract file paths
            file_paths = re.findall(r'[/~][\w/.-]+', content)
            if file_paths and 'properties' in schema:
                for prop_name, prop_schema in schema['properties'].items():
                    if 'path' in prop_name.lower() or 'file' in prop_name.lower():
                        suggestions[prop_name] = file_paths[0]
                        break

        return suggestions

    def _extract_from_memory(
        self,
        schema: Dict[str, Any],
        memory_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract parameter values from memory state."""
        suggestions = {}

        # This could be enhanced based on actual memory structure
        # For now, just a placeholder implementation

        return suggestions

    def _format_tool_name(self, tool_name: str) -> str:
        """Format tool name for display."""
        # Remove 'builtin.' prefix if present
        name = tool_name.replace('builtin.', '')

        # Convert snake_case to Title Case
        name = name.replace('_', ' ').title()

        return name

    def _infer_action_label(self, tool_name: str) -> str:
        """Infer action button label from tool name."""
        name = tool_name.replace('builtin.', '').lower()

        # Common action verbs
        if name.startswith('read'):
            return "Read"
        elif name.startswith('write'):
            return "Write"
        elif name.startswith('execute'):
            return "Execute"
        elif name.startswith('list'):
            return "List"
        elif name.startswith('create'):
            return "Create"
        elif name.startswith('delete'):
            return "Delete"
        elif name.startswith('update'):
            return "Update"
        elif name.startswith('get'):
            return "Get"
        elif name.startswith('set'):
            return "Set"
        else:
            return "Submit"

    def _infer_icon(self, tool_name: str) -> str:
        """Infer icon name from tool name."""
        name = tool_name.replace('builtin.', '').lower()

        # Map to common icon names (using Lucide icon names as reference)
        icon_map = {
            'read': 'file-text',
            'write': 'edit',
            'execute': 'play',
            'list': 'list',
            'create': 'plus',
            'delete': 'trash',
            'update': 'refresh-cw',
            'get': 'download',
            'set': 'settings',
            'file': 'file',
            'directory': 'folder',
            'bash': 'terminal',
            'python': 'code',
            'test': 'test-tube',
        }

        for keyword, icon in icon_map.items():
            if keyword in name:
                return icon

        return 'tool'

    def _infer_result_display(self, tool_name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Infer how to display tool execution results."""
        name = tool_name.replace('builtin.', '').lower()

        # Default display config
        display = {
            "type": "text",
            "syntax": "plain"
        }

        # Specific display types based on tool
        if 'read_file' in name or 'read' in name:
            display = {"type": "code", "syntax": "auto-detect"}
        elif 'list' in name:
            display = {"type": "list"}
        elif 'execute' in name and 'python' in name:
            display = {"type": "code", "syntax": "python"}
        elif 'execute' in name and 'bash' in name:
            display = {"type": "terminal"}
        elif 'get_config' in name or 'config' in name:
            display = {"type": "json"}

        return display

    def _categorize_tools(self, tool_names: List[str]) -> Dict[str, List[str]]:
        """Categorize tools by function."""
        categories: Dict[str, List[str]] = {
            "File Operations": [],
            "Code Execution": [],
            "Configuration": [],
            "Memory Management": [],
            "System": [],
            "Other": [],
        }

        for tool_name in tool_names:
            name_lower = tool_name.lower()

            if any(kw in name_lower for kw in ['file', 'read', 'write', 'directory', 'list']):
                categories["File Operations"].append(tool_name)
            elif any(kw in name_lower for kw in ['execute', 'python', 'bash', 'pytest']):
                categories["Code Execution"].append(tool_name)
            elif any(kw in name_lower for kw in ['config', 'set_system', 'mcp_server']):
                categories["Configuration"].append(tool_name)
            elif any(kw in name_lower for kw in ['memory', 'feature', 'goal', 'progress']):
                categories["Memory Management"].append(tool_name)
            elif any(kw in name_lower for kw in ['validate', 'exists', 'info']):
                categories["System"].append(tool_name)
            else:
                categories["Other"].append(tool_name)

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def _get_common_patterns(self) -> List[Dict[str, Any]]:
        """Get common tool usage patterns."""
        return [
            {
                "name": "Read and analyze file",
                "tools": ["builtin.read_file"],
                "description": "Read a file and analyze its contents"
            },
            {
                "name": "Write and test code",
                "tools": ["builtin.write_file", "builtin.run_pytest"],
                "description": "Write code to a file and run tests"
            },
            {
                "name": "Execute Python script",
                "tools": ["builtin.execute_python_code"],
                "description": "Execute Python code directly"
            },
        ]

    def _suggest_tools_from_context(
        self,
        context: Dict[str, Any],
        available_tools: List[str]
    ) -> List[str]:
        """Suggest tools based on context."""
        suggestions = []

        # Check if user mentioned files recently
        if 'chat_history' in context:
            recent_content = ' '.join([
                msg.get('content', '')
                for msg in context['chat_history'][-3:]
            ])

            if 'file' in recent_content.lower() or 'read' in recent_content.lower():
                if 'builtin.read_file' in available_tools:
                    suggestions.append('builtin.read_file')

            if 'test' in recent_content.lower():
                if 'builtin.run_pytest' in available_tools:
                    suggestions.append('builtin.run_pytest')

        return suggestions[:5]  # Limit to top 5 suggestions

    def _create_wizard_steps(
        self,
        schema: Dict[str, Any],
        description: str
    ) -> List[Dict[str, Any]]:
        """Create wizard steps from schema."""
        steps = []

        properties = schema.get('properties', {})
        required = schema.get('required', [])

        # Group properties into logical steps
        # Step 1: Required parameters
        required_props = {k: v for k, v in properties.items() if k in required}
        if required_props:
            steps.append({
                "title": "Required Information",
                "description": "Please provide the required parameters",
                "fields": list(required_props.keys()),
                "validation": "required"
            })

        # Step 2: Optional parameters
        optional_props = {k: v for k, v in properties.items() if k not in required}
        if optional_props:
            steps.append({
                "title": "Optional Settings",
                "description": "Configure additional options (optional)",
                "fields": list(optional_props.keys()),
                "validation": "optional"
            })

        # Step 3: Review and confirm
        steps.append({
            "title": "Review & Submit",
            "description": "Review your inputs and submit",
            "fields": [],
            "validation": "review"
        })

        return steps
