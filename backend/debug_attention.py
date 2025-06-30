#!/usr/bin/env python3
"""
Debug the attention constraint logic to understand why both chefs can't work simultaneously.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List
from dataclasses import asdict

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import attention_span, instruction_cooking_time

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

def debug_attention_spans():
    """Debug attention spans for both instructions"""
    print("Debugging attention spans...")
    
    recipe = create_multi_task_recipe()
    
    for inst in recipe:
        spans = attention_span(inst)
        duration = instruction_cooking_time(inst)
        print(f"\nInstruction {inst.index} (total duration: {duration}):")
        print(f"  AIs: {[(ai.attention, ai.duration, ai.description) for ai in inst.aiList]}")
        print(f"  Attention spans: {spans}")
        
        # Show what times require attention if started at time 0
        if spans:
            attention_times = set()
            for start, end in spans:
                attention_times.update(range(start, end))
            print(f"  Times requiring attention (if started at 0): {sorted(attention_times)}")

def debug_attention_constraint():
    """Debug the specific attention constraint that's causing problems"""
    print("\nDebugging attention constraint logic...")
    
    recipe = create_multi_task_recipe()
    chefs = ["Alice", "Bob"]
    time_ub = 10
    
    # Simulate the attention constraint logic from session2sat_optimized
    attention_tasks = [inst.index for inst in recipe if attention_span(inst)]
    print(f"Attention tasks: {attention_tasks}")
    
    # For each time slot, see what would conflict
    for t in range(min(5, time_ub)):  # Just check first 5 time slots
        print(f"\nTime slot {t}:")
        conflicts_alice = []
        conflicts_bob = []
        
        for inst_idx in attention_tasks:
            inst = recipe[inst_idx]
            spans = attention_span(inst)
            duration = instruction_cooking_time(inst)
            
            # Check all possible start times for this instruction
            for start_t in range(max(0, t - duration + 1), min(t + 1, time_ub - duration + 1)):
                # Check if any attention span would be active at time t
                for span_start, span_end in spans:
                    if start_t + span_start <= t < start_t + span_end:
                        conflicts_alice.append(f"inst{inst_idx}_start{start_t}")
                        conflicts_bob.append(f"inst{inst_idx}_start{start_t}")
                        break
        
        print(f"  Alice could have attention conflicts: {conflicts_alice}")
        print(f"  Bob could have attention conflicts: {conflicts_bob}")
        
        # The key insight: if Alice starts inst0 at time 0 and Bob starts inst1 at time 0,
        # do they conflict at time t?
        alice_working = False
        bob_working = False
        
        # Alice: instruction 0 starting at time 0
        if 0 <= t < instruction_cooking_time(recipe[0]):
            spans_0 = attention_span(recipe[0])
            for span_start, span_end in spans_0:
                if span_start <= t < span_end:
                    alice_working = True
                    break
        
        # Bob: instruction 1 starting at time 0  
        if 0 <= t < instruction_cooking_time(recipe[1]):
            spans_1 = attention_span(recipe[1])
            for span_start, span_end in spans_1:
                if span_start <= t < span_end:
                    bob_working = True
                    break
        
        print(f"  If Alice starts inst0 at 0, requires attention at time {t}: {alice_working}")
        print(f"  If Bob starts inst1 at 0, requires attention at time {t}: {bob_working}")
        
        if alice_working and bob_working:
            print(f"  ❌ CONFLICT: Both would need attention at time {t}")
        elif alice_working or bob_working:
            print(f"  ✅ OK: Only one needs attention at time {t}")
        else:
            print(f"  ✅ OK: Neither needs attention at time {t}")

if __name__ == "__main__":
    debug_attention_spans()
    debug_attention_constraint()