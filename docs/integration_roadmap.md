# Integration Roadmap: Agent Zero Features → mcp_client_for_ollama

## Executive Summary

This roadmap outlines the strategic integration of Agent Zero's capabilities into mcp_client_for_ollama. Features are prioritized by value, complexity, and architectural compatibility, organized into 4 phases over an estimated 6-12 month timeline.

**Target Outcome:** Transform mcp_client_for_ollama into a multi-provider, autonomous AI agent framework while preserving its strengths in MCP integration, artifact visualization, and task management.

---

## Prioritization Framework

Features are scored on three dimensions (1-5 scale):

- **Value**: Impact on user capabilities and use cases
- **Complexity**: Implementation difficulty and testing requirements
- **Compatibility**: Alignment with existing architecture

**Priority Score = (Value × 2) + (6 - Complexity) + Compatibility**

Higher scores indicate higher priority for implementation.

---

## Phase 1: Foundation & High-Impact Quick Wins (Months 1-2)

### 1.1 Multi-Provider Support via LiteLLM ⭐ **HIGHEST PRIORITY**

**Value:** 5/5 | **Complexity:** 3/5 | **Compatibility:** 4/5 | **Score:** 17

**Why First:**
- Dramatically expands model options (OpenAI, Anthropic, Google, Groq, etc.)
- Unlocks cloud-scale models while keeping local option
- Relatively isolated change (model layer abstraction)
- High user demand for GPT-4/Claude access

**Implementation Approach:**

```python
# New module: mcp_client_for_ollama/models/litellm_provider.py

from litellm import completion, acompletion
import litellm

class LiteLLMProvider:
    """LLM provider using LiteLLM for multi-API support"""

    def __init__(self, provider: str, model: str, api_key: str = None, **kwargs):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.extra_kwargs = kwargs

    async def chat(self, messages: list, stream: bool = True, **kwargs):
        """Chat completion with streaming support"""
        response = await acompletion(
            model=self.model,
            messages=messages,
            stream=stream,
            api_key=self.api_key,
            **self.extra_kwargs,
            **kwargs
        )

        if stream:
            async for chunk in response:
                yield chunk
        else:
            yield response
```

**Configuration Structure:**

```json
// config.json extension
{
  "providers": {
    "ollama": {
      "type": "ollama",
      "host": "http://localhost:11434",
      "models": ["qwen2.5:7b", "llama3.1:8b"]
    },
    "openai": {
      "type": "litellm",
      "litellm_provider": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
      "rate_limit": {"requests": 500, "input_tokens": 150000}
    },
    "anthropic": {
      "type": "litellm",
      "litellm_provider": "anthropic",
      "api_key": "${ANTHROPIC_API_KEY}",
      "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
    },
    "google": {
      "type": "litellm",
      "litellm_provider": "gemini",
      "api_key": "${GOOGLE_API_KEY}",
      "models": ["gemini-pro", "gemini-1.5-pro"]
    }
  },
  "default_provider": "ollama",
  "default_model": "qwen2.5:7b"
}
```

**Key Changes:**

1. Abstract `OllamaClient` to generic `LLMProvider` interface
2. Implement `OllamaProvider` and `LiteLLMProvider` classes
3. Update `client.py` to use provider abstraction
4. Add provider selection to web UI and CLI
5. Implement API key management (encrypted storage)
6. Add rate limiting support
7. Update agent definitions to support provider override

**Files to Modify:**
- `mcp_client_for_ollama/client.py` - Abstract model calls
- `mcp_client_for_ollama/models/__init__.py` - New provider system
- `mcp_client_for_ollama/config/config.py` - Provider config
- `mcp_client_for_ollama/web/app.py` - Provider selection UI
- `pyproject.toml` - Add litellm dependency

**Testing Requirements:**
- Unit tests for each provider
- Integration tests with mock APIs
- Rate limiting tests
- API key encryption tests
- Streaming compatibility tests
- Tool calling compatibility tests (critical!)

**Risks & Mitigation:**
- **Tool format differences**: LiteLLM normalizes but test thoroughly
  - *Mitigation*: Extensive tool calling tests per provider
- **Streaming differences**: Chunk formats vary
  - *Mitigation*: Unified streaming adapter layer
- **Cost control**: Cloud APIs are expensive
  - *Mitigation*: Rate limiting, usage tracking, budget alerts

**Success Metrics:**
- Users can select any LiteLLM-supported provider
- Tool calling works across all providers
- Streaming maintains real-time responsiveness
- Zero regression for existing Ollama users

---

### 1.2 Web Search Integration ⭐

**Value:** 5/5 | **Complexity:** 2/5 | **Compatibility:** 5/5 | **Score:** 18

**Why Early:**
- High user value for research tasks
- Simple integration (HTTP APIs)
- Complements existing MCP tools
- No architectural changes needed

**Implementation Approach:**

```python
# New module: mcp_client_for_ollama/tools/builtin/search_tool.py

class SearchTool:
    """Web search via DuckDuckGo (no API key) or SearXNG"""

    TOOL_DEFINITION = {
        "name": "web_search",
        "description": "Search the web for current information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results (default 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }

    async def execute(self, query: str, num_results: int = 5) -> dict:
        """Execute web search"""
        # DuckDuckGo implementation (no API key needed)
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append({
                    "title": r["title"],
                    "url": r["href"],
                    "snippet": r["body"]
                })

        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
```

**Configuration Options:**

```json
{
  "search": {
    "provider": "duckduckgo",  // or "searxng"
    "searxng_url": "http://localhost:8888",  // if using SearXNG
    "default_results": 5,
    "max_results": 20,
    "safe_search": true
  }
}
```

**Integration Points:**
- Add to builtin tools in `tools/builtin/`
- Register in tool registry
- Add search results artifact renderer (optional)
- Add to RESEARCHER agent's allowed tools
- Add search command to CLI

**Dependencies:**
- `duckduckgo-search` package (no API key!)
- OR `httpx` for SearXNG integration

**Testing:**
- Search accuracy tests
- Rate limiting compliance
- Result parsing tests
- Integration with agent delegation

**Timeline:** 1 week

---

### 1.3 Extension System (Hooks) ⭐

**Value:** 4/5 | **Complexity:** 3/5 | **Compatibility:** 4/5 | **Score:** 15

**Why Early:**
- Enables all future customization
- Users can add features without forking
- Foundation for plugins/extensions
- Relatively self-contained

**Implementation Approach:**

```python
# New module: mcp_client_for_ollama/extensions/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict
import importlib
import os

class Extension(ABC):
    """Base class for extensions"""

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute extension logic"""
        pass

class ExtensionManager:
    """Manages loading and execution of extensions"""

    def __init__(self, extensions_dir: str = "~/.config/ollmcp/extensions"):
        self.extensions_dir = os.path.expanduser(extensions_dir)
        self.hooks = {
            "client_init": [],
            "message_start": [],
            "message_end": [],
            "tool_before": [],
            "tool_after": [],
            "response_start": [],
            "response_end": [],
            "agent_before": [],
            "agent_after": [],
            "error": []
        }
        self.load_extensions()

    def load_extensions(self):
        """Load extensions from directory"""
        for hook_name in self.hooks.keys():
            hook_dir = os.path.join(self.extensions_dir, hook_name)
            if os.path.exists(hook_dir):
                for filename in sorted(os.listdir(hook_dir)):
                    if filename.endswith('.py'):
                        module_path = f"extensions.{hook_name}.{filename[:-3]}"
                        module = importlib.import_module(module_path)
                        extension = module.Extension()
                        self.hooks[hook_name].append(extension)

    async def execute_hook(self, hook_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all extensions for a hook"""
        for extension in self.hooks.get(hook_name, []):
            context = await extension.execute(context)
        return context
```

**Extension Hook Points (10 Initial):**

1. `client_init` - Client initialization
2. `message_start` - Before processing message
3. `message_end` - After message processed
4. `tool_before` - Before tool execution
5. `tool_after` - After tool execution
6. `response_start` - Before LLM response
7. `response_end` - After LLM response
8. `agent_before` - Before agent delegation
9. `agent_after` - After agent completion
10. `error` - Error handling

**Example Extension:**

```python
# ~/.config/ollmcp/extensions/tool_before/10_logging.py

from mcp_client_for_ollama.extensions.base import Extension
import logging

class Extension(Extension):
    """Log all tool executions"""

    async def execute(self, context):
        tool_name = context.get("tool_name")
        args = context.get("args")
        logging.info(f"Tool execution: {tool_name} with args {args}")
        return context
```

**Files to Create:**
- `mcp_client_for_ollama/extensions/base.py`
- `mcp_client_for_ollama/extensions/__init__.py`
- Extension documentation
- Example extensions

**Files to Modify:**
- `mcp_client_for_ollama/client.py` - Add hook calls
- `mcp_client_for_ollama/tools/executor.py` - Tool hooks
- `mcp_client_for_ollama/agents/delegation_client.py` - Agent hooks

**Timeline:** 2 weeks

---

### 1.4 Memory Consolidation (AI-Powered)

**Value:** 3/5 | **Complexity:** 3/5 | **Compatibility:** 5/5 | **Score:** 13

**Why Phase 1:**
- Builds on existing memory system
- Improves long-running session quality
- Leverages multi-provider support (use cheap model)

**Implementation Approach:**

```python
# Extension to: mcp_client_for_ollama/memory/manager.py

class MemoryManager:
    """Existing memory manager with consolidation"""

    async def consolidate_memory(self, domain: str, session_id: str):
        """Consolidate similar memories using LLM"""

        # 1. Load all memories for session
        memories = self.load_session_memories(domain, session_id)

        # 2. Find similar clusters (simple similarity for now)
        clusters = self._cluster_memories(memories)

        # 3. For each cluster, use LLM to consolidate
        for cluster in clusters:
            if len(cluster) > 1:
                consolidated = await self._llm_consolidate(cluster)

                # 4. Replace cluster with consolidated memory
                for mem in cluster:
                    self.delete_memory(mem["id"])
                self.save_memory(consolidated)

    async def _llm_consolidate(self, memories: list) -> dict:
        """Use LLM to merge similar memories"""
        prompt = f"""Consolidate these related memories into a single, comprehensive memory:

{self._format_memories(memories)}

Output a single consolidated memory that captures all important information."""

        # Use cheap model for consolidation
        response = await self.llm_client.chat(
            model="gpt-3.5-turbo",  # or qwen2.5:3b for local
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "content": response,
            "consolidated_from": [m["id"] for m in memories],
            "consolidated_at": datetime.now().isoformat()
        }
```

**Configuration:**

```json
{
  "memory": {
    "consolidation": {
      "enabled": true,
      "auto_interval": "24h",  // Auto-consolidate every 24h
      "similarity_threshold": 0.8,
      "min_cluster_size": 2,
      "consolidation_model": "gpt-3.5-turbo"  // Cheap model
    }
  }
}
```

**Integration:**
- Add `consolidate` command to CLI
- Auto-consolidate on session end (optional)
- Show consolidation status in memory panel
- Background task for scheduled consolidation

**Timeline:** 1 week

---

## Phase 2: Autonomous Capabilities (Months 3-4)

### 2.1 Browser Automation ⭐ **HIGH VALUE**

**Value:** 5/5 | **Complexity:** 4/5 | **Compatibility:** 4/5 | **Score:** 16

**Why Phase 2:**
- Extremely valuable for research and testing
- Complex but well-defined integration
- Requires multi-provider support (better with GPT-4/Claude)

**Implementation Approach:**

```python
# New module: mcp_client_for_ollama/tools/builtin/browser_tool.py

from playwright.async_api import async_playwright
from browser_use import Agent as BrowserAgent

class BrowserTool:
    """Autonomous browser agent using Playwright + browser-use"""

    TOOL_DEFINITION = {
        "name": "browser_agent",
        "description": "Control a web browser to navigate, extract data, or interact with websites",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "What to do in the browser"
                },
                "url": {
                    "type": "string",
                    "description": "Starting URL (optional)"
                },
                "headless": {
                    "type": "boolean",
                    "description": "Run in headless mode",
                    "default": true
                }
            },
            "required": ["task"]
        }
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.browser = None
        self.context = None

    async def execute(self, task: str, url: str = None, headless: bool = True):
        """Execute browser task"""

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()

            # Initialize browser-use agent
            browser_agent = BrowserAgent(
                task=task,
                llm=self.llm_client,
                browser=browser
            )

            # Execute task
            if url:
                await page.goto(url)

            result = await browser_agent.run(page)

            # Cleanup
            await browser.close()

            return {
                "success": True,
                "result": result,
                "final_url": page.url,
                "screenshots": []  # Optional: capture screenshots
            }
```

**Dependencies:**
```toml
[tool.poetry.dependencies]
playwright = "^1.40.0"
browser-use = "^0.1.0"  # Or similar library
```

**Configuration:**

```json
{
  "browser": {
    "enabled": true,
    "headless": true,
    "timeout": 60000,
    "download_dir": "~/.config/ollmcp/downloads",
    "user_agent": null,  // Custom UA
    "proxy": null,  // Proxy settings
    "browser_model": "gpt-4"  // Model for browser decisions
  }
}
```

**Integration:**
- Add to RESEARCHER agent
- Add to EXECUTOR agent
- Create BROWSER artifact type for visualizing navigation
- Add browser session management
- Add screenshot capture

**Challenges:**
- Browser-use library maturity
- Cost control (GPT-4 calls per action)
- Security/sandboxing
- Session persistence

**Mitigations:**
- Use local models for simple navigation
- Use GPT-4/Claude only for complex decisions
- Strict timeout limits
- Headless-only in production
- Whitelist/blacklist domains

**Timeline:** 3 weeks

---

### 2.2 Task Scheduling System ⭐

**Value:** 4/5 | **Complexity:** 3/5 | **Compatibility:** 4/5 | **Score:** 15

**Why Phase 2:**
- Enables automation and recurring tasks
- Natural extension of agent delegation
- Moderate complexity

**Implementation Approach:**

```python
# New module: mcp_client_for_ollama/scheduler/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import json

class TaskScheduler:
    """Schedule and manage recurring/one-time tasks"""

    def __init__(self, client):
        self.client = client
        self.scheduler = AsyncIOScheduler()
        self.tasks = {}  # task_id -> task_config
        self.load_tasks()
        self.scheduler.start()

    def schedule_task(self, task_type: str, schedule: str,
                     prompt: str, **kwargs) -> str:
        """
        Schedule a task

        task_type: 'cron', 'once', 'planned'
        schedule: cron expression or ISO datetime
        prompt: What to execute
        """
        task_id = self._generate_id()

        if task_type == 'cron':
            trigger = CronTrigger.from_crontab(schedule)
        elif task_type == 'once':
            trigger = DateTrigger(run_date=schedule)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

        # Add job to scheduler
        job = self.scheduler.add_job(
            func=self._execute_task,
            trigger=trigger,
            args=[task_id, prompt],
            id=task_id,
            **kwargs
        )

        # Save task config
        self.tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "schedule": schedule,
            "prompt": prompt,
            "status": "scheduled",
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        }

        self.save_tasks()
        return task_id

    async def _execute_task(self, task_id: str, prompt: str):
        """Execute scheduled task"""
        task = self.tasks[task_id]
        task["status"] = "running"
        task["last_run"] = datetime.now().isoformat()

        try:
            # Execute via client
            response = await self.client.chat(prompt)

            task["status"] = "completed"
            task["last_result"] = response

        except Exception as e:
            task["status"] = "failed"
            task["last_error"] = str(e)

        self.save_tasks()
```

**Tool Definition:**

```python
{
    "name": "schedule_task",
    "description": "Schedule a task to run at specific times",
    "inputSchema": {
        "type": "object",
        "properties": {
            "task_type": {
                "type": "string",
                "enum": ["cron", "once", "planned"],
                "description": "Type of schedule"
            },
            "schedule": {
                "type": "string",
                "description": "Cron expression (e.g., '0 9 * * *') or ISO datetime"
            },
            "prompt": {
                "type": "string",
                "description": "What to execute"
            }
        },
        "required": ["task_type", "schedule", "prompt"]
    }
}
```

**CLI Commands:**
- `schedule "0 9 * * *" "Generate daily report"` - Create cron task
- `schedule-list` - List all scheduled tasks
- `schedule-cancel <task_id>` - Cancel task
- `schedule-run <task_id>` - Run task now

**Web UI:**
- Task calendar view (artifact?)
- Task status dashboard
- Task creation form
- Task history

**Dependencies:**
```toml
[tool.poetry.dependencies]
apscheduler = "^3.10.0"
```

**Timeline:** 2 weeks

---

### 2.3 Document Q&A (RAG) ⭐

**Value:** 4/5 | **Complexity:** 3/5 | **Compatibility:** 5/5 | **Score:** 16

**Why Phase 2:**
- High value for research workflows
- Complements existing file tools
- Natural fit with artifacts (document viewer)

**Implementation Approach:**

```python
# New module: mcp_client_for_ollama/tools/builtin/document_qa.py

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.document_loaders import (
    PyPDFLoader, TextLoader, Docx2txtLoader,
    UnstructuredExcelLoader
)

class DocumentQATool:
    """Multi-document Q&A with RAG"""

    TOOL_DEFINITION = {
        "name": "document_query",
        "description": "Ask questions about uploaded documents",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Question to ask"
                },
                "documents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Paths to documents"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of chunks to retrieve",
                    "default": 4
                }
            },
            "required": ["query", "documents"]
        }
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.vector_stores = {}  # document -> vector store

    async def execute(self, query: str, documents: list, top_k: int = 4):
        """Query documents"""

        # 1. Load and chunk documents
        all_chunks = []
        for doc_path in documents:
            if doc_path not in self.vector_stores:
                chunks = await self._load_and_chunk(doc_path)
                vector_store = FAISS.from_documents(chunks, self.embeddings)
                self.vector_stores[doc_path] = vector_store

            # 2. Retrieve relevant chunks
            retriever = self.vector_stores[doc_path].as_retriever(
                search_kwargs={"k": top_k}
            )
            relevant_chunks = await retriever.aget_relevant_documents(query)
            all_chunks.extend(relevant_chunks)

        # 3. Build context from chunks
        context = "\n\n".join([
            f"From {chunk.metadata['source']}:\n{chunk.page_content}"
            for chunk in all_chunks[:top_k * len(documents)]
        ])

        # 4. Query LLM with context
        prompt = f"""Answer this question based on the provided documents:

Question: {query}

Context:
{context}

Answer:"""

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "answer": response,
            "sources": [
                {
                    "document": chunk.metadata['source'],
                    "page": chunk.metadata.get('page', 'N/A'),
                    "snippet": chunk.page_content[:200]
                }
                for chunk in all_chunks[:top_k]
            ]
        }

    async def _load_and_chunk(self, doc_path: str):
        """Load document and split into chunks"""
        # Detect file type and use appropriate loader
        if doc_path.endswith('.pdf'):
            loader = PyPDFLoader(doc_path)
        elif doc_path.endswith('.txt') or doc_path.endswith('.md'):
            loader = TextLoader(doc_path)
        elif doc_path.endswith('.docx'):
            loader = Docx2txtLoader(doc_path)
        elif doc_path.endswith('.xlsx'):
            loader = UnstructuredExcelLoader(doc_path)
        else:
            raise ValueError(f"Unsupported file type: {doc_path}")

        documents = loader.load()

        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = splitter.split_documents(documents)

        return chunks
```

**Dependencies:**
```toml
[tool.poetry.dependencies]
langchain = "^0.1.0"
faiss-cpu = "^1.7.4"
sentence-transformers = "^2.2.0"
pypdf = "^3.17.0"
docx2txt = "^0.8"
unstructured = "^0.11.0"
```

**Integration:**
- Add to RESEARCHER agent
- Add to READER agent
- Create document artifact type
- Add knowledge base directory support
- Web UI: Document upload + Q&A interface

**Timeline:** 2 weeks

---

### 2.4 Vector Memory (FAISS)

**Value:** 3/5 | **Complexity:** 4/5 | **Compatibility:** 3/5 | **Score:** 12

**Why Phase 2:**
- Significant architectural change
- Enables semantic search
- Requires embeddings model

**Implementation Approach:**

Option 1: **Parallel System** (Recommended)
- Keep existing domain-specific memory
- Add vector layer on top for semantic search
- Best of both worlds

```python
# Extension to: mcp_client_for_ollama/memory/manager.py

from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

class EnhancedMemoryManager(MemoryManager):
    """Memory manager with vector search"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        # Vector stores per domain
        self.vector_stores = {}
        self._init_vector_stores()

    def save_memory(self, domain: str, session_id: str,
                   memory_type: str, content: str, metadata: dict = None):
        """Save to both structured and vector storage"""

        # 1. Save to existing system
        memory_id = super().save_memory(domain, session_id, memory_type,
                                       content, metadata)

        # 2. Add to vector store
        vector_store = self._get_vector_store(domain, session_id)
        vector_store.add_texts(
            texts=[content],
            metadatas=[{**metadata, "id": memory_id, "type": memory_type}]
        )

        # 3. Persist vector store
        self._save_vector_store(domain, session_id)

        return memory_id

    def search_memory(self, domain: str, session_id: str,
                     query: str, top_k: int = 5,
                     similarity_threshold: float = 0.7):
        """Semantic search across memories"""

        vector_store = self._get_vector_store(domain, session_id)

        # Similarity search
        results = vector_store.similarity_search_with_score(
            query, k=top_k
        )

        # Filter by threshold
        filtered = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
            if score >= similarity_threshold
        ]

        return filtered
```

Option 2: **Replace System**
- Migrate existing memories to FAISS
- Use metadata for domain/session filtering
- More breaking change

**Migration Strategy:**
1. Run both systems in parallel for 1-2 versions
2. Gradually migrate old memories to vector store
3. Deprecate old system after migration

**Timeline:** 3 weeks

---

## Phase 3: Advanced Features (Months 5-7)

### 3.1 Docker/SSH Execution ⭐

**Value:** 3/5 | **Complexity:** 4/5 | **Compatibility:** 3/5 | **Score:** 11

**Why Phase 3:**
- High complexity (security, permissions)
- Valuable for isolation and remote execution
- Requires careful security design

**Implementation Approach:**

```python
# New module: mcp_client_for_ollama/execution/runtime.py

from abc import ABC, abstractmethod
import docker
import paramiko

class Runtime(ABC):
    """Abstract execution runtime"""

    @abstractmethod
    async def execute(self, command: str, language: str) -> dict:
        pass

class LocalRuntime(Runtime):
    """Existing local execution"""
    async def execute(self, command: str, language: str) -> dict:
        # Current implementation
        pass

class DockerRuntime(Runtime):
    """Execute code in Docker containers"""

    def __init__(self, image: str = "python:3.11-slim"):
        self.client = docker.from_env()
        self.image = image
        self.containers = {}  # session -> container

    async def execute(self, command: str, language: str,
                     session_id: str = None) -> dict:
        """Execute in Docker container"""

        # Get or create container for session
        if session_id and session_id in self.containers:
            container = self.containers[session_id]
        else:
            container = self.client.containers.run(
                image=self.image,
                command="sleep infinity",  # Keep alive
                detach=True,
                remove=False,
                network_mode="none",  # Isolate by default
                mem_limit="512m",  # Resource limits
                cpu_period=100000,
                cpu_quota=50000  # 50% CPU
            )
            if session_id:
                self.containers[session_id] = container

        # Execute command
        exec_result = container.exec_run(
            cmd=f"{self._get_interpreter(language)} -c '{command}'",
            demux=True
        )

        stdout, stderr = exec_result.output

        return {
            "success": exec_result.exit_code == 0,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
            "exit_code": exec_result.exit_code
        }

    def cleanup(self, session_id: str = None):
        """Stop and remove containers"""
        if session_id:
            if session_id in self.containers:
                self.containers[session_id].stop()
                self.containers[session_id].remove()
                del self.containers[session_id]
        else:
            for container in self.containers.values():
                container.stop()
                container.remove()
            self.containers.clear()

class SSHRuntime(Runtime):
    """Execute code on remote server via SSH"""

    def __init__(self, host: str, username: str,
                 key_path: str = None, password: str = None):
        self.host = host
        self.username = username
        self.key_path = key_path
        self.password = password
        self.client = None

    async def connect(self):
        """Establish SSH connection"""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if self.key_path:
            self.client.connect(
                hostname=self.host,
                username=self.username,
                key_filename=self.key_path
            )
        else:
            self.client.connect(
                hostname=self.host,
                username=self.username,
                password=self.password
            )

    async def execute(self, command: str, language: str) -> dict:
        """Execute on remote server"""
        if not self.client:
            await self.connect()

        # Execute command
        stdin, stdout, stderr = self.client.exec_command(
            f"{self._get_interpreter(language)} -c '{command}'"
        )

        return {
            "success": stdout.channel.recv_exit_status() == 0,
            "stdout": stdout.read().decode(),
            "stderr": stderr.read().decode(),
            "exit_code": stdout.channel.recv_exit_status()
        }
```

**Configuration:**

```json
{
  "execution": {
    "runtime": "local",  // "local", "docker", "ssh"
    "docker": {
      "image": "python:3.11-slim",
      "network_mode": "none",  // Security
      "mem_limit": "512m",
      "cpu_limit": 0.5
    },
    "ssh": {
      "host": "remote-server.com",
      "username": "agent",
      "key_path": "~/.ssh/id_rsa",
      "password": null
    }
  }
}
```

**Security Considerations:**
- Network isolation by default
- Resource limits (CPU, memory)
- Read-only filesystem mounts
- Whitelist allowed packages/commands
- Audit logging
- Timeout limits

**Integration:**
- Update EXECUTOR agent to use runtime
- Add runtime selection to web UI
- Add runtime status monitoring
- Container lifecycle management

**Dependencies:**
```toml
[tool.poetry.dependencies]
docker = "^6.1.0"
paramiko = "^3.4.0"
```

**Timeline:** 3 weeks

---

### 3.2 Node.js Execution Support

**Value:** 2/5 | **Complexity:** 2/5 | **Compatibility:** 5/5 | **Score:** 10

**Why Phase 3:**
- Lower priority (Python covers most cases)
- Simple addition to existing execution
- Nice-to-have for JavaScript projects

**Implementation:**

```python
# Extension to: mcp_client_for_ollama/tools/builtin/execution_tools.py

class NodeJSExecutor:
    """Execute Node.js code"""

    async def execute_nodejs(self, code: str) -> dict:
        """Execute Node.js code"""

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Execute with node
            process = await asyncio.create_subprocess_exec(
                'node', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                timeout=30
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "exit_code": process.returncode
            }

        finally:
            os.unlink(temp_file)
```

**Tool Definition:**
```python
{
    "name": "execute_nodejs",
    "description": "Execute Node.js/JavaScript code",
    "inputSchema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Node.js code to execute"
            }
        },
        "required": ["code"]
    }
}
```

**Requirements:**
- Node.js installed on system
- npm package management support
- Session persistence (similar to Python)

**Timeline:** 1 week

---

### 3.3 Voice Interface (STT/TTS)

**Value:** 2/5 | **Complexity:** 3/5 | **Compatibility:** 4/5 | **Score:** 9

**Why Phase 3:**
- Nice-to-have feature
- Moderate complexity
- Requires audio infrastructure

**Implementation Approach:**

```python
# New module: mcp_client_for_ollama/voice/stt.py

import whisper
import sounddevice as sd
import numpy as np

class SpeechToText:
    """Speech-to-Text using OpenAI Whisper"""

    def __init__(self, model_size: str = "base"):
        self.model = whisper.load_model(model_size)
        self.is_recording = False

    async def listen(self, duration: int = None) -> str:
        """Record audio and transcribe"""

        # Record audio
        sample_rate = 16000
        if duration:
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1
            )
            sd.wait()
        else:
            # Voice activity detection
            audio = self._record_until_silence()

        # Transcribe
        result = self.model.transcribe(audio)
        return result["text"]

    def _record_until_silence(self) -> np.ndarray:
        """Record until silence detected"""
        # Implementation with VAD
        pass

# New module: mcp_client_for_ollama/voice/tts.py

import kokoro
import sounddevice as sd

class TextToSpeech:
    """Text-to-Speech using Kokoro"""

    def __init__(self, voice: str = "default"):
        self.engine = kokoro.Kokoro()
        self.voice = voice

    async def speak(self, text: str):
        """Convert text to speech and play"""

        # Generate audio
        audio = self.engine.synthesize(text, voice=self.voice)

        # Play audio
        sd.play(audio, samplerate=22050)
        sd.wait()
```

**CLI Commands:**
- `voice-input` - Record and transcribe
- `voice-output on/off` - Toggle TTS
- `voice-settings` - Configure voice/model

**Web UI:**
- Microphone button for voice input
- Audio player for TTS output
- Voice settings panel

**Dependencies:**
```toml
[tool.poetry.dependencies]
openai-whisper = "^20231117"
sounddevice = "^0.4.6"
kokoro = "^0.1.0"  # Or alternative TTS
numpy = "^1.24.0"
```

**Timeline:** 2 weeks

---

### 3.4 Email Integration

**Value:** 2/5 | **Complexity:** 3/5 | **Compatibility:** 5/5 | **Score:** 9

**Why Phase 3:**
- Specialized use case
- Moderate complexity
- Good for automation workflows

**Implementation:**

```python
# New module: mcp_client_for_ollama/tools/builtin/email_tool.py

import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailTool:
    """Email integration via IMAP/SMTP"""

    TOOLS = [
        {
            "name": "email_read",
            "description": "Read emails from inbox",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "default": "INBOX"},
                    "limit": {"type": "integer", "default": 10},
                    "unread_only": {"type": "boolean", "default": true}
                }
            }
        },
        {
            "name": "email_send",
            "description": "Send an email",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    ]

    def __init__(self, config: dict):
        self.imap_server = config["imap_server"]
        self.smtp_server = config["smtp_server"]
        self.email = config["email"]
        self.password = config["password"]

    async def read_emails(self, folder: str = "INBOX",
                         limit: int = 10,
                         unread_only: bool = True) -> list:
        """Read emails from folder"""

        # Connect to IMAP
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email, self.password)
        mail.select(folder)

        # Search for emails
        search_criteria = "UNSEEN" if unread_only else "ALL"
        _, message_ids = mail.search(None, search_criteria)

        emails = []
        for msg_id in message_ids[0].split()[-limit:]:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            # Parse email...
            emails.append(parsed_email)

        mail.close()
        mail.logout()

        return emails

    async def send_email(self, to: str, subject: str, body: str) -> dict:
        """Send email via SMTP"""

        msg = MIMEMultipart()
        msg['From'] = self.email
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Send via SMTP
        with smtplib.SMTP_SSL(self.smtp_server, 465) as server:
            server.login(self.email, self.password)
            server.send_message(msg)

        return {"success": True, "message": "Email sent"}
```

**Configuration:**
```json
{
  "email": {
    "enabled": false,
    "imap_server": "imap.gmail.com",
    "smtp_server": "smtp.gmail.com",
    "email": "user@example.com",
    "password": "${EMAIL_PASSWORD}",  // Or OAuth2
    "default_folder": "INBOX"
  }
}
```

**Timeline:** 2 weeks

---

## Phase 4: Refinements & Optimization (Months 8-12)

### 4.1 Project System (Full Implementation)

**Value:** 3/5 | **Complexity:** 4/5 | **Compatibility:** 3/5 | **Score:** 11

**Implementation:**

Create full project system similar to Agent Zero:
- Project directory structure
- Project-specific settings
- Project memory isolation
- Project knowledge base
- Project UI/dashboard

**Timeline:** 4 weeks

---

### 4.2 Agent-to-Agent Protocol (A2A)

**Value:** 2/5 | **Complexity:** 4/5 | **Compatibility:** 3/5 | **Score:** 8

**Implementation:**

Implement FastA2A protocol for external agent communication:
- HTTP API for agent messages
- Session management
- Authentication
- Agent discovery

**Timeline:** 3 weeks

---

### 4.3 Tunneling & Mobile Access

**Value:** 2/5 | **Complexity:** 2/5 | **Compatibility:** 4/5 | **Score:** 10

**Implementation:**

Add public URL tunneling for remote access:
- Integration with ngrok/bore/cloudflared
- QR code generation
- Mobile-optimized UI
- Secure authentication

**Timeline:** 1 week

---

### 4.4 Behavior Adjustment (Self-Learning)

**Value:** 2/5 | **Complexity:** 5/5 | **Compatibility:** 2/5 | **Score:** 7

**Implementation:**

Enable agents to learn from feedback:
- Feedback collection
- Behavior pattern extraction
- Prompt/config adjustment
- Learning persistence

**Timeline:** 4 weeks

---

## Implementation Strategy

### Development Approach

**1. Feature Flags**
```python
# config.json
{
  "features": {
    "multi_provider": true,
    "web_search": true,
    "browser_automation": false,  // Beta
    "docker_execution": false,  // Beta
    "voice_interface": false  // Experimental
  }
}
```

**2. Backward Compatibility**
- All new features are opt-in
- Existing Ollama-only users unaffected
- Graceful degradation
- Feature detection

**3. Testing Strategy**
- Unit tests for each new component
- Integration tests with mock services
- Performance benchmarks
- User acceptance testing

**4. Documentation**
- Feature documentation per phase
- Migration guides
- Configuration examples
- Video tutorials

**5. Release Cadence**
- Phase 1: 2 minor releases (0.46, 0.47)
- Phase 2: 2 minor releases (0.48, 0.49)
- Phase 3: 2 minor releases (0.50, 0.51)
- Phase 4: 1 major release (1.0.0)

---

## Resource Requirements

### Dependencies

**Phase 1:**
```toml
litellm = "^1.30.0"
duckduckgo-search = "^4.0.0"
apscheduler = "^3.10.0"
```

**Phase 2:**
```toml
playwright = "^1.40.0"
browser-use = "^0.1.0"
langchain = "^0.1.0"
faiss-cpu = "^1.7.4"
sentence-transformers = "^2.2.0"
```

**Phase 3:**
```toml
docker = "^6.1.0"
paramiko = "^3.4.0"
openai-whisper = "^20231117"
sounddevice = "^0.4.6"
```

### Infrastructure

- **CI/CD**: Expanded test suites (add 30-40 min to pipeline)
- **Storage**: Vector stores require ~500MB per 10k memories
- **Compute**: Browser automation requires headless Chrome (200MB RAM per instance)

### Effort Estimation

| Phase | Features | Estimated Time | Parallel Devs |
|-------|----------|---------------|---------------|
| Phase 1 | 4 features | 2 months | 1-2 |
| Phase 2 | 4 features | 2 months | 1-2 |
| Phase 3 | 4 features | 3 months | 1-2 |
| Phase 4 | 4 features | 5 months | 1-2 |
| **Total** | **16 features** | **12 months** | **1-2** |

---

## Risk Assessment & Mitigation

### High-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LiteLLM tool format incompatibilities | High | Medium | Extensive testing, provider-specific adapters |
| Browser automation cost (GPT-4) | High | High | Local model for simple actions, rate limiting |
| Docker security vulnerabilities | High | Medium | Strict sandboxing, security audit |
| Vector memory migration issues | Medium | Medium | Parallel systems, gradual migration |
| Performance degradation | Medium | Medium | Benchmarking, lazy loading, caching |

### Low-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Web search rate limiting | Low | Medium | Multiple providers, caching |
| Voice quality issues | Low | Medium | Model size options, quality settings |
| Email authentication complexity | Low | High | OAuth2 support, clear docs |

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ Users can use GPT-4, Claude, Gemini
- ✅ 90%+ tool calling success rate across providers
- ✅ Web search results accurate and fast (<3s)
- ✅ Extension system used by community (3+ extensions)
- ✅ Memory consolidation reduces context by 30%+

### Phase 2 Success Criteria
- ✅ Browser automation completes 80%+ tasks successfully
- ✅ Scheduled tasks run reliably with 99%+ uptime
- ✅ Document Q&A accurate on 10+ document types
- ✅ Vector search 50%+ faster than linear search

### Phase 3 Success Criteria
- ✅ Docker execution 100% isolated and secure
- ✅ SSH execution works on 5+ server types
- ✅ Voice interface 95%+ transcription accuracy
- ✅ Email integration handles 10+ providers

### Phase 4 Success Criteria
- ✅ Project system used by 50%+ users
- ✅ A2A protocol enables multi-agent workflows
- ✅ Mobile access works on iOS/Android
- ✅ Self-learning improves performance by 20%+

---

## Community Engagement

### Open Source Contributions
- Create GitHub issues for each feature
- Label as "help wanted" / "good first issue"
- Provide detailed implementation specs
- Code review guidelines

### Beta Testing Program
- Early access to Phase 2+ features
- Feedback collection
- Bug bounty program
- Feature voting

### Documentation
- Architecture decision records (ADRs)
- API documentation
- Tutorial series
- Example projects

---

## Next Steps

### Immediate Actions (Week 1)

1. **Create GitHub Project Board**
   - Organize issues by phase
   - Set milestones
   - Assign initial issues

2. **Set Up Development Environment**
   - Create feature branches
   - Configure CI/CD for new tests
   - Set up staging environment

3. **Community Announcement**
   - Blog post about roadmap
   - Twitter/social media
   - Discord/community channels

4. **Start Phase 1.1 (Multi-Provider)**
   - Create `models/litellm_provider.py`
   - Write provider abstraction tests
   - Update configuration system

### Weekly Cadence

- **Monday**: Sprint planning
- **Wednesday**: Code review session
- **Friday**: Demo + retrospective
- **Saturday**: Community office hours

---

## Conclusion

This roadmap transforms mcp_client_for_ollama from a specialized MCP/Ollama client into a comprehensive, multi-provider AI agent framework while preserving its unique strengths (artifacts, task management, MCP integration).

**Key Principles:**
- ✅ **Incremental**: Each phase adds value independently
- ✅ **Compatible**: Existing features remain functional
- ✅ **Tested**: Comprehensive testing at each stage
- ✅ **Documented**: Clear guides and examples
- ✅ **Community-Driven**: Open source, open process

**Expected Outcome:** By Month 12, mcp_client_for_ollama will be the most feature-rich, flexible AI agent framework with both local and cloud model support, autonomous capabilities, and best-in-class visualization.

---

**Document Version:** 1.0
**Date:** 2026-01-26
**Author:** Development Team
**Review Date:** Monthly
