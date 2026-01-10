# Tool-Based Interactive Artifacts - Design Extension

## Executive Summary

Extension to the LLM Artifact System that enables dynamic generation of interactive forms and user interfaces directly from MCP tool schemas. This allows users to interact with tools through visual interfaces without writing JSON or understanding complex syntax, while maintaining all the power and validation of the underlying tool system.

---

## Core Concept

**Tool-to-UI Pattern:**
```
Tool Schema (JSON Schema) → Dynamic Form Generation → User Interaction → Validated Tool Call → Result Display
```

**Key Benefits:**
1. **Zero Configuration**: Forms auto-generate from existing tool schemas
2. **Built-in Validation**: Schema constraints ensure valid inputs
3. **User-Friendly**: Visual interface instead of JSON syntax
4. **Context-Aware**: Pre-fill forms with conversation context
5. **Composable**: Chain multiple tool calls through workflows

---

## New Tool-Based Artifact Types

### 1. **Tool Form** (artifact:toolform)

**Use Case:** Single tool execution with visual form interface

**Format:**
```json
{
  "type": "artifact:toolform",
  "version": "1.0",
  "title": "File Reader",
  "data": {
    "tool_name": "builtin.read_file",
    "tool_description": "Read the contents of a file",
    "schema": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "The relative path to the file to read",
          "ui_widget": "file_picker",
          "ui_hints": {
            "placeholder": "e.g., src/main.py",
            "extensions": [".py", ".js", ".ts", ".md"]
          }
        },
        "offset": {
          "type": "integer",
          "description": "Line number to start reading from (1-indexed)",
          "minimum": 1,
          "ui_widget": "number",
          "ui_hints": {
            "placeholder": "1",
            "optional": true
          }
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of lines to read",
          "minimum": 1,
          "ui_widget": "number",
          "ui_hints": {
            "placeholder": "100",
            "optional": true
          }
        }
      },
      "required": ["path"]
    },
    "prefill": {
      "path": "docs/README.md"
    },
    "submit_button": {
      "label": "Read File",
      "icon": "file-text"
    },
    "result_display": {
      "type": "code",
      "syntax": "auto-detect"
    }
  }
}
```

**UI Features:**
- Auto-generated form fields from schema
- Field type detection (string → text input, integer → number input, boolean → checkbox)
- Required field indicators
- Validation on submit
- Loading state during execution
- Result display (inline or in new artifact)

**Renderer Implementation:**
```typescript
export const ToolFormRenderer: React.FC<{ data: ToolFormData }> = ({ data }) => {
  const [formValues, setFormValues] = useState(data.prefill || {});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    // Validate against schema
    const validation = validateAgainstSchema(formValues, data.schema);
    if (!validation.valid) {
      setErrors(validation.errors);
      return;
    }

    setLoading(true);
    try {
      // Call tool through MCP
      const response = await callTool(data.tool_name, formValues);
      setResult(response);
    } catch (error) {
      setErrors({ _form: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tool-form">
      <h3>{data.title}</h3>
      <p className="text-sm text-gray-600">{data.tool_description}</p>

      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
        {Object.entries(data.schema.properties).map(([key, prop]) => (
          <FormField
            key={key}
            name={key}
            schema={prop}
            value={formValues[key]}
            onChange={(value) => setFormValues({ ...formValues, [key]: value })}
            error={errors[key]}
            required={data.schema.required?.includes(key)}
          />
        ))}

        <button
          type="submit"
          disabled={loading}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
        >
          {loading ? 'Processing...' : data.submit_button.label}
        </button>
      </form>

      {result && (
        <div className="mt-4 result-display">
          <ResultRenderer type={data.result_display.type} data={result} />
        </div>
      )}
    </div>
  );
};
```

---

### 2. **Query Builder** (artifact:querybuilder)

**Use Case:** Visual interface for building complex queries or tool parameters

**Format:**
```json
{
  "type": "artifact:querybuilder",
  "version": "1.0",
  "title": "File Search Query",
  "data": {
    "target_tool": "builtin.list_files",
    "builder_type": "filter_builder",
    "filters": [
      {
        "id": "extension",
        "label": "File Extension",
        "type": "select",
        "options": [".py", ".js", ".ts", ".md", ".json"],
        "multi": true
      },
      {
        "id": "modified_after",
        "label": "Modified After",
        "type": "date"
      },
      {
        "id": "contains_text",
        "label": "Contains Text",
        "type": "text",
        "placeholder": "Search in filenames"
      },
      {
        "id": "size",
        "label": "File Size",
        "type": "range",
        "units": "KB",
        "min": 0,
        "max": 1000
      }
    ],
    "preview": {
      "enabled": true,
      "live": true
    },
    "actions": [
      {
        "id": "search",
        "label": "Search Files",
        "primary": true
      },
      {
        "id": "save_query",
        "label": "Save Query",
        "secondary": true
      }
    ]
  }
}
```

**UI Features:**
- Visual query construction
- Filter combination (AND/OR logic)
- Live preview of results
- Save/load query templates
- Export query as tool call JSON

---

### 3. **Tool Wizard** (artifact:toolwizard)

**Use Case:** Multi-step workflows requiring multiple tool calls

**Format:**
```json
{
  "type": "artifact:toolwizard",
  "version": "1.0",
  "title": "Create and Test Feature Wizard",
  "data": {
    "steps": [
      {
        "id": "step1_plan",
        "title": "Plan Feature",
        "description": "Define the feature you want to create",
        "tool": "builtin.add_feature",
        "schema": {
          "properties": {
            "goal_id": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"}
          }
        },
        "validation": {
          "continue_if": "success"
        }
      },
      {
        "id": "step2_implement",
        "title": "Write Code",
        "description": "Create the implementation file",
        "tool": "builtin.write_file",
        "schema": {
          "properties": {
            "path": {"type": "string"},
            "content": {"type": "string", "ui_widget": "code_editor"}
          }
        },
        "prefill": {
          "path": "{{step1_plan.result.feature_id}}.py"
        }
      },
      {
        "id": "step3_test",
        "title": "Run Tests",
        "description": "Verify the implementation",
        "tool": "builtin.run_pytest",
        "schema": {
          "properties": {
            "path": {"type": "string"}
          }
        },
        "prefill": {
          "path": "tests/test_{{step1_plan.result.feature_id}}.py"
        }
      },
      {
        "id": "step4_update",
        "title": "Update Status",
        "description": "Mark feature as completed",
        "tool": "builtin.update_feature_status",
        "schema": {
          "properties": {
            "feature_id": {"type": "string"},
            "status": {"type": "string", "enum": ["completed", "failed"]}
          }
        },
        "prefill": {
          "feature_id": "{{step1_plan.result.feature_id}}",
          "status": "{{step3_test.result.passed ? 'completed' : 'failed'}}"
        }
      }
    ],
    "navigation": {
      "allow_back": true,
      "show_progress": true,
      "confirm_exit": true
    }
  }
}
```

**UI Features:**
- Step-by-step wizard interface
- Progress indicator
- Step validation before proceeding
- Context passing between steps ({{step_id.result.field}})
- Back navigation with state preservation
- Summary view at the end

---

### 4. **Batch Tool Executor** (artifact:batchtool)

**Use Case:** Execute same tool on multiple inputs (batch processing)

**Format:**
```json
{
  "type": "artifact:batchtool",
  "version": "1.0",
  "title": "Batch File Processor",
  "data": {
    "tool": "builtin.read_file",
    "batch_source": {
      "type": "list",
      "items": [
        {"path": "src/file1.py"},
        {"path": "src/file2.py"},
        {"path": "src/file3.py"}
      ]
    },
    "execution": {
      "mode": "sequential",
      "continue_on_error": true,
      "max_concurrent": 3,
      "show_progress": true
    },
    "result_aggregation": {
      "type": "table",
      "columns": ["file", "status", "lines", "preview"],
      "export": true
    }
  }
}
```

**UI Features:**
- Input list management (add/remove/reorder)
- Execution modes (sequential, parallel, burst)
- Progress bar with current item
- Error handling options
- Results aggregation view
- Export batch results

---

### 5. **Tool Palette** (artifact:toolpalette)

**Use Case:** Quick access to frequently used tools with saved presets

**Format:**
```json
{
  "type": "artifact:toolpalette",
  "version": "1.0",
  "title": "Common Tasks",
  "data": {
    "categories": [
      {
        "id": "files",
        "label": "File Operations",
        "tools": [
          {
            "tool": "builtin.read_file",
            "label": "Quick Read",
            "icon": "file-text",
            "preset": {
              "limit": 50
            }
          },
          {
            "tool": "builtin.list_files",
            "label": "List Directory",
            "icon": "folder"
          }
        ]
      },
      {
        "id": "code",
        "label": "Code Tools",
        "tools": [
          {
            "tool": "builtin.execute_python_code",
            "label": "Run Python",
            "icon": "play",
            "preset": {
              "code": "# Enter your Python code here\n"
            }
          },
          {
            "tool": "builtin.run_pytest",
            "label": "Run Tests",
            "icon": "check-circle"
          }
        ]
      }
    ],
    "recent": {
      "enabled": true,
      "max_items": 5
    }
  }
}
```

**UI Features:**
- Categorized tool grid
- One-click tool launch with presets
- Recent tools list
- Favorite tools
- Search/filter tools
- Keyboard shortcuts

---

### 6. **Parameter Suggestions** (artifact:paramsuggestions)

**Use Case:** AI-suggested parameter values based on context

**Format:**
```json
{
  "type": "artifact:paramsuggestions",
  "version": "1.0",
  "title": "Smart File Reader",
  "data": {
    "tool": "builtin.read_file",
    "suggestions": {
      "path": {
        "values": [
          {
            "value": "docs/README.md",
            "reason": "Main documentation file",
            "confidence": 0.95
          },
          {
            "value": "src/main.py",
            "reason": "Entry point mentioned in conversation",
            "confidence": 0.85
          },
          {
            "value": "tests/test_api.py",
            "reason": "Recently accessed test file",
            "confidence": 0.7
          }
        ]
      },
      "limit": {
        "values": [
          {
            "value": 100,
            "reason": "Standard preview size",
            "confidence": 0.8
          },
          {
            "value": 50,
            "reason": "Quick glance",
            "confidence": 0.6
          }
        ]
      }
    },
    "auto_fill": {
      "enabled": true,
      "threshold": 0.9
    }
  }
}
```

**UI Features:**
- Suggested values with reasoning
- Confidence scores
- One-click accept suggestion
- Manual override always available
- Context-aware suggestions
- Learning from user corrections

---

## Schema-to-UI Widget Mapping

### Automatic Widget Selection

```typescript
interface UIWidgetMapping {
  // String types
  'string': {
    default: 'text',
    format: {
      'uri': 'url',
      'email': 'email',
      'date': 'date',
      'date-time': 'datetime',
      'time': 'time',
      'color': 'color-picker',
      'password': 'password'
    },
    pattern: {
      '^/.*': 'file-picker',  // Looks like file path
      '\\.(py|js|ts)$': 'code-editor-path'
    },
    enum: 'select',  // Fixed list of values
    minLength: (l) => l > 100 ? 'textarea' : 'text'
  },

  // Numeric types
  'integer': 'number',
  'number': 'number',

  // Boolean
  'boolean': 'checkbox',

  // Arrays
  'array': {
    items: {
      type: {
        'string': 'tag-input',
        'object': 'repeater'
      }
    }
  },

  // Objects
  'object': 'json-editor',

  // Custom UI hints (from schema)
  'ui_widget': 'override'  // Explicit widget type in schema
}
```

### Widget Components

#### 1. File Picker Widget
```typescript
<FilePicker
  value={value}
  onChange={onChange}
  extensions={['.py', '.js', '.ts']}
  basePath={workingDirectory}
  showRecent={true}
  allowMultiple={false}
/>
```

#### 2. Code Editor Widget
```typescript
<CodeEditor
  value={value}
  onChange={onChange}
  language="python"
  height="400px"
  theme="vs-dark"
  minimap={false}
/>
```

#### 3. Tag Input Widget (for arrays)
```typescript
<TagInput
  values={value}
  onChange={onChange}
  suggestions={['option1', 'option2']}
  allowCustom={true}
  validate={(tag) => tag.length > 0}
/>
```

#### 4. JSON Editor Widget
```typescript
<JSONEditor
  value={value}
  onChange={onChange}
  schema={propertySchema}
  validate={true}
  format={true}
/>
```

#### 5. Number Range Widget
```typescript
<NumberRange
  value={value}
  onChange={onChange}
  min={schema.minimum}
  max={schema.maximum}
  step={1}
  showInput={true}
/>
```

---

## Dynamic Form Generation from Tool Schema

### Tool Schema Parser

```python
# tool_schema_parser.py

class ToolSchemaParser:
    """Parse MCP tool schemas and generate artifact forms."""

    def __init__(self, tool_manager):
        self.tool_manager = tool_manager

    def generate_form_artifact(self, tool_name: str, prefill: dict = None) -> dict:
        """Generate a toolform artifact from a tool's schema."""
        tool = self.tool_manager.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")

        # Extract schema
        schema = tool.inputSchema

        # Add UI hints based on schema analysis
        enhanced_schema = self._add_ui_hints(schema)

        # Detect result display type
        result_display = self._infer_result_display(tool_name, schema)

        artifact = {
            "type": "artifact:toolform",
            "version": "1.0",
            "title": self._format_tool_name(tool_name),
            "data": {
                "tool_name": tool_name,
                "tool_description": tool.description,
                "schema": enhanced_schema,
                "prefill": prefill or {},
                "submit_button": {
                    "label": self._infer_action_label(tool_name),
                    "icon": self._infer_icon(tool_name)
                },
                "result_display": result_display
            }
        }

        return artifact

    def _add_ui_hints(self, schema: dict) -> dict:
        """Add UI hints to schema properties."""
        enhanced = schema.copy()

        for prop_name, prop_schema in schema.get("properties", {}).items():
            prop_type = prop_schema.get("type")

            # File path detection
            if prop_name in ["path", "file", "file_path", "directory"]:
                prop_schema["ui_widget"] = "file_picker"

            # Code content detection
            elif prop_name in ["code", "content", "script"]:
                if "description" in prop_schema and "code" in prop_schema["description"].lower():
                    prop_schema["ui_widget"] = "code_editor"

            # Command detection
            elif prop_name in ["command", "cmd"]:
                prop_schema["ui_widget"] = "command_input"
                prop_schema["ui_hints"] = {"mono": True}

            # Enum to select
            elif "enum" in prop_schema:
                prop_schema["ui_widget"] = "select"

            # Long text to textarea
            elif prop_type == "string" and prop_schema.get("minLength", 0) > 100:
                prop_schema["ui_widget"] = "textarea"

            # Optional fields
            if prop_name not in schema.get("required", []):
                prop_schema.setdefault("ui_hints", {})["optional"] = True

        return enhanced

    def _infer_result_display(self, tool_name: str, schema: dict) -> dict:
        """Infer how to display tool results."""
        # File operations → code display
        if "read_file" in tool_name or "list" in tool_name:
            return {"type": "code", "syntax": "auto-detect"}

        # Execute operations → terminal output
        if "execute" in tool_name or "run" in tool_name:
            return {"type": "terminal"}

        # Memory operations → structured data
        if "memory" in tool_name or "get_" in tool_name:
            return {"type": "json", "collapsible": True}

        # Default to text
        return {"type": "text"}

    def _infer_action_label(self, tool_name: str) -> str:
        """Infer button label from tool name."""
        if "read" in tool_name:
            return "Read"
        if "write" in tool_name:
            return "Write"
        if "execute" in tool_name:
            return "Execute"
        if "run" in tool_name:
            return "Run"
        if "list" in tool_name:
            return "List"
        return "Submit"

    def _infer_icon(self, tool_name: str) -> str:
        """Infer icon from tool name."""
        icon_map = {
            "file": "file-text",
            "read": "eye",
            "write": "edit",
            "execute": "play",
            "run": "play-circle",
            "list": "list",
            "delete": "trash",
            "create": "plus",
            "update": "refresh"
        }

        for keyword, icon in icon_map.items():
            if keyword in tool_name.lower():
                return icon

        return "tool"

    def _format_tool_name(self, tool_name: str) -> str:
        """Format tool name for display."""
        # builtin.read_file → Read File
        name = tool_name.split(".")[-1]
        words = name.replace("_", " ").split()
        return " ".join(word.capitalize() for word in words)
```

---

## Agent Integration

### Tool Form Generator Agent

```json
{
  "agent_type": "TOOL_FORM_AGENT",
  "display_name": "🛠️ Tool Form Generator",
  "description": "Generates interactive forms for tool execution",
  "system_prompt": "You generate interactive tool forms for the web UI.\n\nWhen users want to use a tool but need help with parameters:\n1. Identify the tool name\n2. Analyze conversation context for parameter suggestions\n3. Generate artifact:toolform with pre-filled values\n\nExample:\nUser: \"I want to read that README file we talked about\"\n\nYou respond:\n```artifact:toolform\n{\n  \"type\": \"artifact:toolform\",\n  \"version\": \"1.0\",\n  \"title\": \"Read File\",\n  \"data\": {\n    \"tool_name\": \"builtin.read_file\",\n    \"tool_description\": \"Read the contents of a file\",\n    \"schema\": {...},\n    \"prefill\": {\n      \"path\": \"docs/README.md\"\n    }\n  }\n}\n```\n\nFor complex workflows, use artifact:toolwizard.\nFor batch operations, use artifact:batchtool.\nFor quick access to common tools, use artifact:toolpalette.",
  "default_tools": ["builtin.list_files", "builtin.get_memory_state"],
  "temperature": 0.3
}
```

### Context-Aware Suggestions

```python
class ToolParameterSuggester:
    """Suggest tool parameters based on conversation context."""

    def __init__(self, chat_history, memory_state):
        self.chat_history = chat_history
        self.memory_state = memory_state

    def suggest_parameters(self, tool_name: str) -> dict:
        """Generate parameter suggestions with reasoning."""
        suggestions = {}

        if tool_name == "builtin.read_file":
            # Look for file mentions in recent conversation
            files_mentioned = self._extract_file_mentions(self.chat_history[-5:])

            suggestions["path"] = {
                "values": [
                    {
                        "value": file,
                        "reason": f"Mentioned {turns_ago} turns ago",
                        "confidence": 1.0 - (turns_ago * 0.1)
                    }
                    for file, turns_ago in files_mentioned
                ]
            }

        elif tool_name == "builtin.write_file":
            # Suggest path based on current working files
            current_feature = self.memory_state.get_current_feature()
            if current_feature:
                suggested_path = f"src/{current_feature['title'].lower().replace(' ', '_')}.py"
                suggestions["path"] = {
                    "values": [{
                        "value": suggested_path,
                        "reason": f"Working on feature: {current_feature['title']}",
                        "confidence": 0.85
                    }]
                }

        return suggestions
```

---

## Use Case Examples

### Example 1: Quick File Reader

**User:** "Show me a form to read files"

**LLM generates:**
```artifact:toolform
{
  "type": "artifact:toolform",
  "version": "1.0",
  "title": "File Reader",
  "data": {
    "tool_name": "builtin.read_file",
    "tool_description": "Read the contents of a file",
    "schema": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "The relative path to the file to read",
          "ui_widget": "file_picker"
        }
      },
      "required": ["path"]
    },
    "submit_button": {"label": "Read File", "icon": "file-text"},
    "result_display": {"type": "code", "syntax": "auto-detect"}
  }
}
```

### Example 2: Batch File Processor

**User:** "I need to read all the Python files in src/"

**LLM generates:**
```artifact:batchtool
{
  "type": "artifact:batchtool",
  "version": "1.0",
  "title": "Read Python Files",
  "data": {
    "tool": "builtin.read_file",
    "batch_source": {
      "type": "list_files",
      "directory": "src/",
      "pattern": "*.py"
    },
    "execution": {
      "mode": "parallel",
      "max_concurrent": 3,
      "show_progress": true
    },
    "result_aggregation": {
      "type": "table",
      "columns": ["file", "lines", "size", "preview"]
    }
  }
}
```

### Example 3: Feature Implementation Wizard

**User:** "Walk me through creating a new feature"

**LLM generates:**
```artifact:toolwizard
{
  "type": "artifact:toolwizard",
  "version": "1.0",
  "title": "New Feature Wizard",
  "data": {
    "steps": [
      {
        "id": "plan",
        "title": "Plan Feature",
        "tool": "builtin.add_feature",
        "schema": {...}
      },
      {
        "id": "implement",
        "title": "Write Code",
        "tool": "builtin.write_file",
        "prefill": {
          "path": "src/{{plan.result.feature_id}}.py"
        }
      },
      {
        "id": "test",
        "title": "Run Tests",
        "tool": "builtin.run_pytest"
      }
    ]
  }
}
```

---

## Integration with MCP Client

### Modified Tool Manager

```python
# In tool_manager.py

class ToolManager:
    def __init__(self):
        # ... existing init ...
        self.schema_parser = ToolSchemaParser(self)

    def get_tool_form(self, tool_name: str, context: dict = None) -> dict:
        """Generate interactive form for a tool."""
        # Generate base form from schema
        form = self.schema_parser.generate_form_artifact(tool_name)

        # Add context-aware suggestions
        if context:
            suggester = ToolParameterSuggester(
                context.get('chat_history', []),
                context.get('memory_state')
            )
            suggestions = suggester.suggest_parameters(tool_name)

            if suggestions:
                form['data']['suggestions'] = suggestions

        return form

    async def execute_from_form(self, tool_name: str, form_data: dict) -> dict:
        """Execute tool with validated form data."""
        tool = self.get_tool(tool_name)

        # Validate against schema
        validation = self.validate_tool_parameters(tool_name, form_data)
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors']
            }

        # Execute tool
        result = await self.call_tool(tool_name, form_data)

        return {
            'success': True,
            'result': result
        }
```

### Web UI Integration

```typescript
// ToolFormPanel.tsx
export const ToolFormPanel: React.FC = () => {
  const [currentForm, setCurrentForm] = useState(null);

  // Listen for tool form artifacts
  useEffect(() => {
    const subscription = artifactStream.subscribe((artifact) => {
      if (artifact.type === 'artifact:toolform') {
        setCurrentForm(artifact);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleFormSubmit = async (toolName: string, formData: any) => {
    const result = await executeToolFromForm(toolName, formData);

    // Display result as new artifact or inline
    if (result.success) {
      displayResult(result.result);
    } else {
      showErrors(result.errors);
    }
  };

  if (!currentForm) return null;

  return (
    <div className="tool-form-panel">
      <ToolFormRenderer
        data={currentForm.data}
        onSubmit={handleFormSubmit}
      />
    </div>
  );
};
```

---

## Advanced Features

### 1. Form Templates

Save commonly used tool configurations:

```json
{
  "type": "artifact:formtemplate",
  "templates": [
    {
      "id": "quick_read",
      "name": "Quick File Read",
      "tool": "builtin.read_file",
      "defaults": {
        "limit": 50
      }
    },
    {
      "id": "full_test_run",
      "name": "Full Test Suite",
      "tool": "builtin.run_pytest",
      "defaults": {
        "verbose": true,
        "extra_args": "--cov"
      }
    }
  ]
}
```

### 2. Conditional Fields

Show/hide fields based on other field values:

```json
{
  "properties": {
    "use_offset": {
      "type": "boolean",
      "description": "Specify a starting line"
    },
    "offset": {
      "type": "integer",
      "description": "Line number to start from",
      "ui_conditional": {
        "show_when": {
          "use_offset": true
        }
      }
    }
  }
}
```

### 3. Field Dependencies

Auto-populate fields based on other selections:

```json
{
  "properties": {
    "directory": {
      "type": "string",
      "ui_widget": "directory_picker"
    },
    "file": {
      "type": "string",
      "ui_widget": "file_picker",
      "ui_dependencies": {
        "basePath": "{{directory}}"
      }
    }
  }
}
```

### 4. Validation Preview

Show validation errors as user types:

```typescript
<FormField
  name="path"
  value={value}
  onChange={onChange}
  validate={async (value) => {
    // Check if file exists
    const exists = await checkFileExists(value);
    if (!exists) {
      return "File does not exist";
    }
    return null;
  }}
  validateOnChange={true}
/>
```

### 5. Multi-Tool Forms

Combine multiple tools in one form:

```json
{
  "type": "artifact:multitool",
  "version": "1.0",
  "title": "Read and Analyze File",
  "data": {
    "tools": [
      {
        "id": "read",
        "tool": "builtin.read_file",
        "label": "Read"
      },
      {
        "id": "analyze",
        "tool": "builtin.execute_python_code",
        "label": "Analyze",
        "input_mapping": {
          "code": "analyze_code('''{{read.result}}''')"
        }
      }
    ],
    "execution": "chain"
  }
}
```

---

## Benefits Summary

### For Users
1. **No JSON Syntax**: Visual forms instead of writing tool calls
2. **Validation**: Immediate feedback on invalid inputs
3. **Discovery**: See available tools and their parameters
4. **Efficiency**: Pre-filled forms from context
5. **Safety**: Preview before execution

### For Developers
1. **Zero Configuration**: Forms auto-generate from existing schemas
2. **Consistency**: Same validation as programmatic tool calls
3. **Extensibility**: New tools automatically get forms
4. **Type Safety**: Schema-driven UI components
5. **Testability**: Validate forms without executing tools

### For LLMs
1. **Structured Output**: Clear format for generating forms
2. **Context Integration**: Suggest parameters from conversation
3. **Progressive Disclosure**: Simple forms → wizards → batch tools
4. **Feedback Loop**: Form validation helps LLM learn correct parameters
5. **Composability**: Combine multiple tools into workflows

---

## Implementation Roadmap

### Phase 1: Basic Tool Forms
- [ ] Schema-to-form generation
- [ ] Basic widget types (text, number, checkbox, select)
- [ ] Form validation
- [ ] Result display

### Phase 2: Enhanced Widgets
- [ ] File picker with browse
- [ ] Code editor integration
- [ ] Tag input for arrays
- [ ] JSON editor for objects

### Phase 3: Advanced Features
- [ ] Query builder
- [ ] Tool wizard (multi-step)
- [ ] Batch tool executor
- [ ] Parameter suggestions

### Phase 4: Optimization
- [ ] Form templates
- [ ] Conditional fields
- [ ] Field dependencies
- [ ] Validation preview

### Phase 5: Ecosystem
- [ ] Tool palette
- [ ] Custom tool forms (user-defined)
- [ ] Form sharing/export
- [ ] Analytics and usage tracking

---

*Design Extension Version: 1.0*
*Last Updated: 2026-01-09*
*Extends: llm-artifact-system-design.md*
