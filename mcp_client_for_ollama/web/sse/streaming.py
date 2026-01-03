"""SSE streaming endpoint for real-time chat responses"""
from flask import Blueprint, Response, request
from mcp_client_for_ollama.web.session.manager import session_manager
import asyncio
import json
import queue
import threading

bp = Blueprint('streaming', __name__)


@bp.route('/chat', methods=['GET'])
def stream_chat():
    """SSE endpoint for streaming chat responses"""
    session_id = request.args.get('session_id')
    message = request.args.get('message')

    if not session_id or not message:
        return Response(
            json.dumps({'error': 'session_id and message required'}),
            status=400,
            mimetype='application/json'
        )

    client = session_manager.get_session(session_id)
    if not client:
        return Response(
            json.dumps({'error': 'Invalid session'}),
            status=404,
            mimetype='application/json'
        )

    def event_stream():
        """Synchronous generator for SSE events"""
        # Create a queue to pass data from async to sync
        q = queue.Queue()

        async def async_producer():
            """Async function to stream messages and put them in queue"""
            try:
                # Stream chunks from client (pass queue for status updates)
                async for chunk in client.send_message_streaming(message, status_queue=q):
                    q.put(('chunk', chunk))

                # Signal completion
                q.put(('done', True))

            except Exception as e:
                # Signal error
                q.put(('error', str(e)))

        def run_async():
            """Run the async producer in a new event loop"""
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            try:
                # Don't set as the thread's event loop to avoid contamination
                # Just run the coroutine directly
                loop.run_until_complete(async_producer())
            except Exception as e:
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
        thread.start()

        # Yield events from queue
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
