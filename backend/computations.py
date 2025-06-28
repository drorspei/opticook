#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import annotations
import copy
import tqdm
from dataclasses import dataclass, replace
from itertools import product
from typing import Dict, List, Optional, Set, Tuple
from pycryptosat import Solver


from data_models import *


# In[8]:


# ---------------------------------------------------------------------------
# Basic queries
# ---------------------------------------------------------------------------

def instruction_cooking_time(inst: CookingInstruction) -> int:
    """Return total quanta for *inst* (sum of its AIs)."""

    return sum(ai.duration for ai in inst.aiList)


def is_in_attention(recipe: List[CookingInstruction], task: ActiveTask) -> bool:
    return recipe[task.instruction_index].aiList[task.ai_index].attention


def time_left_in_attention(recipe: List[CookingInstruction], task: ActiveTask, now: int) -> int:
    if not is_in_attention(recipe, task):
        raise ValueError("Task is not an attention step")
    if task.start_time is None:
        raise ValueError("Task has not started")

    remaining = recipe[task.instruction_index].aiList[task.ai_index].duration - (now - task.start_time)
    return max(0, remaining)


def attention_span(inst: CookingInstruction) -> List[Tuple[int, int]]:
    offset = 0
    spans: List[Tuple[int, int]] = []
    for ai in inst.aiList:
        if ai.attention:
            spans.append((offset, offset + ai.duration))
        offset += ai.duration
    return spans

# ---------------------------------------------------------------------------
# Dependency graph helper
# ---------------------------------------------------------------------------

def cooking_graph(session: Session) -> Tuple[Set[int], List[Tuple[int, int]], int]:
    def is_instruction_completed(inst_index: int) -> bool:
        """Check if an instruction is fully completed (all AIs are done)."""
        if inst_index not in session.done_tasks:
            return False
        # Check if all AIs are done by comparing the number of completed AIs with total AIs
        completed_ais = len(session.done_tasks[inst_index].time_data)
        total_ais = len(session.recipe[inst_index].aiList)
        return completed_ais == total_ais
    
    vertices: Set[int] = {inst.index for inst in session.recipe if not is_instruction_completed(inst.index)}
    edges: List[Tuple[int, int]] = []
    time_ub = 0
    for inst in session.recipe:
        if not is_instruction_completed(inst.index):
            time_ub += instruction_cooking_time(inst)
            for dep in inst.dependencies:
                if not is_instruction_completed(dep):
                    edges.append((dep, inst.index))
    return vertices, edges, time_ub

# ---------------------------------------------------------------------------
# Interval utilities (SAT helpers)
# ---------------------------------------------------------------------------

def forbidden_int_shifts(x: int, left: bool, spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if left:
        return [(s - x, e - x - 1) for s, e in spans]
    return [(s - x + 1, e - x) for s, e in spans]


def forbidden_intervals_shifts(a: List[Tuple[int, int]], b: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for s, e in a:
        out.extend(forbidden_int_shifts(s, True, b))
        out.extend(forbidden_int_shifts(e, False, b))
    return out


def interval_union(spans: List[Tuple[int, int]]) -> Set[int]:
    out: Set[int] = set()
    for s, e in spans:
        out.update(range(s, e + 1))
    return out

# ---------------------------------------------------------------------------
# Active-recipe projection
# ---------------------------------------------------------------------------

def recipe_active_part(session: Session, now: int) -> Dict[int, CookingInstruction]:
    updated: Dict[int, CookingInstruction] = {}
    for task_dict in session.cooking_map.values():
        for task in task_dict.values():
            ai = session.recipe[task.instruction_index].aiList[task.ai_index]
            remaining = max(0, ai.duration - (now - (task.start_time or now)))
            updated_ai = replace(ai, duration=remaining)
            new_ai_list = [updated_ai] + session.recipe[task.instruction_index].aiList[task.ai_index + 1 :]
            updated[task.instruction_index] = replace(session.recipe[task.instruction_index], aiList=new_ai_list)
    return updated

# ---------------------------------------------------------------------------
# Session‑mutation helpers
# ---------------------------------------------------------------------------

def active_ai_done(session: Session, chef: str, inst_index: int, now: int) -> Session:
    if chef not in session.cooking_map or inst_index not in session.cooking_map[chef]:
        raise KeyError("No such active task for chef")

    task = session.cooking_map[chef][inst_index]
    ai_idx = task.ai_index

    # Ensure task.start_time is not None before using it
    if task.start_time is None:
        raise ValueError("Task has not started (start_time is None)")

    # update DoneTask list
    new_done_tasks = copy.deepcopy(session.done_tasks)
    if ai_idx == 0:
        new_done_tasks[inst_index] = DoneTask(inst_index, chef, [(task.start_time, now)])
    else:
        prev = session.done_tasks[inst_index].time_data
        new_done_tasks[inst_index] = DoneTask(inst_index, chef, prev + [(task.start_time, now)])

    # rebuild cooking_map
    new_map = copy.deepcopy(session.cooking_map)
    if ai_idx + 1 < len(session.recipe[inst_index].aiList):
        new_map[chef][inst_index] = ActiveTask(inst_index, ai_idx + 1, now)
    else:
        del new_map[chef][inst_index]
        if not new_map[chef]:
            del new_map[chef]

    return replace(session, cooking_map=new_map, done_tasks=new_done_tasks)


# Internal helper

def _chef_needs_attention(session: Session, chef: str) -> bool:
    tasks = session.cooking_map.get(chef, {})
    return any(session.recipe[t.instruction_index].aiList[t.ai_index].attention for t in tasks.values())


# Public API

# ---------------------------------------------------------------------------
# SAT encoding + cryptominisat search
# ---------------------------------------------------------------------------

import multiprocessing, queue, tqdm  # noqa: E402 – placed after stdlib imports deliberately
from pycryptosat import Solver       # noqa: E402


def session2sat(session: Session, time_ub: int, now: int):
    """Encode the *remaining* scheduling problem as SAT.

    Returns ``triple2idx, clauses`` where *triple2idx* maps
    ``(chef, t_offset, instr_idx) → SAT variable`` and *clauses* is a list of
    CNF clauses (each a list of ints).  Uses helper functions defined above
    (attention spans, interval shifts, `recipe_active_part`, etc.).
    """

    vertex_set, edges, _ = cooking_graph(session)
    time_slots = range(time_ub)
    chefs      = list(session.chefs_data)

    # ---------------- triple enumeration ----------------
    triples = [(p, t, v) for p in chefs for v in vertex_set for t in time_slots]
    triple2idx = {tpl: idx for idx, tpl in enumerate(triples, 1)}

    # ---------------- part 0 · assert current running tasks ----------------
    clauses0 = [
        [triple2idx[(chef, 0, task.instruction_index)]]
        for chef, tasks in session.cooking_map.items()
        for task in tasks.values()
    ]

    # ---------------- helper to fetch potentially shortened instruction ----
    active_recipe = recipe_active_part(session, now)
    def _inst(idx: int):
        return active_recipe.get(idx, session.recipe[idx])

    # ---------------- part 1 · no overlapping attention on same chef -------
    clauses1: List[List[int]] = []
    for v in vertex_set:
        for u in vertex_set:
            if v == u:  # Skip self-overlap constraints
                continue
            for t in time_slots:
                for s in interval_union(
                    forbidden_intervals_shifts(attention_span(_inst(v)), attention_span(_inst(u)))
                ):
                    if 0 <= t + s < time_ub:
                        for chef in chefs:
                            clauses1.append([-triple2idx[(chef, t + s, v)], -triple2idx[(chef, t, u)]])

    # ---------------- part 2 · every task is done at least once ------------
    clauses2: List[List[int]] = []
    for v in vertex_set:
        clause: List[int] = []
        dur = instruction_cooking_time(_inst(v))
        for chef in chefs:
            for t in time_slots:
                if t + dur <= time_ub:
                    clause.append(triple2idx[(chef, t, v)])
        clauses2.append(clause)

    # ---------------- part 3 · every task at most once ---------------------
    clauses3: List[List[int]] = []
    for v in vertex_set:
        vars_v = [triple2idx[(c, t, v)] for c in chefs for t in time_slots]
        for i in range(len(vars_v)):
            for j in range(i + 1, len(vars_v)):
                clauses3.append([-vars_v[i], -vars_v[j]])

    # ---------------- part 4 · dependency order ----------------------------
    clauses4: List[List[int]] = []
    for dep, dst in edges:  # dep must finish before dst starts
        dur_dep = instruction_cooking_time(_inst(dep))
        for chef1 in chefs:
            for chef2 in chefs:
                for t_dep in time_slots:
                    for t_dst in time_slots:
                        # dst cannot start before dep finishes
                        if t_dst < t_dep + dur_dep:
                            clauses4.append([-triple2idx[(chef1, t_dep, dep)], -triple2idx[(chef2, t_dst, dst)]])

    all_clauses = clauses0 + clauses1 + clauses2 + clauses3 + clauses4
    return triple2idx, all_clauses


# ---------------- cryptominisat driver ------------------------------------

def satSolve(clauses, triple2idx):
    """Run CryptoMiniSat on *clauses*. Return chosen triples list or ``False``."""

    solver = Solver()
    for cls in tqdm.tqdm(clauses, desc="Adding clauses"):
        solver.add_clause(cls)
    sat, solution = solver.solve()
    if not sat:
        return False

    idx2triple = {idx: tpl for tpl, idx in triple2idx.items()}
    return [idx2triple[i] for i, val in enumerate(solution) if val]


# ---------------- timeout wrapper ----------------------------------------

def run_with_timeout(f, args, timeout, default=None):
    ctx = multiprocessing.get_context("fork")
    q = ctx.Queue()

    def _worker(func, a, q_):
        q_.put(func(*a))

    p = ctx.Process(target=_worker, args=(f, args, q))
    p.start()
    try:
        res = q.get(timeout=timeout)
    except queue.Empty:
        p.kill()
        return default
    p.join()
    return res


def graph2solve_with_timeout(session: Session, time_ub: int, now: int, timeout: int = 60):
    t2i, clauses = session2sat(session, time_ub, now)
    return run_with_timeout(satSolve, [clauses, t2i], timeout)


# ---------------- outer binary search ------------------------------------

def _binarysearch(f, lb: int, ub: int):
    last = False
    while lb <= ub:
        mid = (lb + ub) // 2
        res = f(mid)
        if res:
            last = res
            ub = mid - 1
        else:
            lb = mid + 1
    return last


def sat_search(session: Session, now: int = 0, lb: int = 0, timeout: int = 60):
    """High‑level entry: minimum‑UB SAT schedule or ``False``."""

    ub = cooking_graph(session)[2]
    if lb >= ub:
        return False
    return _binarysearch(lambda t: graph2solve_with_timeout(session, t, now, timeout), lb, ub)


# ---------------------------------------------------------------------------
# Session-mutation helper – refresh & schedule
# ---------------------------------------------------------------------------

def refresh_session(session: Session, now: int) -> Session:
    """Return a new *Session* after advancing finished timers **and** assigning
    new work to chefs with spare attention capacity.

    Workflow:
    1. **Auto‑tick timers** – for every *low‑attention* `ActiveTask`, if
       `now - start_time >= duration` we finish that AI via
       :func:`active_ai_done` (looping until all timers are settled).
    2. Identify chefs that are now either idle or running only low‑attention
       tasks.
    3. Run :func:`sat_search` to compute a schedule starting at *now*.
    4. If the SAT solution schedules an instruction at *t = 0* for an eligible
       chef, start that instruction's first AI immediately.
    """

    # ------------------------------------------------------------
    # 1. Auto‑finish low‑attention timers that have expired
    # ------------------------------------------------------------
    s = session  # work on an immutable copy via reassignment
    changed = True
    while changed:
        changed = False
        for chef, tasks in list(s.cooking_map.items()):
            for inst_idx, task in list(tasks.items()):
                ai = s.recipe[task.instruction_index].aiList[task.ai_index]
                if not ai.attention and task.start_time is not None and (
                    now - task.start_time >= ai.duration
                ):
                    finish_time = task.start_time + ai.duration
                    s = active_ai_done(s, chef, inst_idx, finish_time)
                    changed = True
                    break  # restart because s changed
            if changed:
                break

    # ------------------------------------------------------------
    # 2. Find chefs with spare attention bandwidth
    # ------------------------------------------------------------
    eligible_chefs = {
        c for c in s.chefs_data if not _chef_needs_attention(s, c)
    }
    if not eligible_chefs:
        return s

    # ------------------------------------------------------------
    # 3. Ask SAT solver for a schedule at *now*
    # ------------------------------------------------------------
    solution = sat_search(s, now)
    if solution:
        new_map = copy.deepcopy(s.cooking_map)
        for chef in eligible_chefs:
            starts = [tpl for tpl in solution if tpl[0] == chef and tpl[1] == 0]
            if starts:
                inst_idx = starts[0][2]
                new_map.setdefault(chef, {})[inst_idx] = ActiveTask(
                    inst_idx, 0, now
                )

        return replace(s, cooking_map=new_map)

    return s


# In[ ]:




