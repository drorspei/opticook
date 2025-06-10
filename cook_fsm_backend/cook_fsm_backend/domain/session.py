from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from .instruction import Instruction
from .chef_task import ChefTask

@dataclass
class Session:
    recipe: List[Instruction] = field(default_factory=list)
    chef_tasks: Dict[str, List[ChefTask]] = field(default_factory=dict)

__all__ = ["Session"]
