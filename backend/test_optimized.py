#!/usr/bin/env python3
"""Test the optimized SAT solver."""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict
from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations import session2sat, cooking_graph

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

def test_optimized():
    """Test the optimized encoding."""
    session = create_test_session(2)
    vertices, edges, time_ub = cooking_graph(session)
    
    print(f"Testing optimized SAT encoding for {len(vertices)} tasks, time_ub={time_ub}")
    
    start = time.time()
    triple2idx, clauses = session2sat(session, time_ub, now=0)
    encoding_time = time.time() - start
    
    print(f"\nOptimized encoding results:")
    print(f"  Encoding time: {encoding_time:.3f}s")
    print(f"  Variables: {len(triple2idx)}")
    print(f"  Clauses: {len(clauses)}")
    
    # Analyze clause distribution
    clause_lengths = {}
    for clause in clauses:
        length = len(clause)
        clause_lengths[length] = clause_lengths.get(length, 0) + 1
    
    print(f"\nClause length distribution:")
    for length in sorted(clause_lengths.keys()):
        print(f"  Length {length}: {clause_lengths[length]} clauses")

if __name__ == "__main__":
    test_optimized()