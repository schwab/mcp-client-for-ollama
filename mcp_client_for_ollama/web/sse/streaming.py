"""SSE streaming endpoint for real-time chat responses"""
from flask import Blueprint, Response, request, g
from mcp_client_for_ollama.web.session.manager import session_manager
import asyncio
import json
import queue
import threading

bp = Blueprint('streaming', __name__)


@bp.route('/chat', methods=['GET'])
def stream_chat():
    """SSE endpoint for streaming chat responses (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')
    message = request.args.get('message')
    context_json = request.args.get('context')

    print(f"[SSE] stream_chat called: session_id={session_id}, message_len={len(message) if message else 0}, username={username}, has_context={bool(context_json)}")

    if not session_id or not message:
        error_msg = f"Missing parameters: session_id={bool(session_id)}, message={bool(message)}"
        print(f"[SSE ERROR] {error_msg}")
        return Response(
            json.dumps({'error': 'session_id and message required'}),
            status=400,
            mimetype='application/json'
        )

    # Parse conversation context if provided
    conversation_context = None
    if context_json:
        try:
            conversation_context = json.loads(context_json)
            print(f"[SSE] Parsed conversation context: {len(conversation_context)} messages")
        except json.JSONDecodeError as e:
            print(f"[SSE WARNING] Failed to parse context: {e}")

    client = session_manager.get_session(session_id, username=username)
    if not client:
        print(f"[SSE ERROR] Invalid session: {session_id}")
        return Response(
            json.dumps({'error': 'Invalid session'}),
            status=404,
            mimetype='application/json'
        )

    # Store context on client for use during message processing
    if conversation_context:
        client.conversation_context = conversation_context

    print(f"[SSE] Client found for session {session_id}, model={client.get_model()}")

    def event_stream():
        """Synchronous generator for SSE events"""
        # Create a queue to pass data from async to sync
        q = queue.Queue()

        async def async_producer():
            """Async function to stream messages and put them in queue"""
            try:
                print(f"[SSE] async_producer starting for session {session_id}")
                # Stream chunks from client (pass queue for status updates)
                async for chunk in client.send_message_streaming(message, status_queue=q):
                    q.put(('chunk', chunk))

                # Signal completion
                print(f"[SSE] async_producer completed successfully for session {session_id}")
                q.put(('done', True))

            except Exception as e:
                # Signal error
                import traceback
                error_trace = traceback.format_exc()
                print(f"[SSE ERROR] async_producer exception for session {session_id}: {e}\n{error_trace}")
                q.put(('error', str(e)))

        def run_async():
            """Run the async producer in a new event loop"""
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            try:
                print(f"[SSE] run_async: event loop created for session {session_id}")
                # Don't set as the thread's event loop to avoid contamination
                # Just run the coroutine directly
                loop.run_until_complete(async_producer())
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"[SSE ERROR] run_async exception for session {session_id}: {e}\n{error_trace}")
                q.put(('error', f'Stream error: {str(e)}'))
            finally:
                # Clean up pending tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                # Give cancelled tasks a chance to finish
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                # Close the loop
                loop.close()

        # Start async producer in background thread
        thread = threading.Thread(target=run_async, daemon=True)
        print(f"[SSE] Starting background thread for session {session_id}")
        thread.start()

        # Yield events from queue
        print(f"[SSE] event_stream: starting to yield events for session {session_id}")
        try:
            while True:
                event_type, data = q.get(timeout=300)  # 5 minute timeout for long planning

                if event_type == 'chunk':
                    yield f"data: {json.dumps({'chunk': data})}\n\n"
                elif event_type == 'status':
                    # Status update (planning, agent activity, etc.)
                    yield f"data: {json.dumps({'status': data})}\n\n"
                elif event_type == 'agent_update':
                    # Agent activity update
                    yield f"data: {json.dumps({'agent_update': data})}\n\n"
                elif event_type == 'heartbeat':
                    # Keep-alive heartbeat
                    yield f"data: {json.dumps({'heartbeat': True})}\n\n"
                elif event_type == 'done':
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    break
                elif event_type == 'error':
                    yield f"data: {json.dumps({'error': data})}\n\n"
                    break
        except queue.Empty:
            yield f"data: {json.dumps({'error': 'Stream timeout after 5 minutes'})}\n\n"
        finally:
            # Wait for thread to complete
            thread.join(timeout=5)

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )
