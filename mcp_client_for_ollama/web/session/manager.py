"""Web session manager for handling multiple concurrent users"""
import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from mcp_client_for_ollama.web.integration.client_wrapper import WebMCPClient


class WebSessionManager:
    """Manages web user sessions with automatic cleanup.

    Supports two modes:
    - Standalone mode: Single-user, sessions stored in simple dict
    - Nextcloud mode: Multi-user, sessions stored in nested dict by username
    """

    def __init__(self, session_timeout_minutes: int = 60, multi_user_mode: bool = False):
        self.multi_user_mode = multi_user_mode
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self._cleanup_task = None

        if multi_user_mode:
            # Nextcloud mode: {username: {session_id: WebMCPClient}}
            self.user_sessions: Dict[str, Dict[str, WebMCPClient]] = {}
            self.user_timestamps: Dict[str, Dict[str, datetime]] = {}
        else:
            # Standalone mode: {session_id: WebMCPClient}
            self.sessions: Dict[str, WebMCPClient] = {}
            self.session_timestamps: Dict[str, datetime] = {}

    async def create_session(self, config: Optional[Dict] = None, username: Optional[str] = None) -> str:
        """Create new session, return session ID.

        Args:
            config: Session configuration
            username: Nextcloud username (required only in multi-user mode)

        Returns:
            Session ID

        Raises:
            ValueError: If username is required but not provided
        """
        session_id = str(uuid.uuid4())
        client = WebMCPClient(session_id, config)
        # Don't initialize here - let it initialize lazily in the streaming context
        # This avoids event loop binding issues

        if self.multi_user_mode:
            # Nextcloud mode: User-scoped session
            if not username:
                raise ValueError("username required in multi-user mode")

            if username not in self.user_sessions:
                self.user_sessions[username] = {}
                self.user_timestamps[username] = {}

            self.user_sessions[username][session_id] = client
            self.user_timestamps[username][session_id] = datetime.now()
        else:
            # Standalone mode: Global session
            self.sessions[session_id] = client
            self.session_timestamps[session_id] = datetime.now()

        return session_id

    def get_session(self, session_id: str, username: Optional[str] = None) -> Optional[WebMCPClient]:
        """Get existing session and update timestamp.

        Args:
            session_id: Session ID to retrieve
            username: Nextcloud username (required only in multi-user mode)

        Returns:
            WebMCPClient if found, None otherwise
        """
        if self.multi_user_mode:
            # Nextcloud mode: Check username ownership
            if not username or username not in self.user_sessions:
                return None
            if session_id in self.user_sessions[username]:
                self.user_timestamps[username][session_id] = datetime.now()
                return self.user_sessions[username][session_id]
            return None
        else:
            # Standalone mode: Direct lookup
            if session_id in self.sessions:
                self.session_timestamps[session_id] = datetime.now()
                return self.sessions[session_id]
            return None

    async def delete_session(self, session_id: str, username: Optional[str] = None):
        """Cleanup and delete session.

        Args:
            session_id: Session ID to delete
            username: Nextcloud username (required only in multi-user mode)
        """
        if self.multi_user_mode:
            if username and username in self.user_sessions:
                if session_id in self.user_sessions[username]:
                    client = self.user_sessions[username][session_id]
                    await client.cleanup()
                    del self.user_sessions[username][session_id]
                    del self.user_timestamps[username][session_id]
        else:
            if session_id in self.sessions:
                client = self.sessions[session_id]
                await client.cleanup()
                del self.sessions[session_id]
                del self.session_timestamps[session_id]

    async def cleanup_expired_sessions(self):
        """Remove sessions that have exceeded timeout"""
        now = datetime.now()

        if self.multi_user_mode:
            # Nextcloud mode: Check each user's sessions
            for username in list(self.user_timestamps.keys()):
                expired_sessions = [
                    session_id
                    for session_id, timestamp in self.user_timestamps[username].items()
                    if now - timestamp > self.session_timeout
                ]
                for session_id in expired_sessions:
                    await self.delete_session(session_id, username=username)
        else:
            # Standalone mode: Check all sessions
            expired_sessions = [
                session_id
                for session_id, timestamp in self.session_timestamps.items()
                if now - timestamp > self.session_timeout
            ]
            for session_id in expired_sessions:
                await self.delete_session(session_id)

    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        if self.multi_user_mode:
            return sum(len(sessions) for sessions in self.user_sessions.values())
        else:
            return len(self.sessions)

    def get_user_session_count(self, username: str) -> int:
        """Get number of active sessions for a specific user (Nextcloud mode only)"""
        if self.multi_user_mode and username in self.user_sessions:
            return len(self.user_sessions[username])
        return 0

    async def cleanup_all_sessions(self):
        """Cleanup all sessions (for shutdown)"""
        if self.multi_user_mode:
            for username in list(self.user_sessions.keys()):
                session_ids = list(self.user_sessions[username].keys())
                for session_id in session_ids:
                    await self.delete_session(session_id, username=username)
        else:
            session_ids = list(self.sessions.keys())
            for session_id in session_ids:
                await self.delete_session(session_id)


# Global session manager instance
# Mode is determined at runtime based on NEXTCLOUD_AUTH_ENABLED environment variable
import os
_multi_user = os.environ.get('NEXTCLOUD_AUTH_ENABLED', 'false').lower() == 'true'
if _multi_user:
    print("[Session Manager] Initializing in multi-user mode (Nextcloud)")
else:
    print("[Session Manager] Initializing in standalone mode")
session_manager = WebSessionManager(multi_user_mode=_multi_user)
