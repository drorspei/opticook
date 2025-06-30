#!/usr/bin/env python3
"""
Debug the constraint logic step by step to understand what's preventing the expected solution.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List
from dataclasses import asdict

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import attention_span, instruction_cooking_time, session2sat_optimized

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

def debug_clause_violation():
    """Debug exactly which clauses are violated by our expected solution"""
    print("Debugging clause violation in detail...")
    
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    # Our expected solution: Alice gets instruction 0, Bob gets instruction 1, both at time 0
    expected_solution = [("Alice", 0, 0), ("Bob", 0, 1)]
    
    time_ub = 10
    triple2idx, clauses = session2sat_optimized(session, time_ub, 0)
    
    # Set up the assignment
    assignment = [False] * (max(triple2idx.values()) + 100)  # Extra space for aux variables
    for triple in expected_solution:
        if triple in triple2idx:
            assignment[triple2idx[triple]] = True
    
    print(f"Expected solution variables:")
    for triple in expected_solution:
        if triple in triple2idx:
            print(f"  {triple} -> variable {triple2idx[triple]} = True")
    
    # Test each clause type separately
    clause_types = {
        "part0": (0, 0),  # Current running tasks
        "part0.5": (0, 0),  # Exclude already active instructions
        "part1": (0, 0),  # Attention constraints
        "part2": (0, 0),  # Every task done at least once
        "part3": (0, 0),  # Every task at most once
        "part4": (0, 0)   # Dependencies
    }
    
    # Since we don't have the clause boundaries, let's check the clauses one by one
    violated_clauses = []
    satisfied_clauses = []
    
    for i, clause in enumerate(clauses):
        satisfied = any(
            (lit > 0 and lit < len(assignment) and assignment[lit]) or 
            (lit < 0 and abs(lit) < len(assignment) and not assignment[abs(lit)])
            for lit in clause
        )
        
        if satisfied:
            satisfied_clauses.append((i, clause))
        else:
            violated_clauses.append((i, clause))
    
    print(f"\nClause analysis:")
    print(f"Total clauses: {len(clauses)}")
    print(f"Satisfied: {len(satisfied_clauses)}")
    print(f"Violated: {len(violated_clauses)}")
    
    if violated_clauses:
        print(f"\nViolated clauses (first 10):")
        for i, (clause_idx, clause) in enumerate(violated_clauses[:10]):
            print(f"  Clause {clause_idx}: {clause}")
            
            # Try to understand what this clause means
            variables_in_clause = []
            for lit in clause:
                var_id = abs(lit)
                sign = "+" if lit > 0 else "-"
                
                # Find the triple for this variable
                for triple, vid in triple2idx.items():
                    if vid == var_id:
                        variables_in_clause.append(f"{sign}{triple}")
                        break
                else:
                    variables_in_clause.append(f"{sign}var{var_id}")
            
            print(f"    Meaning: {' OR '.join(variables_in_clause)}")

def test_simple_solution():
    """Test a very simple solution to see if the problem is fundamental"""
    print("\n" + "="*60)
    print("Testing simple single-chef solution...")
    
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice"])  # Only one chef
    
    time_ub = 10
    triple2idx, clauses = session2sat_optimized(session, time_ub, 0)
    
    print(f"Single chef variables: {list(triple2idx.keys())}")
    
    # Try Alice doing instruction 0 at time 0
    simple_solution = [("Alice", 0, 0)]
    assignment = [False] * (max(triple2idx.values()) + 100)
    for triple in simple_solution:
        if triple in triple2idx:
            assignment[triple2idx[triple]] = True
    
    violated_clauses = []
    for i, clause in enumerate(clauses):
        satisfied = any(
            (lit > 0 and lit < len(assignment) and assignment[lit]) or 
            (lit < 0 and abs(lit) < len(assignment) and not assignment[abs(lit)])
            for lit in clause
        )
        if not satisfied:
            violated_clauses.append((i, clause))
    
    print(f"Single chef solution violated clauses: {len(violated_clauses)}")
    
    if violated_clauses:
        print("First few violated clauses:")
        for i, (clause_idx, clause) in enumerate(violated_clauses[:3]):
            print(f"  Clause {clause_idx}: {clause}")

if __name__ == "__main__":
    debug_clause_violation()
    test_simple_solution()