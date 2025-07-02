from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dataclasses import asdict
from typing import List, Dict, Optional, Tuple
import csv
import os
import pickle

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, DoneTask
from computations_seconds import active_ai_done, refresh_session

app = FastAPI()

# In-memory recipe store: map recipe_id to raw recipe definitions
RECIPE_STORE: Dict[str, List[Dict]] = {
    "example_recipe": [
        {"index": 0, "aiList": [
            {"attention": True, "duration_seconds": 60, "description": "chop onions"},
            {"attention": False, "duration_seconds": 30, "description": "simmer"}
        ], "dependencies": []}
    ],
    "multi_task_recipe": [
        {"index": 0, "aiList": [
            {"attention": True, "duration_seconds": 60, "description": "chop onions"},
            {"attention": False, "duration_seconds": 30, "description": "simmer onions"}
        ], "dependencies": []},
        {"index": 1, "aiList": [
            {"attention": True, "duration_seconds": 90, "description": "chop carrots"},
            {"attention": False, "duration_seconds": 30, "description": "boil carrots"}
        ], "dependencies": []}
    ]
}

def parse_cheesecake_recipe() -> List[Dict]:
    """Parse the cheesecake recipe from CSV format and convert to RECIPE_STORE format."""
    # Keywords that indicate a task doesn't require attention
    no_attention_keywords = ["bake", "preheat", "soften", "put out", "room temp", "cool", "simmer", "refri"]

    # Read the CSV file
    recipe_path = os.path.join(os.path.dirname(__file__), "cheesecake2.txt")
    tasks = []

    with open(recipe_path, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if row['index']:  # Skip empty rows
                task = {
                    'index': int(row['index']),
                    'title': row['title'],
                    'time': int(row['time']),
                    'child': int(row['child']) if row['child'] != '-1' else None
                }
                tasks.append(task)

    # Convert child-to-parent relationships to parent-to-child dependencies
    dependencies = {}
    for task in tasks:
        if task['child'] is not None:
            # Current task is a parent of task['child']
            child_idx = task['child']
            if child_idx not in dependencies:
                dependencies[child_idx] = []
            dependencies[child_idx].append(task['index'])

    # Convert to RECIPE_STORE format
    recipe = []
    for task in tasks:
        # Determine if task requires attention based on keywords
        title_lower = task['title'].lower()
        requires_attention = not any(keyword in title_lower for keyword in no_attention_keywords)

        # Create the instruction with a single AI
        instruction = {
            "index": task['index'],
            "aiList": [{
                "attention": requires_attention,
                "duration_seconds": task['time'],
                "description": task['title']
            }],
            "dependencies": dependencies.get(task['index'], [])
        }
        recipe.append(instruction)

    return recipe

# Add the parsed cheesecake recipe to RECIPE_STORE
RECIPE_STORE["cheesecake"] = parse_cheesecake_recipe()

# Load added recipes from pickle file
ADDED_RECIPES_FILE = "added_recipes.pkl"

def load_added_recipes():
    if os.path.exists(ADDED_RECIPES_FILE):
        try:
            with open(ADDED_RECIPES_FILE, 'rb') as f:
                added_recipes: List[Tuple[str, List[Dict]]] = pickle.load(f)
                for recipe_name, recipe_data in added_recipes:
                    RECIPE_STORE[recipe_name] = recipe_data
        except Exception as e:
            print(f"Error loading added recipes: {e}")

def save_added_recipes():
    added_recipes = []
    for recipe_id, recipe_data in RECIPE_STORE.items():
        if recipe_id not in ["example_recipe", "multi_task_recipe", "cheesecake"]:
            added_recipes.append((recipe_id, recipe_data))

    try:
        with open(ADDED_RECIPES_FILE, 'wb') as f:
            pickle.dump(added_recipes, f)
    except Exception as e:
        print(f"Error saving added recipes: {e}")
        raise

load_added_recipes()

# Global session holder
_current_session: Optional[Session] = None
_current_recipe_id: Optional[str] = None

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

class AtomicInstructionPayload(BaseModel):
    description: str
    attention: bool
    duration_seconds: int

class CookingInstructionPayload(BaseModel):
    aiList: List[AtomicInstructionPayload]
    dependencies: List[int]

class AddRecipePayload(BaseModel):
    recipe_name: str
    instructions: List[CookingInstructionPayload]

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
    global _current_session, _current_recipe_id
    if _current_session is not None:
        raise HTTPException(status_code=409, detail="Session already running")
    raw_recipe = RECIPE_STORE.get(payload.recipe_id)
    if raw_recipe is None:
        raise HTTPException(status_code=404, detail="Unknown recipe_id")
    _current_recipe_id = payload.recipe_id
    # Build CookingInstruction list with durations in seconds
    cis: List[CookingInstruction] = []
    for item in raw_recipe:
        ais = [
            AtomicInstruction(
                ai["attention"],
                ai["duration_seconds"],  # Keep in seconds
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
    print(f"[DEBUG] mark_done API: chef={payload.chef}, instruction_index={payload.instruction_index}, timestamp_seconds={payload.timestamp_seconds}")
    try:
        new_session = active_ai_done(
            _current_session, payload.chef, payload.instruction_index, payload.timestamp_seconds
        )
        print(f"[DEBUG] mark_done API: session updated successfully")
        _current_session = new_session
        return asdict(_current_session)
    except KeyError as e:
        print(f"[DEBUG] mark_done API: KeyError - {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[DEBUG] mark_done API: Exception - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/session/current/refresh")
def refresh(payload: RefreshPayload):
    global _current_session
    if _current_session is None:
        raise HTTPException(status_code=404, detail="No active session")
    print(f"[DEBUG] refresh API: timestamp_seconds={payload.timestamp_seconds}")
    _current_session = refresh_session(_current_session, payload.timestamp_seconds)
    return asdict(_current_session)

@app.get("/api/v1/session/current/state")
def get_state():
    if _current_session is None:
        raise HTTPException(status_code=404, detail="No active session")
    return asdict(_current_session)

@app.post("/api/v1/session/current/reset")
def reset_session():
    global _current_session, _current_recipe_id
    _current_session = None
    _current_recipe_id = None
    return {}

@app.post("/api/v1/recipes/add")
def add_recipe(payload: AddRecipePayload):
    if payload.recipe_name in RECIPE_STORE:
        raise HTTPException(status_code=409, detail="Recipe name already exists")

    recipe_data = []
    for index, instruction in enumerate(payload.instructions):
        ai_list = []
        for ai in instruction.aiList:
            ai_list.append({
                "attention": ai.attention,
                "duration_seconds": ai.duration_seconds,
                "description": ai.description
            })

        recipe_data.append({
            "index": index,
            "aiList": ai_list,
            "dependencies": instruction.dependencies
        })

    RECIPE_STORE[payload.recipe_name] = recipe_data
    save_added_recipes()

    return {"message": "Recipe added successfully", "recipe_id": payload.recipe_name}

@app.put("/api/v1/recipes/{recipe_id}")
def update_recipe(recipe_id: str, payload: AddRecipePayload):
    global _current_recipe_id

    if recipe_id not in RECIPE_STORE:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Prevent editing built-in recipes
    built_in_recipes = ["example_recipe", "multi_task_recipe", "cheesecake"]
    if recipe_id in built_in_recipes:
        raise HTTPException(status_code=403, detail="Cannot edit built-in recipes")

    # Check if there's an active session using this recipe
    if _current_session and _current_recipe_id == recipe_id:
        raise HTTPException(status_code=409, detail="Cannot update recipe while it's being used in an active session")

    # Check if renaming to a different name
    new_recipe_name = payload.recipe_name
    if new_recipe_name != recipe_id:
        # Check if the new name already exists
        if new_recipe_name in RECIPE_STORE:
            raise HTTPException(status_code=409, detail="Recipe name already exists")

        # If renaming, we need to update the current recipe ID if it's in use
        if _current_recipe_id == recipe_id:
            _current_recipe_id = new_recipe_name

    recipe_data = []
    for index, instruction in enumerate(payload.instructions):
        ai_list = []
        for ai in instruction.aiList:
            ai_list.append({
                "attention": ai.attention,
                "duration_seconds": ai.duration_seconds,
                "description": ai.description
            })

        recipe_data.append({
            "index": index,
            "aiList": ai_list,
            "dependencies": instruction.dependencies
        })

    # If renaming, delete the old entry and create new one
    if new_recipe_name != recipe_id:
        del RECIPE_STORE[recipe_id]
        RECIPE_STORE[new_recipe_name] = recipe_data
    else:
        RECIPE_STORE[recipe_id] = recipe_data

    save_added_recipes()

    return {"message": "Recipe updated successfully", "recipe_id": new_recipe_name}

@app.delete("/api/v1/recipes/{recipe_id}")
def delete_recipe(recipe_id: str):
    global _current_recipe_id

    if recipe_id not in RECIPE_STORE:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Prevent deleting built-in recipes
    built_in_recipes = ["example_recipe", "multi_task_recipe", "cheesecake"]
    if recipe_id in built_in_recipes:
        raise HTTPException(status_code=403, detail="Cannot delete built-in recipes")

    # Check if there's an active session using this recipe
    if _current_session and _current_recipe_id == recipe_id:
        raise HTTPException(status_code=409, detail="Cannot delete recipe while it's being used in an active session")

    # Delete the recipe
    del RECIPE_STORE[recipe_id]
    save_added_recipes()

    return {"message": "Recipe deleted successfully"}
