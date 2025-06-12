# cook_fsm_backend/api.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from cook_fsm_backend.events import Event
from cook_fsm_backend.store import SessionStore
from cook_fsm_backend.fsm import CookFSM
from cook_fsm_backend.domain.session import Session

# Dependency: singleton store
_store: Optional[SessionStore] = None

def get_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store

# Dependency: singleton FSM
_fsm: Optional[CookFSM] = None

def get_fsm(store: SessionStore = Depends(get_store)) -> CookFSM:
    global _fsm
    if _fsm is None:
        _fsm = CookFSM(store)
    return _fsm

app = FastAPI()

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/event", response_model=Session)
async def post_event(event: Event, fsm: CookFSM = Depends(get_fsm), store: SessionStore = Depends(get_store)):
    """
    Receive an FSM event, dispatch it, and return the updated session state.
    """
    try:
        new_state = await fsm.dispatch(event)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    updated = await store.get(event.session_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Session disappeared after dispatch")
    return updated

# Expose app in package
# cook_fsm_backend/__init__.py
# Add the following line to expose the FastAPI app for Uvicorn:
#
#     from cook_fsm_backend.api import app  # noqa: F401

