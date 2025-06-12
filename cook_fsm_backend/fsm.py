import json
from types import SimpleNamespace
from transitions import Machine

import asyncio
from cook_fsm_backend.events import Event
from cook_fsm_backend.store import SessionStore
import cook_fsm_backend.helpers as helpers

class CookFSM:
    def __init__(self, store: SessionStore, spec_path: str = None) -> None:
        self.store = store
        if spec_path is None:
            spec_path = "cook_fsm_backend/fsm_spec.json"
        with open(spec_path, "r") as f:
            spec = json.load(f)
        self.session_spec = spec["sessionMachine"]
        self.chef_spec = spec["chefSubMachine"]

    async def dispatch(self, event: Event) -> str:
        session = await self.store.get(event.session_id)
        if session is None:
            raise KeyError(f"Session '{event.session_id}' not found")

        model = SimpleNamespace(
            session=session,
            chef_id=event.chef_id,
            instr_idx=event.instr_idx,
            timestamp=event.timestamp,
        )
        # attach all helper functions
        for name in dir(helpers):
            if not name.startswith("_") and callable(getattr(helpers, name)):
                setattr(model, name, getattr(helpers, name))

        # session‐level FSM
        Machine(
            model=model,
            states=self.session_spec["states"],
            transitions=self.session_spec["transitions"],
            initial=self.session_spec.get("initial"),
            auto_transitions=False,
            queued=True,
        )
        # chef‐level submachine
        Machine(
            model=model,
            states=self.chef_spec["states"],
            transitions=self.chef_spec["transitions"],
            name="chef",
            initial=self.chef_spec.get("initial"),
            auto_transitions=False,
            queued=True,
        )

        # fire the event
        trigger = getattr(model, event.name)
        trigger()

        # persist and return new state
        await self.store.update(event.session_id, model.session)
        return model.state
