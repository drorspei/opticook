#!/usr/bin/env python3
"""Test monotonicity of the SAT encoding - if time T works, T+k should also work."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_parallel import SATTimeTester, create_test_session
from computations_optimized import cooking_graph, sat_search

def test_with_different_granularities():
    """Test if the time granularity is causing non-monotonicity."""
    session = create_test_session(2)
    vertices, edges, ub = cooking_graph(session)
    
    print("Testing monotonicity with current implementation:")
    print("(If T is SAT, then T+1 should also be SAT)\n")
    
    tester = SATTimeTester(session, 0, 30)
    
    # Find all SAT points in a range
    sat_points = []
    unsat_after_sat = []
    
    for t in range(80, 300):
        result = tester(t)
        if result:
            sat_points.append(t)
            # Check if there's an UNSAT after this SAT
            for t2 in range(t+1, min(t+20, 300)):
                if not tester(t2):
                    unsat_after_sat.append((t, t2))
                    print(f"MONOTONICITY VIOLATION: SAT at {t}, but UNSAT at {t2}")
                    break
    
    print(f"\nFound {len(sat_points)} SAT points between 80 and 300")
    print(f"Found {len(unsat_after_sat)} monotonicity violations")
    
    if unsat_after_sat:
        print("\nThis is a BUG in the SAT encoding!")
        print("The time granularity optimization is breaking the monotonicity property.")
        
    # Test what the original sat_search finds
    print("\n\nTesting original sat_search function:")
    result = sat_search(session, now=0, timeout=60, use_optimized=True)
    print(f"Original sat_search found: {result}")

def theoretical_analysis():
    """Analyze if parallel algorithms are theoretically affected."""
    print("\n\n=== THEORETICAL ANALYSIS ===")
    print("\nAll binary search variants (sequential and parallel) assume monotonicity:")
    print("- If f(T) = True, then f(T+k) = True for all k > 0")
    print("\nWhen this assumption is violated:")
    print("1. Sequential binary search: May find a suboptimal solution")
    print("2. Parallel binary search: Same issue, may find different suboptimal solutions")
    print("3. Parallel interval search: May miss the global optimum if it's in a different interval")
    print("4. Golden section search: Assumes unimodality, will definitely fail")
    print("\nCONCLUSION: ALL algorithms are affected by non-monotonic SAT encoding!")

if __name__ == "__main__":
    test_with_different_granularities()
    theoretical_analysis()