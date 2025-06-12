from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Instruction:
    index: int
    task: str
    duration: int
    attention: bool

    class Config:
        """Pydantic config for dataclass validation."""
        arbitrary_types_allowed = True

__all__ = ["Instruction"]
