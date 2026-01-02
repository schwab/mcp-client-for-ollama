"""Web session manager for handling multiple concurrent users"""
import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from mcp_client_for_ollama.web.integration.client_wrapper import WebMCPClient


class WebSessionManager:
    """Manages web user sessions with automatic cleanup"""

    def __init__(self, session_timeout_minutes: int = 60):
        self.sessions: Dict[str, WebMCPClient] = {}
        self.session_timestamps: Dict[str, datetime] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self._cleanup_task = None

    async def create_session(self, config: Optional[Dict] = None) -> str:
        """Create new session, return session ID"""
        session_id = str(uuid.uuid4())
        client = WebMCPClient(session_id, config)
        await client.initialize()

        self.sessions[session_id] = client
        self.session_timestamps[session_id] = datetime.now()

        return session_id

    def get_session(self, session_id: str) -> Optional[WebMCPClient]:
        """Get existing session and update timestamp"""
        if session_id in self.sessions:
            self.session_timestamps[session_id] = datetime.now()
            return self.sessions[session_id]
        return None

    async def delete_session(self, session_id: str):
        """Cleanup and delete session"""
        if session_id in self.sessions:
            client = self.sessions[session_id]
            await client.cleanup()
            del self.sessions[session_id]
            del self.session_timestamps[session_id]

    async def cleanup_expired_sessions(self):
        """Remove sessions that have exceeded timeout"""
        now = datetime.now()
        expired_sessions = [
            session_id
            for session_id, timestamp in self.session_timestamps.items()
            if now - timestamp > self.session_timeout
        ]

        for session_id in expired_sessions:
            await self.delete_session(session_id)

    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)

    async def cleanup_all_sessions(self):
        """Cleanup all sessions (for shutdown)"""
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.delete_session(session_id)


# Global session manager instance
session_manager = WebSessionManager()
