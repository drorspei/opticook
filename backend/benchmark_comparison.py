#!/usr/bin/env python3
"""Compare original vs optimized SAT solver performance."""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict
from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
import computations
import computations_optimized

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

def benchmark_encoding(session: Session):
    """Compare SAT encoding generation times."""
    vertices, edges, time_ub = computations.cooking_graph(session)
    
    print(f"\nComparing SAT encoding for {len(vertices)} tasks, time_ub={time_ub}")
    
    # Original encoding
    start = time.time()
    triple2idx_orig, clauses_orig = computations.session2sat(session, time_ub, now=0)
    time_orig = time.time() - start
    
    # Optimized encoding
    start = time.time()
    triple2idx_opt, clauses_opt = computations_optimized.session2sat_optimized(session, time_ub, now=0)
    time_opt = time.time() - start
    
    print(f"\nOriginal encoding:")
    print(f"  Time: {time_orig:.3f}s")
    print(f"  Variables: {len(triple2idx_orig)}")
    print(f"  Clauses: {len(clauses_orig)}")
    
    print(f"\nOptimized encoding:")
    print(f"  Time: {time_opt:.3f}s")
    print(f"  Variables: {len(triple2idx_opt)}")
    print(f"  Clauses: {len(clauses_opt)}")
    
    print(f"\nImprovement:")
    print(f"  Encoding time: {time_orig/time_opt:.2f}x faster")
    print(f"  Variable reduction: {(1 - len(triple2idx_opt)/len(triple2idx_orig))*100:.1f}%")
    print(f"  Clause reduction: {(1 - len(clauses_opt)/len(clauses_orig))*100:.1f}%")

def main():
    """Main comparison function."""
    print("=== SAT Solver Optimization Comparison ===\n")
    
    # Test with 2 chefs (typical case)
    session = create_test_session(2)
    benchmark_encoding(session)

if __name__ == "__main__":
    main()