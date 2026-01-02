"""Models API endpoints for web interface"""
from flask import Blueprint, jsonify, request
from mcp_client_for_ollama.web.session.manager import session_manager
import ollama

bp = Blueprint('models', __name__)


@bp.route('/list', methods=['GET'])
async def list_models():
    """Get available Ollama models"""
    try:
        # Import inside function to avoid circular import
        from mcp_client_for_ollama.web.app import get_global_config

        # Get Ollama host from global config
        config = get_global_config()
        ollama_host = config.get('ollama_host', 'http://localhost:11434')

        # Use the ollama client with configured host
        client = ollama.AsyncClient(host=ollama_host)
        models_response = await client.list()

        # The response structure is: {'models': [Model objects]}
        # Model objects have attributes, not dict keys
        models = models_response.get('models', [])

        # Format model list for frontend
        model_list = []
        for model in models:
            # Model is an object with attributes, not a dict
            model_dict = {
                'name': getattr(model, 'model', getattr(model, 'name', '')),
                'size': getattr(model, 'size', 0),
                'modified_at': str(getattr(model, 'modified_at', ''))
            }
            model_list.append(model_dict)

        return jsonify({'models': model_list})
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': str(e.__class__.__name__)}), 500


@bp.route('/select', methods=['POST'])
async def select_model():
    """Set model for session"""
    data = request.json
    session_id = data.get('session_id')
    model_name = data.get('model')

    if not session_id or not model_name:
        return jsonify({'error': 'session_id and model required'}), 400

    client = session_manager.get_session(session_id)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    client.set_model(model_name)
    return jsonify({'status': 'ok', 'model': model_name})


@bp.route('/current', methods=['GET'])
async def get_current_model():
    """Get current model for session"""
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    current_model = client.get_model()
    return jsonify({'model': current_model})
