#!/usr/bin/env python3
"""Debug the parallel search to understand why it finds 85 instead of 259."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_parallel import SATTimeTester, create_test_session
from computations_optimized import cooking_graph
from parallel_search_fixed import ParallelBinarySearcher

def main():
    session = create_test_session(2)
    vertices, edges, ub = cooking_graph(session)
    
    tester_args = {
        'session': session,
        'now': 0,
        'timeout': 30
    }
    
    # Manual binary search to understand the issue
    print("Manual testing of key points:")
    tester = SATTimeTester(**tester_args)
    
    # Test the range where parallel search stops
    test_points = [50, 60, 70, 80, 85, 90, 100, 150, 200, 250, 259, 300]
    for t in test_points:
        result = tester(t)
        print(f"  Time {t}: {'SAT' if result else 'UNSAT'}")
    
    # Now let's trace through what parallel binary search does
    print("\nTracing parallel binary search logic:")
    print(f"Initial range: 0 to {ub}")
    
    # Simulate first iteration with 2 cores
    range_size = ub - 0 + 1
    step = range_size // 3  # (num_cores + 1)
    test_points_iter1 = [0 + step, 0 + 2*step]
    print(f"\nIteration 1 test points: {test_points_iter1}")
    
    for t in test_points_iter1:
        result = tester(t)
        print(f"  Time {t}: {'SAT' if result else 'UNSAT'}")
    
    # The issue might be that when it finds a valid point early (like 85),
    # it updates ub to search lower, but there might be multiple optimal solutions

if __name__ == "__main__":
    main()