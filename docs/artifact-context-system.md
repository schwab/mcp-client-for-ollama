# Artifact Context System Design

**Version:** 1.0
**Date:** 2026-01-10
**Status:** 📋 Design Complete

## Overview

This document describes the **Artifact Context System**, which enables user interactions with artifacts to be accessible by the LLM in subsequent conversation turns. When users submit forms, execute tools via artifacts, or interact with visualizations, the results are automatically tracked and made available for natural language reference.

## Problem Statement

Without context tracking, users cannot reference previous artifact interactions:

**❌ Current behavior (without context):**
```
User: [Submits form to read file "README.md"]
Assistant: [Shows file contents in artifact]
User: "Summarize what I just loaded"
Assistant: "I don't have information about what you loaded."
```

**✅ Desired behavior (with context):**
```
User: [Submits form to read file "README.md"]
Assistant: [Shows file contents in artifact]
         [Context automatically tracks: tool=read_file, args={path: "README.md"}, result=<file contents>]
User: "Summarize what I just loaded"
Assistant: [Has access to README.md contents from context]
         "Based on the README.md file you just loaded, here's a summary..."
```

## Architecture

### 1. Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Artifact    │  │  Form        │  │  Result      │  │
│  │  Display     │  │  Submission  │  │  Display     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────▲───────┘  │
│         │                  │                  │          │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
          ▼                  ▼                  │
┌─────────────────────────────────────────────────────────┐
│              Artifact Context Manager                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Track:                                           │  │
│  │  • Artifacts displayed                            │  │
│  │  • User interactions                              │  │
│  │  • Tool executions                                │  │
│  │  • Execution results                              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Provide:                                         │  │
│  │  • Context injection for LLM                      │  │
│  │  • Reference resolution                           │  │
│  │  • Result caching                                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                   Conversation History                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Messages:                                        │  │
│  │  • User messages                                  │  │
│  │  • Assistant messages                             │  │
│  │  • Artifact execution records ← NEW              │  │
│  │  • Tool results ← NEW                            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                    LLM Context                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Automatically includes:                          │  │
│  │  • Recent artifact results                        │  │
│  │  • Referenced tool outputs                        │  │
│  │  • User interaction history                       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 2. Data Models

#### ArtifactExecution
Represents a single artifact interaction and its result.

```python
class ArtifactExecution:
    """Record of an artifact interaction."""

    execution_id: str              # Unique ID (UUID)
    timestamp: datetime            # When it was executed
    artifact_type: str             # e.g., "toolform", "batchtool"
    artifact_title: str            # Display title

    # Tool execution details
    tool_name: str                 # e.g., "builtin.read_file"
    tool_args: Dict[str, Any]      # Arguments passed to tool
    tool_result: str               # Result from tool execution

    # User interaction
    user_id: Optional[str]         # Who triggered it
    interaction_type: str          # "form_submit", "batch_execute", etc.

    # Result metadata
    result_type: str               # "success", "error", "partial"
    result_summary: str            # Brief summary for reference
    result_size: int               # Size of result in bytes

    # Context flags
    is_referenceable: bool         # Can be referenced in conversation
    context_ttl: int               # Time-to-live in context (in messages)
```

#### ArtifactContext
Manages the collection of artifact executions for a session.

```python
class ArtifactContext:
    """Manages artifact execution history and context."""

    session_id: str
    executions: List[ArtifactExecution]

    # Configuration
    max_context_items: int = 10           # Max items in active context
    max_result_size: int = 50000          # Max size of individual result
    auto_summarize_threshold: int = 10000 # Auto-summarize if larger

    # Reference tracking
    last_execution: Optional[ArtifactExecution]
    recent_files: List[str]               # Recently accessed files
    recent_tools: List[str]               # Recently used tools
```

### 3. Context Injection Strategy

The system automatically injects relevant artifact results into the LLM context based on:

#### A. Recency
Most recent artifact executions are always included.

```python
# Include last N executions
recent_executions = context.get_recent_executions(limit=3)
```

#### B. Explicit References
When user mentions something, resolve and include it.

```python
# User: "summarize what I just loaded"
# System detects: reference to recent action
# System includes: last file read result
```

#### C. Semantic Relevance
Include results that might be relevant to current query.

```python
# User: "what's in the config?"
# System detects: config-related query
# System includes: recent config file reads
```

#### D. Size Management
Large results are automatically summarized or truncated.

```python
if result_size > auto_summarize_threshold:
    # Use LLM to create summary
    summary = summarize_result(result)
    inject_summary_instead_of_full_result()
```

### 4. Reference Resolution

Users can reference previous artifacts using natural language:

#### Temporal References
- "the file I just loaded"
- "what I read earlier"
- "the last execution"
- "the previous result"

```python
def resolve_temporal_reference(query: str) -> Optional[ArtifactExecution]:
    """Resolve time-based references."""
    if "just" in query or "last" in query:
        return context.last_execution
    elif "earlier" in query or "previous" in query:
        return context.get_recent_executions(limit=2)[1]  # Second to last
```

#### Content References
- "the README file"
- "the test results"
- "the config I opened"

```python
def resolve_content_reference(query: str) -> List[ArtifactExecution]:
    """Resolve content-based references."""
    # Extract file names mentioned
    file_names = extract_file_names(query)

    # Find executions involving those files
    return [
        exec for exec in context.executions
        if any(fname in exec.tool_args.get('path', '') for fname in file_names)
    ]
```

#### Tool References
- "the files I listed"
- "what I executed"
- "the batch operation"

```python
def resolve_tool_reference(query: str) -> List[ArtifactExecution]:
    """Resolve tool-based references."""
    tool_keywords = {
        "listed": ["list_files", "list_directories"],
        "executed": ["execute_python_code", "execute_bash_command"],
        "read": ["read_file"],
        "wrote": ["write_file", "patch_file"],
    }

    for keyword, tools in tool_keywords.items():
        if keyword in query.lower():
            return [
                exec for exec in context.recent_executions
                if exec.tool_name in tools
            ]
```

### 5. Context Injection Format

Results are injected into the LLM context as structured messages:

```json
{
  "role": "system",
  "content": "**Artifact Context:**\n\nThe user recently executed the following tools via artifacts:\n\n1. **File Read** (just now)\n   Tool: builtin.read_file\n   Arguments: {\"path\": \"README.md\"}\n   Result:\n   ```markdown\n   # My Project\n   \n   This is a sample project...\n   ```\n\n2. **List Files** (2 minutes ago)\n   Tool: builtin.list_files\n   Arguments: {\"path\": \"src\"}\n   Result:\n   ```\n   src/main.py\n   src/utils.py\n   src/__init__.py\n   ```\n\nYou can reference these results when answering the user's questions."
}
```

### 6. Message Flow

#### Step-by-Step Flow

**1. User Submits Artifact Form**
```
Frontend: User fills out toolform for builtin.read_file
         ↓
Frontend: Submits form via WebSocket/API
         ↓
Backend:  Receives submission
         {
           "artifact_id": "art_123",
           "tool_name": "builtin.read_file",
           "tool_args": {"path": "README.md"}
         }
```

**2. Tool Execution & Result Capture**
```
Backend:  Execute tool
         result = tool_manager.execute_tool("builtin.read_file", {"path": "README.md"})
         ↓
Backend:  Create ArtifactExecution record
         execution = ArtifactExecution(
           execution_id=uuid4(),
           tool_name="builtin.read_file",
           tool_args={"path": "README.md"},
           tool_result=result,
           result_summary="Loaded README.md (2.5 KB)"
         )
         ↓
Backend:  Add to context
         artifact_context.add_execution(execution)
```

**3. Store in Conversation History**
```
Backend:  Add special message to chat history
         chat_history.append({
           "role": "artifact_execution",
           "execution_id": execution.execution_id,
           "tool": execution.tool_name,
           "summary": execution.result_summary,
           "timestamp": execution.timestamp
         })
```

**4. Return Result to User**
```
Backend → Frontend: {
           "execution_id": "exec_456",
           "status": "success",
           "result": result,
           "display": {
             "type": "code",
             "syntax": "markdown",
             "content": result
           }
         }
         ↓
Frontend: Display result in artifact panel
```

**5. User Asks Follow-Up Question**
```
User: "Summarize what I just loaded"
      ↓
Frontend → Backend: {
           "message": "Summarize what I just loaded",
           "session_id": "sess_789"
         }
```

**6. Context Resolution & Injection**
```
Backend:  Resolve reference
         query = "Summarize what I just loaded"
         reference = resolve_temporal_reference(query)  # Returns last execution
         ↓
Backend:  Build context
         context_msg = {
           "role": "system",
           "content": f"""
           **Recent Artifact Activity:**

           The user just loaded the file 'README.md' using the read_file tool.

           File Contents:
           ```markdown
           {reference.tool_result}
           ```

           Please summarize this file in your response.
           """
         }
         ↓
Backend:  Inject into LLM context
         messages = [
           system_prompt,
           context_msg,        # ← Injected context
           *chat_history,
           user_message
         ]
         ↓
Backend:  Call LLM
         response = llm.generate(messages)
```

**7. LLM Response**
```
LLM → Backend: "Based on the README.md file you just loaded,
                this is a sample project that..."
                ↓
Backend → Frontend: {
           "response": "Based on the README.md...",
           "referenced_executions": ["exec_456"]
         }
         ↓
Frontend: Display response
         Optionally highlight referenced artifacts
```

### 7. Implementation Classes

#### Backend: `ArtifactContextManager`

```python
# mcp_client_for_ollama/artifacts/context_manager.py

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from uuid import uuid4
import re


@dataclass
class ArtifactExecution:
    """Record of an artifact interaction."""

    execution_id: str
    timestamp: datetime
    artifact_type: str
    artifact_title: str
    tool_name: str
    tool_args: Dict[str, Any]
    tool_result: str
    user_id: Optional[str] = None
    interaction_type: str = "form_submit"
    result_type: str = "success"
    result_summary: str = ""
    result_size: int = 0
    is_referenceable: bool = True
    context_ttl: int = 10


@dataclass
class ArtifactContext:
    """Manages artifact execution history and context."""

    session_id: str
    executions: List[ArtifactExecution] = field(default_factory=list)
    max_context_items: int = 10
    max_result_size: int = 50000
    auto_summarize_threshold: int = 10000

    @property
    def last_execution(self) -> Optional[ArtifactExecution]:
        """Get the most recent execution."""
        return self.executions[-1] if self.executions else None

    @property
    def recent_files(self) -> List[str]:
        """Get recently accessed file paths."""
        files = []
        for exec in reversed(self.executions):
            if 'path' in exec.tool_args:
                path = exec.tool_args['path']
                if path not in files:
                    files.append(path)
        return files[:10]

    @property
    def recent_tools(self) -> List[str]:
        """Get recently used tools."""
        tools = []
        for exec in reversed(self.executions):
            if exec.tool_name not in tools:
                tools.append(exec.tool_name)
        return tools[:10]

    def add_execution(self, execution: ArtifactExecution):
        """Add an execution record."""
        self.executions.append(execution)

        # Prune old executions
        if len(self.executions) > 50:
            self.executions = self.executions[-50:]

    def get_recent_executions(self, limit: int = 5) -> List[ArtifactExecution]:
        """Get N most recent executions."""
        return list(reversed(self.executions[-limit:]))


class ArtifactContextManager:
    """Manages artifact context for LLM integration."""

    def __init__(self):
        self.contexts: Dict[str, ArtifactContext] = {}
        self.reference_resolvers = [
            self._resolve_temporal_reference,
            self._resolve_content_reference,
            self._resolve_tool_reference,
        ]

    def get_or_create_context(self, session_id: str) -> ArtifactContext:
        """Get or create context for a session."""
        if session_id not in self.contexts:
            self.contexts[session_id] = ArtifactContext(session_id=session_id)
        return self.contexts[session_id]

    def record_execution(
        self,
        session_id: str,
        artifact_type: str,
        artifact_title: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: str,
        **kwargs
    ) -> ArtifactExecution:
        """Record a new artifact execution."""
        context = self.get_or_create_context(session_id)

        # Create execution record
        execution = ArtifactExecution(
            execution_id=str(uuid4()),
            timestamp=datetime.now(),
            artifact_type=artifact_type,
            artifact_title=artifact_title,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            result_size=len(tool_result),
            result_summary=self._create_summary(tool_name, tool_args, tool_result),
            **kwargs
        )

        context.add_execution(execution)
        return execution

    def build_context_message(
        self,
        session_id: str,
        user_query: Optional[str] = None,
        include_recent: int = 3
    ) -> Optional[Dict[str, str]]:
        """
        Build a context message for the LLM.

        Args:
            session_id: The session ID
            user_query: Optional user query to resolve references
            include_recent: Number of recent executions to include

        Returns:
            A system message with artifact context, or None if no context
        """
        context = self.get_or_create_context(session_id)

        if not context.executions:
            return None

        # Get executions to include
        executions_to_include = []

        # 1. Always include recent executions
        recent = context.get_recent_executions(limit=include_recent)
        executions_to_include.extend(recent)

        # 2. If user query provided, resolve references and include
        if user_query:
            referenced = self.resolve_references(session_id, user_query)
            for exec in referenced:
                if exec not in executions_to_include:
                    executions_to_include.append(exec)

        # Build context message
        content_parts = ["**Artifact Context:**\n"]
        content_parts.append("The user recently executed the following tools via artifacts:\n")

        for i, execution in enumerate(executions_to_include, 1):
            content_parts.append(f"\n{i}. **{execution.artifact_title}**")
            content_parts.append(f"   Time: {self._format_time_ago(execution.timestamp)}")
            content_parts.append(f"   Tool: {execution.tool_name}")
            content_parts.append(f"   Arguments: {execution.tool_args}")

            # Include result (with size management)
            result = execution.tool_result
            if execution.result_size > context.auto_summarize_threshold:
                result = self._truncate_result(result, max_size=5000)
                content_parts.append(f"   Result (truncated): {result}")
            else:
                content_parts.append(f"   Result:\n   ```\n{result}\n   ```")

        content_parts.append("\nYou can reference these results when answering the user's questions.")

        return {
            "role": "system",
            "content": "\n".join(content_parts)
        }

    def resolve_references(
        self,
        session_id: str,
        query: str
    ) -> List[ArtifactExecution]:
        """
        Resolve references in user query to artifact executions.

        Args:
            session_id: The session ID
            query: User's query text

        Returns:
            List of referenced executions
        """
        context = self.get_or_create_context(session_id)
        referenced = []

        for resolver in self.reference_resolvers:
            results = resolver(context, query)
            for result in results:
                if result not in referenced:
                    referenced.append(result)

        return referenced

    def _resolve_temporal_reference(
        self,
        context: ArtifactContext,
        query: str
    ) -> List[ArtifactExecution]:
        """Resolve time-based references."""
        query_lower = query.lower()

        # "just", "last", "latest", "recent"
        if any(word in query_lower for word in ["just", "last", "latest", "recent"]):
            if context.last_execution:
                return [context.last_execution]

        # "earlier", "previous", "before"
        if any(word in query_lower for word in ["earlier", "previous", "before"]):
            recent = context.get_recent_executions(limit=2)
            if len(recent) > 1:
                return [recent[1]]  # Second to last

        return []

    def _resolve_content_reference(
        self,
        context: ArtifactContext,
        query: str
    ) -> List[ArtifactExecution]:
        """Resolve content-based references (file names, etc.)."""
        referenced = []

        # Extract potential file names (simple heuristic)
        # Matches: word.ext, path/to/file.ext, "quoted/file.ext"
        file_patterns = [
            r'\b(\w+\.\w+)\b',           # Simple file.ext
            r'\b([\w/]+\.\w+)\b',         # path/file.ext
            r'"([^"]+\.\w+)"',            # "quoted/file.ext"
            r"'([^']+\.\w+)'",            # 'quoted/file.ext'
        ]

        mentioned_files = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, query)
            mentioned_files.update(matches)

        # Find executions involving these files
        for exec in reversed(context.executions):
            if 'path' in exec.tool_args:
                path = exec.tool_args['path']
                # Check if any mentioned file matches this path
                if any(fname in path for fname in mentioned_files):
                    referenced.append(exec)

        return referenced[:5]  # Limit to 5 matches

    def _resolve_tool_reference(
        self,
        context: ArtifactContext,
        query: str
    ) -> List[ArtifactExecution]:
        """Resolve tool-based references."""
        query_lower = query.lower()

        tool_keywords = {
            "list": ["builtin.list_files", "builtin.list_directories"],
            "read": ["builtin.read_file"],
            "wrote": ["builtin.write_file", "builtin.patch_file"],
            "executed": ["builtin.execute_python_code", "builtin.execute_bash_command"],
            "test": ["builtin.run_pytest"],
        }

        for keyword, tools in tool_keywords.items():
            if keyword in query_lower:
                matches = [
                    exec for exec in reversed(context.executions)
                    if exec.tool_name in tools
                ]
                if matches:
                    return matches[:3]  # Return up to 3 most recent

        return []

    def _create_summary(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: str
    ) -> str:
        """Create a brief summary of the execution."""
        # Tool-specific summaries
        if "read_file" in tool_name:
            path = tool_args.get('path', 'unknown')
            size_kb = len(tool_result) / 1024
            return f"Loaded {path} ({size_kb:.1f} KB)"

        elif "write_file" in tool_name:
            path = tool_args.get('path', 'unknown')
            return f"Wrote to {path}"

        elif "list_files" in tool_name or "list_directories" in tool_name:
            path = tool_args.get('path', '.')
            lines = tool_result.split('\n')
            count = len([line for line in lines if line.strip()])
            return f"Listed {count} items in {path}"

        elif "execute" in tool_name:
            return f"Executed code/command"

        else:
            return f"Executed {tool_name}"

    def _format_time_ago(self, timestamp: datetime) -> str:
        """Format timestamp as 'X ago' string."""
        delta = datetime.now() - timestamp

        if delta < timedelta(minutes=1):
            return "just now"
        elif delta < timedelta(hours=1):
            mins = int(delta.total_seconds() / 60)
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = delta.days
            return f"{days} day{'s' if days != 1 else ''} ago"

    def _truncate_result(self, result: str, max_size: int = 5000) -> str:
        """Truncate large results."""
        if len(result) <= max_size:
            return result

        # Show first portion with ellipsis
        keep_size = max_size - 50  # Leave room for message
        truncated = result[:keep_size]
        total_size_kb = len(result) / 1024

        return f"{truncated}\n\n... (truncated, total size: {total_size_kb:.1f} KB)"
```

#### Frontend: Artifact Submission Handler

```typescript
// web/src/services/artifactService.ts

interface ArtifactSubmission {
  artifactId: string;
  artifactType: string;
  toolName: string;
  toolArgs: Record<string, any>;
}

interface ExecutionResult {
  executionId: string;
  status: 'success' | 'error';
  result: string;
  display?: {
    type: string;
    syntax?: string;
    content: string;
  };
  summary: string;
}

class ArtifactService {
  async submitArtifact(submission: ArtifactSubmission): Promise<ExecutionResult> {
    // 1. Submit to backend
    const response = await fetch('/api/artifacts/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submission),
    });

    const result: ExecutionResult = await response.json();

    // 2. Store in local context (for UI state)
    this.addToLocalContext(result);

    // 3. Update chat history with execution record
    this.addToChatHistory({
      role: 'artifact_execution',
      executionId: result.executionId,
      summary: result.summary,
      timestamp: new Date(),
    });

    return result;
  }

  private addToLocalContext(result: ExecutionResult) {
    // Store in React context or state management
    // This allows UI to highlight referenced artifacts
  }

  private addToChatHistory(message: any) {
    // Add to chat history state
    // This creates a visual record in the chat
  }
}
```

### 8. API Endpoints

#### POST `/api/artifacts/execute`

Execute a tool from an artifact and record the result.

**Request:**
```json
{
  "session_id": "sess_123",
  "artifact_id": "art_456",
  "artifact_type": "toolform",
  "artifact_title": "Read File",
  "tool_name": "builtin.read_file",
  "tool_args": {
    "path": "README.md"
  }
}
```

**Response:**
```json
{
  "execution_id": "exec_789",
  "status": "success",
  "result": "# My Project\n\nThis is a sample...",
  "display": {
    "type": "code",
    "syntax": "markdown",
    "content": "# My Project\n\n..."
  },
  "summary": "Loaded README.md (2.5 KB)",
  "timestamp": "2026-01-10T10:30:00Z"
}
```

#### GET `/api/artifacts/context/{session_id}`

Get the current artifact context for a session.

**Response:**
```json
{
  "session_id": "sess_123",
  "executions": [
    {
      "execution_id": "exec_789",
      "timestamp": "2026-01-10T10:30:00Z",
      "artifact_title": "Read File",
      "tool_name": "builtin.read_file",
      "summary": "Loaded README.md (2.5 KB)",
      "result_type": "success"
    }
  ],
  "recent_files": ["README.md", "src/main.py"],
  "recent_tools": ["builtin.read_file", "builtin.list_files"]
}
```

### 9. Chat History Integration

Artifact executions are stored as special message types in the chat history:

```python
# When user submits artifact
chat_history.append({
    "role": "artifact_execution",
    "execution_id": execution.execution_id,
    "tool": execution.tool_name,
    "summary": execution.result_summary,
    "timestamp": execution.timestamp.isoformat(),
    "visible": True  # Show in UI timeline
})

# When building LLM context
messages_for_llm = []
for msg in chat_history:
    if msg["role"] == "artifact_execution":
        # Include as system message with full result
        execution = context_manager.get_execution(msg["execution_id"])
        messages_for_llm.append({
            "role": "system",
            "content": f"Tool Execution: {execution.tool_name}\nResult: {execution.tool_result}"
        })
    else:
        messages_for_llm.append(msg)
```

### 10. UI Components

#### Artifact Execution Timeline

Show visual timeline of artifact executions in the chat:

```tsx
function ArtifactExecutionMessage({ execution }: { execution: ArtifactExecution }) {
  return (
    <div className="artifact-execution-message">
      <div className="execution-header">
        <Icon name={getToolIcon(execution.tool_name)} />
        <span className="tool-name">{execution.artifact_title}</span>
        <span className="timestamp">{formatTimeAgo(execution.timestamp)}</span>
      </div>
      <div className="execution-summary">
        {execution.result_summary}
      </div>
      <button onClick={() => showFullResult(execution.execution_id)}>
        View Full Result
      </button>
    </div>
  );
}
```

#### Referenced Artifact Indicator

Highlight when LLM response references an artifact:

```tsx
function AssistantMessage({ message, referencedExecutions }: Props) {
  return (
    <div className="assistant-message">
      {referencedExecutions.length > 0 && (
        <div className="referenced-context">
          <Icon name="link" />
          <span>Referenced: {referencedExecutions.map(e => e.artifact_title).join(', ')}</span>
        </div>
      )}
      <div className="message-content">
        {message.content}
      </div>
    </div>
  );
}
```

## Configuration

### Environment Variables

```bash
# Maximum size for artifact results (bytes)
ARTIFACT_CONTEXT_MAX_RESULT_SIZE=50000

# Auto-summarize threshold (bytes)
ARTIFACT_CONTEXT_SUMMARIZE_THRESHOLD=10000

# Number of recent executions to include by default
ARTIFACT_CONTEXT_RECENT_LIMIT=3

# TTL for context items (number of conversation turns)
ARTIFACT_CONTEXT_TTL=10

# Enable/disable automatic context injection
ARTIFACT_CONTEXT_AUTO_INJECT=true
```

### Per-Session Configuration

Users can control context behavior:

```python
# Disable auto-injection for a session
context.auto_inject = False

# Increase context window
context.max_context_items = 20

# Increase summarization threshold
context.auto_summarize_threshold = 50000
```

## Examples

### Example 1: File Reading Flow

```
1. User submits toolform: read_file(path="README.md")
2. System executes tool and records result
3. System adds to context: "Loaded README.md (2.5 KB)"
4. User asks: "What's the main purpose of this project?"
5. System injects README.md contents into LLM context
6. LLM responds with summary based on README.md
```

### Example 2: Multi-Step Workflow

```
1. User submits: list_files(path="src")
2. Context: "Listed 15 files in src"
3. User submits: read_file(path="src/main.py")
4. Context: "Loaded src/main.py (5.2 KB)"
5. User asks: "What files did I just look at?"
6. System resolves references to both executions
7. LLM responds: "You listed files in src/ and read main.py"
```

### Example 3: Batch Operations

```
1. User submits batch read: read_file x 5 files
2. Context records all 5 executions
3. User asks: "Which file was longest?"
4. System includes all 5 file contents
5. LLM compares and identifies longest file
```

## Benefits

1. **Natural Conversation:** Users can reference previous actions naturally
2. **Reduced Repetition:** No need to re-upload or re-specify data
3. **Context Awareness:** LLM has full picture of user's workflow
4. **Better UX:** Seamless integration between artifacts and chat
5. **Audit Trail:** Complete history of artifact interactions
6. **Smart Summarization:** Large results are managed automatically

## Next Steps

1. **Implement `ArtifactContextManager` class**
2. **Add API endpoints for artifact execution**
3. **Update delegation client to use context manager**
4. **Create frontend components for execution timeline**
5. **Add reference highlighting in UI**
6. **Write integration tests**

---

**Design Status:** ✅ Complete
**Implementation Status:** ⏳ Pending
**Testing Status:** ⏳ Pending
