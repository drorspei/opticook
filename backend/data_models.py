from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

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
class Session:
    recipe: List[CookingInstruction]
    chefs_data: Dict[str, Chef]
    cooking_map: Dict[str, Dict[int, ActiveTask]]
    done_tasks: Dict[int, DoneTask]

