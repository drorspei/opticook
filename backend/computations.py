#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import annotations
import copy
import tqdm
from typing import Dict, List, Set, Tuple
from pycryptosat import Solver

from dataclasses import replace
from backend.data_models import CookingInstruction, ActiveTask, Session, DoneTask, SATSchedule, Chef


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

def compute_naive_time_upper_bound(session: Session, vertices: Set[int]) -> int:
    """Compute naive upper bound on time to cook by summing all instruction times."""
    time_ub = 0
    for inst in session.recipe:
        if inst.index in vertices:
            inst_time = instruction_cooking_time(inst)
            time_ub += inst_time
            # print(f"[DEBUG] compute_naive_time_upper_bound: instruction {inst.index} adds {inst_time} to time_ub (total now {time_ub})")
    return time_ub


def compute_smart_time_upper_bound(session: Session, vertices: Set[int], edges: List[Tuple[int, int]]) -> int:
    """Compute smarter upper bound considering parallelism and dependencies.

    Uses critical path analysis: the longest path through the dependency graph
    represents the minimum time needed, accounting for parallelization.
    """
    if not vertices:
        return 0

    # Build adjacency lists for the dependency graph
    successors: Dict[int, List[int]] = {v: [] for v in vertices}
    predecessors: Dict[int, List[int]] = {v: [] for v in vertices}

    for pred, succ in edges:
        if pred in vertices and succ in vertices:
            successors[pred].append(succ)
            predecessors[succ].append(pred)

    # Find vertices with no predecessors (can start immediately)
    start_vertices = [v for v in vertices if not predecessors[v]]

    # If no start vertices but we have vertices, there's a cycle - fall back to naive bound
    if not start_vertices and vertices:
        return compute_naive_time_upper_bound(session, vertices)

    # Compute earliest start time for each vertex using topological sort
    earliest_start: Dict[int, int] = {}
    earliest_finish: Dict[int, int] = {}

    # Process vertices in topological order
    processed = set()
    queue = list(start_vertices)

    while queue:
        v = queue.pop(0)
        if v in processed:
            continue

        # Check if all predecessors have been processed
        if all(p in processed for p in predecessors[v]):
            # Compute earliest start time
            if not predecessors[v]:
                earliest_start[v] = 0
            else:
                earliest_start[v] = max(earliest_finish[p] for p in predecessors[v])

            # Compute earliest finish time
            inst_time = instruction_cooking_time(session.recipe[v])
            earliest_finish[v] = earliest_start[v] + inst_time

            processed.add(v)

            # Add successors to queue
            queue.extend(successors[v])

    # The upper bound is the maximum finish time
    if earliest_finish:
        time_ub = max(earliest_finish.values())
    else:
        time_ub = 0

    # Account for number of chefs - if we have fewer chefs than parallel paths,
    # we need to scale up the bound
    num_chefs = len(session.chefs_data)
    if num_chefs > 0:
        # Approximate the effect of limited chefs by computing average parallelism
        total_work = sum(instruction_cooking_time(session.recipe[v]) for v in vertices)
        avg_parallelism = total_work / max(time_ub, 1)
        if avg_parallelism > num_chefs:
            # Scale up based on chef limitation
            time_ub = int(time_ub * (avg_parallelism / num_chefs))

    return time_ub


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

    # print(f"[DEBUG] cooking_graph: vertices={vertices}")

    edges: List[Tuple[int, int]] = []
    for inst in session.recipe:
        if inst.index in vertices:
            for dep in inst.dependencies:
                if dep in vertices:
                    edges.append((dep, inst.index))

    # Compute both bounds and use the minimum
    naive_bound = compute_naive_time_upper_bound(session, vertices)
    smart_bound = compute_smart_time_upper_bound(session, vertices, edges)
    time_ub = min(naive_bound, smart_bound)

    # print(f"[DEBUG] cooking_graph: naive_bound={naive_bound}, smart_bound={smart_bound}, using time_ub={time_ub}")
    # print(f"[DEBUG] cooking_graph: final time_ub={time_ub}, edges={edges}")
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
            remaining = max(0, ai.duration - int(now - (task.start_time or now)))
            updated_ai = replace(ai, duration=remaining)
            new_ai_list = [updated_ai] + session.recipe[task.instruction_index].aiList[task.ai_index + 1 :]
            updated[task.instruction_index] = replace(session.recipe[task.instruction_index], aiList=new_ai_list)
    return updated

# ---------------------------------------------------------------------------
# Session‑mutation helpers
# ---------------------------------------------------------------------------

def active_ai_done(session: Session, chef: str, inst_index: int, now: int) -> Session:
    # print(f"[DEBUG] active_ai_done: chef={chef}, inst_index={inst_index}, now={now}")
    if chef not in session.cooking_map or inst_index not in session.cooking_map[chef]:
        raise KeyError("No such active task for chef")

    task = session.cooking_map[chef][inst_index]
    ai_idx = task.ai_index
    # print(f"[DEBUG] active_ai_done: current ai_idx={ai_idx}, total AIs={len(session.recipe[inst_index].aiList)}")

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
        # print(f"[DEBUG] active_ai_done: advancing to next AI (ai_idx + 1 = {ai_idx + 1})")
        new_map[chef][inst_index] = ActiveTask(inst_index, ai_idx + 1, now)
    else:
        # print(f"[DEBUG] active_ai_done: instruction completed, removing from cooking_map")
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


def at_most_once_clauses(triple2idx: Dict[Tuple[str, int, int], int], vertex_set: Set[int], chefs: List[str], time_slots: range, time_windows: Dict[int, Tuple[int, int]] = None) -> List[List[int]]:
    # Using commander variable encoding for at-most-one constraints
    # This trades O(n²) clauses for O(n) clauses + O(n/k) auxiliary variables
    clauses3: List[List[int]] = []
    next_var = max(triple2idx.values(), default=-1) + 1  # Start auxiliary variables after existing ones

    for v in vertex_set:
        if time_windows:
            v_start, v_end = time_windows[v]
            vars_v = []
            for c in chefs:
                for t in range(v_start, min(v_end + 1, len(time_slots))):
                    triple = (c, t, v)
                    if triple in triple2idx:
                        vars_v.append(triple2idx[triple])
        else:
            vars_v = [triple2idx[(c, t, v)] for c in chefs for t in time_slots]

        if len(vars_v) <= 3:
            # For small groups, pairwise is still efficient
            for i in range(len(vars_v)):
                for j in range(i + 1, len(vars_v)):
                    clauses3.append([-vars_v[i], -vars_v[j]])
        else:
            # Commander variable encoding for larger groups
            # Split variables into groups of size 3
            group_size = 3
            groups = [vars_v[i:i+group_size] for i in range(0, len(vars_v), group_size)]

            # Create commander variables for each group
            commanders = []
            for group in groups:
                if len(group) > 1:
                    # Add at-most-one constraint within the group
                    for i in range(len(group)):
                        for j in range(i + 1, len(group)):
                            clauses3.append([-group[i], -group[j]])

                    # Create commander variable for this group
                    cmd_var = next_var
                    next_var += 1
                    commanders.append(cmd_var)

                    # If any variable in group is true, commander must be true
                    for var in group:
                        clauses3.append([-var, cmd_var])

                    # If commander is false, all variables in group must be false
                    clause = [-cmd_var]
                    clause.extend(group)
                    clauses3.append(clause)
                else:
                    # Single element groups don't need a commander
                    commanders.append(group[0])

            # Ensure at most one commander is true
            for i in range(len(commanders)):
                for j in range(i + 1, len(commanders)):
                    clauses3.append([-commanders[i], -commanders[j]])
    return clauses3


def compute_time_windows(session: Session, vertex_set: Set[int], edges: List[Tuple[int, int]], time_ub: int, now: int) -> Dict[int, Tuple[int, int]]:
    """Compute valid time windows for each instruction based on dependencies and duration constraints."""
    # Helper to get instruction (potentially shortened for active tasks)
    active_recipe = recipe_active_part(session, now)
    def _inst(idx: int):
        return active_recipe.get(idx, session.recipe[idx])

    # Initialize time windows
    time_windows: Dict[int, Tuple[int, int]] = {}

    # Build dependency graph
    successors: Dict[int, List[int]] = {v: [] for v in vertex_set}
    predecessors: Dict[int, List[int]] = {v: [] for v in vertex_set}

    for pred, succ in edges:
        successors[pred].append(succ)
        predecessors[succ].append(pred)

    # Compute earliest start times (forward pass)
    earliest_start: Dict[int, int] = {}
    processed = set()
    queue = [v for v in vertex_set if not predecessors[v]]

    while queue:
        v = queue.pop(0)
        if v in processed:
            continue

        if all(p in processed for p in predecessors[v]):
            if not predecessors[v]:
                earliest_start[v] = 0
            else:
                # Must start after all predecessors finish
                max_pred_finish = max(earliest_start[p] + instruction_cooking_time(_inst(p))
                                    for p in predecessors[v])
                earliest_start[v] = max_pred_finish

            processed.add(v)
            queue.extend(successors[v])

    # For any unprocessed vertices (cycles), set earliest start to 0
    for v in vertex_set:
        if v not in earliest_start:
            earliest_start[v] = 0

    # Compute latest start times using backward pass through dependencies
    latest_start: Dict[int, int] = {}

    # Initialize latest finish times (backward pass)
    latest_finish: Dict[int, int] = {}
    for v in vertex_set:
        duration = instruction_cooking_time(_inst(v))
        latest_finish[v] = time_ub  # Default: can finish at time_ub

    # Process vertices in reverse topological order
    processed_back = set()
    queue_back = [v for v in vertex_set if not successors[v]]

    while queue_back:
        v = queue_back.pop(0)
        if v in processed_back:
            continue

        if all(s in processed_back for s in successors[v]):
            if not successors[v]:
                # No successors - can finish at time_ub
                latest_finish[v] = time_ub
            else:
                # Must finish before any successor starts
                min_succ_start = min(latest_start.get(s, latest_finish[s] - instruction_cooking_time(_inst(s)))
                                   for s in successors[v])
                latest_finish[v] = min(latest_finish[v], min_succ_start)

            # Compute latest start time
            duration = instruction_cooking_time(_inst(v))
            latest_start[v] = max(0, latest_finish[v] - duration)

            processed_back.add(v)
            queue_back.extend(predecessors[v])

    # For any unprocessed vertices, use duration-based constraint
    for v in vertex_set:
        if v not in latest_start:
            duration = instruction_cooking_time(_inst(v))
            latest_start[v] = max(0, time_ub - duration)

        # Time window is [earliest_start, latest_start]
        time_windows[v] = (earliest_start[v], latest_start[v])

    return time_windows


def session2sat(session: Session, time_ub: int, now: int):
    """Encode the *remaining* scheduling problem as SAT.

    Returns ``triple2idx, clauses`` where *triple2idx* maps
    ``(chef, t_offset, instr_idx) → SAT variable`` and *clauses* is a list of
    CNF clauses (each a list of ints).  Uses helper functions defined above
    (attention spans, interval shifts, `recipe_active_part`, etc.).
    """

    vertex_set, edges, time_ub2 = cooking_graph(session)
    time_ub = min(time_ub, time_ub2)
    time_slots = range(time_ub)
    chefs      = list(session.chefs_data)

    # print(f"[DEBUG] session2sat: vertex_set={vertex_set}, edges={edges}, time_ub={time_ub}")
    # print(f"[DEBUG] session2sat: time_slots={list(time_slots)}, chefs={chefs}")

    # Compute valid time windows for each instruction
    time_windows = compute_time_windows(session, vertex_set, edges, time_ub, now)

    # ---------------- triple enumeration (filtered) ----------------
    triples = []
    for p in chefs:
        for v in vertex_set:
            start_time, end_time = time_windows[v]
            for t in range(start_time, min(end_time + 1, time_ub)):
                triples.append((p, t, v))

    triple2idx = {tpl: idx for idx, tpl in enumerate(triples, 1)}

    # print(f"[DEBUG] session2sat: triples={triples}")
    # print(f"[DEBUG] session2sat: triple2idx={triple2idx}")

    # ---------------- part 0 · assert current running tasks ----------------
    clauses0 = []
    for chef, tasks in session.cooking_map.items():
        for task in tasks.values():
            triple = (chef, 0, task.instruction_index)
            # print(f"[DEBUG] session2sat: trying to access triple={triple}")
            if triple in triple2idx:
                clauses0.append([triple2idx[triple]])
            else:
                # print(f"[DEBUG] session2sat: WARNING - triple {triple} not in triple2idx!")
                # Skip this clause if the triple is not in the mapping
                continue

    # print(f"[DEBUG] session2sat: clauses0={clauses0}")

    # ---------------- part 0.5 · exclude instructions already being worked on ----------------
    clauses0_5 = []
    # Get all instructions currently being worked on
    active_instructions = set()
    for chef_tasks in session.cooking_map.values():
        active_instructions.update(chef_tasks.keys())

    # For each active instruction, ensure it's not assigned to any other chef at time 0
    for inst_idx in active_instructions:
        for chef in chefs:
            triple = (chef, 0, inst_idx)
            if triple in triple2idx:
                # Find the chef who is actually working on this instruction
                actual_chef = None
                for c, tasks in session.cooking_map.items():
                    if inst_idx in tasks:
                        actual_chef = c
                        break

                # If this is not the actual chef working on it, exclude this assignment
                if actual_chef and chef != actual_chef:
                    clauses0_5.append([-triple2idx[triple]])
                    # print(f"[DEBUG] session2sat: excluding {triple} (not the actual chef)")

    # print(f"[DEBUG] session2sat: clauses0_5={clauses0_5}")

    # ---------------- helper to fetch potentially shortened instruction ----
    active_recipe = recipe_active_part(session, now)
    def _inst(idx: int):
        return active_recipe.get(idx, session.recipe[idx])

    # ---------------- part 1 · no overlapping attention on same chef -------
    clauses1: List[List[int]] = []

    # Pre-filter: only consider instructions that have attention requirements
    attention_vertices = [v for v in vertex_set if attention_span(_inst(v))]

    # Early exit if no attention conflicts possible
    if len(attention_vertices) <= 1:
        clauses1 = []
    else:
        for i, v in enumerate(tqdm.tqdm(attention_vertices)):
            for u in attention_vertices[i:]:  # Avoid duplicate pairs
                if v == u:  # Skip self-overlap constraints
                    continue
                v_start, v_end = time_windows[v]
                u_start, u_end = time_windows[u]

                # Pre-compute forbidden intervals once
                forbidden_shifts = forbidden_intervals_shifts(attention_span(_inst(v)), attention_span(_inst(u)))
                if not forbidden_shifts:  # No conflicts possible
                    continue

                forbidden_set = interval_union(forbidden_shifts)

                for chef in chefs:
                    for t in range(u_start, min(u_end + 1, time_ub)):
                        for s in forbidden_set:
                            t_v = t + s
                            if v_start <= t_v <= v_end and 0 <= t_v < time_ub:
                                triple_v = (chef, t_v, v)
                                triple_u = (chef, t, u)
                                if triple_v in triple2idx and triple_u in triple2idx:
                                    clauses1.append([-triple2idx[triple_v], -triple2idx[triple_u]])

    # ---------------- part 2 · every task is done at least once ------------
    clauses2: List[List[int]] = []

    for v in vertex_set:
        clause: List[int] = []
        dur = instruction_cooking_time(_inst(v))
        v_start, v_end = time_windows[v]

        for chef in chefs:
            for t in range(v_start, min(v_end + 1, time_ub)):
                if t + dur <= time_ub:
                    triple = (chef, t, v)
                    if triple in triple2idx:
                        clause.append(triple2idx[triple])
        clauses2.append(clause)

    # ---------------- part 3 · every task at most once ---------------------
    clauses3 = at_most_once_clauses(triple2idx, vertex_set, chefs, time_slots, time_windows)

    # ---------------- part 4 · dependency order ----------------------------
    clauses4: List[List[int]] = []
    for dep, dst in edges:  # dep must finish before dst starts
        dur_dep = instruction_cooking_time(_inst(dep))
        dep_start, dep_end = time_windows[dep]
        dst_start, dst_end = time_windows[dst]

        # Skip if windows already ensure correct ordering
        if dst_start >= dep_start + dur_dep:
            continue

        for chef1 in chefs:
            for chef2 in chefs:
                # Only iterate over potentially conflicting time ranges
                for t_dep in range(dep_start, min(dep_end + 1, time_ub)):
                    # Only check dst times that could violate the constraint
                    earliest_invalid_dst = max(dst_start, 0)
                    latest_invalid_dst = min(dst_end + 1, t_dep + dur_dep)

                    for t_dst in range(earliest_invalid_dst, latest_invalid_dst):
                        triple_dep = (chef1, t_dep, dep)
                        triple_dst = (chef2, t_dst, dst)
                        if triple_dep in triple2idx and triple_dst in triple2idx:
                            clauses4.append([-triple2idx[triple_dep], -triple2idx[triple_dst]])

    # ---------------- part 5 · symmetry breaking for identical chefs --------
    clauses5: List[List[int]] = []

    # If we have multiple chefs and no active tasks, add symmetry breaking
    if len(chefs) > 1 and not session.cooking_map:
        # Sort vertices by some canonical order (e.g., by index)
        sorted_vertices = sorted(vertex_set)

        # For the first instruction to be scheduled, prefer earlier chefs
        if sorted_vertices:
            first_v = sorted_vertices[0]
            v_start, v_end = time_windows[first_v]

            # Create preference: chef i can only start first_v at time t if all chefs j < i
            # are not starting any task at times <= t
            for i in range(1, len(chefs)):
                for t in range(v_start, min(v_end + 1, time_ub)):
                    # If chef i starts first_v at time t
                    triple_i = (chefs[i], t, first_v)
                    if triple_i not in triple2idx:
                        continue

                    # Then chef 0 must be busy with something at an earlier or equal time
                    clause = [-triple2idx[triple_i]]
                    for v_other in vertex_set:
                        other_start, other_end = time_windows[v_other]
                        for t_other in range(other_start, min(t + 1, other_end + 1, time_ub)):
                            triple_0 = (chefs[0], t_other, v_other)
                            if triple_0 in triple2idx:
                                clause.append(triple2idx[triple_0])

                    if len(clause) > 1:  # Only add if there are alternatives
                        clauses5.append(clause)

    all_clauses = clauses0 + clauses0_5 + clauses1 + clauses2 + clauses3 + clauses4 + clauses5
    return triple2idx, all_clauses


# ---------------- cryptominisat driver ------------------------------------

def satSolve(clauses, triple2idx, timeout=None):
    """Run CryptoMiniSat on *clauses*. Return chosen triples list or ``False``."""

    solver = Solver(time_limit=timeout) if timeout is not None else Solver()
    for cls in tqdm.tqdm(clauses, desc="Adding clauses"):
        solver.add_clause(cls)
    sat, solution = solver.solve()
    if not sat:
        return False

    idx2triple = {idx: tpl for tpl, idx in triple2idx.items()}
    return [idx2triple[i] for i, val in enumerate(solution) if val and i in idx2triple]


# ---------------- timeout wrapper ----------------------------------------

def run_with_timeout(f, args, timeout, default=None):
    import multiprocessing
    import queue
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
    return satSolve(clauses, t2i, timeout)
    # return run_with_timeout(satSolve, [clauses, t2i], timeout)


# ---------------- outer binary search ------------------------------------

def _binarysearch(f, lb: int, ub: int, interruption_check=None):
    last = False
    while lb <= ub:
        # Check for interruption
        if interruption_check and interruption_check():
            print("Binary search interrupted")
            return None
        
        mid = (lb + ub) // 2
        res = f(mid)
        if res:
            last = res
            ub = mid - 1
        else:
            lb = mid + 1
    return last


def sat_search(session: Session, now: int = 0, lb: int = 0, timeout: int = 60, interruption_check=None):
    """High‑level entry: minimum‑UB SAT schedule or ``False``."""

    ub = cooking_graph(session)[2]
    print(f"done cooking graph, ub={ub}")
    if lb >= ub:
        return False
    return _binarysearch(lambda t: graph2solve_with_timeout(session, t, now, timeout), lb, ub, interruption_check)


# ---------------------------------------------------------------------------
# Session-mutation helper – refresh & schedule
# ---------------------------------------------------------------------------

def refresh_session(session: Session, now: int) -> Session:
    """Assign the next available instruction from the chef's SATSchedule list that is not already active or done."""
    eligible_chefs = {
        c for c in session.chefs_data if not _chef_needs_attention(session, c)
    }
    if not eligible_chefs:
        print(f"[DEBUG] refresh_session: no eligible chefs, returning session")
        return session

    if session.sat_schedule is not None:
        print(f"[DEBUG] refresh_session: using stored SAT schedule (order only)")
        new_map = copy.deepcopy(session.cooking_map)
        active_instructions = set()
        for chef_tasks in new_map.values():
            active_instructions.update(chef_tasks.keys())
        made_new_assignments = False
        for chef in eligible_chefs:
            scheduled = session.sat_schedule.chef_to_tasks.get(chef, [])
            # Find the next scheduled instruction for this chef that is not done or active
            for task_index in scheduled:
                if task_index in session.done_tasks:
                    continue
                if chef in new_map and task_index in new_map[chef]:
                    continue
                # Assign this instruction to the chef
                print(f"[DEBUG] refresh_session: assigning instruction {task_index} to {chef} (from SATSchedule order)")
                if chef not in new_map:
                    new_map[chef] = {}
                new_map[chef][task_index] = ActiveTask(task_index, 0, now)
                made_new_assignments = True
                break  # Only assign one new task per chef per refresh
        if made_new_assignments:
            return replace(session, cooking_map=new_map)
        else:
            print(f"[DEBUG] refresh_session: no new assignments made from SATSchedule, returning original session")
            return session

    # Fallback: run SAT solver as before (should not be needed)
    print(f"[DEBUG] refresh_session: no SATSchedule, falling back to SAT solver")
    solution = sat_search(session, now)
    if solution:
        print(f"[DEBUG] refresh_session: Found valid solution (fallback)")
        new_map = copy.deepcopy(session.cooking_map)
        active_instructions = set()
        for chef_tasks in new_map.values():
            active_instructions.update(chef_tasks.keys())
        made_new_assignments = False
        for chef in eligible_chefs:
            starts = [tpl for tpl in solution if tpl[0] == chef and tpl[1] == 0]
            if starts:
                inst_idx = starts[0][2]
                if inst_idx not in active_instructions:
                    print(f"[DEBUG] refresh_session: assigning instruction {inst_idx} to {chef} at time {now} (fallback)")
                    if chef not in new_map:
                        new_map[chef] = {}
                    new_map[chef][inst_idx] = ActiveTask(
                        inst_idx, 0, now
                    )
                    made_new_assignments = True
        if made_new_assignments:
            return replace(session, cooking_map=new_map)
        else:
            print(f"[DEBUG] refresh_session: no new assignments made, returning original session (fallback)")
            return session
    else:
        print("[DEBUG] refresh_session: No SAT solution found (fallback)")
    return session


def test_example_reciple():
    from data_models import Chef, AtomicInstruction
    solution = satSolve(
        *session2sat(
            Session(recipe=[CookingInstruction(index=0, aiList=[AtomicInstruction(attention=True, duration=60, description='chop onions'), AtomicInstruction(attention=False, duration=30, description='simmer')], dependencies=[])], chefs_data={'Alice': Chef(name='Alice', addr=None, heartbeat=None, disconnected=False), 'Bob': Chef(name='Bob', addr=None, heartbeat=None, disconnected=False)}, cooking_map={'Alice': {}, 'Bob': {}}, done_tasks={}),
            475,
            0
        )[::-1]
    )
    print(solution)
    assert solution is not False


def start_session(recipe: List[CookingInstruction], chefs: List[str]) -> Session:
    """Create a new Session and store the full SAT schedule (chef -> ordered list of instruction indices)."""
    chefs_data = {name: Chef(name, heartbeat=None) for name in chefs}
    cooking_map = {name: {} for name in chefs}
    done_tasks: Dict[int, DoneTask] = {}
    session = Session(recipe, chefs_data, cooking_map, done_tasks)

    # Run SAT solver to get the full schedule
    solution = sat_search(session, now=0)
    chef_to_tasks: Dict[str, List[Tuple[int, int]]] = {name: [] for name in chefs}
    if solution:
        # solution is a list of (chef, start_time, task_index)
        for chef, start_time, task_index in solution:
            chef_to_tasks[chef].append((start_time, task_index))
    # For each chef, sort by planned start time and keep only instruction indices
    chef_to_tasks_ordered: Dict[str, List[int]] = {
        chef: [task_index for start_time, task_index in sorted(tasks)]
        for chef, tasks in chef_to_tasks.items()
    }
    sat_schedule = SATSchedule(chef_to_tasks_ordered)
    return Session(recipe, chefs_data, cooking_map, done_tasks, sat_schedule=sat_schedule)


if __name__ == "__main__":
    test_example_reciple()
