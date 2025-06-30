#!/usr/bin/env python3
"""Quick test of parallel search algorithms."""

import os
import sys

# Suppress debug output
os.environ['OPTICOOK_DEBUG'] = 'false'

# Redirect stderr to suppress SAT solver progress
import contextlib
import io

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import multiprocessing as mp
from typing import List, Dict
from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import cooking_graph, graph2solve_with_timeout, _binarysearch
from parallel_search import parallel_binary_search, adaptive_parallel_search

def load_cheesecake_recipe():
    """Load the cheesecake recipe from main.py."""
    from main import parse_cheesecake_recipe
    return parse_cheesecake_recipe()

def create_test_session(num_chefs: int = 2) -> Session:
    """Create a test session with the cheesecake recipe."""
    raw_recipe = load_cheesecake_recipe()
    
    # Build CookingInstruction list
    cis: List[CookingInstruction] = []
    for item in raw_recipe:
        ais = [
            AtomicInstruction(
                ai["attention"],
                time_in_units(ai["duration_seconds"]),
                ai["description"],
            )
            for ai in item["aiList"]
        ]
        cis.append(CookingInstruction(item["index"], ais, item.get("dependencies", [])))
    
    # Initialize chefs
    chef_names = [f"Chef{i+1}" for i in range(num_chefs)]
    chefs_data = {name: Chef(name, heartbeat=None) for name in chef_names}
    cooking_map = {name: {} for name in chef_names}
    done_tasks: Dict[int, DoneTask] = {}
    
    return Session(cis, chefs_data, cooking_map, done_tasks)

def run_test():
    """Run a simple test comparing sequential vs parallel search."""
    session = create_test_session(2)
    
    # Silence debug output
    import logging
    logging.getLogger().setLevel(logging.WARNING)
    
    # Suppress print statements from cooking_graph
    original_print = print
    def silent_print(*args, **kwargs):
        if not any("DEBUG" in str(arg) for arg in args):
            original_print(*args, **kwargs)
    
    import builtins
    builtins.print = silent_print
    
    vertices, edges, ub = cooking_graph(session)
    lb = 0
    
    def test_time(t: int) -> bool:
        # Suppress stderr output from SAT solver
        with contextlib.redirect_stderr(io.StringIO()):
            result = graph2solve_with_timeout(session, t, 0, 30, use_optimized=True)
        return result is not False
    
    # Restore print
    builtins.print = original_print
    
    print("=== Quick Parallel Search Test ===\n")
    print(f"Recipe: 40 tasks, 2 chefs")
    print(f"Search range: {lb} to {ub}")
    print(f"System cores: {mp.cpu_count()}\n")
    
    # Test sequential
    print("Testing Sequential Binary Search...")
    start = time.time()
    result_seq = _binarysearch(test_time, lb, ub)
    time_seq = time.time() - start
    print(f"  Result: {result_seq} units")
    print(f"  Time: {time_seq:.2f} seconds\n")
    
    # Test parallel with 4 cores
    print("Testing Parallel Binary Search (4 cores)...")
    start = time.time()
    result_par = parallel_binary_search(test_time, lb, ub, 4)
    time_par = time.time() - start
    print(f"  Result: {result_par} units")
    print(f"  Time: {time_par:.2f} seconds")
    print(f"  Speedup: {time_seq/time_par:.2f}x\n")
    
    # Test adaptive with all cores
    print(f"Testing Adaptive Parallel Search ({mp.cpu_count()} cores)...")
    start = time.time()
    result_adaptive = adaptive_parallel_search(test_time, lb, ub, mp.cpu_count())
    time_adaptive = time.time() - start
    print(f"  Result: {result_adaptive} units")
    print(f"  Time: {time_adaptive:.2f} seconds")
    print(f"  Speedup: {time_seq/time_adaptive:.2f}x")

if __name__ == "__main__":
    run_test()