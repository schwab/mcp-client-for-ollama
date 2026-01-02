"""Flask web application for MCP Client"""
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import asyncio
from functools import wraps

# Import blueprints
from mcp_client_for_ollama.web.api import chat, config, sessions, models
from mcp_client_for_ollama.web.sse import streaming
from mcp_client_for_ollama.web.session.manager import session_manager


def async_route(f):
    """Decorator to handle async routes in Flask"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


def create_app(app_config=None):
    """Application factory for creating Flask app"""
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    # Enable CORS for frontend
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/stream/*": {"origins": "*"}
    })

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_TYPE'] = 'filesystem'

    if app_config:
        app.config.update(app_config)

    # Register blueprints
    app.register_blueprint(chat.bp, url_prefix='/api/chat')
    app.register_blueprint(config.bp, url_prefix='/api/config')
    app.register_blueprint(sessions.bp, url_prefix='/api/sessions')
    app.register_blueprint(models.bp, url_prefix='/api/models')
    app.register_blueprint(streaming.bp, url_prefix='/api/stream')

    # Root endpoint - serve UI
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    # API info endpoint
    @app.route('/api')
    def api_info():
        return jsonify({
            'name': 'MCP Client Web API',
            'version': '0.37.6',
            'status': 'running',
            'endpoints': {
                'sessions': '/api/sessions',
                'chat': '/api/chat',
                'models': '/api/models',
                'streaming': '/api/stream/chat',
                'config': '/api/config'
            }
        })

    # Health check endpoint
    @app.route('/health')
    @async_route
    async def health():
        return jsonify({
            'status': 'healthy',
            'active_sessions': session_manager.get_active_session_count()
        })

    # Cleanup expired sessions periodically
    @app.before_request
    @async_route
    async def cleanup_sessions():
        """Cleanup expired sessions before each request"""
        await session_manager.cleanup_expired_sessions()

    return app


# Global app config for sessions
_global_config = {}


def set_global_config(config):
    """Set global configuration for all sessions"""
    global _global_config
    _global_config = config


def get_global_config():
    """Get global configuration for sessions"""
    return _global_config.copy()


# Create default app instance
app = create_app()


def run_web_server(bind='0.0.0.0', port=5000, ollama_host='http://localhost:11434', debug=False):
    """Run the Flask web server

    Args:
        bind: Address to bind Flask server to (e.g., 0.0.0.0, localhost)
        port: Port to bind Flask server to
        ollama_host: Ollama API URL (e.g., http://localhost:11434)
        debug: Enable Flask debug mode
    """
    # Set global config with Ollama host
    set_global_config({'ollama_host': ollama_host})

    print(f"Starting MCP Client Web Server on http://{bind}:{port}")
    print(f"Ollama API: {ollama_host}")
    print(f"API Documentation: http://{bind}:{port}/")
    app.run(host=bind, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    run_web_server(debug=True)
