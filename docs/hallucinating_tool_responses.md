## Problem Statement

   When using the system prompt:
   ```
   You are a helpful software engineer. Use the tools to answer questions and fix problems.
   You have access to all files and directories under /root.  Read the file CLAUDE.md to get an understanding of the project structure and other important details.
   ```

   The model (qwen2.5) exhibits behavior where it:
   1. Outputs thinking/planning steps
   2. Makes tool calls
   3. **Answers its own tool calls** instead of waiting for results
   4. Continues generating text infinitely or until loop limit is reached

   ## Root Cause Analysis

   ### Issue 1: System Prompt is Too Permissive
   The prompt says "Use the tools" but doesn't explicitly state:
   - **Wait for tool responses before responding**
   - **Don't generate fake tool results**
   - **Tool results are provided after tool calls**

   This allows qwen2.5 to interpret the instructions as "generate everything yourself".

   ### Issue 2: Message Format Ambiguity
   In `client.py` line 545-549, the code appends:
   ```python
   messages.append({
       "role": "assistant",
       "content": response_text,
       "tool_calls": tool_calls
   })
   ```

   This creates ambiguity - some models interpret this as "here's the response AND the tool calls",
   making the model think it should answer its own question.

   ### Issue 3: Loop Limit Default is 3
   Default `loop_limit = 3` means the model can make mistakes for 3 iterations before stopping.
   With a verbose system prompt, this creates a lot of hallucination.

   ## Recommended Solutions

   ### Solution 1: Improve System Prompt (HIGHEST PRIORITY)
   Current problem prompt:
   ```
   You are a helpful software engineer. Use the tools to answer questions and fix problems.
   ```

   Recommended improved prompt:
   ```
   You are a helpful software engineer. You have access to tools to answer questions and fix problems.

   CRITICAL INSTRUCTIONS:
   - Only call tools when you need information or need to make changes
   - STOP immediately after each tool call and wait for the tool response
   - NEVER guess or fabricate tool results - you will receive them from the system
   - After receiving tool results, use them to inform your answer
   - Do not repeat tool calls unnecessarily
   ```

   ### Solution 2: Add Task-Focused Instructions
   Add specific guidance about staying focused:
   ```
   Your task is to: [specific task from user]

   Before proceeding with any plan:
   1. Understand what information you need
   2. Call ONLY the tools you need (be minimal)
   3. WAIT for results
   4. Use results to complete the task
   5. Provide FINAL answer only once task is complete
   ```

   ### Solution 3: Set Loop Limit Lower for Verbose Tasks
   For complex tasks like code modifications:
   - Default: 3
   - Recommended for verbose models: 2 or even 1

   Users should run: `loop-limit 2` at the start of complex tasks

   ### Solution 4: Force Response Format Control
   Modify `process_query()` to better separate tool calls from responses.
   Instead of:
   ```python
   messages.append({
       "role": "assistant",
       "content": response_text,
       "tool_calls": tool_calls
   })
   ```

   Consider a clearer approach that distinguishes planning from execution.

   ## Immediate User Fixes

   ### For Current Issue:
   1. **Lower the loop limit**: `ll 1` (loop-limit 1)
      - Forces model to make ONE set of tool calls then wait

   2. **Use better system prompt** with explicit "WAIT for results" instructions

   3. **Be specific in requests**:
      - ❌ "add a new feature"
      - ✅ "read the file falkordb_persist.py, understand the CONSTRAINTS dict, then modify ensure_file_indexes function to create constraints when node_type exists"

   ### Example Better System Prompt:

   ```
   You are a careful software engineer. You have tools available to read files and make changes.

   IMPORTANT: You must WAIT for tool results before proceeding!
   - When you call a tool, STOP and wait for the response
   - NEVER guess what a tool result contains
   - NEVER call multiple tools expecting to get results later
   - Each tool result is provided immediately after your tool call
   - Use the result to inform your next action

   Your workflow:
   1. Call needed tools ONE AT A TIME
   2. Wait for each result
   3. Read and understand the result
   4. Decide next steps based on actual result
   5. Repeat until task is complete
   6. Only then provide your final answer
   ```

   ## Code Changes Needed (Optional Enhancement)

   ### In `utils/streaming.py` or `client.py`:
   Add a "tool execution mode" that:
   - Prevents model from generating text until all tools are resolved
   - Clears response text when tool calls are present
   - Forces model to focus on tool results only

   ### In `models/config_manager.py`:
   Add a built-in "task-focused" system prompt template that emphasizes tool discipline.

   ## Testing the Fix

   After applying a better system prompt, test with:
   ```
   set system prompt to: "You are a careful engineer. Tools: read/write files.
   CRITICAL: Wait for tool results - NEVER guess. Call tools one at a time.
   Wait for response. Then decide next action. Repeat until done."

   Then: loop-limit 1

   Then: add a new feature to [project]. First read CLAUDE.md.
   ```

   Expected behavior:
   1. Model reads CLAUDE.md
   2. Model asks clarifying questions OR identifies what to do
   3. Model makes ONE set of focused tool calls
   4. Model STOPS and waits
   5. User/system provides tool results
   6. Model proceeds with next action
   ```

   ## Why This Happens with qwen2.5 Specifically

   qwen2.5 is trained on diverse content including:
   - Technical documentation
   - Code walkthroughs (where intermediate steps are explained)
   - Self-guided tutorials (where steps include answers)

   This makes it more prone to "thinking aloud + answering itself" without explicit instructions to wait.

   ## Summary

   **Root Cause**: System prompt doesn't explicitly prevent the model from guessing tool results

   **Best Fix**: Use explicit "WAIT for tool results" language in system prompt + lower loop limit

   **Easiest Workaround**: `loop-limit 1` + better prompt guidance
