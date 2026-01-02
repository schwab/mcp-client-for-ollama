"""Configuration API endpoints for web interface"""
from flask import Blueprint, jsonify, request
from mcp_client_for_ollama.web.session.manager import session_manager

bp = Blueprint('config', __name__)


@bp.route('/get', methods=['GET'])
async def get_config():
    """Get configuration for session"""
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    return jsonify({
        'model': client.get_model(),
        'ollama_host': client.ollama_host
    })


@bp.route('/update', methods=['POST'])
async def update_config():
    """Update configuration for session (MVP: limited to model selection)"""
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    # For MVP, only allow model updates (handled via /models/select)
    return jsonify({'status': 'ok', 'message': 'Use /models/select for model changes'})
