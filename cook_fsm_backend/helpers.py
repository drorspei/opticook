from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Optional

from cook_fsm_backend.domain.session import Session
from cook_fsm_backend.domain.chef_task import ChefTask
from cook_fsm_backend.domain.instruction import Instruction
from cook_fsm_backend.sat import Assignment, solver  # SAT definitions to be provided separately

# Note: Assignment, solver, cooking_time_unit are expected to be available from the SAT module
from cook_fsm_backend.sat import Assignment, solver  # adjust import path as needed


def next_unstarted_task(session: Session, chef: str) -> int:
    """
    Return the index of the first unstarted task for `chef`, or the length
    of their task list if all tasks have started.
    """
    return (
        [i for i, task in enumerate(session.chef_tasks[chef]) if task.when_started is None]
        + [len(session.chef_tasks[chef])]
    )[0]


def remaining_recipe_indices(session: Session) -> List[int]:
    """
    Collect the indices of all unstarted instructions across chefs.
    """
    return [
        task.instruction_index
        for tasks in (
            session.chef_tasks[chef][next_unstarted_task(session, chef):]
            for chef in session.chef_tasks
        )
        for task in tasks
    ]


def advance_task_for_chef(
    session: Session,
    chef: str,
    now: datetime
) -> Session:
    """
    Advance the next unstarted task for the given chef, marking it as started at `now`.
    """
    i = next_unstarted_task(session, chef)
    if i == len(session.chef_tasks[chef]):
        return session

    # Copy existing tasks for other chefs
    chef_tasks: Dict[str, List[ChefTask]] = {
        c: t for c, t in session.chef_tasks.items() if c != chef
    }
    # Build updated list for this chef
    updated = (
        session.chef_tasks[chef][:i]
        + [
            ChefTask(
                instruction_index=session.chef_tasks[chef][i].instruction_index,
                when_started=now
            )
        ]
        + session.chef_tasks[chef][i + 1:]
    )
    chef_tasks[chef] = updated
    return Session(session.recipe, chef_tasks)


def solve_remaining_session(
    session: Session,
    remaining_indices: List[int],
    timeout: int
) -> Dict[str, List[ChefTask]]:
    """
    Schedule all remaining instructions via SAT solver; return new ChefTask lists per chef.
    """
    chefs_list = list(session.chef_tasks.keys())
    recipe = session.recipe

    # 1. Filter future instructions
    remaining_instructions = [instr for instr in recipe if instr.index in remaining_indices]
    vertices = [instr.index for instr in remaining_instructions]
    vertex_set = set(vertices)

    # 2. Build edges and time bound
    edges: List[tuple[int, int]] = []
    time_ub = 0
    for instr in remaining_instructions:
        if instr.attention:
            time_ub += instr.duration
        for dep in getattr(instr, 'dependencies', []):
            if dep in vertex_set:
                edges.append((dep, instr.index))

    # 3. Build assignment map
    assignment_map = {
        instr.index: Assignment(instr.attention, instr.duration)
        for instr in remaining_instructions
    }

    # 4. Invoke solver
    chosen = solver(chefs_list, vertices, edges, assignment_map, timeout, time_ub)
    chosen.sort(key=lambda trip: trip[1])

    # 5. Format output
    return {
        chef: [ChefTask(instruction_index=trip[2]) for trip in chosen if trip[0] == chef]
        for chef in chefs_list
    }


def recompile_session(
    session: Session
) -> Session:
    """
    Recompile a fresh session state for all remaining instructions.
    """
    remaining_indices = remaining_recipe_indices(session)
    future = solve_remaining_session(session, remaining_indices, timeout=30)
    return Session(
        session.recipe,
        {
            chef: (
                session.chef_tasks[chef][: next_unstarted_task(session, chef)]
                + future.get(chef, [])
            )
            for chef in session.chef_tasks
        },
    )


def new_chef_joined(
    session: Session,
    chef: str,
    now: datetime
) -> Session:
    """
    Initialize schedule for a new chef joining at `now`.
    """
    if chef in session.chef_tasks:
        return session

    tasks_plus = {**session.chef_tasks, chef: []}
    new_session = Session(session.recipe, tasks_plus)
    return advance_task_for_chef(recompile_session(new_session), chef, now)


def dismiss_timer(
    session: Session,
    instr_idx: int,
    now: datetime
) -> Session:
    """
    Dismiss the timer for instruction `instr_idx` if expired and not already dismissed.
    """
    # Find matching task
    tasks = [
        task
        for tasks in session.chef_tasks.values()
        for task in tasks
        if task.instruction_index == instr_idx
    ]
    if tasks:
        task = tasks[0]
        if task.when_started is None:
            raise ValueError(f"Instruction {instr_idx} hasn't started!")
        if task.when_dismissed is not None:
            raise ValueError(f"Instruction {instr_idx} already dismissed!")

        chef = next(ch for ch, ts in session.chef_tasks.items() if task in ts)
        idx = session.chef_tasks[chef].index(task)
        updated = (
            session.chef_tasks[chef][:idx]
            + [ChefTask(instr_idx, task.when_started, now)]
            + session.chef_tasks[chef][idx + 1:]
        )
        tasks_map = {**{c: t for c, t in session.chef_tasks.items() if c != chef}, chef: updated}
        return Session(session.recipe, tasks_map)

    raise ValueError(f"Instruction {instr_idx} not found")


def active_timers(
    session: Session,
    chef: str
) -> List[ChefTask]:
    """
    Return active, non-attention timers for `chef`.
    """
    return [
        task
        for task in session.chef_tasks[chef]
        if not session.recipe[task.instruction_index].attention
        and task.when_started is not None
        and task.when_dismissed is None
    ]


def reset_active_task(
    session: Session,
    instr_idx: int
) -> Session:
    """
    Reset a running task `instr_idx` back to unstarted.
    """
    tasks = [
        task
        for tasks in session.chef_tasks.values()
        for task in tasks
        if task.instruction_index == instr_idx
    ]
    if not tasks:
        return session
    task = tasks[0]
    if task.when_started is None or task.when_dismissed is not None:
        return session

    chef = next(ch for ch, ts in session.chef_tasks.items() if task in ts)
    idx = session.chef_tasks[chef].index(task)
    updated = (
        session.chef_tasks[chef][:idx]
        + [ChefTask(instr_idx)]
        + session.chef_tasks[chef][idx + 1:]
    )
    tasks_map = {**{c: t for c, t in session.chef_tasks.items() if c != chef}, chef: updated}
    return Session(session.recipe, tasks_map)


def chef_leave(
    session: Session,
    chef: str
) -> Session:
    """
    Remove `chef` from session, reassign tasks, and recompile.
    """
    if chef not in session.chef_tasks:
        return session

    active_idx = [task.instruction_index for task in active_timers(session, chef)]
    tasks_map = {ch: t for ch, t in session.chef_tasks.items() if ch != chef}
    if tasks_map:
        first = next(iter(tasks_map))
        tasks_map[first] += session.chef_tasks[chef]
        for idx in active_idx:
            session = Session(session.recipe, tasks_map)
            session = reset_active_task(session, idx)
    else:
        session = Session(session.recipe, tasks_map)

    return recompile_session(session)


def start_low_attention_task(
    session: Session,
    chef: str,
    now: datetime
) -> Session:
    """
    Start the next low-attention (attention=False) task for `chef` at `now`.
    """
    tasks = session.chef_tasks.get(chef, [])
    for idx, task in enumerate(tasks):
        instr = session.recipe[task.instruction_index]
        if not instr.attention and task.when_started is None:
            updated_task = ChefTask(task.instruction_index, when_started=now)
            new_tasks = tasks[:idx] + [updated_task] + tasks[idx+1:]
            chef_tasks = {c: t for c, t in session.chef_tasks.items() if c != chef}
            chef_tasks[chef] = new_tasks
            return Session(session.recipe, chef_tasks)
    return session



def finish_attention_task(
    session: Session,
    chef: str,
    now: datetime
) -> Session:
    """
    Finish the active attention-required (attention=True) task for `chef` at `now`.
    """
    tasks = session.chef_tasks.get(chef, [])
    for idx, task in enumerate(tasks):
        instr = session.recipe[task.instruction_index]
        if instr.attention and task.when_started is not None and task.when_dismissed is None:
            new_task = ChefTask(task.instruction_index, when_started=task.when_started, when_dismissed=now)
            new_tasks = tasks[:idx] + [new_task] + tasks[idx+1:]
            chef_tasks = {c: t for c, t in session.chef_tasks.items() if c != chef}
            chef_tasks[chef] = new_tasks
            return Session(session.recipe, chef_tasks)
    return session

def undo_timer_pressed(
    session: Session,
    chef_id: str,
    now: datetime
) -> Session:
    """
    Reset the latest active timer for `chef_id` to `now`, leaving `when_dismissed` as None.
    No-op if no active timers.
    """
    timers = active_timers(session, chef_id)
    if not timers:
        return session
    # Find the most recently started timer
    latest = max(timers, key=lambda t: t.when_started)
    tasks = session.chef_tasks.get(chef_id, [])
    idx = tasks.index(latest)
    # Reset its start time
    new_task = ChefTask(latest.instruction_index, when_started=now)
    new_tasks = tasks[:idx] + [new_task] + tasks[idx+1:]
    # Build updated map
    updated_map = {c: t for c, t in session.chef_tasks.items() if c != chef_id}
    updated_map[chef_id] = new_tasks
    return Session(session.recipe, updated_map)



__all__ = [
    "next_unstarted_task",
    "remaining_recipe_indices",
    "advance_task_for_chef",
    "solve_remaining_session",
    "recompile_session",
    "new_chef_joined",
    "active_timers",
    "reset_active_task",
    "chef_leave",
    "start_low_attention_task",
    "finish_attention_task",
    "dismiss_timer",
    "undo_timer_pressed",
]
