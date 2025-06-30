#!/usr/bin/env python3
"""Simple test to verify the monotonicity issue."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_parallel import SATTimeTester, create_test_session

def main():
    session = create_test_session(2)
    tester = SATTimeTester(session, 0, 30)
    
    print("Quick monotonicity check:")
    print("Testing a few key points we know are problematic...\n")
    
    test_points = [85, 86, 87, 88, 89, 90, 100, 150, 200, 250, 259, 260]
    
    for t in test_points:
        result = tester(t)
        print(f"Time {t}: {'SAT' if result else 'UNSAT'}")
    
    print("\n=== ANALYSIS ===")
    print("If we see SAT at 85 but UNSAT at 150, this violates monotonicity.")
    print("The scheduling problem should be monotonic: if a schedule works")
    print("with time limit T, it should also work with time limit T+k.")
    print("\nThis means the time granularity optimization in the SAT encoding")
    print("is introducing bugs that affect ALL search algorithms.")
    
    print("\n=== IMPACT ON PARALLEL ALGORITHMS ===")
    print("- Binary search: Assumes monotonicity, will find wrong results")
    print("- Interval search: May find different results in different intervals")  
    print("- Golden section: Assumes unimodality, definitely affected")
    print("- ALL parallel algorithms inherit this fundamental problem")

if __name__ == "__main__":
    main()