#!/usr/bin/env python
# coding: utf-8

"""
Wrapper around computations_optimized.py that handles time in seconds externally
but converts to quanta (30-second units) internally for SAT solving.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, replace
import copy

from data_models import (
    Chef, AtomicInstruction, CookingInstruction, ActiveTask, DoneTask, Session,
    cooking_time_unit, time_in_units
)
from computations_optimized import (
    active_ai_done as _active_ai_done_quanta,
    refresh_session as _refresh_session_quanta
)


def _convert_active_task_to_seconds(task: ActiveTask) -> ActiveTask:
    """Convert ActiveTask from quanta to seconds."""
    if task.start_time is None:
        return task
    return replace(task, start_time=task.start_time * cooking_time_unit)


def _convert_active_task_to_quanta(task: ActiveTask) -> ActiveTask:
    """Convert ActiveTask from seconds to quanta."""
    if task.start_time is None:
        return task
    return replace(task, start_time=time_in_units(task.start_time))


def _convert_done_task_to_seconds(done_task: DoneTask) -> DoneTask:
    """Convert DoneTask from quanta to seconds."""
    time_data_seconds = [(start * cooking_time_unit, end * cooking_time_unit) 
                         for start, end in done_task.time_data]
    return replace(done_task, time_data=time_data_seconds)


def _convert_done_task_to_quanta(done_task: DoneTask) -> DoneTask:
    """Convert DoneTask from seconds to quanta."""
    time_data_quanta = [(time_in_units(start), time_in_units(end)) 
                        for start, end in done_task.time_data]
    return replace(done_task, time_data=time_data_quanta)


def _convert_atomic_instruction_to_seconds(ai: AtomicInstruction) -> AtomicInstruction:
    """Convert AtomicInstruction duration from quanta to seconds."""
    return replace(ai, duration=ai.duration * cooking_time_unit)


def _convert_atomic_instruction_to_quanta(ai: AtomicInstruction) -> AtomicInstruction:
    """Convert AtomicInstruction duration from seconds to quanta."""
    return replace(ai, duration=time_in_units(ai.duration))


def _convert_cooking_instruction_to_seconds(ci: CookingInstruction) -> CookingInstruction:
    """Convert CookingInstruction from quanta to seconds."""
    ai_list_seconds = [_convert_atomic_instruction_to_seconds(ai) for ai in ci.aiList]
    return replace(ci, aiList=ai_list_seconds)


def _convert_cooking_instruction_to_quanta(ci: CookingInstruction) -> CookingInstruction:
    """Convert CookingInstruction from seconds to quanta."""
    ai_list_quanta = [_convert_atomic_instruction_to_quanta(ai) for ai in ci.aiList]
    return replace(ci, aiList=ai_list_quanta)


def _convert_session_to_seconds(session: Session) -> Session:
    """Convert Session from quanta to seconds."""
    recipe_seconds = [_convert_cooking_instruction_to_seconds(ci) for ci in session.recipe]
    
    cooking_map_seconds = {}
    for chef, tasks in session.cooking_map.items():
        cooking_map_seconds[chef] = {
            idx: _convert_active_task_to_seconds(task)
            for idx, task in tasks.items()
        }
    
    done_tasks_seconds = {
        idx: _convert_done_task_to_seconds(done_task)
        for idx, done_task in session.done_tasks.items()
    }
    
    return replace(
        session,
        recipe=recipe_seconds,
        cooking_map=cooking_map_seconds,
        done_tasks=done_tasks_seconds
    )


def _convert_session_to_quanta(session: Session) -> Session:
    """Convert Session from seconds to quanta."""
    recipe_quanta = [_convert_cooking_instruction_to_quanta(ci) for ci in session.recipe]
    
    cooking_map_quanta = {}
    for chef, tasks in session.cooking_map.items():
        cooking_map_quanta[chef] = {
            idx: _convert_active_task_to_quanta(task)
            for idx, task in tasks.items()
        }
    
    done_tasks_quanta = {
        idx: _convert_done_task_to_quanta(done_task)
        for idx, done_task in session.done_tasks.items()
    }
    
    return replace(
        session,
        recipe=recipe_quanta,
        cooking_map=cooking_map_quanta,
        done_tasks=done_tasks_quanta
    )


def active_ai_done(session: Session, chef_name: str, instruction_index: int, now_seconds: float) -> Session:
    """
    Mark an active AI as done. Time is in seconds.
    Internally converts to quanta for SAT solving.
    """
    # Convert session to quanta
    session_quanta = _convert_session_to_quanta(session)
    now_quanta = time_in_units(now_seconds)
    
    # Call the original function with quanta
    result_quanta = _active_ai_done_quanta(session_quanta, chef_name, instruction_index, now_quanta)
    
    # Convert back to seconds
    return _convert_session_to_seconds(result_quanta)


def refresh_session(session: Session, now_seconds: float) -> Session:
    """
    Refresh session state. Time is in seconds.
    Internally converts to quanta for SAT solving.
    """
    # Convert session to quanta
    session_quanta = _convert_session_to_quanta(session)
    now_quanta = time_in_units(now_seconds)
    
    # Call the original function with quanta
    result_quanta = _refresh_session_quanta(session_quanta, now_quanta)
    
    # Convert back to seconds
    return _convert_session_to_seconds(result_quanta)