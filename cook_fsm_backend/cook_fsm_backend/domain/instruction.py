from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Instruction:
    index: int
    task: str
    duration: int
    attention: bool

__all__ = ["Instruction"]
