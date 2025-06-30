#!/usr/bin/env python3
"""Find the true minimum time by checking all feasible values."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_parallel import SATTimeTester, create_test_session
from computations_optimized import cooking_graph

def main():
    session = create_test_session(2)
    vertices, edges, ub = cooking_graph(session)
    
    tester = SATTimeTester(session, 0, 30)
    
    print("Finding the true minimum time...")
    print("(Checking from low to high until we find first SAT)\n")
    
    # Check from 1 upward to find the minimum
    for t in range(1, min(300, ub+1)):
        result = tester(t)
        if result:
            print(f"Found first SAT at time {t}")
            
            # Double-check a few values around it
            print("\nDouble-checking nearby values:")
            for dt in [-5, -3, -2, -1, 0, 1, 2, 3, 5]:
                if t + dt > 0:
                    check = tester(t + dt)
                    print(f"  Time {t + dt}: {'SAT' if check else 'UNSAT'}")
            
            print(f"\nConfirmed: The true minimum time is {t} units")
            break
        
        if t % 10 == 0:
            print(f"  Checked up to {t}... still UNSAT")

if __name__ == "__main__":
    main()