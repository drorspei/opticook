#!/usr/bin/env python3
"""Simple benchmark script for parallel SAT solver algorithms."""

import time
import sys
import os
import multiprocessing as mp

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict
from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import cooking_graph, graph2solve_with_timeout, _binarysearch
from parallel_search import (
    parallel_binary_search,
    parallel_interval_search,
    parallel_golden_section_search,
    adaptive_parallel_search
)

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

def test_algorithm(session, search_func, search_name, num_cores=None):
    """Test a single algorithm once."""
    vertices, edges, ub = cooking_graph(session)
    lb = 0
    
    def test_time(t: int) -> bool:
        result = graph2solve_with_timeout(session, t, 0, 30, use_optimized=True)
        return result is not False
    
    print(f"\nTesting {search_name}...")
    if num_cores:
        print(f"  Using {num_cores} cores")
    
    start_time = time.time()
    
    # Run the search
    try:
        if num_cores is not None:
            try:
                result = search_func(test_time, lb, ub, num_cores)
            except TypeError:
                result = search_func(test_time, lb, ub)
        else:
            result = search_func(test_time, lb, ub)
    except Exception as e:
        print(f"  Error: {e}")
        return None, 0
    
    elapsed = time.time() - start_time
    
    if result is not None:
        print(f"  Found optimal time: {result} units")
        print(f"  Time taken: {elapsed:.2f} seconds")
    else:
        print(f"  No solution found")
        print(f"  Time taken: {elapsed:.2f} seconds")
    
    return result, elapsed

def main():
    """Run a simple benchmark."""
    print("=== Simple SAT Solver Benchmark ===\n")
    
    # Create session with 2 chefs
    session = create_test_session(2)
    
    # Get system info
    num_cores = mp.cpu_count()
    print(f"System has {num_cores} CPU cores available")
    
    # Test sequential baseline
    print("\n" + "="*50)
    result_seq, time_seq = test_algorithm(session, _binarysearch, "Sequential Binary Search")
    
    # Test parallel algorithms with different core counts
    algorithms = [
        ("Parallel Binary Search", parallel_binary_search),
        ("Parallel Interval Search", parallel_interval_search),
        ("Parallel Golden Section Search", parallel_golden_section_search),
        ("Adaptive Parallel Search", adaptive_parallel_search),
    ]
    
    results = {"Sequential": (result_seq, time_seq)}
    
    for algo_name, algo_func in algorithms:
        # Test with 4 cores
        result, elapsed = test_algorithm(session, algo_func, f"{algo_name} (4 cores)", 4)
        results[f"{algo_name} (4)"] = (result, elapsed)
        
        # Test with all cores
        if num_cores > 4:
            result, elapsed = test_algorithm(session, algo_func, f"{algo_name} ({num_cores} cores)", num_cores)
            results[f"{algo_name} ({num_cores})"] = (result, elapsed)
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"{'Algorithm':<40} {'Time (s)':<10} {'Speedup':<10}")
    print("-"*60)
    
    for name, (result, elapsed) in results.items():
        speedup = time_seq / elapsed if elapsed > 0 else 0
        print(f"{name:<40} {elapsed:<10.2f} {speedup:<10.2f}x")

if __name__ == "__main__":
    main()