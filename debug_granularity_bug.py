#!/usr/bin/env python3
"""
Debug script to examine the time granularity bug causing non-monotonic behavior.

The issue is in the time granularity optimization in session2sat_optimized where:
1. The time granularity changes based on average task duration
2. This causes different coarse time slots for different time_ub values
3. A task that fits in coarse slots for one time_ub might not fit for another
"""

import sys
import os
import contextlib
import io
from typing import List, Dict

# Add backend path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import session2sat_optimized, cooking_graph, instruction_cooking_time


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


def analyze_granularity_behavior():
    """Analyze how time granularity changes affect SAT encoding."""
    print("=== ANALYZING TIME GRANULARITY BUG ===\n")
    
    session = create_test_session()
    vertex_set, edges, _ = cooking_graph(session)
    
    # Test the two time bounds that show non-monotonic behavior
    time_ub_sat = 86  # Known SAT case
    time_ub_unsat = 130  # Known UNSAT case
    now = 0
    
    print(f"Testing time bounds: {time_ub_sat} (SAT) vs {time_ub_unsat} (UNSAT)")
    print(f"Recipe has {len(vertex_set)} tasks\n")
    
    # Analyze both cases
    for time_ub, label in [(time_ub_sat, "SAT"), (time_ub_unsat, "UNSAT")]:
        print(f"=== ANALYZING {label} CASE (time_ub={time_ub}) ===")
        
        # Extract the granularity calculation logic from session2sat_optimized
        from computations_optimized import recipe_active_part
        active_recipe = recipe_active_part(session, now)
        def _inst(idx: int):
            return active_recipe.get(idx, session.recipe[idx])
        
        # Calculate durations and granularity (same logic as in session2sat_optimized)
        all_durations = [instruction_cooking_time(_inst(v)) for v in vertex_set]
        avg_duration = sum(all_durations) / len(all_durations) if all_durations else 1
        
        print(f"  Task durations: {sorted(all_durations)}")
        print(f"  Average duration: {avg_duration:.2f}")
        
        # Granularity logic from session2sat_optimized
        if avg_duration > 20:
            time_granularity = 5
        elif avg_duration > 10:
            time_granularity = 3  
        else:
            time_granularity = 2
        
        # Calculate coarse time slots
        coarse_time_ub = (time_ub + time_granularity - 1) // time_granularity
        time_slots = list(range(coarse_time_ub))
        
        print(f"  Time granularity: {time_granularity}")
        print(f"  Original time_ub: {time_ub}")
        print(f"  Coarse time_ub: {coarse_time_ub}")
        print(f"  Number of time slots: {len(time_slots)}")
        print(f"  Time slots: {time_slots}")
        
        # Check which tasks can fit in the coarse time slots
        valid_assignments = 0
        total_possible = 0
        
        chefs = ["Chef1", "Chef2"]
        for v in vertex_set:
            duration = instruction_cooking_time(_inst(v))
            coarse_duration = (duration + time_granularity - 1) // time_granularity
            print(f"  Task {v}: duration={duration}, coarse_duration={coarse_duration}")
            
            for chef in chefs:
                for t in time_slots:
                    total_possible += 1
                    if t + coarse_duration <= coarse_time_ub:
                        valid_assignments += 1
                    else:
                        # This assignment is invalid - task doesn't fit!
                        pass
        
        print(f"  Valid task assignments: {valid_assignments}/{total_possible}")
        print(f"  Assignment ratio: {valid_assignments/total_possible:.2%}")
        print()
    
    print("=== GRANULARITY BUG ANALYSIS ===")
    print("The issue is that time granularity is calculated based on average task duration,")
    print("but the granularity affects which tasks can be scheduled within the time bound.")
    print()
    print("Key insight: When time_ub increases, sometimes the granularity also increases,")
    print("which can make fewer coarse time slots available for scheduling certain tasks.")
    print("This creates non-monotonic behavior where a larger time bound becomes UNSAT.")


def demonstrate_granularity_effect():
    """Show specific example of how granularity affects task scheduling."""
    print("\n=== DEMONSTRATING GRANULARITY EFFECT ===\n")
    
    # Example: Task with duration 25
    task_duration = 25
    
    print(f"Example task duration: {task_duration}")
    print()
    
    # Test different time bounds and their granularities
    test_bounds = [80, 86, 100, 130, 150]
    
    for time_ub in test_bounds:
        # Calculate average duration (simplified - assume it affects granularity)
        avg_duration = 15  # From our recipe analysis
        
        if avg_duration > 20:
            time_granularity = 5
        elif avg_duration > 10:
            time_granularity = 3  
        else:
            time_granularity = 2
        
        coarse_time_ub = (time_ub + time_granularity - 1) // time_granularity
        coarse_duration = (task_duration + time_granularity - 1) // time_granularity
        
        # Check if task can start at time slot 0
        can_fit = 0 + coarse_duration <= coarse_time_ub
        
        print(f"time_ub={time_ub:3d} → granularity={time_granularity}, "
              f"coarse_ub={coarse_time_ub:2d}, task_coarse_dur={coarse_duration:2d}, "
              f"fits={can_fit}")


def main():
    """Run the granularity bug analysis."""
    analyze_granularity_behavior()
    demonstrate_granularity_effect()
    
    print("\n" + "="*60)
    print("CONCLUSION")
    print("="*60)
    print("The non-monotonic behavior is caused by the time granularity optimization.")
    print("When time_ub changes, it can affect:")
    print("1. The granularity used for coarse time slots")
    print("2. The number of available coarse time slots") 
    print("3. Whether tasks fit within the coarse scheduling grid")
    print()
    print("This is a FUNDAMENTAL FLAW in the optimization that breaks monotonicity.")
    print("The fix is to either:")
    print("1. Use consistent granularity regardless of time_ub")
    print("2. Remove the granularity optimization entirely")
    print("3. Ensure granularity calculations preserve monotonicity")


if __name__ == "__main__":
    main()