"""JSONL Viewer/Editor API endpoints"""
from flask import Blueprint, request, jsonify
from pathlib import Path
import json
import os

bp = Blueprint('jsonl', __name__)

# Default data folder
DEFAULT_DATA_FOLDER = Path.home() / "Nextcloud/DEV/ollmcp/mcp-client-for-ollama/data"


def get_data_folder():
    """Get the data folder from environment or use default"""
    folder = os.environ.get('JSONL_DATA_FOLDER', str(DEFAULT_DATA_FOLDER))
    return Path(folder)


@bp.route('/list', methods=['GET'])
def list_files():
    """List all JSONL files in the data folder"""
    try:
        data_folder = get_data_folder()

        if not data_folder.exists():
            return jsonify({'error': f'Data folder not found: {data_folder}'}), 404

        # Get all JSONL files
        jsonl_files = []
        for file_path in sorted(data_folder.glob('**/*.jsonl')):
            try:
                size = file_path.stat().st_size
                lines = sum(1 for _ in file_path.open('r'))
                jsonl_files.append({
                    'name': file_path.name,
                    'path': str(file_path.relative_to(data_folder)),
                    'size': size,
                    'lines': lines,
                    'modified': file_path.stat().st_mtime
                })
            except Exception as e:
                continue

        return jsonify({
            'folder': str(data_folder),
            'files': jsonl_files,
            'count': len(jsonl_files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/content', methods=['GET'])
def get_content():
    """Get JSONL file content with pagination"""
    try:
        filename = request.args.get('file')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        if not filename:
            return jsonify({'error': 'file parameter required'}), 400

        data_folder = get_data_folder()
        file_path = data_folder / filename

        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(data_folder.resolve()):
            return jsonify({'error': 'Access denied'}), 403

        if not file_path.exists():
            return jsonify({'error': f'File not found: {filename}'}), 404

        # Read file with pagination
        lines = []
        total_lines = 0

        with open(file_path, 'r') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= (page - 1) * per_page and i < page * per_page:
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        lines.append({'_raw': line.strip(), '_error': 'Invalid JSON'})

        return jsonify({
            'file': filename,
            'path': str(file_path.relative_to(data_folder)),
            'page': page,
            'per_page': per_page,
            'total_lines': total_lines,
            'total_pages': (total_lines + per_page - 1) // per_page,
            'lines': lines
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/search', methods=['POST'])
def search_content():
    """Search for lines matching a query"""
    try:
        data = request.json
        filename = data.get('file')
        query = data.get('query', '').lower()
        limit = int(data.get('limit', 100))

        if not filename or not query:
            return jsonify({'error': 'file and query parameters required'}), 400

        data_folder = get_data_folder()
        file_path = data_folder / filename

        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(data_folder.resolve()):
            return jsonify({'error': 'Access denied'}), 403

        if not file_path.exists():
            return jsonify({'error': f'File not found: {filename}'}), 404

        results = []
        line_numbers = []

        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if len(results) >= limit:
                    break

                if query in line.lower():
                    try:
                        results.append({
                            'line_num': line_num,
                            'content': json.loads(line)
                        })
                    except json.JSONDecodeError:
                        results.append({
                            'line_num': line_num,
                            'content': {'_raw': line.strip()}
                        })
                    line_numbers.append(line_num)

        return jsonify({
            'file': filename,
            'query': query,
            'limit': limit,
            'results_count': len(results),
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/edit', methods=['POST'])
def edit_line():
    """Edit a specific line in a JSONL file"""
    try:
        data = request.json
        filename = data.get('file')
        line_num = int(data.get('line_num', 0))
        new_content = data.get('content')

        if not filename or line_num <= 0 or new_content is None:
            return jsonify({'error': 'file, line_num, and content required'}), 400

        data_folder = get_data_folder()
        file_path = data_folder / filename

        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(data_folder.resolve()):
            return jsonify({'error': 'Access denied'}), 403

        if not file_path.exists():
            return jsonify({'error': f'File not found: {filename}'}), 404

        # Read all lines
        lines = []
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Check line number
        if line_num > len(lines):
            return jsonify({'error': f'Line {line_num} out of range'}), 400

        # Update the line
        if isinstance(new_content, dict):
            lines[line_num - 1] = json.dumps(new_content) + '\n'
        else:
            lines[line_num - 1] = new_content + '\n'

        # Write back
        with open(file_path, 'w') as f:
            f.writelines(lines)

        return jsonify({
            'file': filename,
            'line_num': line_num,
            'status': 'updated'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/delete-line', methods=['POST'])
def delete_line():
    """Delete a specific line from a JSONL file"""
    try:
        data = request.json
        filename = data.get('file')
        line_num = int(data.get('line_num', 0))

        if not filename or line_num <= 0:
            return jsonify({'error': 'file and line_num required'}), 400

        data_folder = get_data_folder()
        file_path = data_folder / filename

        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(data_folder.resolve()):
            return jsonify({'error': 'Access denied'}), 403

        if not file_path.exists():
            return jsonify({'error': f'File not found: {filename}'}), 404

        # Read all lines
        lines = []
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Check line number
        if line_num > len(lines):
            return jsonify({'error': f'Line {line_num} out of range'}), 400

        # Remove the line
        del lines[line_num - 1]

        # Write back
        with open(file_path, 'w') as f:
            f.writelines(lines)

        return jsonify({
            'file': filename,
            'line_num': line_num,
            'status': 'deleted'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/add-line', methods=['POST'])
def add_line():
    """Add a new line to a JSONL file"""
    try:
        data = request.json
        filename = data.get('file')
        content = data.get('content')
        position = int(data.get('position', -1))  # -1 = end of file

        if not filename or content is None:
            return jsonify({'error': 'file and content required'}), 400

        data_folder = get_data_folder()
        file_path = data_folder / filename

        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(data_folder.resolve()):
            return jsonify({'error': 'Access denied'}), 403

        if not file_path.exists():
            return jsonify({'error': f'File not found: {filename}'}), 404

        # Read all lines
        lines = []
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Prepare new line
        if isinstance(content, dict):
            new_line = json.dumps(content) + '\n'
        else:
            new_line = str(content) + '\n'

        # Insert line
        if position < 0 or position >= len(lines):
            lines.append(new_line)
            insert_pos = len(lines)
        else:
            lines.insert(position, new_line)
            insert_pos = position + 1

        # Write back
        with open(file_path, 'w') as f:
            f.writelines(lines)

        return jsonify({
            'file': filename,
            'position': insert_pos,
            'status': 'added'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/validate', methods=['POST'])
def validate_jsonl():
    """Validate JSONL file format"""
    try:
        data = request.json
        filename = data.get('file')

        if not filename:
            return jsonify({'error': 'file parameter required'}), 400

        data_folder = get_data_folder()
        file_path = data_folder / filename

        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(data_folder.resolve()):
            return jsonify({'error': 'Access denied'}), 403

        if not file_path.exists():
            return jsonify({'error': f'File not found: {filename}'}), 404

        errors = []
        valid_lines = 0

        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    json.loads(line)
                    valid_lines += 1
                except json.JSONDecodeError as e:
                    errors.append({
                        'line': line_num,
                        'error': str(e),
                        'content': line[:100]
                    })

        is_valid = len(errors) == 0

        return jsonify({
            'file': filename,
            'valid': is_valid,
            'valid_lines': valid_lines,
            'error_count': len(errors),
            'errors': errors[:10]  # Return first 10 errors
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stats', methods=['GET'])
def file_stats():
    """Get detailed statistics about a JSONL file"""
    try:
        filename = request.args.get('file')

        if not filename:
            return jsonify({'error': 'file parameter required'}), 400

        data_folder = get_data_folder()
        file_path = data_folder / filename

        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(data_folder.resolve()):
            return jsonify({'error': 'Access denied'}), 403

        if not file_path.exists():
            return jsonify({'error': f'File not found: {filename}'}), 404

        stats = {
            'file': filename,
            'size': file_path.stat().st_size,
            'lines': 0,
            'valid_json': 0,
            'invalid_json': 0,
            'keys': {},
            'sample': None
        }

        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                stats['lines'] = line_num
                try:
                    obj = json.loads(line)
                    stats['valid_json'] += 1

                    # Track keys
                    if isinstance(obj, dict):
                        for key in obj.keys():
                            stats['keys'][key] = stats['keys'].get(key, 0) + 1

                    # Save first sample
                    if stats['sample'] is None:
                        stats['sample'] = obj
                except json.JSONDecodeError:
                    stats['invalid_json'] += 1

        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
