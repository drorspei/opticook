# cook_fsm_backend/sat.py
# coding: utf-8

import tqdm
from subprocess import check_call
from collections import namedtuple
from pycryptosat import Solver
from itertools import product
import multiprocessing
import queue

# Time unit for scheduling (in seconds)
cooking_time_unit = 30    # in seconds
assert 60 % cooking_time_unit == 0

# Assignment metadata for SAT solver
tuple_fields = ["attention", "time"]
Assignment = namedtuple("Assignment", tuple_fields)


def Resources(v: int) -> set:
    """
    Placeholder for resource requirements of an instruction.
    """
    return set()


def recipe2sat(
    chefs: list[str],
    vertices: list[int],
    edges: list[tuple[int, int]],
    a: dict[int, Assignment],
    time_ub: int,
    time_unit: int = cooking_time_unit
) -> tuple[list[list[int]], list[tuple[str, int, int]], dict[tuple[str, int, int], int]]:
    """
    Convert the scheduling problem into CNF clauses for the SAT solver.
    Returns:
      - clauses: List of clause lists
      - tuples: List of (chef, timeslot, vertex) tuples
      - tuple2idx: Mapping from tuple to variable index
    """
    time_slots = range((time_ub * 60) // time_unit + 1)
    tuples = []
    for p in chefs:
        for v in vertices:
            for t in time_slots:
                tuples.append((p, t, v))

    tuple2idx = {tpl: i for i, tpl in enumerate(tuples, start=1)}
    clauses: list[list[int]] = []

    # 1. Only one high-attention task at a time per chef
    for v, u in tqdm.tqdm(list(product(vertices, vertices))):
        if v != u and a[v].attention and a[u].attention:
            for t in time_slots:
                for s in range(t, min(t + a[v].time, time_slots[-1] + 1)):
                    for p in chefs:
                        clauses.append([
                            -tuple2idx[(p, t, v)],
                            -tuple2idx[(p, s, u)]
                        ])

    # 2. Resource conflict constraints
    for (v, rv), (u, ru) in tqdm.tqdm(
        list(product(
            [(v, Resources(v)) for v in vertices],
            repeat=2
        ))
    ):
        if v != u and rv & ru:
            for p1, p2, t in product(chefs, chefs, time_slots):
                for s in range(t, min(t + a[v].time, time_slots[-1] + 1)):
                    clauses.append([
                        -tuple2idx[(p1, t, v)],
                        -tuple2idx[(p2, s, u)]
                    ])

    # 3. Every vertex must be scheduled at least once
    for v in tqdm.tqdm(vertices):
        cls = [tuple2idx[(p, t, v)] for p in chefs for t in time_slots]
        clauses.append(cls)

    # 4. Each task at most once
    for p, q in tqdm.tqdm(list(product(chefs, chefs))):
        for t, s in product(time_slots, time_slots):
            if p != q or t != s:
                for v in vertices:
                    clauses.append([
                        -tuple2idx[(p, t, v)],
                        -tuple2idx[(q, s, v)]
                    ])

    # 5. Dependency constraints follow graph structure
    for v, u in tqdm.tqdm(edges):
        for t, s in product(time_slots, time_slots):
            if s < t + a[v].time:
                for p, q in product(chefs, chefs):
                    clauses.append([
                        -tuple2idx[(p, t, v)],
                        -tuple2idx[(q, s, u)]
                    ])

    return clauses, tuples, tuple2idx


def satSolve(
    clauses: list[list[int]],
    tuple2idx: dict[tuple[str, int, int], int]
) -> list[tuple[str, int, int]] | bool:
    """
    Solve the CNF clauses using pycryptosat. Returns a list of chosen (chef, time, vertex)
    if satisfiable, else False.
    """
    solver = Solver()
    for cls in tqdm.tqdm(clauses):
        solver.add_clause(cls)
    sat, solution = solver.solve()
    if sat:
        idx2tuple = {i: tpl for tpl, i in tuple2idx.items()}
        chosen = [idx2tuple[i] for i, val in enumerate(solution, start=1) if val]
        return chosen
    return False


def run_with_timeout(
    f: callable,
    args: list,
    timeout: int,
    default=None
):
    """
    Run function `f` with `args`, killing if it exceeds `timeout` seconds.
    """
    ctx = multiprocessing.get_context('fork')
    q = ctx.Queue()
    def _worker(fn, fn_args, q_obj):
        res = fn(*fn_args)
        q_obj.put(res)
    p = ctx.Process(target=_worker, args=(f, args, q))
    p.start()
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        p.kill()
        return default
    finally:
        p.join()


def recipe2solve_with_timeout(
    chefs: list[str],
    vertices: list[int],
    edges: list[tuple[int, int]],
    a: dict[int, Assignment],
    time_ub: int,
    timeout: int
) -> list[tuple[str, int, int]] | bool:
    """
    Full SAT-based scheduling with timeout.
    """
    clauses, tuples, tuple2idx = recipe2sat(chefs, vertices, edges, a, time_ub)
    return run_with_timeout(satSolve, [clauses, tuple2idx], timeout)


def binarysearch(
    f: callable,
    lb: int,
    ub: int
) -> list[tuple[str, int, int]]:
    """
    Find minimal time_ub between lb and ub for which f returns truthy.
    """
    last = False
    while lb < ub:
        mid = (lb + ub) // 2
        res = f(mid)
        if res:
            last = res
            ub = mid
        else:
            lb = mid + 1
    return last


def solver(
    chefs: list[str],
    vertices: list[int],
    edges: list[tuple[int, int]],
    a: dict[int, Assignment],
    timeout: int,
    ub: int,
    lb: int = 0
) -> list[tuple[str, int, int]] | bool:
    """
    Top-level scheduling: finds minimal UB via binary search if lb < ub.
    """
    if lb < ub:
        return binarysearch(
            lambda t: recipe2solve_with_timeout(chefs, vertices, edges, a, t, timeout),
            lb,
            ub
        )
    print(f"Error: lb={lb} is not < ub={ub}")
    return False

__all__ = [
    "cooking_time_unit",
    "Assignment",
    "Resources",
    "recipe2sat",
    "satSolve",
    "run_with_timeout",
    "recipe2solve_with_timeout",
    "binarysearch",
    "solver",
]

