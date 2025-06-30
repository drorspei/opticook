#!/usr/bin/env python3
"""
Debug script to examine the actual SAT clauses generated for different time bounds.
This will help identify the exact cause of non-monotonic behavior.
"""

import sys
import os
import contextlib
import io
from typing import List, Dict

# Add backend path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import session2sat_optimized, cooking_graph


def create_test_session():
    """Create test session using the cheesecake recipe."""
    from main import parse_cheesecake_recipe
    raw_recipe = parse_cheesecake_recipe()
    
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
    chef_names = ["Chef1", "Chef2"]
    chefs_data = {name: Chef(name, heartbeat=None) for name in chef_names}
    cooking_map = {name: {} for name in chef_names}
    done_tasks: Dict[int, DoneTask] = {}
    
    return Session(cis, chefs_data, cooking_map, done_tasks)


def compare_sat_encodings():
    """Compare SAT encodings for the two problematic time bounds."""
    print("=== COMPARING SAT ENCODINGS ===\n")
    
    session = create_test_session()
    
    # Test the two time bounds that show non-monotonic behavior
    time_ub_sat = 86  # Known SAT case
    time_ub_unsat = 130  # Known UNSAT case
    now = 0
    
    print(f"Comparing time bounds: {time_ub_sat} (SAT) vs {time_ub_unsat} (UNSAT)")
    
    # Generate SAT encodings for both cases
    sat_encoding = session2sat_optimized(session, time_ub_sat, now)
    unsat_encoding = session2sat_optimized(session, time_ub_unsat, now)
    
    sat_triple2idx, sat_clauses = sat_encoding
    unsat_triple2idx, unsat_clauses = unsat_encoding
    
    print(f"\nSAT case (time_ub={time_ub_sat}):")
    print(f"  Variables (triples): {len(sat_triple2idx)}")
    print(f"  Clauses: {len(sat_clauses)}")
    
    print(f"\nUNSAT case (time_ub={time_ub_unsat}):")
    print(f"  Variables (triples): {len(unsat_triple2idx)}")
    print(f"  Clauses: {len(unsat_clauses)}")
    
    # Analyze differences in variable sets
    sat_triples = set(sat_triple2idx.keys())
    unsat_triples = set(unsat_triple2idx.keys())
    
    only_in_sat = sat_triples - unsat_triples
    only_in_unsat = unsat_triples - sat_triples
    common = sat_triples & unsat_triples
    
    print(f"\nVariable analysis:")
    print(f"  Common variables: {len(common)}")
    print(f"  Only in SAT case: {len(only_in_sat)}")
    print(f"  Only in UNSAT case: {len(only_in_unsat)}")
    
    if only_in_sat:
        print(f"\n  Variables only in SAT case (first 10):")
        for triple in sorted(list(only_in_sat))[:10]:
            chef, time, task = triple
            print(f"    {triple} (Chef {chef}, time {time}, task {task})")
    
    if only_in_unsat:
        print(f"\n  Variables only in UNSAT case (first 10):")
        for triple in sorted(list(only_in_unsat))[:10]:
            chef, time, task = triple
            print(f"    {triple} (Chef {chef}, time {time}, task {task})")
    
    # Check if the UNSAT case is actually a superset (monotonic)
    is_superset = sat_triples.issubset(unsat_triples)
    print(f"\nIs UNSAT variable set a superset of SAT? {is_superset}")
    if not is_superset:
        print("❌ NON-MONOTONIC: UNSAT case has fewer variables than SAT case!")
        print("This violates the fundamental assumption that more time = more possibilities")
    
    return sat_encoding, unsat_encoding


def analyze_specific_variables():
    """Look at specific variables that might cause the issue."""
    print("\n=== ANALYZING SPECIFIC VARIABLES ===\n")
    
    session = create_test_session()
    time_ub_sat = 86
    time_ub_unsat = 130
    now = 0
    
    # Generate both encodings
    sat_triple2idx, sat_clauses = session2sat_optimized(session, time_ub_sat, now)
    unsat_triple2idx, unsat_clauses = session2sat_optimized(session, time_ub_unsat, now)
    
    # Focus on Task 24 (the 130-unit duration task) which might be problematic
    task_24_vars_sat = [t for t in sat_triple2idx.keys() if t[2] == 24]
    task_24_vars_unsat = [t for t in unsat_triple2idx.keys() if t[2] == 24]
    
    print(f"Task 24 variables in SAT case: {len(task_24_vars_sat)}")
    for var in task_24_vars_sat:
        print(f"  {var}")
    
    print(f"\nTask 24 variables in UNSAT case: {len(task_24_vars_unsat)}")
    for var in task_24_vars_unsat:
        print(f"  {var}")
    
    # Check the critical path - look at tasks with long durations
    vertex_set, edges, _ = cooking_graph(session)
    from computations_optimized import instruction_cooking_time, recipe_active_part
    
    active_recipe = recipe_active_part(session, now)
    def _inst(idx: int):
        return active_recipe.get(idx, session.recipe[idx])
    
    long_tasks = []
    for v in vertex_set:
        duration = instruction_cooking_time(_inst(v))
        if duration >= 20:  # Focus on longer tasks
            long_tasks.append((v, duration))
    
    long_tasks.sort(key=lambda x: x[1], reverse=True)
    print(f"\nLong duration tasks:")
    for task_id, duration in long_tasks:
        print(f"  Task {task_id}: {duration} units")
        
        # Check how many scheduling variables exist for this task
        sat_vars = [t for t in sat_triple2idx.keys() if t[2] == task_id]
        unsat_vars = [t for t in unsat_triple2idx.keys() if t[2] == task_id]
        
        print(f"    SAT variables: {len(sat_vars)}")
        print(f"    UNSAT variables: {len(unsat_vars)}")
        
        if len(sat_vars) > len(unsat_vars):
            print(f"    ❌ PROBLEM: SAT case has MORE variables than UNSAT case!")


def investigate_time_slot_issue():
    """Investigate the time slot allocation issue."""
    print("\n=== INVESTIGATING TIME SLOT ALLOCATION (UNIT TIME) ===\n")
    
    session = create_test_session()
    vertex_set, edges, _ = cooking_graph(session)
    
    # Look at the unit time slot calculation for both cases
    time_ub_sat = 86
    time_ub_unsat = 130
    now = 0
    
    from computations_optimized import recipe_active_part, instruction_cooking_time
    active_recipe = recipe_active_part(session, now)
    def _inst(idx: int):
        return active_recipe.get(idx, session.recipe[idx])
    
    print(f"Using unit time slots (no granularity)")
    
    # Compare unit time slots
    print(f"\nSAT case:")
    print(f"  Time_ub: {time_ub_sat}")
    print(f"  Time slots: 0 to {time_ub_sat-1}")
    
    print(f"\nUNSAT case:")
    print(f"  Time_ub: {time_ub_unsat}")
    print(f"  Time slots: 0 to {time_ub_unsat-1}")
    
    # Check if Task 24 (130 units) can fit in either case
    task_24_duration = 130
    
    print(f"\nTask 24 analysis:")
    print(f"  Duration: {task_24_duration}")
    print(f"  Can start at t=0 in SAT case: {0 + task_24_duration <= time_ub_sat}")
    print(f"  Can start at t=0 in UNSAT case: {0 + task_24_duration <= time_ub_unsat}")
    
    # Check all possible start times for Task 24
    sat_start_times = []
    unsat_start_times = []
    
    for t in range(time_ub_sat):
        if t + task_24_duration <= time_ub_sat:
            sat_start_times.append(t)
    
    for t in range(time_ub_unsat):
        if t + task_24_duration <= time_ub_unsat:
            unsat_start_times.append(t)
    
    print(f"  Valid start times in SAT case: {sat_start_times}")
    print(f"  Valid start times in UNSAT case: {unsat_start_times}")
    
    if len(sat_start_times) > len(unsat_start_times):
        print(f"  ❌ PROBLEM: SAT case has MORE start times than UNSAT case!")
    else:
        print(f"  ✅ Good: UNSAT case has more or equal start times ({len(unsat_start_times)} vs {len(sat_start_times)})")


def main():
    """Run the SAT clause analysis."""
    print("SAT CLAUSE ANALYSIS FOR NON-MONOTONIC BEHAVIOR")
    print("=" * 60)
    
    sat_encoding, unsat_encoding = compare_sat_encodings()
    analyze_specific_variables()
    investigate_time_slot_issue()
    
    print("\n" + "="*60)
    print("CONCLUSION")
    print("="*60)
    print("The analysis reveals the specific mechanism causing non-monotonic behavior.")
    print("The issue is in how the coarse time slots interact with task durations.")


if __name__ == "__main__":
    main()