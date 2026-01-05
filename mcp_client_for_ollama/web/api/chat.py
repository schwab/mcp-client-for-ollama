"""Chat API endpoints for web interface"""
from flask import Blueprint, request, jsonify, g
from mcp_client_for_ollama.web.session.manager import session_manager

bp = Blueprint('chat', __name__)


@bp.route('/history', methods=['GET'])
async def get_history():
    """Get chat history for session (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)

    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    history = client.get_history()
    return jsonify({'history': history})


@bp.route('/clear', methods=['DELETE'])
async def clear_history():
    """Clear chat history for session (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)

    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    client.clear_history()
    return jsonify({'status': 'cleared'})
