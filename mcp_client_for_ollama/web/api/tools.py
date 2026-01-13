"""Tools API endpoints for web interface"""
from flask import Blueprint, request, jsonify, g
from mcp_client_for_ollama.web.session.manager import session_manager

bp = Blueprint('tools', __name__)


@bp.route('/list', methods=['GET'])
async def list_tools():
    """Get all available tools with their enabled status (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    # Ensure client is initialized before getting tools
    await client.initialize()

    tools = client.get_tools()
    return jsonify({'tools': tools})


@bp.route('/toggle', methods=['POST'])
async def toggle_tool():
    """Toggle a tool's enabled status (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    data = request.json
    session_id = data.get('session_id')
    tool_name = data.get('tool_name')
    enabled = data.get('enabled')

    if not session_id or not tool_name or enabled is None:
        return jsonify({'error': 'session_id, tool_name, and enabled required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    success = client.set_tool_enabled(tool_name, enabled)
    if not success:
        return jsonify({'error': 'Tool not found'}), 404

    return jsonify({'status': 'ok', 'tool_name': tool_name, 'enabled': enabled})


@bp.route('/enabled', methods=['GET'])
async def get_enabled_tools():
    """Get list of enabled tools (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    enabled_tools = client.get_enabled_tools()
    return jsonify({'tools': enabled_tools})


@bp.route('/disabled', methods=['GET'])
async def get_disabled_tools():
    """Get list of disabled tools (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    disabled_tools = client.get_disabled_tools()
    return jsonify({'tools': disabled_tools})


@bp.route('/execute', methods=['POST'])
async def execute_tool():
    """Execute a tool with the given arguments (supports both standalone and Nextcloud mode)"""
    username = g.get('nextcloud_user', None)
    data = request.json
    session_id = data.get('session_id')
    tool_name = data.get('tool_name')
    arguments = data.get('arguments', {})

    if not session_id or not tool_name:
        return jsonify({'error': 'session_id and tool_name required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    # Ensure client is initialized
    await client.initialize()

    try:
        # Execute the tool directly through the client
        # The client has access to both builtin tools and MCP server tools
        result = await client.execute_tool(tool_name, arguments)

        return jsonify({
            'status': 'ok',
            'tool_name': tool_name,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'tool_name': tool_name,
            'error': str(e)
        }), 500
