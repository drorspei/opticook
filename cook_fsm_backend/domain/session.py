from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

from cook_fsm_backend.domain.instruction import Instruction
from cook_fsm_backend.domain.chef_task import ChefTask

@dataclass
class Session:
    recipe: List[Instruction]
    chef_tasks: Dict[str, List[ChefTask]] = field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

__all__ = ["Session"]
