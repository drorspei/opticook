#!/usr/bin/env python3
"""Verify the correct optimal time for the cheesecake recipe."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_parallel import SATTimeTester, create_test_session
from computations_optimized import cooking_graph

def main():
    session = create_test_session(2)
    vertices, edges, ub = cooking_graph(session)
    
    tester = SATTimeTester(session, 0, 60)  # Longer timeout
    
    print(f"Testing specific time values around the reported optima...")
    print(f"Search range: 0 to {ub}\n")
    
    # Test around 85
    print("Testing around 85:")
    for t in [80, 82, 84, 85, 86, 88, 90]:
        result = tester(t)
        print(f"  Time {t}: {'SAT' if result else 'UNSAT'}")
    
    print("\nTesting around 259:")
    for t in [254, 256, 258, 259, 260, 262, 264]:
        result = tester(t)
        print(f"  Time {t}: {'SAT' if result else 'UNSAT'}")
    
    # Binary search from scratch
    print("\nRunning fresh binary search:")
    lb, ub = 0, 475
    last = None
    iterations = 0
    while lb <= ub:
        mid = (lb + ub) // 2
        res = tester(mid)
        iterations += 1
        print(f"  Testing {mid}: {'SAT' if res else 'UNSAT'}")
        if res:
            last = mid
            ub = mid - 1
        else:
            lb = mid + 1
    
    print(f"\nBinary search found: {last} units in {iterations} iterations")

if __name__ == "__main__":
    main()