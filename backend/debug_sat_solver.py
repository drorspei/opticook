#!/usr/bin/env python3
"""
Debug the SAT solver to understand why it's not assigning both tasks initially.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List
from dataclasses import asdict

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import sat_search, cooking_graph, session2sat_optimized

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

def debug_sat_encoding():
    """Debug the SAT encoding to understand the problem"""
    print("Debugging SAT encoding for multi-task recipe...")
    
    # Create recipe and session
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    print(f"Recipe has {len(recipe)} instructions:")
    for i, inst in enumerate(recipe):
        total_duration = sum(ai.duration for ai in inst.aiList)
        print(f"  Instruction {i}: total duration={total_duration} quanta, dependencies: {inst.dependencies}")
        for j, ai in enumerate(inst.aiList):
            print(f"    AI {j}: attention={ai.attention}, duration={ai.duration}, desc='{ai.description}'")
    
    # Test different time upper bounds manually
    now = 0
    vertex_set, edges, calculated_ub = cooking_graph(session)
    print(f"\nCooking graph: vertices={vertex_set}, edges={edges}, calculated_ub={calculated_ub}")
    
    for time_ub in [3, 4, 5, 7, 10]:
        print(f"\n--- Testing with time_ub={time_ub} ---")
        try:
            triple2idx, clauses = session2sat_optimized(session, time_ub, now)
            print(f"Number of variables (triples): {len(triple2idx)}")
            print(f"Number of clauses: {len(clauses)}")
            
            # Show the variables (triples)
            print("Variables (chef, time, instruction):")
            for triple, idx in sorted(triple2idx.items(), key=lambda x: x[1]):
                chef, time, inst = triple
                print(f"  {idx}: ({chef}, {time}, {inst})")
            
            # Try to solve
            from computations_optimized import satSolve
            solution = satSolve(clauses, triple2idx)
            if solution:
                print(f"Solution found: {solution}")
                # Count instructions assigned
                instructions_assigned = set(triple[2] for triple in solution)
                chefs_assigned = set(triple[0] for triple in solution if triple[1] == 0)  # at time 0
                print(f"Instructions assigned at time 0: {len([t for t in solution if t[1] == 0])}")
                print(f"Chefs with assignments at time 0: {len(chefs_assigned)}")
                print(f"Assignments at time 0: {[t for t in solution if t[1] == 0]}")
            else:
                print("No solution found")
                
        except Exception as e:
            print(f"Error: {e}")

def test_expected_solution():
    """Test what we expect the solution to be"""
    print("\n" + "="*60)
    print("Testing expected solution manually...")
    
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    # What we want: Alice gets instruction 0, Bob gets instruction 1, both at time 0
    expected_solution = [("Alice", 0, 0), ("Bob", 0, 1)]
    
    print(f"Expected solution: {expected_solution}")
    
    # Check if this is valid according to constraints
    time_ub = 10
    triple2idx, clauses = session2sat_optimized(session, time_ub, 0)
    
    print(f"Available variables: {list(triple2idx.keys())}")
    
    # Check if our expected solution variables exist
    for triple in expected_solution:
        if triple in triple2idx:
            print(f"  {triple} -> variable {triple2idx[triple]} ✅")
        else:
            print(f"  {triple} -> NOT AVAILABLE ❌")
    
    # Try to construct assignment manually
    if all(triple in triple2idx for triple in expected_solution):
        print("\nTesting if expected solution satisfies constraints...")
        assignment = [False] * (max(triple2idx.values()) + 1)
        for triple in expected_solution:
            assignment[triple2idx[triple]] = True
        
        # Check clauses
        violated_clauses = []
        for i, clause in enumerate(clauses):
            satisfied = any(
                (lit > 0 and assignment[lit]) or (lit < 0 and not assignment[-lit])
                for lit in clause if abs(lit) < len(assignment)
            )
            if not satisfied:
                violated_clauses.append((i, clause))
        
        if violated_clauses:
            print(f"❌ Expected solution violates {len(violated_clauses)} clauses:")
            for i, (clause_idx, clause) in enumerate(violated_clauses[:5]):  # Show first 5
                print(f"  Clause {clause_idx}: {clause}")
                if i >= 4:
                    print(f"  ... and {len(violated_clauses) - 5} more")
                    break
        else:
            print("✅ Expected solution satisfies all constraints!")

if __name__ == "__main__":
    debug_sat_encoding()
    test_expected_solution()