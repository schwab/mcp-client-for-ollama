# Memory Control Panel - UI Design & Implementation Plan

## Overview
Design for a comprehensive Memory Control Panel in the web UI, allowing users to create, view, and manage memory sessions, goals, and features through a visual interface.

## UI Structure

### Layout Position
- **Location**: Left panel (similar to existing Tools sidebar)
- **Type**: Collapsible accordion panel
- **Position**: Above or below existing Tools panel
- **Responsive**: Collapsible on mobile

### Panel Hierarchy
```
┌─────────────────────────────────────┐
│ 🧠 Memory Control Panel         ▼  │
├─────────────────────────────────────┤
│                                     │
│ 📊 Session Status                   │
│ ┌─────────────────────────────────┐ │
│ │ Session: abc-123-def            │ │
│ │ Domain: software_dev            │ │
│ │ Progress: 5/12 (42%)            │ │
│ │ [View Full Status]              │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 🎯 Goals                            │
│ ┌─────────────────────────────────┐ │
│ │ ✓ G1: User Authentication       │ │
│ │    5/5 features (100%)          │ │
│ │    [Details] [Edit]             │ │
│ │                                 │ │
│ │ ⟳ G2: API Endpoints             │ │
│ │    3/7 features (43%)           │ │
│ │    [Details] [Edit]             │ │
│ │                                 │ │
│ │ [+ New Goal]                    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 📋 Features (Expanded Goal View)    │
│ ┌─────────────────────────────────┐ │
│ │ Goal G2: API Endpoints          │ │
│ │ ─────────────────────────────   │ │
│ │ ✓ F1: Create endpoints [High]  │ │
│ │ ⟳ F2: Validation [Medium]      │ │
│ │ ○ F3: Error handling [Low]     │ │
│ │ [+ Add Feature to G2]           │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ⚙️  Quick Actions                    │
│ ┌─────────────────────────────────┐ │
│ │ [New Session] [Import] [Export] │ │
│ └─────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

## Component Design

### 1. Memory Session Status Card
**Purpose**: Display current session overview

**Elements**:
- Session ID (truncated with tooltip)
- Domain name
- Session description (editable inline)
- Overall progress bar (% of features completed)
- "View Full Status" button → Opens modal with detailed memory state

**Data Source**: `GET /api/memory/status`

**Visual Design**:
```
┌────────────────────────────────────────┐
│ 📊 Session Status                      │
│ ────────────────────────────────────── │
│ Session: abc-123-def (📋 copy)         │
│ Domain: software_dev                   │
│ Description: "Building MCP web client" │
│                                        │
│ ████████░░░░░░░░░░░  42% Complete      │
│                                        │
│ 5 of 12 features completed             │
│ 2 goals active, 1 completed            │
│                                        │
│ [View Full Details]                    │
└────────────────────────────────────────┘
```

### 2. Goals List Component
**Purpose**: Show all goals with status indicators

**Elements per Goal**:
- Status icon (○ pending, ⟳ in_progress, ✓ completed, ✗ failed, ⊘ blocked)
- Goal ID + Description
- Progress fraction (completed/total features)
- Progress percentage
- Action buttons: [Details] [Edit] [Delete]

**Interaction**:
- Click goal card → Expands to show features
- [Details] → Opens modal with full goal details
- [Edit] → Opens edit modal
- [Delete] → Confirmation dialog

**Data Source**: `GET /api/memory/goals`

**Visual Design**:
```
┌────────────────────────────────────────┐
│ 🎯 Goals                        [+ New]│
│ ────────────────────────────────────── │
│ ✓ G1: User Authentication              │
│   ████████████████████  100%           │
│   5/5 features completed               │
│   [Details] [Edit]                     │
│ ────────────────────────────────────── │
│ ⟳ G2: API Development                  │
│   ████████░░░░░░░░░░░   43%            │
│   3/7 features completed               │
│   [Details] [Edit] [Delete]            │
│ ────────────────────────────────────── │
│ ○ G3: Testing Framework                │
│   ░░░░░░░░░░░░░░░░░░░   0%             │
│   0/4 features completed               │
│   [Details] [Edit] [Delete]            │
└────────────────────────────────────────┘
```

### 3. Features List (Nested View)
**Purpose**: Show features within expanded goal

**Elements per Feature**:
- Status icon with color coding
- Feature ID + Description (truncated if long)
- Priority badge ([HIGH], [LOW], or no badge for medium)
- Assignee if set
- Test count indicator (if tests defined)
- Action buttons: [Details] [Edit] [Status]

**Interaction**:
- Click feature → Expands to show criteria/tests
- [Details] → Modal with full feature details
- [Status] → Quick status change dropdown
- [Edit] → Edit feature modal

**Data Source**: `GET /api/memory/goals/{goal_id}/features`

**Visual Design**:
```
┌────────────────────────────────────────┐
│ Goal G2: API Development        [▲]   │
│ ────────────────────────────────────── │
│ Features (3/7 completed):              │
│                                        │
│ ✓ F1: [HIGH] POST /api/users          │
│   → CODER | 3 tests ✓                  │
│   [Details]                            │
│                                        │
│ ⟳ F2: Request validation               │
│   → EXECUTOR | 2 tests (1✓ 1✗)        │
│   [Details] [Edit] [Status ▼]         │
│                                        │
│ ○ F3: Error handling                   │
│   No tests defined                     │
│   [Details] [Edit] [Status ▼]         │
│                                        │
│ [+ Add Feature]                        │
└────────────────────────────────────────┘
```

### 4. Status Indicators Legend
**Purpose**: Help users understand status icons

**Location**: Bottom of panel or tooltip

```
○ Pending     ⟳ In Progress     ✓ Completed
✗ Failed      ⊘ Blocked
```

### 5. Quick Actions Toolbar
**Purpose**: Top-level memory operations

**Buttons**:
- [New Session] - Create new memory session
- [Clear Memory] - Clear current session
- [Import] - Import memory from JSON
- [Export] - Export memory to JSON
- [Refresh] - Reload memory state

**Visual Design**:
```
┌────────────────────────────────────────┐
│ ⚙️ Quick Actions                        │
│ ────────────────────────────────────── │
│ [🆕 New] [🗑️ Clear] [📥 Import] [📤 Export] │
│ [🔄 Refresh]                           │
└────────────────────────────────────────┘
```

## Modal Dialogs

### 1. Full Memory Status Modal
**Trigger**: Click "View Full Details" in session status

**Content**:
- Complete memory state from `get_memory_state()`
- Project context information
- Progress history chart (if available)
- Session metadata (created, updated timestamps)

**Actions**: [Export] [Close]

### 2. Goal Details Modal
**Trigger**: Click [Details] on a goal

**Content**:
- Goal ID, description, status
- Constraints list (editable)
- All features with full details
- Progress statistics

**Actions**: [Edit] [Delete] [Close]

### 3. Feature Details Modal
**Trigger**: Click [Details] on a feature

**Content**:
- Feature ID, description, status
- Priority, assignee
- Criteria checklist (each criterion can be checked/unchecked)
- Tests list
- Test results history (table with pass/fail/timestamp)
- Notes section

**Actions**: [Edit] [Update Status] [Close]

### 4. Create/Edit Goal Modal
**Trigger**: Click [+ New Goal] or [Edit] on goal

**Form Fields**:
- Goal ID (optional, auto-generated if empty)
- Description (required, textarea)
- Constraints (list, add/remove items)

**Validation**:
- Description required
- Goal ID unique (if provided)

**Actions**: [Save] [Cancel]

### 5. Create/Edit Feature Modal
**Trigger**: Click [+ Add Feature] or [Edit] on feature

**Form Fields**:
- Parent Goal (dropdown if creating)
- Description (required, textarea)
- Priority (dropdown: High, Medium, Low)
- Assigned To (text input, optional)
- Criteria (list, add/remove items)
- Tests (list, add/remove items)

**Validation**:
- Description required
- Priority must be valid

**Actions**: [Save] [Cancel]

### 6. Quick Status Update Dropdown
**Trigger**: Click [Status ▼] on feature

**Options**:
- ○ Pending
- ⟳ In Progress
- ✓ Completed
- ✗ Failed
- ⊘ Blocked

**Additional**:
- Notes field (optional)
- [Update] [Cancel] buttons

## API Endpoints Required

### Memory Session Management
```
GET    /api/memory/status
  → Returns current session status (session_id, domain, description, progress)
  → Response: { session_id, domain, description, total_features, completed_features, completion_percentage }

POST   /api/memory/new
  → Creates new memory session
  → Body: { domain, description }
  → Response: { session_id, domain, description }

DELETE /api/memory/clear
  → Clears current memory session
  → Body: { session_id }
  → Response: { status: 'cleared' }

GET    /api/memory/export
  → Exports memory session to JSON
  → Query: session_id
  → Response: JSON file download

POST   /api/memory/import
  → Imports memory session from JSON
  → Body: { json_data }
  → Response: { status: 'imported', session_id }
```

### Goals API
```
GET    /api/memory/goals
  → List all goals with summary
  → Query: session_id
  → Response: { goals: [{ id, description, status, feature_count, completed_count, percentage }] }

GET    /api/memory/goals/:goal_id
  → Get detailed goal info
  → Query: session_id
  → Response: { id, description, status, constraints, features: [...] }

POST   /api/memory/goals
  → Create new goal
  → Body: { session_id, goal_id (optional), description, constraints }
  → Response: { goal_id, status: 'created' }

PUT    /api/memory/goals/:goal_id
  → Update goal
  → Body: { session_id, description, add_constraints, remove_constraints }
  → Response: { goal_id, status: 'updated' }

DELETE /api/memory/goals/:goal_id
  → Delete goal
  → Body: { session_id, confirm: true }
  → Response: { status: 'deleted', features_removed }
```

### Features API
```
GET    /api/memory/features/:feature_id
  → Get detailed feature info
  → Query: session_id
  → Response: { id, description, status, priority, criteria, tests, test_results, ... }

POST   /api/memory/features
  → Create new feature
  → Body: { session_id, goal_id, description, criteria, tests, priority, assigned_to }
  → Response: { feature_id, status: 'created' }

PUT    /api/memory/features/:feature_id
  → Update feature
  → Body: { session_id, description, add_criteria, remove_criteria, priority, assigned_to, ... }
  → Response: { feature_id, status: 'updated' }

PUT    /api/memory/features/:feature_id/status
  → Quick status update
  → Body: { session_id, status, notes }
  → Response: { feature_id, new_status, status: 'updated' }

DELETE /api/memory/features/:feature_id
  → Delete feature
  → Body: { session_id, confirm: true }
  → Response: { status: 'deleted' }

POST   /api/memory/features/:feature_id/move
  → Move feature to different goal
  → Body: { session_id, target_goal_id }
  → Response: { feature_id, old_goal_id, new_goal_id, status: 'moved' }
```

### Progress Tracking
```
POST   /api/memory/progress
  → Log progress entry
  → Body: { session_id, agent_type, action, outcome, details, feature_id, artifacts_changed }
  → Response: { status: 'logged' }

POST   /api/memory/test-results
  → Add test result
  → Body: { session_id, feature_id, test_id, passed, details, output }
  → Response: { status: 'added', feature_status_updated }
```

## Implementation Plan

### Phase 1: Backend API Development (2-3 hours)
**Priority**: High

**Tasks**:
1. Create new blueprint: `mcp_client_for_ollama/web/api/memory.py`
2. Implement session endpoints (status, new, clear, export, import)
3. Implement goals CRUD endpoints
4. Implement features CRUD endpoints
5. Implement progress tracking endpoints
6. Add memory tools integration (connect to MCPClient memory system)
7. Add error handling and validation
8. Test all endpoints with curl/Postman

**Files to Create**:
- `mcp_client_for_ollama/web/api/memory.py` (new blueprint)

**Files to Modify**:
- `mcp_client_for_ollama/web/app.py` (register memory blueprint)
- `mcp_client_for_ollama/web/integration/client_wrapper.py` (add memory access methods)

### Phase 2: Frontend State Management (1-2 hours)
**Priority**: High

**Tasks**:
1. Add memory state management to index.html JavaScript
2. Create data structures for goals/features
3. Implement API call functions
4. Add WebSocket/SSE support for real-time updates (optional)

**JavaScript Structure**:
```javascript
// Memory state
let memoryState = {
    session_id: null,
    domain: null,
    description: null,
    goals: [],
    features: {},
    loading: false,
    error: null
};

// API functions
async function getMemoryStatus()
async function loadGoals()
async function loadFeatures(goalId)
async function createGoal(data)
async function updateFeatureStatus(featureId, status, notes)
...
```

### Phase 3: Memory Panel UI Component (2-3 hours)
**Priority**: High

**Tasks**:
1. Add HTML structure for memory panel
2. Style with existing CSS patterns (matching tools/agent activity panels)
3. Implement accordion expand/collapse
4. Add session status card
5. Add goals list rendering
6. Add features list rendering (nested)
7. Add status indicators and icons
8. Test responsive design

**HTML Structure**:
```html
<!-- Memory Control Panel -->
<div class="memory-panel">
    <div class="panel-header" onclick="toggleMemory()">
        <span>🧠 Memory Control</span>
        <span id="memoryToggle" class="accordion-arrow">▼</span>
    </div>
    <div id="memoryContent" class="panel-content">
        <!-- Session Status -->
        <div id="sessionStatus" class="session-status-card">
            <!-- Dynamic content -->
        </div>

        <!-- Goals List -->
        <div id="goalsList" class="goals-list">
            <!-- Dynamic content -->
        </div>

        <!-- Quick Actions -->
        <div class="quick-actions">
            <button onclick="newSession()">New Session</button>
            <button onclick="exportMemory()">Export</button>
            <button onclick="importMemory()">Import</button>
        </div>
    </div>
</div>
```

### Phase 4: Modal Dialogs (2-3 hours)
**Priority**: Medium

**Tasks**:
1. Create reusable modal component
2. Implement goal details modal
3. Implement feature details modal
4. Implement create/edit goal modal
5. Implement create/edit feature modal
6. Implement quick status update dropdown
7. Add form validation
8. Test all modal workflows

### Phase 5: Integration & Testing (1-2 hours)
**Priority**: High

**Tasks**:
1. Connect frontend to backend APIs
2. Test create/read/update/delete operations
3. Test error handling
4. Test with real memory sessions
5. Test concurrent updates
6. Performance testing with large memory sets

### Phase 6: Polish & Documentation (1 hour)
**Priority**: Medium

**Tasks**:
1. Add loading spinners
2. Add success/error toast notifications
3. Add keyboard shortcuts (optional)
4. Add tooltips and help text
5. Write user documentation
6. Create demo video/screenshots

## Styling Guidelines

### Color Scheme
Match existing web UI colors:
```css
:root {
    --memory-primary: #0082c9;       /* Matches chat header */
    --status-pending: #999;          /* Gray */
    --status-in-progress: #f4a70c;   /* Orange */
    --status-completed: #46ba61;     /* Green */
    --status-failed: #f44336;        /* Red */
    --status-blocked: #666;          /* Dark gray */
}
```

### Status Icons
```css
.status-icon {
    display: inline-block;
    width: 16px;
    height: 16px;
    line-height: 16px;
    text-align: center;
    margin-right: 8px;
}

.status-pending { color: var(--status-pending); }
.status-in-progress { color: var(--status-in-progress); }
.status-completed { color: var(--status-completed); }
.status-failed { color: var(--status-failed); }
.status-blocked { color: var(--status-blocked); }
```

### Progress Bars
```css
.progress-bar {
    width: 100%;
    height: 8px;
    background: #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(to right, #667eea, #764ba2);
    transition: width 0.3s ease;
}
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────┐
│           User Interaction                  │
│  (Click, Edit, Create, Delete)              │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│      Frontend JavaScript (index.html)       │
│  - Event handlers                           │
│  - State management                         │
│  - API calls (fetch with credentials)       │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│      Flask API (memory blueprint)           │
│  - Route handlers                           │
│  - Validation                               │
│  - Session management                       │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│    WebMCPClient (client_wrapper.py)         │
│  - Memory tools access                      │
│  - Session context                          │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│      MCPClient Memory System                │
│  - MemoryTools                              │
│  - MemoryStorage                            │
│  - DomainMemory                             │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│         JSON File Storage                   │
│  ~/.config/ollmcp/{domain}_memory.json      │
└─────────────────────────────────────────────┘
```

## Error Handling

### Frontend
- Show toast notifications for errors
- Disable buttons during async operations
- Show loading spinners
- Validate form inputs before submission

### Backend
- Return proper HTTP status codes (400, 404, 500)
- Include error messages in response
- Log errors to console
- Handle missing sessions gracefully

## Security Considerations

### Nextcloud Mode
- Session ID validation (user can only access their own memory)
- Username scoping (multi-user isolation)
- Input sanitization (prevent XSS)

### Standalone Mode
- Session validation
- Input sanitization
- Rate limiting (optional)

## Future Enhancements

### Phase 7+ (Optional)
1. **Real-time Collaboration**: WebSocket support for multi-user editing
2. **Memory Templates**: Pre-defined goal/feature templates
3. **Bulk Operations**: Bulk status updates, bulk delete
4. **Search & Filter**: Search goals/features by keyword, filter by status
5. **Drag & Drop**: Reorder features, move features between goals
6. **Keyboard Shortcuts**: Vim-like navigation
7. **Memory Visualization**: Graph view of dependencies, timeline view
8. **Auto-save Draft**: Save form state to localStorage
9. **Undo/Redo**: History of memory changes
10. **Memory Comparison**: Compare two memory sessions side-by-side

## Success Criteria

✅ Users can view current memory session status
✅ Users can create/edit/delete goals via UI
✅ Users can create/edit/delete features via UI
✅ Users can update feature status with one click
✅ Users can see progress indicators for goals
✅ Users can export/import memory sessions
✅ UI is responsive and works on mobile
✅ All operations work in both standalone and Nextcloud modes
✅ No regressions to existing chat/tools functionality

## Estimated Time
- **Phase 1**: 2-3 hours (Backend API)
- **Phase 2**: 1-2 hours (State Management)
- **Phase 3**: 2-3 hours (UI Components)
- **Phase 4**: 2-3 hours (Modal Dialogs)
- **Phase 5**: 1-2 hours (Integration & Testing)
- **Phase 6**: 1 hour (Polish & Documentation)

**Total**: 9-14 hours (approximately 2 working days)

## Dependencies
- Existing web UI framework (Flask, HTML/CSS/JS)
- Memory system (MemoryTools, MemoryStorage)
- Session management (WebSessionManager)
- Dual-mode support (Standalone/Nextcloud)
