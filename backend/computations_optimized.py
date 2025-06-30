#!/usr/bin/env python
# coding: utf-8

# Optimized version of computations.py with better SAT encodings

from __future__ import annotations
import copy
import tqdm
from dataclasses import dataclass, replace
from itertools import product, combinations
from typing import Dict, List, Optional, Set, Tuple
from pycryptosat import Solver
from functools import lru_cache


from data_models import *


# ---------------------------------------------------------------------------
# Basic queries (unchanged)
# ---------------------------------------------------------------------------

# Cache using a wrapper that converts to hashable types
@lru_cache(maxsize=1000)
def _instruction_cooking_time_cached(ai_durations: tuple) -> int:
    """Cached version that takes tuple of durations."""
    return sum(ai_durations)

def instruction_cooking_time(inst: CookingInstruction) -> int:
    """Return total quanta for *inst* (sum of its AIs)."""
    # Convert to hashable tuple for caching
    ai_durations = tuple(ai.duration for ai in inst.aiList)
    return _instruction_cooking_time_cached(ai_durations)


def is_in_attention(recipe: List[CookingInstruction], task: ActiveTask) -> bool:
    return recipe[task.instruction_index].aiList[task.ai_index].attention


def time_left_in_attention(recipe: List[CookingInstruction], task: ActiveTask, now: int) -> int:
    if not is_in_attention(recipe, task):
        raise ValueError("Task is not an attention step")
    if task.start_time is None:
        raise ValueError("Task has not started")

    remaining = recipe[task.instruction_index].aiList[task.ai_index].duration - (now - task.start_time)
    return max(0, remaining)


# Cache using a wrapper that converts to hashable types
@lru_cache(maxsize=1000)
def _attention_span_cached(ai_data: tuple) -> List[Tuple[int, int]]:
    """Cached version that takes tuple of (attention, duration) pairs."""
    offset = 0
    spans: List[Tuple[int, int]] = []
    for attention, duration in ai_data:
        if attention:
            spans.append((offset, offset + duration))
        offset += duration
    return spans

def attention_span(inst: CookingInstruction) -> List[Tuple[int, int]]:
    """Return attention spans for instruction."""
    # Convert to hashable tuple for caching
    ai_data = tuple((ai.attention, ai.duration) for ai in inst.aiList)
    return _attention_span_cached(ai_data)

# ---------------------------------------------------------------------------
# Dependency graph helper (unchanged)
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
    
    # Include all instructions that are either not completed OR currently active
    vertices: Set[int] = set()
    for inst in session.recipe:
        if not is_instruction_completed(inst.index):
            vertices.add(inst.index)
        # Also include instructions that are currently being worked on
        for chef_tasks in session.cooking_map.values():
            if inst.index in chef_tasks:
                vertices.add(inst.index)
    
    print(f"[DEBUG] cooking_graph: vertices={len(vertices)}")
    
    edges: List[Tuple[int, int]] = []
    time_ub = 0
    for inst in session.recipe:
        if inst.index in vertices:
            inst_time = instruction_cooking_time(inst)
            time_ub += inst_time
            print(f"[DEBUG] cooking_graph: instruction {inst.index} adds {inst_time} to time_ub (total now {time_ub})")
            for dep in inst.dependencies:
                if dep in vertices:
                    edges.append((dep, inst.index))
    
    print(f"[DEBUG] cooking_graph: final time_ub={time_ub}, edges={len(edges)}")
    return vertices, edges, time_ub

# ---------------------------------------------------------------------------
# Interval utilities (SAT helpers) - unchanged
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1000)
def forbidden_int_shifts(x: int, left: bool, spans: tuple) -> List[Tuple[int, int]]:
    # Convert tuple back to list for processing
    spans_list = list(spans)
    if left:
        return [(s - x, e - x - 1) for s, e in spans_list]
    return [(s - x + 1, e - x) for s, e in spans_list]


@lru_cache(maxsize=1000)
def forbidden_intervals_shifts(a: tuple, b: tuple) -> List[Tuple[int, int]]:
    # Convert tuples back to lists for processing
    a_list = list(a)
    b_tuple = b  # Keep as tuple for forbidden_int_shifts
    out: List[Tuple[int, int]] = []
    for s, e in a_list:
        out.extend(forbidden_int_shifts(s, True, b_tuple))
        out.extend(forbidden_int_shifts(e, False, b_tuple))
    return out


@lru_cache(maxsize=1000)
def interval_union(spans: tuple) -> Set[int]:
    # Convert tuple back to list for processing
    spans_list = list(spans)
    out: Set[int] = set()
    for s, e in spans_list:
        out.update(range(s, e + 1))
    return out

# ---------------------------------------------------------------------------
# Active-recipe projection (unchanged)
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
# Session‑mutation helpers (unchanged)
# ---------------------------------------------------------------------------

def active_ai_done(session: Session, chef: str, inst_index: int, now: int) -> Session:
    print(f"[DEBUG] active_ai_done: chef={chef}, inst_index={inst_index}, now={now}")
    if chef not in session.cooking_map or inst_index not in session.cooking_map[chef]:
        raise KeyError("No such active task for chef")

    task = session.cooking_map[chef][inst_index]
    ai_idx = task.ai_index
    print(f"[DEBUG] active_ai_done: current ai_idx={ai_idx}, total AIs={len(session.recipe[inst_index].aiList)}")

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
        print(f"[DEBUG] active_ai_done: advancing to next AI (ai_idx + 1 = {ai_idx + 1})")
        new_map[chef][inst_index] = ActiveTask(inst_index, ai_idx + 1, now)
    else:
        print(f"[DEBUG] active_ai_done: instruction completed, removing from cooking_map")
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
# OPTIMIZED SAT encoding + cryptominisat search
# ---------------------------------------------------------------------------

import multiprocessing, queue, tqdm  # noqa: E402 – placed after stdlib imports deliberately
from pycryptosat import Solver       # noqa: E402


def session2sat_optimized(session: Session, time_ub: int, now: int):
    """Optimized SAT encoding with better clause generation.
    
    Key optimizations:
    1. Use at-most-one encoding instead of pairwise exclusion for attention tasks
    2. Reduce time slots by using larger granularity where possible
    3. Pre-filter impossible assignments
    """

    vertex_set, edges, _ = cooking_graph(session)
    time_slots = range(time_ub)
    chefs      = list(session.chefs_data)

    print(f"[DEBUG] session2sat_optimized: vertex_set={vertex_set}, edges={edges}, time_ub={time_ub}")
    print(f"[DEBUG] session2sat_optimized: time_slots={list(time_slots)}, chefs={chefs}...")

    # ---------------- triple enumeration with filtering ----------------
    # Only create variables for valid time windows
    triples = []
    for p in chefs:
        for v in vertex_set:
            duration = instruction_cooking_time(session.recipe[v] if v not in recipe_active_part(session, now) else recipe_active_part(session, now)[v])
            for t in time_slots:
                if t + duration <= time_ub:  # Only valid start times
                    triples.append((p, t, v))
    
    triple2idx = {tpl: idx for idx, tpl in enumerate(triples, 1)}

    print(f"[DEBUG] session2sat_optimized: reduced triples count: {len(triples)} (vs {len(chefs) * len(vertex_set) * len(time_slots)} unfiltered)")

    # ---------------- part 0 · assert current running tasks ----------------
    clauses0 = []
    for chef, tasks in session.cooking_map.items():
        for task in tasks.values():
            triple = (chef, 0, task.instruction_index)
            if triple in triple2idx:
                clauses0.append([triple2idx[triple]])

    # ---------------- part 0.5 · exclude instructions already being worked on ----------------
    clauses0_5 = []
    active_instructions = set()
    for chef_tasks in session.cooking_map.values():
        active_instructions.update(chef_tasks.keys())
    
    for inst_idx in active_instructions:
        for chef in chefs:
            triple = (chef, 0, inst_idx)
            if triple in triple2idx:
                actual_chef = None
                for c, tasks in session.cooking_map.items():
                    if inst_idx in tasks:
                        actual_chef = c
                        break
                
                if actual_chef and chef != actual_chef:
                    clauses0_5.append([-triple2idx[triple]])

    # ---------------- helper to fetch potentially shortened instruction ----
    active_recipe = recipe_active_part(session, now)
    def _inst(idx: int):
        return active_recipe.get(idx, session.recipe[idx])

    # ---------------- part 1 · OPTIMIZED no overlapping attention -------
    # Use at-most-one encoding for better performance
    clauses1: List[List[int]] = []
    
    # Group tasks by whether they have attention requirements
    attention_tasks = [v for v in vertex_set if attention_span(_inst(v))]
    
    # For each chef and time slot, at most one attention task can be active
    for chef in chefs:
        for t in time_slots:
            # Find all attention tasks that could be active at time t
            active_at_t = []
            for v in attention_tasks:
                spans = attention_span(_inst(v))
                duration = instruction_cooking_time(_inst(v))
                
                # Check all possible start times for task v
                for start_t in range(max(0, t - duration + 1), min(t + 1, time_ub - duration + 1)):
                    # Check if any attention span would be active at time t
                    for span_start, span_end in spans:
                        if start_t + span_start <= t < start_t + span_end:
                            triple = (chef, start_t, v)
                            if triple in triple2idx:
                                active_at_t.append(triple2idx[triple])
                                break
            
            # Use sequential encoding for at-most-one constraint
            if len(active_at_t) > 1:
                clauses_tuple = _at_most_one_sequential(tuple(active_at_t))
                clauses1.extend([list(clause) for clause in clauses_tuple])

    # ---------------- part 2 · every task is done at least once ------------
    clauses2: List[List[int]] = []
    for v in vertex_set:
        clause: List[int] = []
        dur = instruction_cooking_time(_inst(v))
        for chef in chefs:
            for t in time_slots:
                if t + dur <= time_ub:
                    triple = (chef, t, v)
                    if triple in triple2idx:
                        clause.append(triple2idx[triple])
        if clause:  # Only add if there are valid assignments
            clauses2.append(clause)

    # ---------------- part 3 · every task at most once (OPTIMIZED) -----
    clauses3: List[List[int]] = []
    for v in vertex_set:
        vars_v = [triple2idx[(c, t, v)] for c in chefs for t in time_slots 
                  if (c, t, v) in triple2idx]
        if len(vars_v) > 1:
            # Use sequential encoding instead of pairwise
            clauses_tuple = _at_most_one_sequential(tuple(vars_v))
            clauses3.extend([list(clause) for clause in clauses_tuple])

    # ---------------- part 4 · dependency order ----------------------------
    clauses4: List[List[int]] = []
    for dep, dst in edges:  # dep must finish before dst starts
        dur_dep = instruction_cooking_time(_inst(dep))
        for chef1 in chefs:
            for chef2 in chefs:
                for t_dep in time_slots:
                    if (chef1, t_dep, dep) not in triple2idx:
                        continue
                    for t_dst in time_slots:
                        if (chef2, t_dst, dst) not in triple2idx:
                            continue
                        # dst cannot start before dep finishes
                        if t_dst < t_dep + dur_dep:
                            clauses4.append([-triple2idx[(chef1, t_dep, dep)], -triple2idx[(chef2, t_dst, dst)]])

    all_clauses = clauses0 + clauses0_5 + clauses1 + clauses2 + clauses3 + clauses4
    
    print(f"[DEBUG] Clause counts - part0: {len(clauses0)}, part0.5: {len(clauses0_5)}, "
          f"part1: {len(clauses1)}, part2: {len(clauses2)}, part3: {len(clauses3)}, part4: {len(clauses4)}")
    
    return triple2idx, all_clauses


@lru_cache(maxsize=1000)
def _at_most_one_sequential(variables: tuple) -> tuple:
    """Generate clauses for at-most-one constraint using sequential encoding.
    
    This is more efficient than pairwise encoding for large sets.
    Uses O(3n) clauses instead of O(n²) clauses.
    """
    # Convert tuple back to list for processing
    vars_list = list(variables)
    
    if len(vars_list) <= 1:
        return tuple()
    
    if len(vars_list) == 2:
        # For 2 variables, pairwise is optimal
        return ((-vars_list[0], -vars_list[1]),)
    
    # Sequential encoding with auxiliary variables
    # We need len(variables) - 1 auxiliary variables
    aux_base = max(vars_list) + 1
    aux_vars = list(range(aux_base, aux_base + len(vars_list) - 1))
    
    clauses = []
    
    # First variable implies first aux
    clauses.append((-vars_list[0], aux_vars[0]))
    
    # Middle variables
    for i in range(1, len(vars_list) - 1):
        # If variable i is true, then aux[i] is true
        clauses.append((-vars_list[i], aux_vars[i]))
        # If aux[i-1] is true, then variable i is false
        clauses.append((-aux_vars[i-1], -vars_list[i]))
        # If aux[i-1] is false and variable i is false, then aux[i] is false
        clauses.append((aux_vars[i-1], vars_list[i], -aux_vars[i]))
    
    # Last variable
    clauses.append((-aux_vars[-1], -vars_list[-1]))
    
    return tuple(clauses)


# ---------------- cryptominisat driver (unchanged) ------------------------------------

def satSolve(clauses, triple2idx):
    """Run CryptoMiniSat on *clauses*. Return chosen triples list or ``False``."""

    solver = Solver()
    for cls in tqdm.tqdm(clauses, desc="Adding clauses"):
        solver.add_clause(cls)
    sat, solution = solver.solve()
    if not sat:
        return False

    idx2triple = {idx: tpl for tpl, idx in triple2idx.items()}
    return [idx2triple[i] for i, val in enumerate(solution) if val and i in idx2triple]


# ---------------- timeout wrapper (unchanged) ----------------------------------------

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


def graph2solve_with_timeout(session: Session, time_ub: int, now: int, timeout: int = 60, use_optimized: bool = True):
    if use_optimized:
        t2i, clauses = session2sat_optimized(session, time_ub, now)
    else:
        from computations import session2sat
        t2i, clauses = session2sat(session, time_ub, now)
    return run_with_timeout(satSolve, [clauses, t2i], timeout)


# ---------------- outer binary search (unchanged) ------------------------------------

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


def sat_search(session: Session, now: int = 0, lb: int = 0, timeout: int = 60, use_optimized: bool = True):
    """High‑level entry: minimum‑UB SAT schedule or ``False``."""

    ub = cooking_graph(session)[2]
    if lb >= ub:
        return False
    return _binarysearch(lambda t: graph2solve_with_timeout(session, t, now, timeout, use_optimized), lb, ub)


# ---------------------------------------------------------------------------
# Session-mutation helper – refresh & schedule (unchanged except for sat_search call)
# ---------------------------------------------------------------------------

def refresh_session(session: Session, now: int, use_optimized: bool = True) -> Session:
    """Return a new *Session* after assigning new work to chefs with spare attention capacity.

    Workflow:
    1. Identify chefs that are now either idle or running only low‑attention
       tasks.
    2. Run :func:`sat_search` to compute a schedule starting at *now*.
    3. If the SAT solution schedules an instruction at *t = 0* for an eligible
       chef, start that instruction's first AI immediately.
    """

    # ------------------------------------------------------------
    # 1. Find chefs with spare attention bandwidth
    # ------------------------------------------------------------
    eligible_chefs = {
        c for c in session.chefs_data if not _chef_needs_attention(session, c)
    }
    print(f"[DEBUG] refresh_session: now={now}, eligible_chefs={eligible_chefs}")
    if not eligible_chefs:
        print(f"[DEBUG] refresh_session: no eligible chefs, returning session")
        return session

    # ------------------------------------------------------------
    # 2. Ask SAT solver for a schedule at *now*
    # ------------------------------------------------------------
    solution = sat_search(session, now, use_optimized=use_optimized)
    print(f"[DEBUG] refresh_session: SAT solution={solution}")
    if solution:
        print(f"[DEBUG] refresh_session: Found valid solution: {solution}")
        new_map = copy.deepcopy(session.cooking_map)
        print(f"[DEBUG] refresh_session: initial new_map={new_map}")
        
        # Get set of instructions that are already being worked on
        active_instructions = set()
        for chef_tasks in new_map.values():
            active_instructions.update(chef_tasks.keys())
        print(f"[DEBUG] refresh_session: active_instructions={active_instructions}")
        
        # Track if we actually made any new assignments
        made_new_assignments = False
        
        for chef in eligible_chefs:
            starts = [tpl for tpl in solution if tpl[0] == chef and tpl[1] == 0]
            print(f"[DEBUG] refresh_session: chef={chef}, starts={starts}")
            if starts:
                inst_idx = starts[0][2]
                # Only assign if this instruction is not already being worked on
                if inst_idx not in active_instructions:
                    print(f"[DEBUG] refresh_session: assigning instruction {inst_idx} to {chef} at time {now}")
                    if chef not in new_map:
                        new_map[chef] = {}
                    new_map[chef][inst_idx] = ActiveTask(
                        inst_idx, 0, now
                    )
                    made_new_assignments = True
                    print(f"[DEBUG] refresh_session: updated new_map={new_map}")
                else:
                    print(f"[DEBUG] refresh_session: instruction {inst_idx} already active, skipping assignment")
        
        # Only update the session if we actually made new assignments
        if made_new_assignments:
            return replace(session, cooking_map=new_map)
        else:
            print(f"[DEBUG] refresh_session: no new assignments made, returning original session")
            return session
    else:
        print(f"[DEBUG] refresh_session: No SAT solution found")

    return session