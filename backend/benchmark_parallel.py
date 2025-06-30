#!/usr/bin/env python3
"""Benchmark script for parallel SAT search algorithms using callable classes."""

import time
import sys
import os
import multiprocessing as mp
from typing import List, Dict
import contextlib
import io

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import cooking_graph, graph2solve_with_timeout, _binarysearch
from parallel_search_fixed import (
    ParallelBinarySearcher,
    ParallelIntervalSearcher,
    ParallelGoldenSectionSearcher,
    AdaptiveParallelSearcher
)


class SATTimeTester:
    """Callable class for testing SAT satisfiability at a given time."""
    
    def __init__(self, session: Session, now: int = 0, timeout: int = 30):
        self.session = session
        self.now = now
        self.timeout = timeout
    
    def __call__(self, t: int) -> bool:
        """Test if the scheduling problem is satisfiable with time bound t."""
        # Suppress stderr output from SAT solver
        with contextlib.redirect_stderr(io.StringIO()):
            result = graph2solve_with_timeout(self.session, t, self.now, self.timeout, use_optimized=True)
        return result is not False


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


def benchmark_algorithm(name: str, search_func, session: Session, num_cores: int = None, iterations: int = 3):
    """Benchmark a search algorithm."""
    vertices, edges, ub = cooking_graph(session)
    lb = 0
    
    print(f"\nTesting {name}...")
    if num_cores:
        print(f"  Using {num_cores} cores")
    
    times = []
    results = []
    
    for i in range(iterations):
        print(f"  Iteration {i+1}/{iterations}: ", end="", flush=True)
        
        start_time = time.time()
        if num_cores is not None:
            result = search_func(lb, ub, num_cores)
        else:
            result = search_func(lb, ub)
        elapsed = time.time() - start_time
        
        times.append(elapsed)
        results.append(result)
        
        print(f"{result} units in {elapsed:.2f}s")
    
    avg_time = sum(times) / len(times) if times else float('inf')
    print(f"  Average: {avg_time:.2f} seconds")
    
    # Verify all results are the same
    unique_results = set(results)
    if len(unique_results) > 1:
        print(f"  WARNING: Different results found: {unique_results}")
    
    return avg_time, results[0] if results else None


def main():
    """Run benchmarks comparing sequential and parallel search algorithms."""
    print("=== Parallel SAT Search Benchmark ===\n")
    
    # Create test session
    session = create_test_session(2)
    vertices, edges, ub = cooking_graph(session)
    
    print(f"Recipe: {len(session.recipe)} tasks, {len(session.chefs_data)} chefs")
    print(f"Search range: 0 to {ub}")
    print(f"System cores: {mp.cpu_count()}")
    
    # Prepare tester arguments
    tester_args = {
        'session': session,
        'now': 0,
        'timeout': 30
    }
    
    results = {}
    
    # Test sequential baseline
    print("\n" + "="*60)
    print("SEQUENTIAL BASELINE")
    print("="*60)
    
    # Create a tester instance for sequential search
    tester = SATTimeTester(**tester_args)
    
    # Create a wrapper that properly calls the tester
    def sequential_wrapper(lb, ub):
        last = None
        while lb <= ub:
            mid = (lb + ub) // 2
            res = tester(mid)
            if res:
                last = mid
                ub = mid - 1
            else:
                lb = mid + 1
        return last
    
    avg_time, result = benchmark_algorithm(
        "Sequential Binary Search",
        sequential_wrapper,
        session,
        iterations=3
    )
    results["Sequential"] = (avg_time, result)
    baseline_time = avg_time
    
    # Test parallel algorithms
    print("\n" + "="*60)
    print("PARALLEL ALGORITHMS")
    print("="*60)
    
    algorithms = [
        ("Parallel Binary Search", ParallelBinarySearcher),
        ("Parallel Interval Search", ParallelIntervalSearcher),
        ("Parallel Golden Section Search", ParallelGoldenSectionSearcher),
        ("Adaptive Parallel Search", AdaptiveParallelSearcher),
    ]
    
    # Test with different core counts
    core_counts = [2, 4, 8, min(16, mp.cpu_count()), mp.cpu_count()]
    core_counts = sorted(list(set([c for c in core_counts if c <= mp.cpu_count()])))
    
    for algo_name, algo_class in algorithms:
        print(f"\n{algo_name}:")
        for cores in core_counts:
            searcher = algo_class(SATTimeTester, tester_args)
            name = f"{algo_name} ({cores} cores)"
            avg_time, result = benchmark_algorithm(
                name, 
                searcher.search,
                session,
                num_cores=cores,
                iterations=2  # Fewer iterations for parallel tests
            )
            results[name] = (avg_time, result)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"{'Algorithm':<45} {'Time (s)':<12} {'Speedup':<10} {'Result':<10}")
    print("-"*77)
    
    for name, (avg_time, result) in sorted(results.items(), key=lambda x: x[1][0]):
        speedup = baseline_time / avg_time if avg_time > 0 else 0
        print(f"{name:<45} {avg_time:<12.2f} {speedup:<10.2f}x {result or 'None':<10}")
    
    # Check all algorithms found the same result
    all_results = [r for _, r in results.values() if r is not None]
    if all_results and len(set(all_results)) > 1:
        print("\nWARNING: Different algorithms found different optimal times!")
        print(f"Results: {set(all_results)}")


if __name__ == "__main__":
    main()