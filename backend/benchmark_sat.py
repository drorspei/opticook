#!/usr/bin/env python3
"""Benchmark script for SAT solver performance on the cheesecake recipe."""

import time
import sys
import os
import multiprocessing as mp
from typing import List, Dict, Callable, Optional
from functools import partial

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import sat_search, session2sat_optimized, satSolve, cooking_graph, graph2solve_with_timeout, _binarysearch
from parallel_search import (
    parallel_binary_search,
    parallel_interval_search,
    parallel_golden_section_search,
    speculative_execution_search,
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

def sat_search_with_custom_search(session: Session, search_func: Callable, now: int = 0, timeout: int = 60, num_cores: int = None) -> Optional[int]:
    """Modified sat_search that uses a custom search function."""
    vertices, edges, ub = cooking_graph(session)
    lb = 0
    if lb >= ub:
        return None
    
    # Create a wrapper function for the search
    def test_time(t: int) -> bool:
        result = graph2solve_with_timeout(session, t, now, timeout, use_optimized=True)
        return result is not False
    
    # Use the custom search function
    if num_cores is not None:
        # Pass num_cores if the function supports it
        try:
            return search_func(test_time, lb, ub, num_cores)
        except TypeError:
            # Function doesn't accept num_cores
            return search_func(test_time, lb, ub)
    else:
        return search_func(test_time, lb, ub)

def benchmark_search_algorithm(session: Session, search_func: Callable, search_name: str, 
                              iterations: int = 3, num_cores: int = None, timeout: int = 60):
    """Benchmark a specific search algorithm."""
    print(f"\nBenchmarking {search_name} with {len(session.recipe)} tasks and {len(session.chefs_data)} chefs...")
    if num_cores:
        print(f"Using {num_cores} cores")
    print(f"Running {iterations} iterations...\n")
    
    times = []
    solutions = []
    
    for i in range(iterations):
        print(f"  Iteration {i+1}/{iterations}: ", end="", flush=True)
        
        # Time the SAT solving
        start_time = time.time()
        solution_time = sat_search_with_custom_search(
            session, search_func, now=0, timeout=timeout, num_cores=num_cores
        )
        end_time = time.time()
        
        elapsed = end_time - start_time
        times.append(elapsed)
        solutions.append(solution_time)
        
        if solution_time is not None:
            print(f"Found optimal time {solution_time} in {elapsed:.2f} seconds")
        else:
            print(f"No solution found after {elapsed:.2f} seconds")
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"\n  Average time: {avg_time:.2f} seconds")
        print(f"  Min time: {min(times):.2f} seconds")
        print(f"  Max time: {max(times):.2f} seconds")
        
        # Verify all solutions are the same
        unique_solutions = set(s for s in solutions if s is not None)
        if len(unique_solutions) == 1:
            print(f"  Optimal schedule time: {unique_solutions.pop()} units")
        elif len(unique_solutions) > 1:
            print(f"  WARNING: Different solutions found: {unique_solutions}")
    
    return times, solutions

def analyze_sat_encoding(session: Session):
    """Analyze the SAT encoding to understand clause counts."""
    print("\nAnalyzing SAT encoding...")
    
    vertices, edges, time_ub = cooking_graph(session)
    print(f"  Graph vertices: {len(vertices)}")
    print(f"  Graph edges: {len(edges)}")
    print(f"  Time upper bound: {time_ub}")
    
    # Generate SAT encoding (using optimized version)
    triple2idx, clauses = session2sat_optimized(session, time_ub, now=0)
    
    print(f"\nSAT encoding statistics:")
    print(f"  Total variables: {len(triple2idx)}")
    print(f"  Total clauses: {len(clauses)}")
    
    # Analyze clause types
    clause_lengths = {}
    for clause in clauses:
        length = len(clause)
        clause_lengths[length] = clause_lengths.get(length, 0) + 1
    
    print(f"\nClause length distribution:")
    for length in sorted(clause_lengths.keys())[:10]:  # Show first 10
        print(f"  Length {length}: {clause_lengths[length]} clauses")

def compare_algorithms(session: Session, timeout: int = 60):
    """Compare all search algorithms."""
    print("=" * 80)
    print("COMPARING SEARCH ALGORITHMS")
    print("=" * 80)
    
    # Detect number of cores
    num_cores = mp.cpu_count()
    print(f"\nSystem has {num_cores} CPU cores available")
    
    # Test with different core counts
    core_configs = [1, 2, 4, min(8, num_cores), min(16, num_cores), num_cores]
    core_configs = sorted(list(set([c for c in core_configs if c <= num_cores])))
    
    results = {}
    
    # Algorithms to test
    algorithms = [
        ("Sequential Binary Search", _binarysearch, False),
        ("Parallel Binary Search", parallel_binary_search, True),
        ("Parallel Interval Search", parallel_interval_search, True),
        ("Parallel Golden Section Search", parallel_golden_section_search, True),
        ("Speculative Execution Search", speculative_execution_search, True),
        ("Adaptive Parallel Search", adaptive_parallel_search, True),
    ]
    
    for algo_name, algo_func, supports_cores in algorithms:
        print(f"\n{'=' * 60}")
        print(f"Testing: {algo_name}")
        print(f"{'=' * 60}")
        
        if supports_cores:
            # Test with different core counts
            for cores in core_configs:
                key = f"{algo_name} ({cores} cores)"
                times, solutions = benchmark_search_algorithm(
                    session, algo_func, key, iterations=3, num_cores=cores, timeout=timeout
                )
                results[key] = {
                    'times': times,
                    'solutions': solutions,
                    'avg_time': sum(times) / len(times) if times else float('inf')
                }
        else:
            # Sequential algorithm
            times, solutions = benchmark_search_algorithm(
                session, algo_func, algo_name, iterations=3, timeout=timeout
            )
            results[algo_name] = {
                'times': times,
                'solutions': solutions,
                'avg_time': sum(times) / len(times) if times else float('inf')
            }
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY OF RESULTS")
    print("=" * 80)
    print(f"{'Algorithm':<50} {'Avg Time (s)':<15} {'Speedup':<10}")
    print("-" * 75)
    
    # Get baseline (sequential) time
    baseline_time = results.get("Sequential Binary Search", {}).get('avg_time', float('inf'))
    
    # Sort by average time
    sorted_results = sorted(results.items(), key=lambda x: x[1]['avg_time'])
    
    for algo_name, data in sorted_results:
        avg_time = data['avg_time']
        speedup = baseline_time / avg_time if avg_time > 0 else 0
        print(f"{algo_name:<50} {avg_time:<15.2f} {speedup:<10.2f}x")

def main():
    """Main benchmark function."""
    print("=== SAT Solver Benchmark for Cheesecake Recipe ===\n")
    
    # Test with different numbers of chefs
    for num_chefs in [2, 3]:
        print(f"\n{'#' * 80}")
        print(f"# Testing with {num_chefs} chefs")
        print(f"{'#' * 80}")
        
        session = create_test_session(num_chefs)
        
        # Analyze the encoding
        analyze_sat_encoding(session)
        
        # Compare all algorithms
        compare_algorithms(session, timeout=120)  # 2 minute timeout per solve
        
        print("\n" + "#" * 80)

if __name__ == "__main__":
    main()