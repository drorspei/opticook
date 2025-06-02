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
            # Assuming default values for recipe and chef_tasks
            self._session = Session(recipe=[], chef_tasks=[])
        return self._session

    def reset_session(self) -> None:
        """
        Reset the current session, creating a new session instance.
        """
        self._session = Session()

# Create a global instance of SessionManager
session_manager = SessionManager()

def allocate_tasks(session: Session) -> None:
    """
    Allocate tasks to chefs in the session. Attention tasks are assigned
    round-robin, while passive tasks are added to each chef's passive list.

    Args:
        session (Session): The session containing the recipe and chefs.
    """
    chefs = session.chefs
    num_chefs = len(chefs)
    attention_index = 0

    for task in session.recipe.tasks:
        if task.attention:
            # Assign attention tasks round-robin
            chefs[attention_index % num_chefs].attention_tasks.append(task)
            attention_index += 1
        else:
            # Add passive tasks to every chef's passive list
            for chef in chefs:
                chef.passive_tasks.append(task)
