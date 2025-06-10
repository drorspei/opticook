#!/usr/bin/env python3
"""Test the full SAT solving with optimizations."""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict
from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations import sat_search

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

def test_full_solve():
    """Test the full SAT solving."""
    session = create_test_session(2)
    
    print("Testing full SAT solving with optimized encoding...")
    
    start = time.time()
    solution = sat_search(session, now=0, timeout=120)  # 2 minute timeout
    solve_time = time.time() - start
    
    print(f"\nSAT solving results:")
    print(f"  Total time: {solve_time:.3f}s")
    
    if solution:
        print(f"  Solution found: YES")
        print(f"  Solution length: {len(solution)} assignments")
        
        # Show first few assignments
        print(f"  First 10 assignments:")
        for i, (chef, start_time, task) in enumerate(solution[:10]):
            print(f"    {chef} starts task {task} at time {start_time}")
    else:
        print(f"  Solution found: NO (timeout or unsatisfiable)")

if __name__ == "__main__":
    test_full_solve()