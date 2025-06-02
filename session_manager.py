from typing import Optional
from cooking.models import Session

class SessionManager:
    """
    A singleton class to manage a single global Session instance.
    """

    _instance: Optional['SessionManager'] = None
    _session: Optional[Session] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
        return cls._instance

    def get_session(self) -> Session:
        """
        Retrieve the current session. If no session exists, create a new one.

        Returns:
            Session: The current session instance.
        """
        if self._session is None:
            self._session = Session()
        return self._session

    def reset_session(self) -> None:
        """
        Reset the current session, creating a new session instance.
        """
        self._session = Session()

# Create a global instance of SessionManager
session_manager = SessionManager()
