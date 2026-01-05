"""Flask web application for MCP Client"""
from flask import Flask, jsonify, send_from_directory, request, g
from flask_cors import CORS
import os
import asyncio
from functools import wraps

# Import blueprints
from mcp_client_for_ollama.web.api import chat, config, sessions, models, tools, memory
from mcp_client_for_ollama.web.sse import streaming
from mcp_client_for_ollama.web.session.manager import session_manager

# Import Nextcloud auth (conditional)
try:
    from mcp_client_for_ollama.web.auth import NextcloudAuthProvider
    NEXTCLOUD_AUTH_AVAILABLE = True
except ImportError:
    NEXTCLOUD_AUTH_AVAILABLE = False


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

    # Determine if Nextcloud mode is enabled
    nextcloud_url = os.environ.get('NEXTCLOUD_URL', 'https://nextcloudsch.ftp.sh')
    auth_enabled = os.environ.get('NEXTCLOUD_AUTH_ENABLED', 'false').lower() == 'true'

    # Configure CORS based on mode
    if auth_enabled:
        # Nextcloud mode: Restrict CORS to Nextcloud origin only
        print(f"[Nextcloud Mode] CORS restricted to: {nextcloud_url}")
        CORS(app, resources={
            r"/api/*": {
                "origins": [nextcloud_url],
                "supports_credentials": True
            },
            r"/stream/*": {
                "origins": [nextcloud_url],
                "supports_credentials": True
            }
        })
    else:
        # Standalone mode: Allow all origins (current behavior)
        print("[Standalone Mode] CORS allows all origins")
        CORS(app, resources={
            r"/api/*": {"origins": "*"},
            r"/stream/*": {"origins": "*"}
        })

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['NEXTCLOUD_AUTH_ENABLED'] = auth_enabled
    app.config['NEXTCLOUD_URL'] = nextcloud_url

    # Initialize Nextcloud auth provider if enabled
    if auth_enabled:
        if NEXTCLOUD_AUTH_AVAILABLE:
            app.config['NEXTCLOUD_AUTH_PROVIDER'] = NextcloudAuthProvider(nextcloud_url)
            print(f"[Nextcloud Mode] Authentication provider initialized for {nextcloud_url}")
        else:
            print("[ERROR] Nextcloud authentication enabled but module not available")
            auth_enabled = False
            app.config['NEXTCLOUD_AUTH_ENABLED'] = False

    if app_config:
        app.config.update(app_config)

    # Register blueprints
    app.register_blueprint(chat.bp, url_prefix='/api/chat')
    app.register_blueprint(config.bp, url_prefix='/api/config')
    app.register_blueprint(sessions.bp, url_prefix='/api/sessions')
    app.register_blueprint(models.bp, url_prefix='/api/models')
    app.register_blueprint(tools.bp, url_prefix='/api/tools')
    app.register_blueprint(memory.bp, url_prefix='/api/memory')
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
            'version': '0.42.6',
            'status': 'running',
            'endpoints': {
                'sessions': '/api/sessions',
                'chat': '/api/chat',
                'models': '/api/models',
                'tools': '/api/tools',
                'memory': '/api/memory',
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

    # Authentication middleware (Nextcloud mode only)
    @app.before_request
    def authenticate_request():
        """Authenticate request if Nextcloud mode is enabled"""
        # Skip auth in standalone mode
        if not app.config.get('NEXTCLOUD_AUTH_ENABLED', False):
            g.nextcloud_user = None  # No user in standalone mode
            return

        # Skip health check endpoint
        if request.path == '/health' or request.path == '/api':
            return

        # Nextcloud mode: Require authentication
        auth_provider = app.config.get('NEXTCLOUD_AUTH_PROVIDER')
        if not auth_provider:
            g.nextcloud_user = None
            return

        user = auth_provider.get_current_user(request)

        if not user:
            return jsonify({'error': 'Unauthorized', 'message': 'Nextcloud authentication required'}), 401

        g.nextcloud_user = user

    # Start background thread for periodic session cleanup
    # (every 5 minutes instead of on every request to avoid race conditions)
    import threading
    import time

    def periodic_session_cleanup():
        """Background thread that periodically cleans up expired sessions"""
        while True:
            try:
                time.sleep(300)  # 5 minutes
                # Run cleanup in asyncio event loop
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(session_manager.cleanup_expired_sessions())
                finally:
                    loop.close()
            except Exception as e:
                print(f"[Session Cleanup] Error: {e}")

    cleanup_thread = threading.Thread(target=periodic_session_cleanup, daemon=True)
    cleanup_thread.start()
    print("[Session Cleanup] Started background cleanup thread (5 minute interval)")

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


def run_web_server(bind='0.0.0.0', port=5222, ollama_host='http://localhost:11434', config_dir=None, debug=False):
    """Run the Flask web server

    Args:
        bind: Address to bind Flask server to (e.g., 0.0.0.0, localhost)
        port: Port to bind Flask server to
        ollama_host: Ollama API URL (e.g., http://localhost:11434)
        config_dir: Config directory path (e.g., /path/to/.config)
        debug: Enable Flask debug mode
    """
    # Set global config with Ollama host and config directory
    set_global_config({
        'ollama_host': ollama_host,
        'config_dir': config_dir
    })

    print(f"Starting MCP Client Web Server on http://{bind}:{port}")
    print(f"Ollama API: {ollama_host}")
    print(f"API Documentation: http://{bind}:{port}/")
    app.run(host=bind, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    run_web_server(debug=True)
