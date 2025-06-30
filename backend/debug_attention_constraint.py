#!/usr/bin/env python3
"""
Debug the attention constraint in detail to see what's going wrong.
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

def debug_attention_constraints():
    """Debug exactly what attention constraints are being generated"""
    print("Debugging attention constraints in detail...")
    
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    time_ub = 10
    chefs = ["Alice", "Bob"]
    vertex_set = {0, 1}
    
    # Manually replicate the attention constraint generation
    from computations_optimized import recipe_active_part
    active_recipe = recipe_active_part(session, 0)
    def _inst(idx: int):
        return active_recipe.get(idx, recipe[idx])
    
    attention_tasks = [v for v in vertex_set if attention_span(_inst(v))]
    print(f"Attention tasks: {attention_tasks}")
    
    for inst_idx in attention_tasks:
        inst = _inst(inst_idx)
        spans = attention_span(inst)
        duration = instruction_cooking_time(inst)
        print(f"Instruction {inst_idx}: duration={duration}, attention_spans={spans}")
    
    # Create the triple mapping
    triples = []
    for p in chefs:
        for v in vertex_set:
            duration = instruction_cooking_time(_inst(v))
            for t in range(time_ub):
                if t + duration <= time_ub:
                    triples.append((p, t, v))
    
    triple2idx = {tpl: idx for idx, tpl in enumerate(triples, 1)}
    
    print(f"\nTriple to variable mapping:")
    for triple, var_id in sorted(triple2idx.items(), key=lambda x: x[1]):
        print(f"  {var_id}: {triple}")
    
    # Generate attention constraints manually
    print(f"\nAttention constraints:")
    constraint_count = 0
    
    for chef in chefs:
        print(f"\nChef {chef}:")
        for t in range(min(5, time_ub)):  # Just first 5 time slots
            print(f"  Time {t}:")
            
            # Find all attention tasks that could be active at time t
            active_at_t = []
            for v in attention_tasks:
                spans = attention_span(_inst(v))
                duration = instruction_cooking_time(_inst(v))
                
                # Check all possible start times for task v
                for start_t in range(max(0, t - duration + 1), min(t + 1, time_ub - duration + 1)):
                    # Check if any attention span would be active at time t
                    for span_start, span_end in spans:
                        if start_t + span_start <= t < start_t + span_end:
                            triple = (chef, start_t, v)
                            if triple in triple2idx:
                                active_at_t.append(triple2idx[triple])
                                print(f"    {triple} (var {triple2idx[triple]}) would be active")
                                break
            
            if len(active_at_t) > 1:
                print(f"    CONSTRAINT: at most one of {active_at_t}")
                constraint_count += 1
            elif len(active_at_t) == 1:
                print(f"    No constraint needed (only one option)")
            else:
                print(f"    No attention tasks active")
    
    print(f"\nTotal attention constraints: {constraint_count}")
    
    # Check our specific case: Alice on inst 0, Bob on inst 1, both at time 0
    print(f"\nChecking our expected solution:")
    alice_var = triple2idx.get(("Alice", 0, 0))
    bob_var = triple2idx.get(("Bob", 0, 1))
    print(f"Alice starts inst 0 at time 0: variable {alice_var}")
    print(f"Bob starts inst 1 at time 0: variable {bob_var}")
    
    # Check if they conflict in any constraint
    for chef in chefs:
        for t in range(3):  # Check first 3 time slots
            active_at_t = []
            for v in attention_tasks:
                spans = attention_span(_inst(v))
                duration = instruction_cooking_time(_inst(v))
                
                for start_t in range(max(0, t - duration + 1), min(t + 1, time_ub - duration + 1)):
                    for span_start, span_end in spans:
                        if start_t + span_start <= t < start_t + span_end:
                            triple = (chef, start_t, v)
                            if triple in triple2idx:
                                active_at_t.append(triple2idx[triple])
                                break
            
            if len(active_at_t) > 1:
                if chef == "Alice" and alice_var in active_at_t:
                    print(f"Alice has constraint at time {t}: at most one of {active_at_t}")
                if chef == "Bob" and bob_var in active_at_t:
                    print(f"Bob has constraint at time {t}: at most one of {active_at_t}")

if __name__ == "__main__":
    debug_attention_constraints()