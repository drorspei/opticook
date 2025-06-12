# cook_fsm_backend/events.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Event(BaseModel):
    """
    Representation of an incoming FSM event.
    """
    name: str
    session_id: str
    chef_id: Optional[str] = None
    instr_idx: Optional[int] = None
    timestamp: datetime


# cook_fsm_backend/fsm.py
import json
from types import SimpleNamespace
from transitions import Machine
import asyncio

from cook_fsm_backend.events import Event
from cook_fsm_backend.store import SessionStore
import cook_fsm_backend.helpers as helpers


class CookFSM:
    """
    Coordinates the session- and chef-level state machines based on JSON specs.
    """
    def __init__(self, store: SessionStore, spec_path: str = None) -> None:
        self.store = store
        # Load FSM specification
        if spec_path is None:
            spec_path = "cook_fsm_backend/fsm_spec.json"
        with open(spec_path, "r") as f:
            spec = json.load(f)
        self.session_spec = spec["sessionMachine"]
        self.chef_spec = spec["chefSubMachine"]

    async def dispatch(self, event: Event) -> str:
        """
        Handle an incoming Event:
        - Load Session
        - Build FSM(s) with initial state = session.metadata.state (or default)
        - Fire event
        - Persist new Session
        - Return new state
        """
        # 1. Load session
        session = await self.store.get(event.session_id)
        if session is None:
            raise KeyError(f"Session '{event.session_id}' not found")

        # 2. Prepare model
        model = SimpleNamespace()
        model.session = session
        model.chef_id = event.chef_id
        model.instr_idx = event.instr_idx
        model.timestamp = event.timestamp

        # 3. Attach helper functions to model
        for name in dir(helpers):
            if not name.startswith("_") and callable(getattr(helpers, name)):
                setattr(model, name, getattr(helpers, name))

        # 4. Build session-level FSM
        session_machine = Machine(
            model=model,
            states=self.session_spec["states"],
            transitions=self.session_spec["transitions"],
            initial=self.session_spec.get("initial"),
            auto_transitions=False,
            queued=True
        )

        # 5. Build chef-level submachine as an additional machine
        Machine(
            model=model,
            states=self.chef_spec["states"],
            transitions=self.chef_spec["transitions"],
            name="chef",
            initial=self.chef_spec.get("initial"),
            auto_transitions=False,
            queued=True
        )

        # 6. Fire the event trigger
        trigger = getattr(model, event.name)
        # Call with any relevant args (e.g., session, chef_id, instr_idx, timestamp)
        trigger()

        # 7. Persist updated session
        updated = model.session
        await self.store.update(event.session_id, updated)

        # 8. Return the new global state
        return model.state


