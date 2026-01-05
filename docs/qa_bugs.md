

### 0.41.0

## Error trying to call obsidian function
❌ Delegation failed: Event loop is closed
Falling back to direct execution...


╭─ 🔧 Executing Tool obsidian.obsidian_get_recent_changes ─╮
│                                                          │
│  Arguments:                                              │
│                                                          │
│                                                          │
│  {                                                       │
│    "days": "2",                                          │
│    "limit": "10"                                         │
│  }                                                       │
│                                                          │
╰──────────────────────────────────────────────────────────╯
⠼ working...ERROR in send_message_streaming: Error: 
Traceback (most recent call last):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/agents/delegation_client.py", line 265, in process_with_delegation
    task_plan = await self.create_plan(user_query)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/agents/delegation_client.py", line 763, in create_plan
    response_text = await self._execute_with_tools(
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/agents/delegation_client.py", line 1369, in _execute_with_tools
    response_text, tool_calls, _metrics = await self.mcp_client.streaming_manager.process_streaming_response(
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/utils/streaming.py", line 54, in process_streaming_response
    async for chunk in stream:
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/ollama/_client.py", line 752, in inner
    async with self._client.stream(*args, **kwargs) as r:
  File "/usr/lib/python3.10/contextlib.py", line 199, in __aenter__
    return await anext(self.gen)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpx/_client.py", line 1583, in stream
    response = await self.send(
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpx/_client.py", line 1629, in send
    response = await self._send_handling_auth(
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpx/_client.py", line 1657, in _send_handling_auth
    response = await self._send_handling_redirects(
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpx/_client.py", line 1694, in _send_handling_redirects
    response = await self._send_single_request(request)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpx/_client.py", line 1730, in _send_single_request
    response = await transport.handle_async_request(request)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpx/_transports/default.py", line 394, in handle_async_request
    resp = await self._pool.handle_async_request(req)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 256, in handle_async_request
    raise exc from None
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 229, in handle_async_request
    await self._close_connections(closing)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 345, in _close_connections
    await connection.aclose()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpcore/_async/connection.py", line 173, in aclose
    await self._connection.aclose()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpcore/_async/http11.py", line 258, in aclose
    await self._network_stream.aclose()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/httpcore/_backends/anyio.py", line 53, in aclose
    await self._stream.aclose()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/streams/tls.py", line 241, in aclose
    await self.transport_stream.aclose()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 1352, in aclose
    self._transport.close()
  File "/usr/lib/python3.10/asyncio/selector_events.py", line 706, in close
    self._loop.call_soon(self._call_connection_lost, None)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 753, in call_soon
    self._check_closed()
  File "/usr/lib/python3.10/asyncio/base_events.py", line 515, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed

## Obsidian tool handling failed and crashed
NFO:mcp.server.lowlevel.server:Processing request of type ListToolsRequest
Successfully connected to obsidian with 12 tools
Loading tools from tool_manager, available_tools: 35
Loaded 35 tools: ['builtin.set_system_prompt', 'builtin.get_system_prompt', 'builtin.execute_python_code', 'builtin.execute_bash_command', 'builtin.run_pytest', 'builtin.read_file', 'builtin.validate_file_path', 'builtin.write_file', 'builtin.patch_file', 'builtin.list_files', 'builtin.list_directories', 'builtin.create_directory', 'builtin.delete_file', 'builtin.file_exists', 'builtin.get_file_info', 'builtin.read_image', 'builtin.open_file', 'builtin.get_config', 'builtin.update_config_section', 'builtin.add_mcp_server', 'builtin.remove_mcp_server', 'builtin.list_mcp_servers', 'builtin.get_config_path', 'obsidian.obsidian_list_files_in_dir', 'obsidian.obsidian_list_files_in_vault', 'obsidian.obsidian_get_file_contents', 'obsidian.obsidian_simple_search', 'obsidian.obsidian_patch_content', 'obsidian.obsidian_append_content', 'obsidian.obsidian_delete_file', 'obsidian.obsidian_complex_search', 'obsidian.obsidian_batch_get_file_contents', 'obsidian.obsidian_get_periodic_note', 'obsidian.obsidian_get_recent_periodic_notes', 'obsidian.obsidian_get_recent_changes']
an error occurred during closing of asynchronous generator <async_generator object stdio_client at 0x7f0dea90bbc0>
asyncgen: <async_generator object stdio_client at 0x7f0dea90bbc0>
  + Exception Group Traceback (most recent call last):
  |   File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 783, in __aexit__
  |     raise BaseExceptionGroup(
  | exceptiongroup.BaseExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/client/stdio/__init__.py", line 189, in stdio_client
    |     yield read_stream, write_stream
    | GeneratorExit
    +------------------------------------

During handling of the above exception, another exception occurred:

## hallucination of search results
TRACE: 
/home/mcstar/Nextcloud/Vault/Journal/.trace/trace_20260102_213703.json

The AI is making up results instead of finding actual md files.



## Tool selections not saving to config for the ui
- when the user changes the enabled tools, it should save their changes to the config.json

## evenloop closed errors:
File "/usr/lib/python3.10/asyncio/selector_events.py", line 706, in close
    self._loop.call_soon(self._call_connection_lost, None)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 753, in call_soon
    self._check_closed()
  File "/usr/lib/python3.10/asyncio/base_events.py", line 515, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/web/integration/client_wrapper.py", line 164, in send_message_streaming
    response = await delegation_client.process_with_delegation(
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/agents/delegation_client.py", line 296, in process_with_delegation
    return await self._fallback_direct_execution(user_query)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/agents/delegation_client.py", line 1704, in _fallback_direct_execution
    return await self.mcp_client.process_query(query)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/client.py", line 716, in process_query
    result = await self.sessions[server_name]["session"].call_tool(actual_tool_name, tool_args)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/client/session.py", line 383, in call_tool
    result = await self.send_request(
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/shared/session.py", line 281, in send_request
    await self._write_stream.send(SessionMessage(message=JSONRPCMessage(jsonrpc_request), metadata=metadata))
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/streams/memory.py", line 249, in send
    self.send_nowait(item)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/streams/memory.py", line 218, in send_nowait
    raise ClosedResourceError
anyio.ClosedResourceError

## Config Load MCP servers Fails
CONFIG:
- /home/mcstar/Nextcloud/Vault/Journal/.config/config.json
- reload servers gives the error: Error reloading servers: Unexpected token '<', 

## Obsidian tools returned file count but no contents
TRACE: /home/mcstar/Nextcloud/Vault/Journal/.trace/trace_20260103_114424.json
- AI reports it was able to get a count of recently changed files, but not their contents 

## AI responds 2x but later calls give the error:
-Error: Connection failed. Please try again
- looks like session issues as this was in the log:
[SSE] async_producer completed successfully for session a0896988-9266-4516-aa07-fde26291b2e7
[SSE] stream_chat called: session_id=a0896988-9266-4516-aa07-fde26291b2e7, message_len=51
[SSE ERROR] Invalid session: a0896988-9266-4516-aa07-fde26291b2e7
127.0.0.1 - - [03/Jan/2026 13:34:42] "GET /api/stream/chat?session_id=a0896988-9266-4516-aa07-fde26291b2e7&message=Summarize%20the%20obsidian%20changes%20for%20the%20last%203%20days. HTTP/1.1" 404 -

## Web AI gives user commands to run instead of answering the question
- TRACE:  /home/mcstar/Nextcloud/Vault/Journal/.trace/trace_20260103_134329.json
- LOGS:
 1. [📝🔮 OBSIDIAN] List all files in the Obsidian vault that have been modified in the last 3 days                              │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
✓ Created 1 tasks

⚙️  Execution Phase

🌊 Wave 1

▶️  Executing task_1 (📝🔮 OBSIDIAN) <llama3.2:latest>
   List all files in the Obsidian vault that have been modified in the last 3 days

🔧 Detected 1 tool call(s)
INFO:mcp.server.lowlevel.server:Processing request of type CallToolRequest

📝 Answer:                                                                                                                         
───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

I've adjusted the limit to a reasonable number. Here's another attempt:

```
obsidian.obsidian_get_recent_changes days=3 limit=5
```

This will list the 5 most recently modified files in the vault over the last 3 days.

📝 Answer (Markdown):                                                                                                              
───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

I've adjusted the limit to a reasonable number. Here's another attempt:                                                            

                                                                                                                                   
 obsidian.obsidian_get_recent_changes days=3 limit=5                                                                               
                                                                                                                                   

This will list the 5 most recently modified files in the vault over the last 3 days.      


## 404 errors calling obsidian tools
TRACE: /home/mcstar/Nextcloud/Vault/Journal/.trace/trace_20260104_082437.json


## New regression error:
- application now crashes when calling server reload
- no tools are shown
- 
Connecting to server: obsidian
INFO:mcp.server.lowlevel.server:Processing request of type ListToolsRequest
Successfully connected to obsidian with 12 tools
Loading tools from tool_manager, available_tools: 35
Loaded 35 tools: ['builtin.set_system_prompt', 'builtin.get_system_prompt', 'builtin.execute_python_code', 'builtin.execute_bash_command', 'builtin.run_pytest', 'builtin.read_file', 'builtin.validate_file_path', 'builtin.write_file', 'builtin.patch_file', 'builtin.list_files', 'builtin.list_directories', 'builtin.create_directory', 'builtin.delete_file', 'builtin.file_exists', 'builtin.get_file_info', 'builtin.read_image', 'builtin.open_file', 'builtin.get_config', 'builtin.update_config_section', 'builtin.add_mcp_server', 'builtin.remove_mcp_server', 'builtin.list_mcp_servers', 'builtin.get_config_path', 'obsidian.obsidian_list_files_in_dir', 'obsidian.obsidian_list_files_in_vault', 'obsidian.obsidian_get_file_contents', 'obsidian.obsidian_simple_search', 'obsidian.obsidian_patch_content', 'obsidian.obsidian_append_content', 'obsidian.obsidian_delete_file', 'obsidian.obsidian_complex_search', 'obsidian.obsidian_batch_get_file_contents', 'obsidian.obsidian_get_periodic_note', 'obsidian.obsidian_get_recent_periodic_notes', 'obsidian.obsidian_get_recent_changes']
unhandled exception during asyncio.run() shutdown
task: <Task finished name='Task-46' coro=<AsyncExitStack.aclose() done, defined at /usr/lib/python3.10/contextlib.py:654> exception=RuntimeError('Attempted to exit cancel scope in a different task than it was entered in')>
Traceback (most recent call last):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 787, in __aexit__
    raise exc_val
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 755, in __aexit__
    await self._on_completed_fut
asyncio.exceptions.CancelledError

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/client/stdio/__init__.py", line 189, in stdio_client
    yield read_stream, write_stream
  File "/usr/lib/python3.10/contextlib.py", line 697, in __aexit__
    cb_suppress = await cb(*exc_details)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/shared/session.py", line 238, in __aexit__
    return await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 789, in __aexit__
    if self.cancel_scope.__exit__(type(exc), exc, exc.__traceback__):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 461, in __exit__
    raise RuntimeError(
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in

## Regression error -- Planner failures
❌ Plan validation failed: Task 1 has invalid agent_type: builtin.get_system_prompt (valid: ACCENT_WRITER, AGGREGATOR, 
CHARACTER_KEEPER, CODER, CONFIG_EXECUTOR, DEBUGGER, DETAIL_CONTRIVER, EXECUTOR, FILE_EXECUTOR, INITIALIZER, LORE_KEEPER, LYRICIST, 
MEMORY_EXECUTOR, OBSIDIAN, PROMPT_SPECIALIST, QUALITY_MONITOR, READER, RESEARCHER, SHELL_EXECUTOR, STORY_RESEARCHER, 
STYLE_DESIGNER, STYLE_MONITOR, SUNO_COMPOSER, TEST_EXECUTOR)
❌ Delegation failed: Invalid task plan: Task 1 has invalid agent_type: builtin.get_system_prompt (valid: ACCENT_WRITER, 
AGGREGATOR, CHARACTER_KEEPER, CODER, CONFIG_EXECUTOR, DEBUGGER, DETAIL_CONTRIVER, EXECUTOR, FILE_EXECUTOR, INITIALIZER, 
LORE_KEEPER, LYRICIST, MEMORY_EXECUTOR, OBSIDIAN, PROMPT_SPECIALIST, QUALITY_MONITOR, READER, RESEARCHER, SHELL_EXECUTOR, 
STORY_RESEARCHER, STYLE_DESIGNER, STYLE_MONITOR, SUNO_COMPOSER, TEST_EXECUTOR)

## memory ui issues
- shows prompts, but no goals or feauture after entering goals (possible failure to create memory session)

## Error Creating memory session in ui
task: <Task finished name='Task-45' coro=<AsyncExitStack.aclose() done, defined at /usr/lib/python3.10/contextlib.py:654> exception=RuntimeError('Attempted to exit cancel scope in a different task than it was entered in')>
Traceback (most recent call last):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 787, in __aexit__
    raise exc_val
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 755, in __aexit__
    await self._on_completed_fut
asyncio.exceptions.CancelledError

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/client/stdio/__init__.py", line 189, in stdio_client
    yield read_stream, write_stream
  File "/usr/lib/python3.10/contextlib.py", line 697, in __aexit__
    cb_suppress = await cb(*exc_details)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/shared/session.py", line 238, in __aexit__
    return await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 789, in __aexit__
    if self.cancel_scope.__exit__(type(exc), exc, exc.__traceback__):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 461, in __exit__
    raise RuntimeError(
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 787, in __aexit__
    raise exc_val
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/client/stdio/__init__.py", line 205, in stdio_client
    await process.wait()
asyncio.exceptions.CancelledError

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/lib/python3.10/contextlib.py", line 656, in aclose
    await self.__aexit__(None, None, None)
  File "/usr/lib/python3.10/contextlib.py", line 714, in __aexit__
    raise exc_details[1]
  File "/usr/lib/python3.10/contextlib.py", line 697, in __aexit__
    cb_suppress = await cb(*exc_details)
  File "/usr/lib/python3.10/contextlib.py", line 217, in __aexit__
    await self.gen.athrow(typ, value, traceback)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/client/stdio/__init__.py", line 182, in stdio_client
    async with (
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 789, in __aexit__
    if self.cancel_scope.__exit__(type(exc), exc, exc.__traceback__):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 461, in __exit__
    raise RuntimeError(
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
Exception in thread Thread-11 (process_request_thread):
Traceback (most recent call last):
  File "/usr/lib/python3.10/asyncio/tasks.py", line 432, in wait_for
    await waiter
asyncio.exceptions.CancelledError: Cancelled via cancel scope 7f37640a0cd0 by <Task pending name='Task-45' coro=<AsyncExitStack.aclose() running at /usr/lib/python3.10/contextlib.py:656> cb=[_release_waiter(<Future pendi...ask_wakeup()]>)() at /usr/lib/python3.10/asyncio/tasks.py:387]>

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/usr/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/usr/lib/python3.10/socketserver.py", line 683, in process_request_thread
    self.finish_request(request, client_address)
  File "/usr/lib/python3.10/socketserver.py", line 360, in finish_request
    self.RequestHandlerClass(request, client_address, self)
  File "/usr/lib/python3.10/socketserver.py", line 747, in __init__
    self.handle()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/werkzeug/serving.py", line 398, in handle
    super().handle()
  File "/usr/lib/python3.10/http/server.py", line 433, in handle
    self.handle_one_request()
  File "/usr/lib/python3.10/http/server.py", line 421, in handle_one_request
    method()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/werkzeug/serving.py", line 370, in run_wsgi
    execute(self.server.app)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/werkzeug/serving.py", line 331, in execute
    application_iter = app(environ, start_response)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/flask/app.py", line 1536, in __call__
    return self.wsgi_app(environ, start_response)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/flask/app.py", line 1511, in wsgi_app
    response = self.full_dispatch_request()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/flask/app.py", line 917, in full_dispatch_request
    rv = self.dispatch_request()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/flask/app.py", line 902, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/asgiref/sync.py", line 325, in __call__
    return call_result.result()
  File "/usr/lib/python3.10/concurrent/futures/_base.py", line 451, in result
    return self.__get_result()
  File "/usr/lib/python3.10/concurrent/futures/_base.py", line 403, in __get_result
    raise self._exception
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/asgiref/sync.py", line 365, in main_wrap
    result = await awaitable
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/web/api/memory.py", line 61, in create_memory_session
    result = await client.create_memory_session(domain, description)
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/web/integration/client_wrapper.py", line 472, in create_memory_session
    await temp_client.cleanup()
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp_client_for_ollama/client.py", line 2282, in cleanup
    await asyncio.wait_for(self.exit_stack.aclose(), timeout=5.0)
  File "/usr/lib/python3.10/asyncio/tasks.py", line 441, in wait_for
    await _cancel_and_wait(fut, loop=loop)
  File "/usr/lib/python3.10/asyncio/tasks.py", line 518, in _cancel_and_wait
    await waiter
asyncio.exceptions.CancelledError: Cancelled via cancel scope 7f37640a0cd0 by <Task pending name='Task-45' coro=<AsyncExitStack.aclose() running at /usr/lib/python3.10/contextlib.py:656> cb=[_release_waiter(<Future pendi...ask_wakeup()]>)() at /usr/lib/python3.10/asyncio/tasks.py:387]>

## Goal was created but error in the logs
- UI does not show the new goal
Memory file not found for session aa86cb20-d1e4-4a61-8b75-3444e207c605 in domain web
unhandled exception during asyncio.run() shutdown
task: <Task finished name='Task-79' coro=<<async_generator_athrow without __name__>()> exception=RuntimeError('Attempted to exit cancel scope in a different task than it was entered in')>
  + Exception Group Traceback (most recent call last):
  |   File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 783, in __aexit__
  |     raise BaseExceptionGroup(
  | exceptiongroup.BaseExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/client/stdio/__init__.py", line 189, in stdio_client
    |     yield read_stream, write_stream
    | asyncio.exceptions.CancelledError
    | 
    | During handling of the above exception, another exception occurred:
    | 
    | Traceback (most recent call last):
    |   File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/client/stdio/__init__.py", line 197, in stdio_client
    |     await process.stdin.aclose()
    | GeneratorExit
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/mcp/client/stdio/__init__.py", line 182, in stdio_client
    async with (
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 789, in __aexit__
    if self.cancel_scope.__exit__(type(exc), exc, exc.__traceback__):
  File "/home/mcstar/.virtualenvs/Journal-dqnp/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 461, in __exit__
    raise RuntimeError(
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in