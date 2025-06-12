import asyncio
from typing import Dict, Optional

from cook_fsm_backend.domain.session import Session


class SessionStore:
    """
    In-memory, thread-safe store for cooking FSM sessions.
    Provides CRUD operations guarded by an asyncio.Lock.
    """
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._sessions: Dict[str, Session] = {}

    async def create(self, session_id: str, session: Session) -> Session:
        """
        Create a new session under the given ID.
        Raises KeyError if the session_id already exists.
        """
        async with self._lock:
            if session_id in self._sessions:
                raise KeyError(f"Session '{session_id}' already exists")
            self._sessions[session_id] = session
            return session

    async def get(self, session_id: str) -> Optional[Session]:
        """
        Retrieve the session for the given ID.
        Returns None if not found.
        """
        async with self._lock:
            return self._sessions.get(session_id)

    async def update(self, session_id: str, session: Session) -> Session:
        """
        Update an existing session.
        Raises KeyError if session_id does not exist.
        """
        async with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session '{session_id}' not found")
            self._sessions[session_id] = session
            return session

    async def delete(self, session_id: str) -> None:
        """
        Delete the session with the given ID.
        Raises KeyError if session_id does not exist.
        """
        async with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session '{session_id}' not found")
            del self._sessions[session_id]

    async def state_of(self, session_id: str) -> Session:
        """
        Alias for get with strict existence requirement.
        Raises KeyError if session_id does not exist.
        """
        async with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session '{session_id}' not found")
            return self._sessions[session_id]

__all__ = ['SessionStore']

