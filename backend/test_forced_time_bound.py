#!/usr/bin/env python3
"""
Test with a forced higher time bound to see if the SAT solver can handle both tasks.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List
from dataclasses import asdict

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import active_ai_done, refresh_session, session2sat_optimized, satSolve

def create_multi_task_recipe() -> List[CookingInstruction]:
    """Create the multi_task_recipe from main.py"""
    raw_recipe = [
        {"index": 0, "aiList": [
            {"attention": True, "duration_seconds": 60, "description": "chop onions"},
            {"attention": False, "duration_seconds": 30, "description": "simmer onions"}
        ], "dependencies": []},
        {"index": 1, "aiList": [
            {"attention": True, "duration_seconds": 90, "description": "chop carrots"},
            {"attention": False, "duration_seconds": 30, "description": "boil carrots"}
        ], "dependencies": []}
    ]
    
    # Convert to CookingInstruction format
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
    
    return cis

def create_session(recipe: List[CookingInstruction], chef_names: List[str]) -> Session:
    """Create a new session with given recipe and chefs"""
    chefs_data = {name: Chef(name, heartbeat=None) for name in chef_names}
    cooking_map = {name: {} for name in chef_names}
    done_tasks: Dict[int, DoneTask] = {}
    return Session(recipe, chefs_data, cooking_map, done_tasks)

def test_forced_time_bound():
    """Test with forced time bounds to see if both tasks can be assigned"""
    print("Testing with forced time bounds...")
    
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    print(f"Recipe durations: instruction 0 = 3 quanta, instruction 1 = 4 quanta")
    
    # Test with different forced time bounds
    for time_ub in [7, 8, 10, 15]:
        print(f"\n--- Testing with forced time_ub={time_ub} ---")
        
        try:
            triple2idx, clauses = session2sat_optimized(session, time_ub, 0)
            print(f"Variables created: {len(triple2idx)}")
            
            # Check which instructions are represented
            instructions_in_variables = set()
            for chef, time, inst in triple2idx.keys():
                instructions_in_variables.add(inst)
            print(f"Instructions in variables: {sorted(instructions_in_variables)}")
            
            # Check if we have both instructions at time 0
            time_0_assignments = [(chef, inst) for chef, time, inst in triple2idx.keys() if time == 0]
            print(f"Possible assignments at time 0: {time_0_assignments}")
            
            # Try to solve
            solution = satSolve(clauses, triple2idx)
            if solution:
                print(f"SAT solution found: {solution}")
                
                # Check assignments at time 0
                time_0_solution = [triple for triple in solution if triple[1] == 0]
                print(f"Assignments at time 0: {time_0_solution}")
                
                # Count chefs and instructions
                chefs_at_0 = set(triple[0] for triple in time_0_solution)
                instructions_at_0 = set(triple[2] for triple in time_0_solution)
                
                print(f"Chefs assigned at time 0: {len(chefs_at_0)} ({chefs_at_0})")
                print(f"Instructions assigned at time 0: {len(instructions_at_0)} ({instructions_at_0})")
                
                if len(chefs_at_0) == 2 and len(instructions_at_0) == 2:
                    print("✅ SUCCESS: Both chefs get different instructions at time 0!")
                else:
                    print("❌ Still not both chefs getting tasks at time 0")
            else:
                print("❌ No SAT solution found")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def test_manual_constraint_check():
    """Manually check if our expected solution should work"""
    print("\n" + "="*60)
    print("Manual constraint check...")
    
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    time_ub = 10
    triple2idx, clauses = session2sat_optimized(session, time_ub, 0)
    
    # Our expected solution: Alice gets instruction 0, Bob gets instruction 1, both at time 0
    expected_solution = [("Alice", 0, 0), ("Bob", 0, 1)]
    
    print(f"Expected solution: {expected_solution}")
    print(f"Variables available: {len(triple2idx)}")
    
    # Check if variables exist
    for triple in expected_solution:
        if triple in triple2idx:
            print(f"  {triple} -> variable {triple2idx[triple]} ✅")
        else:
            print(f"  {triple} -> NOT AVAILABLE ❌")
            return
    
    # Test the assignment manually
    max_var = max(triple2idx.values())
    assignment = [False] * (max_var + 1000)  # Extra space for aux vars
    
    for triple in expected_solution:
        assignment[triple2idx[triple]] = True
    
    # Check constraints
    print(f"\nChecking {len(clauses)} clauses...")
    violated = []
    
    for i, clause in enumerate(clauses):
        satisfied = False
        for lit in clause:
            var_id = abs(lit)
            if var_id < len(assignment):
                if (lit > 0 and assignment[var_id]) or (lit < 0 and not assignment[var_id]):
                    satisfied = True
                    break
        
        if not satisfied:
            violated.append((i, clause))
    
    print(f"Violated clauses: {len(violated)}")
    
    if violated:
        print("First few violated clauses:")
        for i, (clause_idx, clause) in enumerate(violated[:5]):
            print(f"  Clause {clause_idx}: {clause}")
    else:
        print("✅ All clauses satisfied! Expected solution should work.")

if __name__ == "__main__":
    test_forced_time_bound()
    test_manual_constraint_check()