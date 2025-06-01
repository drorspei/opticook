from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class CookingInstruction:
    index: int
    task: str
    duration: int
    attention: bool
    dependencies: List[int] = ()

@dataclass
class ChefTask:
    instruction_index: int
    when_started: Optional[int]=None
    when_dismissed: Optional[int]=None

@dataclass
class Session:
    recipe: List[CookingInstruction]
    chef_tasks: Dict[str, List[ChefTask]]

