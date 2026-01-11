# Artifact Context Integration Guide

**Version:** 1.0
**Date:** 2026-01-10

## Overview

This guide shows how to integrate the Artifact Context System into the mcp-client-for-ollama delegation client and web UI.

## Backend Integration

### 1. Initialize Context Manager

Add the context manager to the delegation client:

```python
# mcp_client_for_ollama/client.py

from .artifacts import ArtifactContextManager

class DelegationClient:
    def __init__(self, ...):
        # ... existing initialization ...

        # Initialize artifact context manager
        self.artifact_context = ArtifactContextManager()

        # Pass to builtin tool manager
        self.tool_manager.set_artifact_context(self.artifact_context)
```

### 2. Record Artifact Executions

When a tool is executed via an artifact, record it:

```python
# In builtin tool handlers
def _handle_generate_tool_form(self, args: Dict[str, Any]) -> str:
    """Handles the 'generate_tool_form' tool call."""
    tool_name = args.get("tool_name")

    # ... generate form artifact ...

    # No execution recorded here - form just displayed
    return artifact_json

# When user SUBMITS the form:
def execute_artifact_tool(
    self,
    session_id: str,
    artifact_type: str,
    artifact_title: str,
    tool_name: str,
    tool_args: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a tool from an artifact submission."""

    # 1. Execute the tool
    result = self.execute_tool(tool_name, tool_args)

    # 2. Record the execution
    execution = self.artifact_context.record_execution(
        session_id=session_id,
        artifact_type=artifact_type,
        artifact_title=artifact_title,
        tool_name=tool_name,
        tool_args=tool_args,
        tool_result=result,
        result_type="success" if "Error:" not in result else "error"
    )

    # 3. Return result with execution ID
    return {
        "execution_id": execution.execution_id,
        "status": "success" if "Error:" not in result else "error",
        "result": result,
        "summary": execution.result_summary,
        "timestamp": execution.timestamp.isoformat(),
    }
```

### 3. Inject Context into LLM Prompts

Modify the message building to inject artifact context:

```python
# In delegation client's generate_response method
def generate_response(self, user_message: str, session_id: str) -> str:
    """Generate a response from the LLM."""

    # Build base messages
    messages = [
        {"role": "system", "content": self.system_prompt},
    ]

    # Inject artifact context if available
    context_msg = self.artifact_context.build_context_message(
        session_id=session_id,
        user_query=user_message,
        include_recent=3
    )
    if context_msg:
        messages.append(context_msg)

    # Add chat history
    messages.extend(self.chat_history)

    # Add user message
    messages.append({"role": "user", "content": user_message})

    # Generate response
    response = self.llm_generate(messages)

    return response
```

### 4. Add API Endpoints

Create endpoints for artifact execution:

```python
# mcp_client_for_ollama/server/api.py (or new file)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class ArtifactExecutionRequest(BaseModel):
    """Request to execute a tool via artifact."""
    session_id: str
    artifact_id: str
    artifact_type: str
    artifact_title: str
    tool_name: str
    tool_args: Dict[str, Any]


class ArtifactExecutionResponse(BaseModel):
    """Response from artifact execution."""
    execution_id: str
    status: str
    result: str
    summary: str
    timestamp: str
    display: Optional[Dict[str, Any]] = None


@router.post("/execute", response_model=ArtifactExecutionResponse)
async def execute_artifact(request: ArtifactExecutionRequest):
    """Execute a tool from an artifact and record the result."""

    # Get delegation client instance
    client = get_delegation_client()

    # Execute the tool
    result = client.execute_artifact_tool(
        session_id=request.session_id,
        artifact_type=request.artifact_type,
        artifact_title=request.artifact_title,
        tool_name=request.tool_name,
        tool_args=request.tool_args,
    )

    # Determine display format
    display = infer_result_display(request.tool_name, result["result"])

    return ArtifactExecutionResponse(
        execution_id=result["execution_id"],
        status=result["status"],
        result=result["result"],
        summary=result["summary"],
        timestamp=result["timestamp"],
        display=display,
    )


@router.get("/context/{session_id}")
async def get_artifact_context(session_id: str):
    """Get the current artifact context for a session."""

    client = get_delegation_client()

    summary = client.artifact_context.get_context_summary(session_id)

    return summary


@router.delete("/context/{session_id}")
async def clear_artifact_context(session_id: str):
    """Clear artifact context for a session."""

    client = get_delegation_client()
    client.artifact_context.clear_context(session_id)

    return {"status": "cleared"}


def infer_result_display(tool_name: str, result: str) -> Dict[str, Any]:
    """Infer how to display the result."""

    if "read_file" in tool_name:
        # Detect syntax from file extension if possible
        return {"type": "code", "syntax": "auto-detect"}

    elif "list" in tool_name:
        return {"type": "list"}

    elif "execute_python" in tool_name:
        return {"type": "terminal", "syntax": "python-output"}

    elif "execute_bash" in tool_name:
        return {"type": "terminal", "syntax": "bash-output"}

    else:
        return {"type": "text"}
```

## Frontend Integration

### 1. Artifact Submission Service

```typescript
// web/src/services/artifactService.ts

interface ArtifactSubmission {
  sessionId: string;
  artifactId: string;
  artifactType: string;
  artifactTitle: string;
  toolName: string;
  toolArgs: Record<string, any>;
}

interface ExecutionResult {
  executionId: string;
  status: 'success' | 'error';
  result: string;
  summary: string;
  timestamp: string;
  display?: {
    type: string;
    syntax?: string;
  };
}

export class ArtifactService {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  /**
   * Submit an artifact form and execute the tool.
   */
  async submitArtifact(submission: ArtifactSubmission): Promise<ExecutionResult> {
    const response = await fetch(`${this.baseUrl}/api/artifacts/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submission),
    });

    if (!response.ok) {
      throw new Error(`Failed to execute artifact: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Get the current artifact context for a session.
   */
  async getContext(sessionId: string) {
    const response = await fetch(`${this.baseUrl}/api/artifacts/context/${sessionId}`);

    if (!response.ok) {
      throw new Error(`Failed to get context: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Clear artifact context for a session.
   */
  async clearContext(sessionId: string) {
    const response = await fetch(`${this.baseUrl}/api/artifacts/context/${sessionId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to clear context: ${response.statusText}`);
    }

    return await response.json();
  }
}
```

### 2. Chat History Integration

Add artifact execution records to chat history:

```typescript
// web/src/types/chat.ts

interface Message {
  role: 'user' | 'assistant' | 'system' | 'artifact_execution';
  content: string;
  timestamp: Date;
  // For artifact executions
  executionId?: string;
  toolName?: string;
  summary?: string;
}

// web/src/stores/chatStore.ts

class ChatStore {
  messages: Message[] = [];

  async submitArtifact(submission: ArtifactSubmission) {
    const artifactService = new ArtifactService();

    // Execute the artifact
    const result = await artifactService.submitArtifact(submission);

    // Add execution record to chat history
    this.messages.push({
      role: 'artifact_execution',
      content: result.result,
      timestamp: new Date(result.timestamp),
      executionId: result.executionId,
      toolName: submission.toolName,
      summary: result.summary,
    });

    return result;
  }
}
```

### 3. Artifact Execution Timeline Component

Display artifact executions in the chat:

```tsx
// web/src/components/ArtifactExecutionMessage.tsx

import { Clock, Tool } from 'lucide-react';

interface Props {
  execution: {
    executionId: string;
    toolName: string;
    summary: string;
    timestamp: Date;
    result: string;
  };
  onViewResult: (executionId: string) => void;
}

export function ArtifactExecutionMessage({ execution, onViewResult }: Props) {
  const formatTimeAgo = (date: Date) => {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const getToolIcon = (toolName: string) => {
    // Return appropriate icon based on tool
    return <Tool className="w-4 h-4" />;
  };

  return (
    <div className="artifact-execution-message border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20 p-4 rounded-r-lg my-2">
      <div className="flex items-center gap-2 mb-2">
        {getToolIcon(execution.toolName)}
        <span className="font-medium text-sm">Tool Executed</span>
        <span className="text-xs text-gray-500 ml-auto flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {formatTimeAgo(execution.timestamp)}
        </span>
      </div>

      <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">
        {execution.summary}
      </div>

      <button
        onClick={() => onViewResult(execution.executionId)}
        className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
      >
        View Full Result →
      </button>
    </div>
  );
}
```

### 4. Tool Form with Submission Handler

```tsx
// web/src/components/ToolFormArtifact.tsx

import { useState } from 'react';
import { ArtifactService } from '../services/artifactService';

interface Props {
  artifact: {
    type: string;
    title: string;
    data: {
      tool_name: string;
      schema: any;
      prefill: Record<string, any>;
    };
  };
  sessionId: string;
  onSubmit: (result: any) => void;
}

export function ToolFormArtifact({ artifact, sessionId, onSubmit }: Props) {
  const [formData, setFormData] = useState(artifact.data.prefill || {});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const artifactService = new ArtifactService();

      const result = await artifactService.submitArtifact({
        sessionId,
        artifactId: 'form_' + Date.now(),
        artifactType: 'toolform',
        artifactTitle: artifact.title,
        toolName: artifact.data.tool_name,
        toolArgs: formData,
      });

      setResult(result);
      onSubmit(result);
    } catch (error) {
      console.error('Failed to submit form:', error);
      // Show error to user
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="tool-form-artifact">
      <h3 className="text-lg font-semibold mb-4">{artifact.title}</h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Render form fields based on schema */}
        {Object.entries(artifact.data.schema.properties || {}).map(([key, prop]: [string, any]) => (
          <div key={key}>
            <label className="block text-sm font-medium mb-1">
              {prop.ui_hints?.help_text || key}
              {artifact.data.schema.required?.includes(key) && (
                <span className="text-red-500 ml-1">*</span>
              )}
            </label>

            {prop.ui_widget === 'file_picker' ? (
              <input
                type="text"
                value={formData[key] || ''}
                onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
                placeholder={prop.ui_hints?.placeholder}
                className="w-full px-3 py-2 border rounded"
              />
            ) : prop.ui_widget === 'textarea' ? (
              <textarea
                value={formData[key] || ''}
                onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
                placeholder={prop.ui_hints?.placeholder}
                className="w-full px-3 py-2 border rounded"
                rows={4}
              />
            ) : (
              <input
                type="text"
                value={formData[key] || ''}
                onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
                placeholder={prop.ui_hints?.placeholder}
                className="w-full px-3 py-2 border rounded"
              />
            )}
          </div>
        ))}

        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Executing...' : 'Submit'}
        </button>
      </form>

      {/* Display result */}
      {result && (
        <div className="mt-4 p-4 bg-gray-100 dark:bg-gray-800 rounded">
          <h4 className="font-semibold mb-2">Result:</h4>
          <pre className="text-sm overflow-auto">{result.result}</pre>
        </div>
      )}
    </div>
  );
}
```

## Usage Examples

### Example 1: Read File via Artifact

```python
# Backend: User requests a form
user: "Create a form to read README.md"

# TOOL_FORM_AGENT generates form artifact
assistant: """
```artifact:toolform
{
  "type": "artifact:toolform",
  "title": "Read File",
  "data": {
    "tool_name": "builtin.read_file",
    "schema": {...},
    "prefill": {"path": "README.md"}
  }
}
```
"""

# Frontend: User clicks submit button
# → Calls /api/artifacts/execute with tool_args: {path: "README.md"}

# Backend: Executes read_file tool
result = execute_tool("builtin.read_file", {"path": "README.md"})

# Backend: Records execution
execution = context_manager.record_execution(
    session_id="sess_123",
    artifact_type="toolform",
    artifact_title="Read File",
    tool_name="builtin.read_file",
    tool_args={"path": "README.md"},
    tool_result=result  # File contents
)

# Backend: Returns result
→ Frontend displays file contents

# User asks follow-up
user: "Summarize what I just loaded"

# Backend: Builds context message
context_msg = {
    "role": "system",
    "content": """
    **Artifact Context:**

    The user recently executed the following tools via artifacts:

    1. **Read File**
       Time: just now
       Tool: builtin.read_file
       Arguments: {'path': 'README.md'}
       Result:
       ```
       # My Project
       ...
       ```
    """
}

# Backend: Injects into LLM prompt
messages = [
    system_prompt,
    context_msg,  # ← Artifact context
    *chat_history,
    {"role": "user", "content": "Summarize what I just loaded"}
]

# LLM has access to README.md contents and responds with summary
```

### Example 2: Batch File Reading

```python
# User submits batch artifact with 3 files
files = ["src/main.py", "src/utils.py", "src/config.py"]

# Each file read is recorded separately
for file in files:
    execution = context_manager.record_execution(
        session_id="sess_123",
        artifact_type="batchtool",
        artifact_title="Batch Read Files",
        tool_name="builtin.read_file",
        tool_args={"path": file},
        tool_result=read_result
    )

# User asks: "Which file has the most functions?"
# Context includes all 3 file contents
# LLM can analyze and compare all files
```

## Testing

### Unit Tests

```python
# tests/test_artifact_context.py

import pytest
from mcp_client_for_ollama.artifacts import ArtifactContextManager


def test_record_execution():
    """Test recording an artifact execution."""
    manager = ArtifactContextManager()

    execution = manager.record_execution(
        session_id="test_session",
        artifact_type="toolform",
        artifact_title="Read File",
        tool_name="builtin.read_file",
        tool_args={"path": "test.py"},
        tool_result="print('hello')",
    )

    assert execution.execution_id is not None
    assert execution.tool_name == "builtin.read_file"
    assert execution.result_summary == "Loaded test.py (0.0 KB)"


def test_temporal_reference_resolution():
    """Test resolving 'what I just loaded' references."""
    manager = ArtifactContextManager()

    # Record an execution
    manager.record_execution(
        session_id="test_session",
        artifact_type="toolform",
        artifact_title="Read File",
        tool_name="builtin.read_file",
        tool_args={"path": "README.md"},
        tool_result="# My Project",
    )

    # Resolve reference
    referenced = manager.resolve_references(
        "test_session",
        "summarize what I just loaded"
    )

    assert len(referenced) == 1
    assert referenced[0].tool_name == "builtin.read_file"
    assert "README.md" in referenced[0].tool_args["path"]


def test_context_message_building():
    """Test building context message for LLM."""
    manager = ArtifactContextManager()

    # Record execution
    manager.record_execution(
        session_id="test_session",
        artifact_type="toolform",
        artifact_title="Read File",
        tool_name="builtin.read_file",
        tool_args={"path": "test.py"},
        tool_result="print('hello')",
    )

    # Build context message
    msg = manager.build_context_message("test_session")

    assert msg is not None
    assert msg["role"] == "system"
    assert "Artifact Context" in msg["content"]
    assert "Read File" in msg["content"]
    assert "test.py" in msg["content"]
```

### Integration Tests

```python
# tests/test_artifact_integration.py

def test_end_to_end_artifact_flow(delegation_client, session_id):
    """Test complete flow from form submission to context injection."""

    # 1. User requests a form
    response = delegation_client.generate_response(
        "Create a form to read README.md",
        session_id
    )

    assert "artifact:toolform" in response

    # 2. User submits the form
    result = delegation_client.execute_artifact_tool(
        session_id=session_id,
        artifact_type="toolform",
        artifact_title="Read File",
        tool_name="builtin.read_file",
        tool_args={"path": "README.md"},
    )

    assert result["status"] == "success"
    execution_id = result["execution_id"]

    # 3. User asks follow-up
    response = delegation_client.generate_response(
        "What did I just load?",
        session_id
    )

    # Response should reference README.md
    assert "README" in response
```

## Next Steps

1. **Add to Delegation Client** - Integrate context manager initialization
2. **Create API Endpoints** - Add artifact execution endpoints
3. **Build Frontend Components** - Create form submission UI
4. **Add WebSocket Support** - For real-time execution updates
5. **Implement Testing** - Unit and integration tests
6. **Add Monitoring** - Track context usage and performance

---

**Integration Status:** 📋 Design Complete
**Implementation:** ⏳ Pending
