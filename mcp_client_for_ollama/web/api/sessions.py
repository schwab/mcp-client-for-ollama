"""Sessions API endpoints for web interface"""
from flask import Blueprint, request, jsonify
from mcp_client_for_ollama.web.session.manager import session_manager

bp = Blueprint('sessions', __name__)


@bp.route('/create', methods=['POST'])
async def create_session():
    """Create new user session

    Accepts optional JSON body with config, but works with empty POST too.
    """
    # Import inside function to avoid circular import
    from mcp_client_for_ollama.web.app import get_global_config

    # Use get_json(silent=True) to handle both JSON and empty requests
    data = request.get_json(silent=True) or {}
    user_config = data.get('config', {})

    # Merge global config with user config (user config takes precedence)
    config = get_global_config()
    config.update(user_config)

    session_id = await session_manager.create_session(config)
    return jsonify({'session_id': session_id})


@bp.route('/delete', methods=['DELETE'])
async def delete_session():
    """Delete session"""
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    await session_manager.delete_session(session_id)
    return jsonify({'status': 'deleted'})


@bp.route('/info', methods=['GET'])
async def get_session_info():
    """Get session information"""
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    return jsonify({
        'session_id': session_id,
        'model': client.get_model(),
        'message_count': len(client.get_history())
    })


@bp.route('/stats', methods=['GET'])
async def get_stats():
    """Get server statistics"""
    return jsonify({
        'active_sessions': session_manager.get_active_session_count()
    })
