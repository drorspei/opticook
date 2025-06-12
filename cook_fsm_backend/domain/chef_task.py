from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ChefTask:
    instruction_index: int
    when_started: Optional[datetime] = None
    when_dismissed: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True

__all__ = ["ChefTask"]
