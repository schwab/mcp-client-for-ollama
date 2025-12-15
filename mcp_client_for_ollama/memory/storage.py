"""
Storage layer for persistent domain memory.

Handles saving and loading memory to/from filesystem with support for
backups, versioning, and session management.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from .base_memory import DomainMemory, ProgressEntry, OutcomeType
from .schemas import MemorySchema, DomainType


logger = logging.getLogger(__name__)


class MemoryStorage:
    """
    Persistent storage for domain memory.

    Stores memory as JSON files with the following structure:
    base_dir/
        {domain}/
            {session_id}/
                memory.json          (main memory state)
                progress.log         (human-readable log)
                artifacts/           (domain-specific files)
                backups/             (automatic backups)
    """

    MEMORY_FILENAME = "memory.json"
    PROGRESS_LOG_FILENAME = "progress.log"
    ARTIFACTS_DIR = "artifacts"
    BACKUPS_DIR = "backups"

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize storage.

        Args:
            base_dir: Base directory for memory storage. Defaults to ~/.mcp-memory
        """
        if base_dir is None:
            base_dir = Path.home() / ".mcp-memory"
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Memory storage initialized at {self.base_dir}")

    def _get_session_dir(self, session_id: str, domain: str) -> Path:
        """Get the directory path for a session."""
        return self.base_dir / domain / session_id

    def _get_memory_path(self, session_id: str, domain: str) -> Path:
        """Get the path to the memory.json file."""
        return self._get_session_dir(session_id, domain) / self.MEMORY_FILENAME

    def _get_progress_log_path(self, session_id: str, domain: str) -> Path:
        """Get the path to the progress.log file."""
        return self._get_session_dir(session_id, domain) / self.PROGRESS_LOG_FILENAME

    def _get_artifacts_dir(self, session_id: str, domain: str) -> Path:
        """Get the artifacts directory path."""
        return self._get_session_dir(session_id, domain) / self.ARTIFACTS_DIR

    def _get_backups_dir(self, session_id: str, domain: str) -> Path:
        """Get the backups directory path."""
        return self._get_session_dir(session_id, domain) / self.BACKUPS_DIR

    def save_memory(
        self,
        memory: DomainMemory,
        create_backup: bool = True,
    ) -> None:
        """
        Persist memory to disk.

        Args:
            memory: The domain memory to save
            create_backup: Whether to create a backup before saving

        Raises:
            IOError: If saving fails
        """
        session_id = memory.metadata.session_id
        domain = memory.metadata.domain
        session_dir = self._get_session_dir(session_id, domain)
        memory_path = self._get_memory_path(session_id, domain)

        try:
            # Create session directory structure
            session_dir.mkdir(parents=True, exist_ok=True)
            self._get_artifacts_dir(session_id, domain).mkdir(exist_ok=True)
            self._get_backups_dir(session_id, domain).mkdir(exist_ok=True)

            # Create backup if requested and file exists
            if create_backup and memory_path.exists():
                self._create_backup(session_id, domain)

            # Update timestamp
            memory.metadata.updated_at = datetime.now()

            # Save memory.json
            memory_dict = memory.to_dict()
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump(memory_dict, f, indent=2, ensure_ascii=False)

            # Save human-readable progress.log
            self._write_progress_log(memory, session_id, domain)

            logger.info(f"Saved memory for session {session_id} in domain {domain}")

        except Exception as e:
            logger.error(f"Failed to save memory for session {session_id}: {e}")
            raise IOError(f"Failed to save memory: {e}")

    def load_memory(
        self,
        session_id: str,
        domain: str,
    ) -> Optional[DomainMemory]:
        """
        Load memory from disk.

        Args:
            session_id: The session ID
            domain: The domain type

        Returns:
            DomainMemory if found, None otherwise

        Raises:
            ValueError: If memory data is invalid
        """
        memory_path = self._get_memory_path(session_id, domain)

        if not memory_path.exists():
            logger.warning(f"Memory file not found for session {session_id} in domain {domain}")
            return None

        try:
            with open(memory_path, 'r', encoding='utf-8') as f:
                memory_dict = json.load(f)

            # Validate structure
            is_valid, error = MemorySchema.validate_memory_structure(memory_dict)
            if not is_valid:
                raise ValueError(f"Invalid memory structure: {error}")

            # Load from dictionary
            memory = DomainMemory.from_dict(memory_dict)

            logger.info(f"Loaded memory for session {session_id} from domain {domain}")
            return memory

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in memory file for session {session_id}: {e}")
            raise ValueError(f"Invalid JSON in memory file: {e}")
        except Exception as e:
            logger.error(f"Failed to load memory for session {session_id}: {e}")
            raise ValueError(f"Failed to load memory: {e}")

    def session_exists(self, session_id: str, domain: str) -> bool:
        """Check if a session exists."""
        return self._get_memory_path(session_id, domain).exists()

    def list_sessions(
        self,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all available sessions.

        Args:
            domain: Filter by domain. If None, return all sessions.

        Returns:
            List of session info dictionaries with keys:
                - session_id
                - domain
                - description
                - created_at
                - updated_at
                - completion_percentage
        """
        sessions = []

        # Determine which domains to search
        if domain:
            domains_to_search = [domain]
        else:
            # Search all domain directories
            domains_to_search = [
                d.name for d in self.base_dir.iterdir()
                if d.is_dir()
            ]

        for domain_name in domains_to_search:
            domain_dir = self.base_dir / domain_name
            if not domain_dir.exists():
                continue

            # Find all session directories in this domain
            for session_dir in domain_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                memory_path = session_dir / self.MEMORY_FILENAME
                if not memory_path.exists():
                    continue

                try:
                    # Load minimal info from memory
                    with open(memory_path, 'r', encoding='utf-8') as f:
                        memory_dict = json.load(f)

                    metadata = memory_dict.get("metadata", {})

                    # Calculate completion percentage
                    goals = memory_dict.get("goals", [])
                    all_features = [
                        f for goal in goals
                        for f in goal.get("features", [])
                    ]
                    completed = sum(
                        1 for f in all_features
                        if f.get("status") == "completed"
                    )
                    total = len(all_features)
                    completion = (completed / total * 100) if total > 0 else 0

                    sessions.append({
                        "session_id": metadata.get("session_id"),
                        "domain": metadata.get("domain"),
                        "description": metadata.get("description"),
                        "created_at": metadata.get("created_at"),
                        "updated_at": metadata.get("updated_at"),
                        "completion_percentage": completion,
                        "total_features": total,
                        "completed_features": completed,
                    })

                except Exception as e:
                    logger.warning(f"Failed to read session {session_dir.name}: {e}")
                    continue

        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    def delete_session(self, session_id: str, domain: str) -> bool:
        """
        Delete a session and all its data.

        Args:
            session_id: The session ID
            domain: The domain type

        Returns:
            True if deleted, False if not found
        """
        session_dir = self._get_session_dir(session_id, domain)

        if not session_dir.exists():
            logger.warning(f"Session {session_id} not found in domain {domain}")
            return False

        try:
            shutil.rmtree(session_dir)
            logger.info(f"Deleted session {session_id} from domain {domain}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def archive_session(self, session_id: str, domain: str) -> bool:
        """
        Archive a session by moving it to an archive directory.

        Args:
            session_id: The session ID
            domain: The domain type

        Returns:
            True if archived, False if failed
        """
        session_dir = self._get_session_dir(session_id, domain)
        if not session_dir.exists():
            return False

        archive_dir = self.base_dir / "_archived" / domain / session_id
        archive_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(session_dir), str(archive_dir))
            logger.info(f"Archived session {session_id} from domain {domain}")
            return True
        except Exception as e:
            logger.error(f"Failed to archive session {session_id}: {e}")
            return False

    def _create_backup(self, session_id: str, domain: str) -> None:
        """Create a timestamped backup of the memory file."""
        memory_path = self._get_memory_path(session_id, domain)
        if not memory_path.exists():
            return

        backups_dir = self._get_backups_dir(session_id, domain)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backups_dir / f"memory_{timestamp}.json"

        shutil.copy2(memory_path, backup_path)
        logger.debug(f"Created backup at {backup_path}")

        # Keep only last 10 backups
        self._cleanup_old_backups(backups_dir, keep=10)

    def _cleanup_old_backups(self, backups_dir: Path, keep: int = 10) -> None:
        """Remove old backups, keeping only the most recent N."""
        backups = sorted(
            backups_dir.glob("memory_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for old_backup in backups[keep:]:
            old_backup.unlink()
            logger.debug(f"Removed old backup {old_backup}")

    def _write_progress_log(
        self,
        memory: DomainMemory,
        session_id: str,
        domain: str,
    ) -> None:
        """Write human-readable progress log."""
        log_path = self._get_progress_log_path(session_id, domain)

        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"# Progress Log for Session {session_id}\n")
            f.write(f"Domain: {domain}\n")
            f.write(f"Description: {memory.metadata.description}\n")
            f.write(f"Created: {memory.metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Updated: {memory.metadata.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\n{'=' * 80}\n\n")

            for entry in memory.progress_log:
                f.write(entry.to_log_line() + "\n")

    def get_artifacts_path(self, session_id: str, domain: str) -> Path:
        """
        Get the path to the artifacts directory for external use.

        This allows other components to save domain-specific artifacts.
        """
        return self._get_artifacts_dir(session_id, domain)

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Delete sessions older than N days (based on updated_at).

        Args:
            days: Delete sessions not updated in this many days

        Returns:
            Number of sessions deleted
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0

        for domain_dir in self.base_dir.iterdir():
            if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
                continue

            for session_dir in domain_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                memory_path = session_dir / self.MEMORY_FILENAME
                if memory_path.exists():
                    if memory_path.stat().st_mtime < cutoff:
                        shutil.rmtree(session_dir)
                        deleted_count += 1
                        logger.info(f"Cleaned up old session {session_dir.name}")

        return deleted_count
