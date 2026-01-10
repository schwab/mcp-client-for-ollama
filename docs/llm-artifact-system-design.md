# LLM Artifact System - Comprehensive Design Document

## Executive Summary

A framework for LLMs (specifically Ollama) to generate rich, interactive artifacts that can be detected, parsed, and rendered in a web UI with advanced user interactions. This system enables LLMs to produce structured outputs that go beyond simple text, creating interactive visualizations, editable data tables, executable code, and more.

---

## Core Concept

**Artifact Pattern:**
```
LLM Output → Artifact Detection → Specialized Renderer → Interactive UI Component
```

**Key Principles:**
1. LLMs generate structured output with special markers
2. Parser detects artifact type from markers/metadata
3. Specialized renderers display each artifact type
4. User can interact with artifacts (edit, export, regenerate)
5. Artifacts can be versioned and refined iteratively

---

## Artifact Format Specification

### Universal Artifact Wrapper

All artifacts use a consistent envelope format for detection:

```markdown
```artifact:type
{
  "id": "unique-artifact-id",
  "type": "artifact_type",
  "title": "Display Title",
  "metadata": {},
  "content": { ... }
}
```
```

---

## Comprehensive Artifact Types

> **Note:** See [tool-based-artifacts-extension.md](./tool-based-artifacts-extension.md) for additional tool-based interactive artifacts including dynamic forms, query builders, and multi-step wizards.

### 1. **Interactive Data Table / Spreadsheet**

**Use Case:** Displaying structured data with sorting, filtering, editing

**Format:**
```json
{
  "type": "spreadsheet",
  "version": "1.0",
  "data": {
    "columns": [
      {"field": "name", "header": "Name", "type": "string", "editable": true},
      {"field": "age", "type": "number", "format": "integer"},
      {"field": "salary", "type": "number", "format": "currency"}
    ],
    "rows": [
      {"name": "Alice", "age": 30, "salary": 75000},
      {"name": "Bob", "age": 25, "salary": 65000}
    ],
    "features": {
      "sortable": true,
      "filterable": true,
      "editable": false,
      "exportable": true
    }
  }
}
```

**Capabilities:**
- Sort by column
- Filter rows
- Search
- Export to CSV/Excel
- Formula support (optional)
- Cell highlighting/validation

---

### 2. Interactive Charts & Graphs (D3.js/Chart.js)

**Format:** `artifact:chart`

**Schema:**
```json
{
  "type": "artifact",
  "artifact_type": "chart",
  "chart_type": "line|bar|pie|scatter|area|radar|...",
  "title": "Chart Title",
  "data": {
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "datasets": [
      {
        "label": "Revenue",
        "data": [100, 150, 200, 180],
        "backgroundColor": "#4CAF50"
      }
    ]
  },
  "options": {
    "responsive": true,
    "plugins": {
      "legend": {"position": "top"},
      "title": {"display": true, "text": "Quarterly Revenue"}
    }
  }
}
```

**Rendering:** Chart.js or D3.js integration

---

### 2. Interactive Spreadsheet

**Format:** `artifact:spreadsheet`

```json
{
  "type": "spreadsheet",
  "title": "Sales Data Q4 2025",
  "data": {
    "headers": ["Product", "Q1", "Q2", "Q3", "Q4", "Total"],
    "rows": [
      ["Product A", 100, 150, 200, 250],
      ["Product B", 200, 180, 220, 190],
      ["Product C", 150, 200, 180, 220]
    ]
  },
  "features": {
    "editable": true,
    "sortable": true,
    "filterable": true,
    "exportFormats": ["csv", "json", "xlsx"]
  },
  "metadata": {
    "title": "Q4 Sales Data",
    "source": "database query"
  }
}
```

**Display Features:**
- Inline editing with validation
- Column sorting and filtering
- Formula support
- Export to CSV/Excel
- Cell formatting (currency, dates, etc.)

**Use Cases:**
- Data analysis results
- Financial reports
- Comparison tables
- Query results

---

### 2. Interactive Charts & Graphs (D3.js/Chart.js)

**Format:**
```json
{
  "type": "artifact:chart",
  "version": "1.0",
  "chart_type": "line|bar|pie|scatter|tree|sankey|network",
  "title": "Chart Title",
  "data": {
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "datasets": [
      {
        "label": "Revenue",
        "data": [100, 150, 200, 180],
        "color": "#4F46E5"
      }
    ]
  },
  "options": {
    "responsive": true,
    "plugins": {
      "legend": { "position": "top" }
    }
  }
}
```

**Supported Chart Types:**
- Line charts (time series)
- Bar/column charts
- Pie/donut charts
- Scatter plots
- Heatmaps
- Network graphs

**Skills Required:**
- D3.js or Chart.js
- SVG manipulation
- Data transformation
- Interactive legends

---

### 2. Interactive Spreadsheet/Table

**Format:**
```json
{
  "type": "artifact:spreadsheet",
  "version": "1.0",
  "title": "Expense Breakdown Q4 2025",
  "data": {
    "columns": [
      {"id": "category", "name": "Category", "type": "string", "editable": false},
      {"id": "amount", "name": "Amount", "type": "currency", "editable": true},
      {"id": "notes", "name": "Notes", "type": "text", "editable": true}
    ],
    "rows": [
      {"category": "Travel", "amount": 2500.00, "notes": "Conference"},
      {"category": "Equipment", "amount": 1200.00, "notes": "Laptop"}
    ],
    "totals": {
      "amount": {"formula": "SUM", "value": 3700.00}
    },
    "features": {
      "sorting": true,
      "filtering": true,
      "export": ["csv", "xlsx", "json"],
      "formulas": ["SUM", "AVG", "COUNT"]
    }
  }
}
```

**UI Features:**
- Cell editing with validation
- Sort by column
- Filter rows
- Formula calculation
- Export to CSV/Excel
- Copy/paste support
- Undo/redo

**Use Cases:**
- Financial data analysis
- Inventory management
- Comparison tables
- Data exploration

---

### 3. Node/Graph Visualization

**Format:**
```json
{
  "type": "artifact:graph",
  "version": "1.0",
  "title": "Knowledge Graph: Project Dependencies",
  "data": {
    "nodes": [
      {
        "id": "n1",
        "label": "mcp-client",
        "type": "project",
        "properties": {
          "version": "0.43.5",
          "language": "Python"
        },
        "style": {
          "color": "#3498db",
          "size": 30,
          "icon": "folder"
        }
      }
    ],
    "edges": [
      {
        "id": "e1",
        "source": "n1",
        "target": "n2",
        "label": "depends on",
        "type": "dependency",
        "weight": 1.0
      }
    ],
    "layout": {
      "type": "force-directed",
      "options": {
        "strength": -400,
        "distance": 100
      }
    },
    "interactions": {
      "nodeClick": "showDetails",
      "edgeClick": "showRelationship",
      "zoom": true,
      "pan": true,
      "search": true
    }
  }
}
```

**UI Features:**
- Force-directed or hierarchical layouts
- Node expansion/collapse
- Search and highlight
- Filter by node/edge type
- Zoom and pan
- Minimap for navigation
- Export as image/SVG

**Use Cases:**
- Zettelkasten note connections
- Project dependencies
- Concept maps
- Organizational charts
- State machines

---

### 4. Timeline Visualization

**Format:**
```json
{
  "type": "artifact:timeline",
  "version": "1.0",
  "title": "Project Milestones 2025",
  "data": {
    "events": [
      {
        "id": "e1",
        "start": "2025-01-15T09:00:00Z",
        "end": "2025-01-20T17:00:00Z",
        "title": "Sprint 1: Planning",
        "description": "Initial project planning and architecture design",
        "category": "planning",
        "style": {
          "color": "#3498db"
        }
      }
    ],
    "categories": [
      {"id": "planning", "label": "Planning", "color": "#3498db"},
      {"id": "development", "label": "Development", "color": "#2ecc71"},
      {"id": "testing", "label": "Testing", "color": "#f39c12"}
    ],
    "view": {
      "defaultZoom": "month",
      "zoomLevels": ["day", "week", "month", "year"],
      "groupBy": "category"
    }
  }
}
```

**UI Features:**
- Horizontal or vertical orientation
- Zoom levels (day/week/month/year)
- Group by category
- Drag to move events
- Resize events
- Tooltips with details
- Current time indicator

**Use Cases:**
- Project timelines
- Historical events
- Video transcript timestamps
- Personal journeys
- Process flows

---

### 5. Markdown Document with Enhanced Features

**Format:**
```json
{
  "type": "artifact:markdown",
  "version": "1.0",
  "title": "Project Documentation",
  "data": {
    "content": "# Overview\n\nThis is **enhanced** markdown with interactive features.\n\n```python\nprint('Hello, World!')\n```\n\n[[Internal Link to Node]]\n\n- [ ] Task 1\n- [x] Task 2\n",
    "features": {
      "syntaxHighlighting": true,
      "internalLinks": true,
      "checkboxes": true,
      "tableOfContents": true,
      "mermaidDiagrams": true,
      "latexMath": true
    },
    "metadata": {
      "tags": ["documentation", "api"],
      "created": "2025-01-09T12:00:00Z",
      "updated": "2025-01-09T14:30:00Z"
    }
  }
}
```

**UI Features:**
- Live preview
- Syntax highlighting for code blocks
- Interactive checkboxes
- Internal wiki-links
- Mermaid diagram rendering
- LaTeX math rendering
- Table of contents navigation
- Export to PDF/HTML

**Use Cases:**
- Documentation
- Note-taking
- Reports
- Technical specifications

---

### 6. Code Editor/Viewer with Execution

**Format:**
```json
{
  "type": "artifact:code",
  "version": "1.0",
  "title": "Data Processing Script",
  "data": {
    "language": "python",
    "code": "import pandas as pd\n\ndf = pd.DataFrame({'a': [1, 2, 3]})\nprint(df.describe())",
    "editable": true,
    "executable": true,
    "sandbox": {
      "type": "pyodide",
      "allowedModules": ["pandas", "numpy", "matplotlib"]
    },
    "files": [
      {"name": "data.csv", "content": "a,b,c\n1,2,3\n4,5,6"}
    ]
  }
}
```

**UI Features:**
- Monaco/CodeMirror editor
- Syntax highlighting
- Autocomplete
- Execute button (sandboxed)
- Output panel
- File tree for multi-file projects
- Diff view for changes

**Use Cases:**
- Code examples
- Interactive tutorials
- Data analysis notebooks
- Algorithm demonstrations

---

### 7. Kanban Board

**Format:**
```json
{
  "type": "artifact:kanban",
  "version": "1.0",
  "title": "Development Board",
  "data": {
    "columns": [
      {
        "id": "todo",
        "title": "To Do",
        "color": "#95a5a6",
        "limit": null
      },
      {
        "id": "in_progress",
        "title": "In Progress",
        "color": "#3498db",
        "limit": 3
      },
      {
        "id": "done",
        "title": "Done",
        "color": "#2ecc71",
        "limit": null
      }
    ],
    "cards": [
      {
        "id": "c1",
        "columnId": "todo",
        "title": "Implement artifact system",
        "description": "Build JSON format detection",
        "tags": ["backend", "urgent"],
        "assignee": "dev1",
        "dueDate": "2025-02-01"
      }
    ],
    "interactions": {
      "drag": true,
      "addCard": true,
      "editCard": true,
      "deleteCard": true
    }
  }
}
```

**UI Features:**
- Drag-and-drop between columns
- WIP limits
- Card filtering by tag/assignee
- Card creation/editing
- Progress indicators
- Export to JSON/CSV

**Use Cases:**
- Task management
- Sprint planning
- Content pipeline
- Issue tracking

---

### 8. Form/Survey Builder

**Format:**
```json
{
  "type": "artifact:form",
  "version": "1.0",
  "title": "User Feedback Survey",
  "data": {
    "fields": [
      {
        "id": "name",
        "type": "text",
        "label": "Full Name",
        "required": true,
        "placeholder": "Enter your name"
      },
      {
        "id": "rating",
        "type": "radio",
        "label": "How would you rate our service?",
        "options": ["Excellent", "Good", "Fair", "Poor"],
        "required": true
      },
      {
        "id": "comments",
        "type": "textarea",
        "label": "Additional Comments",
        "rows": 5
      }
    ],
    "validation": {
      "name": {"minLength": 2, "maxLength": 100}
    },
    "submission": {
      "method": "api",
      "endpoint": "/api/feedback",
      "successMessage": "Thank you for your feedback!"
    }
  }
}
```

**UI Features:**
- Dynamic field types (text, radio, checkbox, select, date, file)
- Real-time validation
- Conditional fields
- Submit to API or download as JSON
- Response summary

**Use Cases:**
- Data collection
- User onboarding
- Settings configuration
- Surveys and polls

---

### 9. Mind Map

**Format:**
```json
{
  "type": "artifact:mindmap",
  "version": "1.0",
  "title": "Project Architecture",
  "data": {
    "root": {
      "id": "r1",
      "label": "MCP Client",
      "children": [
        {
          "id": "c1",
          "label": "Agents",
          "children": [
            {"id": "c1a", "label": "Planner"},
            {"id": "c1b", "label": "Executor"}
          ]
        },
        {
          "id": "c2",
          "label": "Memory",
          "children": [
            {"id": "c2a", "label": "Goals"},
            {"id": "c2b", "label": "Features"}
          ]
        }
      ]
    },
    "style": {
      "layout": "radial",
      "colors": {
        "root": "#e74c3c",
        "level1": "#3498db",
        "level2": "#2ecc71"
      }
    },
    "interactions": {
      "expandCollapse": true,
      "addNode": true,
      "editNode": true,
      "dragNode": true
    }
  }
}
```

**UI Features:**
- Radial or tree layout
- Expand/collapse branches
- Add/edit/delete nodes
- Drag to rearrange
- Export as image/JSON
- Search nodes

**Use Cases:**
- Brainstorming
- Concept organization
- Project planning
- Knowledge mapping

---

### 10. Diff Viewer (Code/Text Comparison)

**Format:**
```json
{
  "type": "artifact:diff",
  "version": "1.0",
  "title": "Code Review: Bug Fix",
  "data": {
    "left": {
      "label": "Before (v0.43.4)",
      "content": "def process(data):\n    return data.upper()",
      "language": "python"
    },
    "right": {
      "label": "After (v0.43.5)",
      "content": "def process(data):\n    if not data:\n        return ''\n    return data.upper()",
      "language": "python"
    },
    "options": {
      "viewType": "split",
      "showLineNumbers": true,
      "highlightChanges": true,
      "ignoreWhitespace": false
    }
  }
}
```

**UI Features:**
- Split or unified view
- Syntax highlighting
- Line-by-line comparison
- Expand/collapse unchanged regions
- Navigate to next/previous change
- Toggle whitespace visibility

**Use Cases:**
- Code review
- Document comparison
- Version tracking
- Change analysis

---

### 11. File Tree Explorer

**Format:**
```json
{
  "type": "artifact:filetree",
  "version": "1.0",
  "title": "Project Structure",
  "data": {
    "root": {
      "name": "src",
      "type": "directory",
      "children": [
        {
          "name": "components",
          "type": "directory",
          "children": [
            {"name": "Button.tsx", "type": "file", "size": 1024}
          ]
        },
        {
          "name": "index.ts",
          "type": "file",
          "size": 512,
          "language": "typescript"
        }
      ]
    },
    "features": {
      "expandCollapse": true,
      "search": true,
      "filePreview": true,
      "download": true
    }
  }
}
```

**UI Features:**
- Expandable directory tree
- File icons by type
- File size display
- Search/filter
- Click to preview file contents
- Download files
- Right-click context menu

**Use Cases:**
- Project documentation
- File system navigation
- Archive exploration
- Code structure overview

---

### 12. Interactive Map

**Format:**
```json
{
  "type": "artifact:map",
  "version": "1.0",
  "title": "Delivery Locations",
  "data": {
    "center": {"lat": 37.7749, "lng": -122.4194},
    "zoom": 12,
    "markers": [
      {
        "id": "m1",
        "lat": 37.7849,
        "lng": -122.4094,
        "label": "Pickup: Warehouse A",
        "icon": "warehouse",
        "popup": "<strong>Warehouse A</strong><br>123 Main St"
      },
      {
        "id": "m2",
        "lat": 37.7649,
        "lng": -122.4294,
        "label": "Delivery: Customer B",
        "icon": "home"
      }
    ],
    "routes": [
      {
        "id": "r1",
        "points": [
          {"lat": 37.7849, "lng": -122.4094},
          {"lat": 37.7649, "lng": -122.4294}
        ],
        "color": "#3498db",
        "distance": "5.2 miles"
      }
    ],
    "layers": {
      "traffic": false,
      "satellite": false
    }
  }
}
```

**UI Features:**
- Pan and zoom
- Custom markers
- Route visualization
- Popup info windows
- Layer toggles
- Distance measurement
- Export as image

**Use Cases:**
- Logistics planning (rate confirmations)
- Location tracking
- Geographic data visualization
- Travel routes

---

### 13. Interactive Slides/Presentation

**Format:**
```json
{
  "type": "artifact:slides",
  "version": "1.0",
  "title": "Quarterly Review",
  "data": {
    "slides": [
      {
        "id": "s1",
        "title": "Q4 Performance",
        "layout": "title-content",
        "content": {
          "type": "markdown",
          "text": "## Revenue Growth\n\n- **25%** increase YoY\n- Key driver: Enterprise sales"
        }
      },
      {
        "id": "s2",
        "title": "Sales by Region",
        "layout": "full-chart",
        "content": {
          "type": "chart",
          "chartType": "bar",
          "data": {...}
        }
      }
    ],
    "theme": {
      "colors": ["#3498db", "#2ecc71"],
      "font": "Inter"
    },
    "navigation": {
      "arrows": true,
      "bullets": true,
      "fullscreen": true
    }
  }
}
```

**UI Features:**
- Slide navigation (arrow keys)
- Full-screen mode
- Presenter notes
- Transitions
- Export to PDF
- Embed charts/images/code
- Timer for presentations

**Use Cases:**
- Presentations
- Tutorials
- Reports
- Storytelling

---

### 14. Calendar/Schedule View

**Format:**
```json
{
  "type": "artifact:calendar",
  "version": "1.0",
  "title": "Team Schedule",
  "data": {
    "events": [
      {
        "id": "ev1",
        "title": "Sprint Planning",
        "start": "2025-01-15T09:00:00Z",
        "end": "2025-01-15T10:30:00Z",
        "allDay": false,
        "category": "meeting",
        "attendees": ["dev1", "dev2", "pm1"]
      }
    ],
    "categories": [
      {"id": "meeting", "label": "Meetings", "color": "#3498db"},
      {"id": "deadline", "label": "Deadlines", "color": "#e74c3c"}
    ],
    "view": {
      "defaultView": "month",
      "views": ["day", "week", "month", "agenda"]
    }
  }
}
```

**UI Features:**
- Multiple views (day/week/month/agenda)
- Drag-and-drop events
- Event creation/editing
- Category filtering
- Export to iCal
- Print view

**Use Cases:**
- Team scheduling
- Project deadlines
- Event planning
- Availability tracking

---

### 15. Dashboard/Metrics Panel

**Format:**
```json
{
  "type": "artifact:dashboard",
  "version": "1.0",
  "title": "System Metrics",
  "data": {
    "layout": "grid",
    "widgets": [
      {
        "id": "w1",
        "type": "metric",
        "position": {"row": 1, "col": 1, "width": 1, "height": 1},
        "data": {
          "title": "Active Users",
          "value": 1247,
          "change": "+12%",
          "trend": "up",
          "icon": "users"
        }
      },
      {
        "id": "w2",
        "type": "chart",
        "position": {"row": 1, "col": 2, "width": 2, "height": 1},
        "data": {
          "title": "Response Time",
          "chartType": "line",
          "xAxis": ["Mon", "Tue", "Wed", "Thu", "Fri"],
          "series": [
            {"name": "API", "data": [120, 115, 130, 110, 105]}
          ]
        }
      },
      {
        "id": "w3",
        "type": "table",
        "position": {"row": 2, "col": 1, "width": 3, "height": 1},
        "data": {
          "title": "Top Errors",
          "columns": ["Error", "Count", "Last Seen"],
          "rows": [
            ["500 Internal Server Error", 12, "2m ago"],
            ["404 Not Found", 8, "15m ago"]
          ]
        }
      }
    ],
    "refresh": {
      "enabled": true,
      "interval": 30000
    }
  }
}
```

**UI Features:**
- Grid layout with drag-and-drop
- Multiple widget types (metrics, charts, tables, gauges)
- Auto-refresh
- Full-screen widgets
- Export dashboard as PDF/image
- Responsive layout

**Use Cases:**
- System monitoring
- Business intelligence
- Analytics reporting
- Performance tracking

---

## Implementation Architecture

### Artifact Detection System

```python
# artifact_detector.py
import json
import re
from typing import Optional, Dict

class ArtifactDetector:
    """Detects artifact markers in LLM output."""

    ARTIFACT_PATTERN = re.compile(
        r'```artifact:(\w+)\n(.*?)\n```',
        re.DOTALL
    )

    def detect(self, llm_output: str) -> list[Dict]:
        """Extract all artifacts from LLM output."""
        artifacts = []
        for match in self.ARTIFACT_PATTERN.finditer(llm_output):
            artifact_type = match.group(1)
            artifact_data = match.group(2)

            try:
                parsed = json.loads(artifact_data)
                artifacts.append({
                    'type': f"artifact:{artifact_type}",
                    'data': parsed,
                    'raw': artifact_data
                })
            except json.JSONDecodeError:
                # Log error but continue
                pass

        return artifacts
```

### Artifact Agent Definition

```json
{
  "agent_type": "ARTIFACT_AGENT",
  "display_name": "🎨 Artifact Generator",
  "description": "Generates interactive visualizations and UI components",
  "system_prompt": "You generate interactive artifacts for the web UI. When asked to create visualizations, tables, graphs, or interactive components, output them using the artifact format.\n\nAvailable artifact types:\n- artifact:chart - For charts and graphs (D3.js/Chart.js compatible)\n- artifact:spreadsheet - For editable tables and spreadsheets\n- artifact:graph - For node/edge graph visualizations\n- artifact:timeline - For temporal data visualization\n- artifact:markdown - For enhanced markdown documents\n- artifact:code - For executable code snippets\n- artifact:kanban - For kanban boards\n- artifact:form - For interactive forms\n- artifact:mindmap - For mind maps\n- artifact:diff - For code/text comparison\n- artifact:filetree - For file structure visualization\n- artifact:map - For geographic maps\n- artifact:slides - For presentations\n- artifact:calendar - For schedules and events\n- artifact:dashboard - For metrics dashboards\n\nFormat:\n```artifact:chart\n{\n  \"type\": \"artifact:chart\",\n  \"version\": \"1.0\",\n  \"title\": \"...\",\n  \"data\": {...}\n}\n```\n\nIMPORTANT:\n- Always use valid JSON\n- Include all required fields for the artifact type\n- Provide meaningful titles and labels\n- Use appropriate chart types for the data\n- Consider user interaction needs",
  "default_tools": [
    "builtin.read_file",
    "builtin.list_files"
  ],
  "temperature": 0.3
}
```

### Web UI Integration

```typescript
// ArtifactPanel.tsx
import React, { useState } from 'react';
import { ChartRenderer } from './renderers/ChartRenderer';
import { SpreadsheetRenderer } from './renderers/SpreadsheetRenderer';
import { GraphRenderer } from './renderers/GraphRenderer';
// ... other renderers

interface Artifact {
  type: string;
  version: string;
  title: string;
  data: any;
}

const RENDERER_MAP = {
  'artifact:chart': ChartRenderer,
  'artifact:spreadsheet': SpreadsheetRenderer,
  'artifact:graph': GraphRenderer,
  'artifact:timeline': TimelineRenderer,
  'artifact:markdown': MarkdownRenderer,
  'artifact:code': CodeRenderer,
  'artifact:kanban': KanbanRenderer,
  'artifact:form': FormRenderer,
  'artifact:mindmap': MindMapRenderer,
  'artifact:diff': DiffRenderer,
  'artifact:filetree': FileTreeRenderer,
  'artifact:map': MapRenderer,
  'artifact:slides': SlidesRenderer,
  'artifact:calendar': CalendarRenderer,
  'artifact:dashboard': DashboardRenderer,
};

export const ArtifactPanel: React.FC<{ artifact: Artifact }> = ({ artifact }) => {
  const Renderer = RENDERER_MAP[artifact.type];

  if (!Renderer) {
    return <div>Unknown artifact type: {artifact.type}</div>;
  }

  return (
    <div className="artifact-panel">
      <div className="artifact-header">
        <h3>{artifact.title}</h3>
        <button onClick={() => exportArtifact(artifact)}>Export</button>
      </div>
      <div className="artifact-content">
        <Renderer data={artifact.data} />
      </div>
    </div>
  );
};
```

### Ollama Prompt Example

```
User: Show me a breakdown of our Q4 expenses in an interactive table.

LLM (Artifact Agent): Here's an interactive spreadsheet with your Q4 expense data:

```artifact:spreadsheet
{
  "type": "artifact:spreadsheet",
  "version": "1.0",
  "title": "Q4 2025 Expense Breakdown",
  "data": {
    "columns": [
      {"id": "category", "name": "Category", "type": "string", "editable": false},
      {"id": "amount", "name": "Amount", "type": "currency", "editable": true},
      {"id": "percent", "name": "% of Total", "type": "percentage", "editable": false},
      {"id": "notes", "name": "Notes", "type": "text", "editable": true}
    ],
    "rows": [
      {"category": "Salaries", "amount": 125000, "percent": 45.2, "notes": "Engineering team"},
      {"category": "Infrastructure", "amount": 35000, "percent": 12.7, "notes": "AWS, Azure costs"},
      {"category": "Marketing", "amount": 28000, "percent": 10.1, "notes": "Digital campaigns"},
      {"category": "Travel", "amount": 22000, "percent": 8.0, "notes": "Conferences, client visits"},
      {"category": "Equipment", "amount": 18000, "percent": 6.5, "notes": "New laptops, monitors"},
      {"category": "Software Licenses", "amount": 15000, "percent": 5.4, "notes": "Tools and subscriptions"},
      {"category": "Office", "amount": 12000, "percent": 4.3, "notes": "Rent and utilities"},
      {"category": "Other", "amount": 21000, "percent": 7.6, "notes": "Misc expenses"}
    ],
    "totals": {
      "amount": {"formula": "SUM", "value": 276000},
      "percent": {"value": 100.0}
    },
    "features": {
      "sorting": true,
      "filtering": true,
      "export": ["csv", "xlsx", "json"],
      "formulas": ["SUM", "AVG", "COUNT"]
    }
  }
}
```

You can sort by any column, edit the amounts or notes, and export the data to CSV or Excel.
```

---

## Renderer Component Library

### Technology Stack Recommendations

**Frontend Framework:**
- React with TypeScript
- Tailwind CSS for styling
- Shadcn/UI for base components

**Visualization Libraries:**
- **Charts**: Chart.js or Recharts (simpler) | D3.js (advanced)
- **Graphs**: Cytoscape.js or React Flow
- **Tables**: TanStack Table (formerly React Table)
- **Code**: Monaco Editor (VS Code) or CodeMirror
- **Markdown**: react-markdown with plugins
- **Maps**: Leaflet or Mapbox GL JS
- **Diagrams**: Mermaid.js (integrated with markdown)
- **Math**: KaTeX or MathJax

### Sample Renderer: SpreadsheetRenderer.tsx

```typescript
import React, { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
} from '@tanstack/react-table';

interface SpreadsheetData {
  columns: Array<{
    id: string;
    name: string;
    type: string;
    editable: boolean;
  }>;
  rows: Array<Record<string, any>>;
  totals?: Record<string, any>;
  features: {
    sorting?: boolean;
    filtering?: boolean;
    export?: string[];
  };
}

export const SpreadsheetRenderer: React.FC<{ data: SpreadsheetData }> = ({
  data,
}) => {
  const [tableData, setTableData] = useState(data.rows);
  const [sorting, setSorting] = useState([]);
  const [filtering, setFiltering] = useState('');

  const columns = useMemo(
    () =>
      data.columns.map((col) => ({
        accessorKey: col.id,
        header: col.name,
        cell: ({ getValue, row, column }) => {
          const value = getValue();
          const isEditable = col.editable;

          if (isEditable) {
            return (
              <EditableCell
                value={value}
                onChange={(newValue) =>
                  handleCellEdit(row.index, column.id, newValue)
                }
                type={col.type}
              />
            );
          }

          return formatValue(value, col.type);
        },
      })),
    [data.columns]
  );

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: data.features.sorting ? getSortedRowModel() : undefined,
    getFilteredRowModel: data.features.filtering
      ? getFilteredRowModel()
      : undefined,
    state: {
      sorting,
      globalFilter: filtering,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFiltering,
  });

  const handleCellEdit = (rowIndex: number, columnId: string, value: any) => {
    setTableData((old) =>
      old.map((row, index) =>
        index === rowIndex ? { ...row, [columnId]: value } : row
      )
    );
  };

  const handleExport = (format: string) => {
    switch (format) {
      case 'csv':
        exportToCSV(tableData, data.columns);
        break;
      case 'xlsx':
        exportToExcel(tableData, data.columns);
        break;
      case 'json':
        downloadJSON(tableData);
        break;
    }
  };

  return (
    <div className="spreadsheet-renderer">
      {data.features.filtering && (
        <input
          type="text"
          value={filtering}
          onChange={(e) => setFiltering(e.target.value)}
          placeholder="Search..."
          className="mb-4 px-3 py-2 border rounded"
        />
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className="px-4 py-2 bg-gray-100 border cursor-pointer"
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
                    {{
                      asc: ' 🔼',
                      desc: ' 🔽',
                    }[header.column.getIsSorted() as string] ?? null}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-2 border">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
          {data.totals && (
            <tfoot>
              <tr className="font-bold bg-gray-50">
                {data.columns.map((col) => (
                  <td key={col.id} className="px-4 py-2 border">
                    {data.totals[col.id]
                      ? formatValue(data.totals[col.id].value, col.type)
                      : ''}
                  </td>
                ))}
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      {data.features.export && (
        <div className="mt-4 flex gap-2">
          {data.features.export.map((format) => (
            <button
              key={format}
              onClick={() => handleExport(format)}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Export as {format.toUpperCase()}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// Helper components and functions
const EditableCell = ({ value, onChange, type }) => {
  const [editValue, setEditValue] = useState(value);

  return (
    <input
      type={type === 'number' ? 'number' : 'text'}
      value={editValue}
      onChange={(e) => setEditValue(e.target.value)}
      onBlur={() => onChange(editValue)}
      className="w-full px-2 py-1 border-none focus:outline-none"
    />
  );
};

const formatValue = (value: any, type: string): string => {
  switch (type) {
    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
      }).format(value);
    case 'percentage':
      return `${value.toFixed(1)}%`;
    case 'number':
      return value.toLocaleString();
    default:
      return String(value);
  }
};

const exportToCSV = (data, columns) => {
  const csv = [
    columns.map((c) => c.name).join(','),
    ...data.map((row) =>
      columns.map((c) => JSON.stringify(row[c.id] ?? '')).join(',')
    ),
  ].join('\n');

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'export.csv';
  a.click();
};

// Similar functions for exportToExcel and downloadJSON
```

---

## Artifact Agent System Prompt (Complete)

```markdown
# Artifact Agent Instructions

You are an Artifact Agent specialized in generating interactive UI components for the web interface. When users request visualizations, data displays, or interactive elements, you generate them using the artifact format.

## Available Artifact Types

1. **artifact:spreadsheet** - Interactive data tables with sorting, filtering, editing
2. **artifact:chart** - Charts and graphs (line, bar, pie, scatter, etc.)
3. **artifact:graph** - Node/edge network visualizations
4. **artifact:timeline** - Temporal event visualization
5. **artifact:markdown** - Enhanced markdown with features
6. **artifact:code** - Executable code with syntax highlighting
7. **artifact:kanban** - Kanban boards for task management
8. **artifact:form** - Interactive forms with validation
9. **artifact:mindmap** - Mind map visualizations
10. **artifact:diff** - Code/text comparison views
11. **artifact:filetree** - File structure visualization
12. **artifact:map** - Geographic maps with markers and routes
13. **artifact:slides** - Presentation slides
14. **artifact:calendar** - Event calendars and schedules
15. **artifact:dashboard** - Metrics dashboards with multiple widgets

## Output Format

Always use this format:

\`\`\`artifact:type
{
  "type": "artifact:type",
  "version": "1.0",
  "title": "Descriptive Title",
  "data": {
    // Type-specific data structure
  }
}
\`\`\`

## Guidelines

1. **Choose the Right Type**: Match the artifact type to the user's request
   - Data table → spreadsheet
   - Trends over time → chart (line)
   - Comparisons → chart (bar)
   - Proportions → chart (pie)
   - Relationships → graph
   - Events → timeline or calendar
   - Tasks → kanban
   - Maps/locations → map

2. **Provide Complete Data**: Include all required fields for the artifact type

3. **Make it Interactive**: Enable features like sorting, filtering, editing where appropriate

4. **Use Clear Labels**: Provide meaningful titles, axis labels, and legends

5. **Consider Context**: If the user asks for multiple related artifacts, generate them separately

6. **Validate JSON**: Ensure your output is valid JSON

## Examples

### Example 1: User asks for expense breakdown

\`\`\`artifact:spreadsheet
{
  "type": "artifact:spreadsheet",
  "version": "1.0",
  "title": "Monthly Expenses",
  "data": {
    "columns": [
      {"id": "category", "name": "Category", "type": "string", "editable": false},
      {"id": "amount", "name": "Amount", "type": "currency", "editable": true}
    ],
    "rows": [
      {"category": "Rent", "amount": 2000},
      {"category": "Food", "amount": 500}
    ],
    "features": {"sorting": true, "export": ["csv"]}
  }
}
\`\`\`

### Example 2: User asks to visualize trends

\`\`\`artifact:chart
{
  "type": "artifact:chart",
  "version": "1.0",
  "chart_type": "line",
  "title": "Revenue Trend Q4 2025",
  "data": {
    "labels": ["Oct", "Nov", "Dec"],
    "datasets": [{
      "label": "Revenue",
      "data": [100000, 120000, 150000],
      "color": "#3498db"
    }]
  }
}
\`\`\`

### Example 3: User asks for project structure

\`\`\`artifact:filetree
{
  "type": "artifact:filetree",
  "version": "1.0",
  "title": "Project Structure",
  "data": {
    "root": {
      "name": "src",
      "type": "directory",
      "children": [
        {"name": "index.ts", "type": "file", "size": 1024}
      ]
    }
  }
}
\`\`\`

## When to Use Artifacts

- User explicitly asks for a visualization, table, or interactive element
- Data analysis results that are best shown visually
- Complex information that benefits from structure
- Multi-step processes (timeline, kanban)
- Comparisons and relationships (charts, graphs)

## When NOT to Use Artifacts

- Simple text responses
- Lists with few items
- Explanations or discussions
- When the user asks "how" or "why" questions

Remember: Your goal is to make data and information more accessible and interactive for the user.
```

---

## Integration with MCP Client

### Modified Delegation Client Integration

```python
# In delegation_client.py

from artifact_detector import ArtifactDetector

class DelegationClient:
    def __init__(self, mcp_client, config):
        # ... existing init ...
        self.artifact_detector = ArtifactDetector()
        self.artifacts_storage = []  # Store artifacts for session

    async def process_with_delegation(self, user_query):
        # ... existing processing ...

        # After getting response from agent
        artifacts = self.artifact_detector.detect(response_text)

        if artifacts:
            # Store artifacts with metadata
            for artifact in artifacts:
                artifact_id = f"artifact_{len(self.artifacts_storage)}"
                self.artifacts_storage.append({
                    'id': artifact_id,
                    'type': artifact['type'],
                    'data': artifact['data'],
                    'created_at': datetime.now(),
                    'query': user_query
                })

                # Send artifact to web UI via WebSocket or SSE
                await self.send_artifact_to_ui(artifact_id, artifact)

        return response_text

    async def send_artifact_to_ui(self, artifact_id, artifact):
        """Send artifact to web UI for rendering."""
        # Implementation depends on web communication method
        # Could use WebSocket, SSE, or HTTP endpoint
        pass
```

### Web UI Backend Integration (FastAPI)

```python
# web_backend.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import json

app = FastAPI()

# Store active connections
active_connections: list[WebSocket] = []

@app.websocket("/ws/artifacts")
async def artifact_websocket(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle messages from client if needed
    except:
        active_connections.remove(websocket)

async def broadcast_artifact(artifact_id: str, artifact: dict):
    """Send artifact to all connected clients."""
    message = json.dumps({
        'type': 'artifact',
        'id': artifact_id,
        'artifact': artifact
    })

    for connection in active_connections:
        await connection.send_text(message)

@app.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    """Retrieve a specific artifact by ID."""
    # Fetch from storage
    artifact = artifacts_storage.get(artifact_id)
    return artifact

@app.post("/artifacts/{artifact_id}/export")
async def export_artifact(artifact_id: str, format: str):
    """Export artifact in specified format."""
    artifact = artifacts_storage.get(artifact_id)
    # Convert to requested format (CSV, JSON, etc.)
    return exported_data
```

---

## Prompt Engineering for Artifact Generation

### Context-Aware Artifact Selection

```python
# artifact_prompt_builder.py

class ArtifactPromptBuilder:
    """Helps LLM choose the right artifact type."""

    CONTEXT_PATTERNS = {
        'spreadsheet': [
            'table', 'data', 'list', 'rows', 'columns',
            'expenses', 'breakdown', 'comparison'
        ],
        'chart': [
            'trend', 'over time', 'growth', 'visualize',
            'graph', 'plot', 'compare'
        ],
        'graph': [
            'connected', 'relationship', 'network',
            'dependencies', 'links', 'nodes'
        ],
        'timeline': [
            'schedule', 'events', 'chronological',
            'history', 'milestones', 'when'
        ],
        'kanban': [
            'tasks', 'todo', 'progress', 'workflow',
            'board', 'status'
        ],
        'map': [
            'location', 'address', 'route', 'delivery',
            'geographic', 'where'
        ]
    }

    def suggest_artifact_type(self, user_query: str) -> str:
        """Suggest artifact type based on query analysis."""
        query_lower = user_query.lower()
        scores = {}

        for artifact_type, patterns in self.CONTEXT_PATTERNS.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            scores[artifact_type] = score

        # Return highest scoring type, or None if no match
        max_type = max(scores, key=scores.get)
        return max_type if scores[max_type] > 0 else None

    def build_artifact_hint(self, suggested_type: str) -> str:
        """Build a hint for the LLM."""
        hints = {
            'spreadsheet': 'Consider using an artifact:spreadsheet to display this data in an editable table.',
            'chart': 'Consider using an artifact:chart to visualize this data graphically.',
            'graph': 'Consider using an artifact:graph to show the relationships between entities.',
            'timeline': 'Consider using an artifact:timeline to show events chronologically.',
            'kanban': 'Consider using an artifact:kanban to organize tasks by status.',
            'map': 'Consider using an artifact:map to show locations geographically.'
        }
        return hints.get(suggested_type, '')
```

---

## Artifact Versioning and Refinement

### Artifact Evolution System

Users should be able to refine artifacts through conversation:

```typescript
// Artifact with version history
interface ArtifactVersion {
  version: number;
  timestamp: string;
  data: any;
  prompt: string;  // What the user asked for
  changes: string;  // What changed from previous version
}

interface VersionedArtifact {
  id: string;
  type: string;
  current_version: number;
  versions: ArtifactVersion[];
}

// Example conversation flow:
/*
User: Show me our expenses as a table
LLM: [generates artifact:spreadsheet v1]

User: Add a column for the payment method
LLM: [generates artifact:spreadsheet v2 with new column]

User: Sort by amount descending
LLM: [generates artifact:spreadsheet v3 with sorting applied]
*/
```

### Refinement Agent Prompt

```
When a user asks to modify an existing artifact:

1. Check if there's a current artifact displayed
2. Understand what modification is requested
3. Load the previous artifact data
4. Apply the requested changes
5. Generate a new version with updated data
6. Increment the version number

Example:
User: "Change the chart to a bar chart"

Response:
\`\`\`artifact:chart
{
  "type": "artifact:chart",
  "version": "2.0",
  "parent_version": "1.0",
  "changes": "Changed chart type from line to bar",
  "chart_type": "bar",
  // ... rest of data with modifications
}
\`\`\`
```

---

## Advanced Features

### 1. Artifact Composition

Allow multiple artifacts to reference each other:

```json
{
  "type": "artifact:dashboard",
  "widgets": [
    {
      "type": "chart",
      "artifact_ref": "artifact_123"  // Reference to existing chart
    },
    {
      "type": "spreadsheet",
      "artifact_ref": "artifact_124"  // Reference to existing table
    }
  ]
}
```

### 2. Artifact Actions/Callbacks

Artifacts can trigger agent actions:

```json
{
  "type": "artifact:spreadsheet",
  "actions": [
    {
      "id": "analyze_row",
      "label": "Analyze with LLM",
      "callback": "analyze_expense",
      "parameters": ["row_id"]
    }
  ]
}
```

When user clicks "Analyze with LLM" on a row, it triggers:
```
Agent receives: "Analyze expense: {row_data}"
Agent responds with analysis or new artifact
```

### 3. Artifact Export Formats

Standard export capabilities for all artifacts:

- **JSON**: Raw artifact data
- **PNG/SVG**: Visual rendering
- **PDF**: Formatted document
- **CSV/XLSX**: For tabular data
- **Markdown**: Text-based representation
- **HTML**: Standalone HTML page

### 4. Artifact Theming

Allow users to customize appearance:

```json
{
  "theme": {
    "colorScheme": "dark|light|auto",
    "primaryColor": "#3498db",
    "font": "Inter",
    "borderRadius": "8px"
  }
}
```

---

## Testing Strategy

### Unit Tests for Artifact Detection

```python
# test_artifact_detector.py
import pytest
from artifact_detector import ArtifactDetector

def test_detect_spreadsheet():
    detector = ArtifactDetector()
    output = '''
Here's your data:

```artifact:spreadsheet
{"type": "artifact:spreadsheet", "data": {...}}
```
    '''

    artifacts = detector.detect(output)
    assert len(artifacts) == 1
    assert artifacts[0]['type'] == 'artifact:spreadsheet'

def test_detect_multiple_artifacts():
    detector = ArtifactDetector()
    output = '''
Here's a table and a chart:

```artifact:spreadsheet
{"type": "artifact:spreadsheet", "data": {...}}
```

And here's the chart:

```artifact:chart
{"type": "artifact:chart", "data": {...}}
```
    '''

    artifacts = detector.detect(output)
    assert len(artifacts) == 2
```

### Integration Tests

Test full flow from LLM output → detection → rendering:

```typescript
describe('Artifact Integration', () => {
  it('should render spreadsheet from LLM output', async () => {
    const llmOutput = `
Here's your data:

\`\`\`artifact:spreadsheet
${JSON.stringify(mockSpreadsheetArtifact)}
\`\`\`
    `;

    const artifacts = detectArtifacts(llmOutput);
    const rendered = render(<ArtifactPanel artifact={artifacts[0]} />);

    expect(rendered.getByText('Category')).toBeInTheDocument();
    expect(rendered.getByText('Amount')).toBeInTheDocument();
  });
});
```

---

## Deployment Checklist

### Backend Requirements

- [ ] Artifact detection system integrated with delegation client
- [ ] WebSocket or SSE for real-time artifact delivery
- [ ] Artifact storage with versioning
- [ ] Export endpoints for each format
- [ ] Artifact agent configured and tested

### Frontend Requirements

- [ ] Renderer components for all artifact types
- [ ] Side panel UI for artifact display
- [ ] Export functionality
- [ ] Artifact versioning UI
- [ ] Responsive layouts for all artifact types
- [ ] Loading states and error handling

### LLM Training/Prompting

- [ ] Artifact agent system prompt configured
- [ ] Example artifacts in few-shot prompts
- [ ] Context detection for artifact suggestion
- [ ] Refinement prompts tested

---

## Future Enhancements

1. **Collaborative Artifacts**: Multiple users can interact with the same artifact in real-time
2. **Artifact Templates**: Pre-built templates for common use cases
3. **AI-Powered Refinement**: "Make this chart better" → LLM improves design automatically
4. **Artifact Chaining**: One artifact's output becomes input to another
5. **Natural Language Queries on Artifacts**: "What's the highest expense?" on a spreadsheet
6. **Artifact Plugins**: Community-contributed artifact types
7. **Voice Interaction**: "Show me this as a pie chart" voice commands
8. **Mobile Support**: Touch-optimized artifact renderers
9. **Offline Mode**: Artifacts work without internet connection
10. **Version Control Integration**: Sync artifacts with Git for documentation

---

## Artifact Type Summary

### Data Visualization (5 types)
1. **Spreadsheet** - Interactive tables with editing, sorting, formulas
2. **Chart** - Line, bar, pie, scatter, and more
3. **Dashboard** - Multi-widget metrics panels
4. **Timeline** - Temporal event visualization
5. **Calendar** - Event scheduling

### Structure & Relationships (3 types)
6. **Graph** - Node/edge network visualizations
7. **Mind Map** - Radial concept mapping
8. **File Tree** - Hierarchical file explorer

### Task Management (2 types)
9. **Kanban** - Task boards with drag-and-drop
10. **Form** - Interactive forms with validation

### Code & Documentation (4 types)
11. **Code** - Syntax-highlighted, executable code
12. **Markdown** - Enhanced markdown with features
13. **Diff** - Code/text comparison
14. **Slides** - Interactive presentations

### Geographic (1 type)
15. **Map** - Interactive maps with markers and routes

### Tool-Based (6 additional types - see extension doc)
16. **Tool Form** - Dynamic forms from tool schemas
17. **Query Builder** - Visual query construction
18. **Tool Wizard** - Multi-step workflows
19. **Batch Tool** - Batch execution interface
20. **Tool Palette** - Quick access tool launcher
21. **Parameter Suggestions** - AI-suggested values

**Total: 21 artifact types across 6 categories**

---

## Related Documents

- **[tool-based-artifacts-extension.md](./tool-based-artifacts-extension.md)** - Tool-based interactive artifacts design
  - Dynamic form generation from MCP tool schemas
  - Query builders and wizards
  - Batch execution interfaces
  - Context-aware parameter suggestions

---

## Conclusion

This artifact system enables rich, interactive outputs from LLMs that go far beyond simple text. By standardizing the format and providing specialized renderers, we create a powerful platform for data visualization, interactive documentation, and dynamic UI generation—all driven by natural language conversations with the LLM.

The key innovations are:
1. **Standardized Format**: Consistent JSON wrapper for all artifacts
2. **Type Safety**: Each artifact type has a clear schema
3. **Interactivity**: Users can interact with and modify artifacts
4. **Versioning**: Artifacts can be refined through conversation
5. **Extensibility**: New artifact types can be added easily
6. **Tool Integration**: Dynamic forms from existing tool schemas (see extension doc)

This system transforms the LLM from a text generator into a comprehensive UI builder, unlocking new possibilities for human-AI interaction.

---

*Design Document Version: 1.1*
*Last Updated: 2026-01-09*
*Author: System Architect*