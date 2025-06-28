from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dataclasses import asdict
from typing import List, Dict, Optional

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations import active_ai_done, refresh_session

app = FastAPI()

# In-memory recipe store: map recipe_id to raw recipe definitions
RECIPE_STORE: Dict[str, List[Dict]] = {
    "example_recipe": [
        {"index": 0, "aiList": [
            {"attention": True, "duration_seconds": 60, "description": "chop onions"},
            {"attention": False, "duration_seconds": 120, "description": "simmer"}
        ], "dependencies": []}
    ],
    "multi_task_recipe": [
        {"index": 0, "aiList": [
            {"attention": True, "duration_seconds": 60, "description": "chop onions"},
            {"attention": False, "duration_seconds": 120, "description": "simmer onions"}
        ], "dependencies": []},
        {"index": 1, "aiList": [
            {"attention": True, "duration_seconds": 90, "description": "chop carrots"},
            {"attention": False, "duration_seconds": 180, "description": "boil carrots"}
        ], "dependencies": []}
    ]
}

# Global session holder
_current_session: Optional[Session] = None

# Pydantic models
class StartPayload(BaseModel):
    recipe_id: str
    chefs: List[str]

class DonePayload(BaseModel):
    chef: str
    instruction_index: int
    timestamp_seconds: float = Field(..., description="Epoch seconds from client")

class RefreshPayload(BaseModel):
    timestamp_seconds: float = Field(..., description="Epoch seconds from client")

@app.get("/api/v1/session/current/recipes", response_model=List[str])
def list_recipes():
    return list(RECIPE_STORE.keys())

@app.get("/api/v1/session/current/recipes/{recipe_id}")
def get_recipe(recipe_id: str):
    raw = RECIPE_STORE.get(recipe_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Unknown recipe_id")
    return JSONResponse(content=raw)

@app.post("/api/v1/session/current/start")
def start_session(payload: StartPayload):
    global _current_session
    if _current_session is not None:
        raise HTTPException(status_code=409, detail="Session already running")
    raw_recipe = RECIPE_STORE.get(payload.recipe_id)
    if raw_recipe is None:
        raise HTTPException(status_code=404, detail="Unknown recipe_id")
    # Build CookingInstruction list with quanta durations
    cis: List[CookingInstruction] = []
    for item in raw_recipe:
        ais = [
            AtomicInstruction(
                ai["attention"],
                time_in_units(ai["duration_seconds"]),
                ai["description"],
            )
            for ai in item["aiList"]
        ]
        cis.append(CookingInstruction(item["index"], ais, item.get("dependencies", [])))
    # Initialize chefs
    chefs_data = {name: Chef(name, heartbeat=None) for name in payload.chefs}
    cooking_map = {name: {} for name in payload.chefs}
    done_tasks: Dict[int, DoneTask] = {}
    _current_session = Session(cis, chefs_data, cooking_map, done_tasks)
    return asdict(_current_session)

@app.post("/api/v1/session/current/done")
def mark_done(payload: DonePayload):
    global _current_session
    if _current_session is None:
        raise HTTPException(status_code=404, detail="No active session")
    # Convert client timestamp to quanta
    now_quanta = time_in_units(payload.timestamp_seconds)
    try:
        new_session = active_ai_done(
            _current_session, payload.chef, payload.instruction_index, now_quanta
        )
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _current_session = new_session
    return asdict(_current_session)

@app.post("/api/v1/session/current/refresh")
def refresh(payload: RefreshPayload):
    global _current_session
    if _current_session is None:
        raise HTTPException(status_code=404, detail="No active session")
    now_quanta = time_in_units(payload.timestamp_seconds)
    _current_session = refresh_session(_current_session, now_quanta)
    return asdict(_current_session)

@app.get("/api/v1/session/current/state")
def get_state():
    if _current_session is None:
        raise HTTPException(status_code=404, detail="No active session")
    return asdict(_current_session)

@app.post("/api/v1/session/current/reset")
def reset_session():
    global _current_session
    _current_session = None
    return {}

