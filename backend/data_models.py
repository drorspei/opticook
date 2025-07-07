from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from copy import deepcopy

cooking_time_unit = 30  # seconds per quantum
assert 60 % cooking_time_unit == 0

def time_in_units(seconds: float) -> int:
    """Return ceil(seconds / 30)."""
    return int(seconds / cooking_time_unit) + int(bool(seconds % cooking_time_unit))

@dataclass(frozen=True)
class Chef:  # information about a chef
    name: str
    addr: Optional[str] = None
    heartbeat: Optional[int] = None  # last heartbeat (epoch seconds)
    disconnected: bool = False

@dataclass(frozen=True)
class AtomicInstruction:  # aka "ai"
    attention: bool
    duration: int  # seconds (original recipe time for display, converted to quanta for SAT)
    description: str

@dataclass(frozen=True)
class CookingInstruction:
    index: int
    aiList: List[AtomicInstruction]
    dependencies: List[int]

@dataclass(frozen=True)
class ActiveTask:  # Information about an atomic instruction currently handled
    instruction_index: int
    ai_index: int
    start_time: Optional[int] = None

@dataclass(frozen=True)
class DoneTask:  # information about a finished instruction
    instruction_index: int
    chef_name: str
    time_data: List[Tuple[int, int]]  # (start, end) per AI

@dataclass(frozen=True)
class SATSchedule:
    chef_to_tasks: Dict[str, List[int]]  # chef -> ordered list of instruction indices

@dataclass(frozen=True)
class Session:
    recipe: List[CookingInstruction]
    chefs_data: Dict[str, Chef]
    cooking_map: Dict[str, Dict[int, ActiveTask]]
    done_tasks: Dict[int, DoneTask]
    sat_schedule: Optional[SATSchedule] = None

# Helper to convert all durations in a Session or recipe from seconds to quanta (for SAT solving)
def session_with_quanta_durations(session: Session) -> Session:
    """Return a deep copy of the session with all AI durations converted from seconds to quanta."""
    session_copy = deepcopy(session)
    new_recipe = []
    for inst in session_copy.recipe:
        new_ai_list = [AtomicInstruction(ai.attention, time_in_units(ai.duration), ai.description) for ai in inst.aiList]
        new_inst = CookingInstruction(inst.index, new_ai_list, inst.dependencies)
        new_recipe.append(new_inst)
    
    # Also convert start_time values in ActiveTask objects from seconds to quanta
    new_cooking_map = {}
    for chef, tasks in session_copy.cooking_map.items():
        new_cooking_map[chef] = {}
        for task_index, task in tasks.items():
            new_start_time = time_in_units(task.start_time) if task.start_time is not None else None
            new_cooking_map[chef][task_index] = ActiveTask(task.instruction_index, task.ai_index, new_start_time)
    
    return Session(new_recipe, session_copy.chefs_data, new_cooking_map, session_copy.done_tasks, session_copy.sat_schedule)

# If you need to convert just a recipe (list of CookingInstruction):
def recipe_with_quanta_durations(recipe: List[CookingInstruction]) -> List[CookingInstruction]:
    new_recipe = []
    for inst in recipe:
        new_ai_list = [AtomicInstruction(ai.attention, time_in_units(ai.duration), ai.description) for ai in inst.aiList]
        new_inst = CookingInstruction(inst.index, new_ai_list, inst.dependencies)
        new_recipe.append(new_inst)
    return new_recipe

