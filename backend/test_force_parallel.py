#!/usr/bin/env python3
"""
Test if we can force parallel execution by adding constraints.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List
from dataclasses import asdict

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import session2sat_optimized, satSolve

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

def test_force_parallel_execution():
    """Test if we can force both chefs to work at time 0"""
    print("Testing forced parallel execution...")
    
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    time_ub = 10
    triple2idx, clauses = session2sat_optimized(session, time_ub, 0)
    
    print(f"Original clauses: {len(clauses)}")
    
    # Add constraint: both chefs must work at time 0
    # This means at least one of Alice's time-0 options AND at least one of Bob's time-0 options
    alice_time_0 = [var for (chef, time, inst), var in triple2idx.items() if chef == "Alice" and time == 0]
    bob_time_0 = [var for (chef, time, inst), var in triple2idx.items() if chef == "Bob" and time == 0]
    
    print(f"Alice's time-0 options: {alice_time_0}")
    print(f"Bob's time-0 options: {bob_time_0}")
    
    # Add constraints requiring both to work at time 0
    modified_clauses = clauses + [alice_time_0, bob_time_0]
    
    print(f"Modified clauses: {len(modified_clauses)}")
    
    # Try to solve
    solution = satSolve(modified_clauses, triple2idx)
    
    if solution:
        print(f"Solution with forced parallel execution: {solution}")
        
        # Check assignments at time 0
        time_0_solution = [triple for triple in solution if triple[1] == 0]
        print(f"Assignments at time 0: {time_0_solution}")
        
        chefs_at_0 = set(triple[0] for triple in time_0_solution)
        instructions_at_0 = set(triple[2] for triple in time_0_solution)
        
        print(f"Chefs assigned at time 0: {len(chefs_at_0)} ({chefs_at_0})")
        print(f"Instructions assigned at time 0: {len(instructions_at_0)} ({instructions_at_0})")
        
        if len(chefs_at_0) == 2 and len(instructions_at_0) == 2:
            print("✅ SUCCESS: Forced both chefs to work at time 0!")
            return True
        else:
            print("❌ Forced solution still doesn't have both chefs working")
    else:
        print("❌ No solution found with forced parallel execution")
    
    return False

def test_preference_encoding():
    """Test adding preference for time-0 assignments without hard constraints"""
    print("\n" + "="*60)
    print("Testing preference encoding...")
    
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    time_ub = 10
    triple2idx, clauses = session2sat_optimized(session, time_ub, 0)
    
    # Find all solutions and pick the best one
    print("Finding all possible solutions...")
    
    solutions = []
    current_clauses = clauses[:]
    
    # Find up to 10 solutions by adding blocking clauses
    for i in range(10):
        solution = satSolve(current_clauses, triple2idx)
        if solution:
            solutions.append(solution)
            print(f"Solution {i+1}: {solution}")
            
            # Add blocking clause to prevent this exact solution
            blocking_clause = []
            for chef, time, inst in solution:
                if (chef, time, inst) in triple2idx:
                    blocking_clause.append(-triple2idx[(chef, time, inst)])
            current_clauses.append(blocking_clause)
        else:
            break
    
    if solutions:
        print(f"\nFound {len(solutions)} solutions. Evaluating them...")
        
        best_solution = None
        best_score = -1
        
        for i, solution in enumerate(solutions):
            time_0_assignments = [triple for triple in solution if triple[1] == 0]
            chefs_at_0 = len(set(triple[0] for triple in time_0_assignments))
            instructions_at_0 = len(set(triple[2] for triple in time_0_assignments))
            
            # Score: prioritize having both chefs work at time 0
            score = chefs_at_0 * 10 + instructions_at_0
            
            print(f"Solution {i+1}: {chefs_at_0} chefs, {instructions_at_0} instructions at time 0, score={score}")
            
            if score > best_score:
                best_score = score
                best_solution = solution
        
        print(f"\nBest solution: {best_solution}")
        time_0_best = [triple for triple in best_solution if triple[1] == 0]
        chefs_best = set(triple[0] for triple in time_0_best)
        
        if len(chefs_best) == 2:
            print("✅ SUCCESS: Found a solution with both chefs working at time 0!")
            return True
    
    print("❌ No good parallel solution found")
    return False

if __name__ == "__main__":
    success1 = test_force_parallel_execution()
    success2 = test_preference_encoding()
    
    if success1 or success2:
        print("\n✅ Parallel execution is possible!")
    else:
        print("\n❌ Could not achieve parallel execution")