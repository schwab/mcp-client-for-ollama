"""Memory API endpoints for web interface"""
from flask import Blueprint, request, jsonify, g
from mcp_client_for_ollama.web.session.manager import session_manager
import json
from datetime import datetime

bp = Blueprint('memory', __name__)


# ========================================================================
# MEMORY SESSION ENDPOINTS
# ========================================================================

@bp.route('/status', methods=['GET'])
async def get_memory_status():
    """Get current memory session status"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        # Get memory state from client
        memory_state = await client.get_memory_status()

        if not memory_state:
            return jsonify({
                'active': False,
                'message': 'No active memory session'
            })

        return jsonify(memory_state)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/new', methods=['POST'])
async def create_memory_session():
    """Create new memory session"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    domain = data.get('domain', 'default')
    description = data.get('description', '')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        # Initialize memory session
        result = await client.create_memory_session(domain, description)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/clear', methods=['DELETE'])
async def clear_memory():
    """Clear current memory session"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.clear_memory()
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/export', methods=['GET'])
async def export_memory():
    """Export memory session to JSON"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        memory_data = await client.export_memory()

        # Return as JSON download
        response = jsonify(memory_data)
        response.headers['Content-Disposition'] = f'attachment; filename=memory_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/import', methods=['POST'])
async def import_memory():
    """Import memory session from JSON"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    memory_data = data.get('memory_data')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    if not memory_data:
        return jsonify({'error': 'memory_data required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.import_memory(memory_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========================================================================
# GOALS ENDPOINTS
# ========================================================================

@bp.route('/goals', methods=['GET'])
async def list_goals():
    """List all goals with summary"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        goals = await client.list_goals()
        return jsonify({'goals': goals})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/goals/<goal_id>', methods=['GET'])
async def get_goal_details(goal_id):
    """Get detailed goal information"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        goal = await client.get_goal(goal_id)
        if not goal:
            return jsonify({'error': f'Goal {goal_id} not found'}), 404

        return jsonify(goal)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/goals', methods=['POST'])
async def create_goal():
    """Create new goal"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    goal_id = data.get('goal_id')  # Optional
    description = data.get('description', '')
    constraints = data.get('constraints', [])

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    if not description:
        return jsonify({'error': 'description required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.create_goal(goal_id, description, constraints)
        return jsonify(result), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/goals/<goal_id>', methods=['PUT'])
async def update_goal(goal_id):
    """Update existing goal"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    description = data.get('description')
    add_constraints = data.get('add_constraints')
    remove_constraints = data.get('remove_constraints')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.update_goal(
            goal_id,
            description=description,
            add_constraints=add_constraints,
            remove_constraints=remove_constraints
        )
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/goals/<goal_id>', methods=['DELETE'])
async def delete_goal(goal_id):
    """Delete goal"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    confirm = data.get('confirm', False)

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.delete_goal(goal_id, confirm=confirm)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========================================================================
# FEATURES ENDPOINTS
# ========================================================================

@bp.route('/features/<feature_id>', methods=['GET'])
async def get_feature_details(feature_id):
    """Get detailed feature information"""
    username = g.get('nextcloud_user', None)
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        feature = await client.get_feature(feature_id)
        if not feature:
            return jsonify({'error': f'Feature {feature_id} not found'}), 404

        return jsonify(feature)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/features', methods=['POST'])
async def create_feature():
    """Create new feature"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    goal_id = data.get('goal_id')
    description = data.get('description', '')
    criteria = data.get('criteria', [])
    tests = data.get('tests', [])
    priority = data.get('priority', 'medium')
    assigned_to = data.get('assigned_to')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    if not goal_id:
        return jsonify({'error': 'goal_id required'}), 400

    if not description:
        return jsonify({'error': 'description required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.create_feature(
            goal_id=goal_id,
            description=description,
            criteria=criteria,
            tests=tests,
            priority=priority,
            assigned_to=assigned_to
        )
        return jsonify(result), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/features/<feature_id>', methods=['PUT'])
async def update_feature(feature_id):
    """Update existing feature"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.update_feature(
            feature_id=feature_id,
            description=data.get('description'),
            add_criteria=data.get('add_criteria'),
            remove_criteria=data.get('remove_criteria'),
            add_tests=data.get('add_tests'),
            remove_tests=data.get('remove_tests'),
            priority=data.get('priority'),
            assigned_to=data.get('assigned_to')
        )
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/features/<feature_id>/status', methods=['PUT'])
async def update_feature_status(feature_id):
    """Quick status update for feature"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    status = data.get('status')
    notes = data.get('notes')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    if not status:
        return jsonify({'error': 'status required'}), 400

    # Validate status
    valid_statuses = ['pending', 'in_progress', 'completed', 'failed', 'blocked']
    if status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.update_feature_status(feature_id, status, notes)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/features/<feature_id>', methods=['DELETE'])
async def delete_feature(feature_id):
    """Delete feature"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    confirm = data.get('confirm', False)

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.delete_feature(feature_id, confirm=confirm)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/features/<feature_id>/move', methods=['POST'])
async def move_feature(feature_id):
    """Move feature to different goal"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    target_goal_id = data.get('target_goal_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    if not target_goal_id:
        return jsonify({'error': 'target_goal_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.move_feature(feature_id, target_goal_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========================================================================
# PROGRESS TRACKING ENDPOINTS
# ========================================================================

@bp.route('/progress', methods=['POST'])
async def log_progress():
    """Log progress entry"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    agent_type = data.get('agent_type', 'WEB_USER')
    action = data.get('action', '')
    outcome = data.get('outcome', 'success')
    details = data.get('details', '')
    feature_id = data.get('feature_id')
    artifacts_changed = data.get('artifacts_changed', [])

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    if not action:
        return jsonify({'error': 'action required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.log_progress(
            agent_type=agent_type,
            action=action,
            outcome=outcome,
            details=details,
            feature_id=feature_id,
            artifacts_changed=artifacts_changed
        )
        return jsonify(result), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/test-results', methods=['POST'])
async def add_test_result():
    """Add test result to feature"""
    username = g.get('nextcloud_user', None)
    data = request.json or {}
    session_id = data.get('session_id')
    feature_id = data.get('feature_id')
    test_id = data.get('test_id')
    passed = data.get('passed', False)
    details = data.get('details', '')
    output = data.get('output', '')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    if not feature_id:
        return jsonify({'error': 'feature_id required'}), 400

    if not test_id:
        return jsonify({'error': 'test_id required'}), 400

    client = session_manager.get_session(session_id, username=username)
    if not client:
        return jsonify({'error': 'Invalid session'}), 404

    try:
        result = await client.add_test_result(
            feature_id=feature_id,
            test_id=test_id,
            passed=passed,
            details=details,
            output=output
        )
        return jsonify(result), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
