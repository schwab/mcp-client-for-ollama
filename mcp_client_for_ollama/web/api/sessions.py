"""Sessions API endpoints for web interface"""
from flask import Blueprint, request, jsonify, g
from mcp_client_for_ollama.web.session.manager import session_manager

bp = Blueprint('sessions', __name__)


@bp.route('/create', methods=['POST'])
async def create_session():
    """Create new user session

    Accepts optional JSON body with config, but works with empty POST too.
    Supports both standalone mode (no auth) and Nextcloud mode (authenticated).
    """
    # Import inside function to avoid circular import
    from mcp_client_for_ollama.web.app import get_global_config

    # Get username from auth middleware (None in standalone mode)
    username = g.get('nextcloud_user', None)

    # Use get_json(silent=True) to handle both JSON and empty requests
    data = request.get_json(silent=True) or {}
    user_config = data.get('config', {})

    # Merge global config with user config (user config takes precedence)
    config = get_global_config()
    config.update(user_config)

    # Pass username only if in Nextcloud mode
    if username:
        session_id = await session_manager.create_session(config, username=username)
    else:
        session_id = await session_manager.create_session(config)

    return jsonify({'session_id': session_id})


@bp.route('/delete', methods=['DELETE'])
async def delete_session():
    """Delete session (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    # Pass username only if in Nextcloud mode
    if username:
        await session_manager.delete_session(session_id, username=username)
    else:
        await session_manager.delete_session(session_id)

    return jsonify({'status': 'deleted'})


@bp.route('/info', methods=['GET'])
async def get_session_info():
    """Get session information (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    # Get session (username only used in Nextcloud mode)
    client = session_manager.get_session(session_id, username=username)
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
