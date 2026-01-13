# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.44.0] - 2026-01-10

### Added - Artifact System

#### Core Artifact Generation
- **Artifact Detection System** (`artifacts/detector.py`) - Detects and validates 21 artifact types from LLM output
- **Tool Schema Parser** (`artifacts/tool_schema_parser.py`) - Automatically generates interactive forms from MCP tool schemas
- **Type System** (`artifacts/types.py`) - Type definitions for artifacts and UI widgets

#### 21 Artifact Types
**Base Artifacts (15):**
- `spreadsheet` - Interactive tables with sorting, filtering, editing
- `chart` - Various chart types (line, bar, pie, scatter, radar, etc.)
- `graph` - Network/node graphs with relationships
- `timeline` - Chronological event visualization
- `kanban` - Kanban board with columns and cards
- `code` - Code display with syntax highlighting
- `markdown` - Formatted markdown with math and diagrams
- `diff` - Side-by-side or unified diff view
- `filetree` - Hierarchical file/folder structure
- `map` - Geographic visualization with markers
- `slides` - Presentation slides
- `calendar` - Calendar/schedule view
- `dashboard` - Multi-widget dashboard layout
- `form` - Interactive form with validation
- `mindmap` - Mind map/concept map visualization

**Tool-Based Artifacts (6):**
- `toolform` - Auto-generated forms from tool schemas
- `querybuilder` - Tool discovery and query building interface
- `toolwizard` - Multi-step wizards for complex tools
- `batchtool` - Batch processing interfaces
- `toolpalette` - Quick access tool panel
- `paramsuggestions` - Context-aware parameter suggestions

#### Context Tracking System
- **Artifact Context Manager** (`artifacts/context_manager.py`) - Tracks user interactions with artifacts
- **Execution Recording** - Records every tool execution via artifacts with metadata
- **Reference Resolution** - Resolves natural language references:
  - Temporal: "what I just loaded", "the last file"
  - Content: "README.md", "the config file"
  - Tool-based: "what I listed", "the code I ran"
- **Context Injection** - Automatically injects artifact results into LLM context
- **Smart Size Management** - Auto-truncates large results (>10KB)

#### New Agents
- **ARTIFACT_AGENT** (🎨📊) - Generates interactive visualizations and data presentations
- **TOOL_FORM_AGENT** (🔧📝) - Generates interactive forms from MCP tool schemas

#### New Builtin Tools
- `builtin.generate_tool_form` - Generate interactive form for a specific tool
- `builtin.generate_query_builder` - Generate tool discovery interface
- `builtin.generate_tool_wizard` - Generate multi-step wizard for complex tools
- `builtin.generate_batch_tool` - Generate batch processing interface

#### Smart Features
- **Widget Inference** - Automatically selects best UI widget based on:
  - Property names (e.g., "path" → file picker)
  - JSON Schema types (e.g., boolean → checkbox)
  - Schema formats (e.g., email, date, uri)
  - Enum values → select dropdown
- **Context-Aware Suggestions** - Prefills form parameters from:
  - Recent chat history
  - File paths mentioned
  - Memory state
- **Automatic Summaries** - Creates brief summaries of executions:
  - "Loaded README.md (2.5 KB)"
  - "Listed 15 items in src"
  - "Executed Python code"

#### Documentation
- **System Design** (`docs/llm-artifact-system-design.md`) - Complete design for 15 base artifact types
- **Tool-Based Extension** (`docs/tool-based-artifacts-extension.md`) - Design for 6 tool-based artifacts
- **Implementation Guide** (`docs/artifact-system-implementation.md`) - Implementation summary and examples
- **Context System** (`docs/artifact-context-system.md`) - Context tracking architecture
- **Integration Guide** (`docs/artifact-context-integration.md`) - Backend/frontend integration
- **Complete Summary** (`docs/artifact-system-summary.md`) - Full system overview

### Technical Details

**Lines of Code:** ~1,600 lines
**Documentation:** ~5,350 lines
**Files Created:** 11
**Files Modified:** 2

**Architecture:**
```
User → Artifact Form → Execute Tool → Record Context → LLM References → Natural Response
```

### Benefits

1. **Natural Interaction** - Users can reference previous actions naturally
2. **Reduced Repetition** - No need to re-upload or re-specify data
3. **Context Awareness** - LLM has complete picture of user's workflow
4. **Better UX** - Seamless integration between artifacts and chat
5. **Audit Trail** - Complete history of artifact interactions
6. **Smart Management** - Automatic summarization of large results

### Example Usage

```
User: "Create a form to read files"
→ TOOL_FORM_AGENT generates interactive file picker form

User: Fills in "README.md" and clicks Submit
→ System executes, records result, displays file

User: "Summarize what I just loaded"
→ LLM has README.md contents from context, generates summary
```

### Status

- ✅ Backend Implementation: Complete
- 📋 Frontend Implementation: Design complete, pending development
- ⏳ Testing: Pending
- ✅ Documentation: Complete

### Breaking Changes

None - All changes are additive and backward compatible.

### Migration Guide

No migration required. The artifact system is opt-in and doesn't affect existing functionality.

To start using artifacts:
1. Use ARTIFACT_AGENT or TOOL_FORM_AGENT in conversations
2. Submit generated forms through the UI
3. Reference previous executions naturally in chat

### Notes

- Frontend implementation required for full functionality
- API endpoints need to be added for artifact execution
- Context injection must be integrated into delegation client

---

## [0.43.5] - Previous Version

(Previous changelog entries would go here)

## [0.44.1] - 2026-01-10

### Fixed
- **Form Not Shown in UI**: Fixed PLANNER agent assignment for generic form requests
  - PLANNER now correctly routes generic form requests to ARTIFACT_AGENT
  - Added clear agent routing guidance for form vs toolform creation
  - ARTIFACT_AGENT now includes explicit generic form creation examples
  - Fixes issue where TOOL_FORM_AGENT was incorrectly assigned for generic data collection forms

### Changed
- Updated PLANNER agent list to include ARTIFACT_AGENT and TOOL_FORM_AGENT with usage guidance
- Enhanced ARTIFACT_AGENT with comprehensive form creation instructions and field type documentation


## [0.44.2] - 2026-01-10

### Fixed
- **Tool Form Artifacts Not Displayed**: Fixed critical bug in artifact generation tool handlers
  - Fixed KeyError in `builtin.generate_tool_form` and related handlers accessing wrong artifact structure
  - Changed from `artifact['data']['type']` to correct `artifact['type']`
  - Fixed all 4 artifact generation handlers: generate_tool_form, generate_query_builder, generate_tool_wizard, generate_batch_tool
  - Tool handlers now return complete artifact JSON (not just data field)
  - Added explicit output instructions to TOOL_FORM_AGENT to ensure artifact pass-through

### Changed
- Updated TOOL_FORM_AGENT with critical workflow instructions for artifact output
- Artifact generation tools now output full artifact structure in proper code fence format


## [0.44.3] - 2026-01-10

### Added
- **Artifact Rendering System in Web UI**: Complete implementation of artifact detection and rendering
  - Added right panel (Artifacts) to web interface (400px sidebar)
  - Implemented artifact detection via regex pattern matching
  - Created FormRenderer for `artifact:form` (generic data collection forms)
  - Created ToolFormRenderer for `artifact:toolform` (MCP tool execution forms)
  - Added form submission handlers with API integration
  - Auto-detection and rendering of artifacts in LLM responses
  - Form field types: text, textarea, select, checkbox, radio, email, number
  - Tool form execution via `/api/tools/execute` endpoint
  - Result display for both generic and tool forms

### Changed
- Updated web UI layout to three-column design (left panel, chat, right panel)
- Modified `updateMessage()` function to detect and render artifacts
- Increased max-width of app container to 1800px to accommodate artifact panel

### Documentation
- Added ARTIFACT_UI_IMPLEMENTATION.md with complete implementation details
- Documented user flows for generic and tool forms
- Added testing instructions and known limitations


## [0.44.4] - 2026-01-10

### Fixed
- **Web Server Not Loading MCP Servers from Config**: Fixed critical bug where web interface only showed builtin tools
  - `run_web_server()` now loads config.json file when config_dir is provided
  - Previously only passed config_dir path without loading mcpServers configuration
  - Web interface now loads all MCP servers (biblerag, obsidian, nextcloud-api, etc.) just like CLI
  - Added informative logging showing loaded config file and server count

### Changed
- Enhanced `run_web_server()` to merge config file contents into global config
- Web sessions now have access to full configuration including mcpServers definitions

