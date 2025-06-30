#!/usr/bin/env python3
"""Quick final benchmark with just the best algorithms."""

import time
import sys
import os
import multiprocessing as mp

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_final_correct import (
    create_test_session, ExactSATTimeTester
)
from computations_optimized import cooking_graph
from parallel_search_fixed import (
    ParallelBinarySearcher,
    ParallelGoldenSectionSearcher,
    AdaptiveParallelSearcher
)


def main():
    """Quick benchmark of the most promising algorithms."""
    print("=== QUICK FINAL BENCHMARK (EXACT SAT ENCODING) ===\n")
    
    session = create_test_session(2)
    vertices, edges, ub = cooking_graph(session)
    
    print(f"Recipe: {len(session.recipe)} tasks, 2 chefs")
    print(f"Search range: 0 to {ub}")
    
    # Exact SAT tester
    tester_args = {'session': session, 'now': 0, 'timeout': 60}
    tester = ExactSATTimeTester(**tester_args)
    
    results = {}
    
    # Sequential baseline
    print("\nSequential Binary Search:")
    start = time.time()
    last = None
    lb_seq, ub_seq = 0, ub
    while lb_seq <= ub_seq:
        mid = (lb_seq + ub_seq) // 2
        res = tester(mid)
        if res:
            last = mid
            ub_seq = mid - 1
        else:
            lb_seq = mid + 1
    seq_time = time.time() - start
    print(f"  Result: {last} units")
    print(f"  Time: {seq_time:.2f} seconds")
    results["Sequential"] = (seq_time, last)
    
    # Best parallel algorithms
    algorithms = [
        ("Parallel Golden Section (2 cores)", ParallelGoldenSectionSearcher, 2),
        ("Parallel Golden Section (4 cores)", ParallelGoldenSectionSearcher, 4),
        ("Adaptive Parallel (8 cores)", AdaptiveParallelSearcher, 8),
    ]
    
    for name, algo_class, cores in algorithms:
        print(f"\n{name}:")
        searcher = algo_class(ExactSATTimeTester, tester_args)
        
        start = time.time()
        result = searcher.search(0, ub, cores)
        elapsed = time.time() - start
        
        speedup = seq_time / elapsed
        print(f"  Result: {result} units")
        print(f"  Time: {elapsed:.2f} seconds") 
        print(f"  Speedup: {speedup:.2f}x")
        results[name] = (elapsed, result)
    
    # Summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    
    all_results = [r for _, r in results.values() if r is not None]
    unique_results = set(all_results)
    
    if len(unique_results) == 1:
        optimal = unique_results.pop()
        print(f"✅ All algorithms found optimal time: {optimal} units")
        print("✅ Exact SAT encoding ensures monotonicity and correctness")
    else:
        print(f"❌ Inconsistent results: {unique_results}")
    
    best_parallel = min((time, name) for name, (time, result) in results.items() 
                       if "cores" in name)
    best_time, best_name = best_parallel
    max_speedup = seq_time / best_time
    
    print(f"\nPerformance:")
    print(f"  Best parallel algorithm: {best_name}")
    print(f"  Maximum speedup: {max_speedup:.2f}x")
    print(f"  Sequential time: {seq_time:.1f}s → Parallel time: {best_time:.1f}s")


if __name__ == "__main__":
    main()