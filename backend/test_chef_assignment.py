#!/usr/bin/env python3
"""Test that chefs get assigned tasks when starting a recipe."""

import sys
from dataclasses import asdict
from main import _current_session, app
from data_models import Chef, AtomicInstruction, CookingInstruction, Session
from computations_seconds import refresh_session
import computations_optimized

def test_chef_assignment():
    """Test that a chef gets assigned 'chop onions' when starting Example Recipe."""
    print("Testing chef assignment for Example Recipe...")
    
    # Reset any existing session
    global _current_session
    _current_session = None
    
    # Create session with Example Recipe
    from main import RECIPE_STORE
    raw_recipe = RECIPE_STORE["example_recipe"]
    print(f"Raw recipe data: {raw_recipe}")
    
    # Build CookingInstruction list with durations in seconds
    cis = []
    for item in raw_recipe:
        ais = [
            AtomicInstruction(
                ai["attention"],
                ai["duration_seconds"],  # Keep in seconds
                ai["description"],
            )
            for ai in item["aiList"]
        ]
        cis.append(CookingInstruction(item["index"], ais, item.get("dependencies", [])))
    
    # Initialize session with two chefs
    chefs_data = {"Alice": Chef("Alice", heartbeat=None), "Bob": Chef("Bob", heartbeat=None)}
    cooking_map = {"Alice": {}, "Bob": {}}
    done_tasks = {}
    session = Session(cis, chefs_data, cooking_map, done_tasks)
    
    print(f"Initial session created with recipe: {[ai.description for ai in cis[0].aiList]}")
    print(f"Recipe AI durations: {[ai.duration for ai in cis[0].aiList]}")
    print(f"Initial cooking_map: {cooking_map}")
    
    # Refresh session to trigger task assignment
    # Use relative time starting from 0 instead of absolute epoch time
    current_time = 0.0
    
    # Enable debug prints by temporarily uncommenting them in computations_optimized.py
    from computations_optimized import _chef_needs_attention, sat_search
    
    print(f"\nDebug info before refresh:")
    print(f"Alice needs attention: {_chef_needs_attention(session, 'Alice')}")
    print(f"Bob needs attention: {_chef_needs_attention(session, 'Bob')}")
    
    # Try SAT search directly with time 0
    solution = sat_search(session, int(current_time))
    print(f"SAT solution: {solution}")
    
    # Try with original functions using quanta
    print(f"\nTesting with original quanta-based functions:")
    # Convert session to quanta for original functions
    from data_models import time_in_units
    cis_quanta = []
    for item in RECIPE_STORE["example_recipe"]:
        ais_quanta = [
            AtomicInstruction(
                ai["attention"],
                time_in_units(ai["duration_seconds"]),  # Convert to quanta
                ai["description"],
            )
            for ai in item["aiList"]
        ]
        cis_quanta.append(CookingInstruction(item["index"], ais_quanta, item.get("dependencies", [])))
    
    session_quanta = Session(cis_quanta, chefs_data, cooking_map, done_tasks)
    print(f"Quanta-based AI durations: {[ai.duration for ai in cis_quanta[0].aiList]}")
    
    # Check what cooking_graph returns
    from computations_optimized import cooking_graph
    nodes, edges, time_ub = cooking_graph(session_quanta)
    print(f"Cooking graph: nodes={nodes}, edges={edges}, time_ub={time_ub}")
    
    # Try with longer timeout
    solution_quanta = computations_optimized.sat_search(session_quanta, 0, lb=0, timeout=120)
    print(f"SAT solution with quanta: {solution_quanta}")
    
    # Debug the SAT encoding to see why multiple chefs get same instruction
    from computations_optimized import session2sat_optimized
    triple2idx, clauses = session2sat_optimized(session_quanta, time_ub=5, now=0)
    
    print(f"\nSAT encoding debug:")
    print(f"Triples: {[(idx, triple) for triple, idx in triple2idx.items()]}")
    
    # Look specifically at instruction 0 triples
    inst_0_triples = [(triple, idx) for triple, idx in triple2idx.items() if triple[2] == 0]
    print(f"Instruction 0 triples: {inst_0_triples}")
    
    # Check the "at most once" constraints for instruction 0
    vars_v_0 = [triple2idx[(c, t, 0)] for c in ['Alice', 'Bob'] for t in range(5)
                if (c, t, 0) in triple2idx]
    print(f"Variables for instruction 0: {vars_v_0}")
    
    # Find clauses that constrain instruction 0
    inst_0_constraints = []
    for clause in clauses:
        clause_vars = [abs(lit) for lit in clause]
        if any(var in vars_v_0 for var in clause_vars):
            inst_0_constraints.append(clause)
    print(f"Constraints involving instruction 0: {inst_0_constraints[:10]}")  # Show first 10
    
    refreshed_session_quanta = computations_optimized.refresh_session(session_quanta, 0)
    print(f"Cooking map after refresh with quanta: {refreshed_session_quanta.cooking_map}")
    
    refreshed_session = refresh_session(session, current_time)
    
    print(f"\nAfter refresh at time {current_time}:")
    print(f"Cooking map: {refreshed_session.cooking_map}")
    
    # Check if any chef was assigned the "chop onions" task
    chop_onions_assigned = False
    assigned_chef = None
    
    for chef_name, tasks in refreshed_session.cooking_map.items():
        for inst_idx, active_task in tasks.items():
            if inst_idx == 0 and active_task.ai_index == 0:
                # This is the first AI of the first instruction (chop onions)
                chop_onions_assigned = True
                assigned_chef = chef_name
                print(f"\n✓ '{chef_name}' was assigned 'chop onions' (instruction {inst_idx}, AI {active_task.ai_index})")
                print(f"  Task details: {active_task}")
                break
    
    if not chop_onions_assigned:
        print("\n✗ FAIL: No chef was assigned the 'chop onions' task!")
        print(f"  Current cooking_map: {refreshed_session.cooking_map}")
        return False
    
    print(f"\n✓ SUCCESS: '{assigned_chef}' is chopping onions!")
    return True

if __name__ == "__main__":
    success = test_chef_assignment()
    sys.exit(0 if success else 1)