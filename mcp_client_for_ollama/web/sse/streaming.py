"""SSE streaming endpoint for real-time chat responses"""
from flask import Blueprint, Response, request
from mcp_client_for_ollama.web.session.manager import session_manager
import asyncio
import json

bp = Blueprint('streaming', __name__)


@bp.route('/chat', methods=['GET'])
async def stream_chat():
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

    async def event_stream():
        """Generator for SSE events"""
        try:
            # Stream chunks from client
            async for chunk in client.send_message_streaming(message):
                # Format as SSE event
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )
