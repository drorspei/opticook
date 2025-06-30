#!/usr/bin/env python3
"""Debug the exact encoding to understand the inconsistency."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_final_correct import create_test_session, ExactSATTimeTester
from computations_optimized import cooking_graph

def main():
    """Debug the exact encoding."""
    session = create_test_session(2)
    tester = ExactSATTimeTester(session, 0, 60)
    
    print("=== DEBUGGING EXACT ENCODING ===\n")
    
    # Test specific points around the discrepancy
    print("Testing key points:")
    test_points = [70, 75, 79, 80, 85, 90, 100, 200, 240, 243, 245, 250]
    
    for t in test_points:
        result = tester(t)
        print(f"  Time {t}: {'SAT' if result else 'UNSAT'}")
    
    # Find the true minimum by exhaustive search in a small range
    print(f"\nExhaustive search from 70 to 90:")
    for t in range(70, 91):
        result = tester(t)
        if result:
            print(f"First SAT found at: {t}")
            
            # Verify monotonicity in the next few points
            violations = []
            for t2 in range(t+1, t+11):
                if not tester(t2):
                    violations.append(t2)
            
            if violations:
                print(f"MONOTONICITY VIOLATIONS after {t}: {violations}")
            else:
                print(f"Monotonicity preserved for next 10 points after {t}")
            break
    
    # The issue might be that parallel and sequential search different paths
    print(f"\nTesting times around sequential result (243):")
    for t in range(240, 250):
        result = tester(t)
        print(f"  Time {t}: {'SAT' if result else 'UNSAT'}")


if __name__ == "__main__":
    main()