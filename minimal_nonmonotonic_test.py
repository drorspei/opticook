#!/usr/bin/env python3
"""
Minimal test case to reproduce non-monotonic SAT behavior.

The bug occurs when a lower time bound is satisfiable but a higher time bound is not.
This happens due to how the SAT solver handles resource allocation and timing constraints.
"""

import sys
import os
import contextlib
import io
from typing import List, Dict

# Add backend path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import graph2solve_with_timeout


def create_minimal_nonmonotonic_recipe() -> List[Dict]:
    """
    Create a recipe that exhibits non-monotonic SAT behavior.
    
    This recipe creates complex dependencies and resource conflicts that can lead to 
    non-monotonic behavior in the SAT solver due to how constraints interact.
    """
    return [
        # Parallel prep tasks that create resource conflicts
        {
            "index": 0,
            "aiList": [{
                "attention": True,
                "duration_seconds": 180,  # 3 minutes
                "description": "prep vegetables"
            }],
            "dependencies": []
        },
        {
            "index": 1,
            "aiList": [{
                "attention": True,
                "duration_seconds": 240,  # 4 minutes
                "description": "prep meat"
            }],
            "dependencies": []
        },
        # Background tasks
        {
            "index": 2,
            "aiList": [{
                "attention": False,
                "duration_seconds": 600,  # 10 minutes bake
                "description": "preheat oven"
            }],
            "dependencies": []
        },
        {
            "index": 3,
            "aiList": [{
                "attention": False,
                "duration_seconds": 900,  # 15 minutes
                "description": "marinate meat"
            }],
            "dependencies": [1]  # depends on meat prep
        },
        # Tasks that need attention after background tasks
        {
            "index": 4,
            "aiList": [{
                "attention": True,
                "duration_seconds": 120,  # 2 minutes
                "description": "season vegetables"
            }],
            "dependencies": [0, 2]  # needs veggies and hot oven
        },
        {
            "index": 5,
            "aiList": [{
                "attention": True,
                "duration_seconds": 90,  # 1.5 minutes
                "description": "sear meat"
            }],
            "dependencies": [3]  # needs marinated meat
        },
        # Final assembly requiring multiple completed tasks
        {
            "index": 6,
            "aiList": [{
                "attention": True,
                "duration_seconds": 300,  # 5 minutes
                "description": "combine and cook"
            }],
            "dependencies": [4, 5]  # needs both seasoned veggies and seared meat
        },
        # Final background cooking
        {
            "index": 7,
            "aiList": [{
                "attention": False,
                "duration_seconds": 1200,  # 20 minutes final cook
                "description": "final bake"
            }],
            "dependencies": [6]
        },
        # Final attention task
        {
            "index": 8,
            "aiList": [{
                "attention": True,
                "duration_seconds": 60,  # 1 minute
                "description": "garnish and serve"
            }],
            "dependencies": [7]
        }
    ]


def create_test_session(num_chefs: int = 2) -> Session:
    """Create a test session with the minimal recipe."""
    raw_recipe = create_minimal_nonmonotonic_recipe()
    
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


def test_time_satisfiable(session: Session, t: int, timeout: int = 30) -> bool:
    """Test if time t is satisfiable with the given session."""
    with contextlib.redirect_stderr(io.StringIO()):
        result = graph2solve_with_timeout(session, t, 0, timeout, use_optimized=True)
    return result is not False


def find_nonmonotonic_behavior():
    """Search for non-monotonic behavior using the cheesecake recipe."""
    print("=== Testing Cheesecake Recipe for Non-Monotonic Behavior ===\n")
    
    # Use the actual cheesecake recipe that's known to have the bug
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
    
    session = Session(cis, chefs_data, cooking_map, done_tasks)
    
    print("Recipe structure:")
    for i, task in enumerate(session.recipe):
        deps = task.dependencies if task.dependencies else "None"
        duration = sum(ai.duration for ai in task.aiList)
        attention = any(ai.attention for ai in task.aiList)
        print(f"  Task {i}: {duration}s, attention={attention}, deps={deps}")
    print()
    
    # Test a range of time bounds to find non-monotonic behavior
    print("Testing time bounds for SAT/UNSAT...")
    results = {}
    
    # Test times around the critical range where non-monotonic behavior occurs
    # Based on previous tests, focus on 80-120 time units range
    test_times = list(range(80, 140, 2))
    
    for t_units in test_times:
        t_seconds = t_units / 10  # Convert back to seconds for display
        is_sat = test_time_satisfiable(session, t_units)
        results[t_units] = is_sat
        status = "SAT" if is_sat else "UNSAT"
        print(f"  Time {t_seconds:5.1f}s ({t_units:3d} units): {status}")
    
    # Look for violations: SAT at t1 but UNSAT at t2 where t2 > t1
    violations = []
    sat_times = [t for t, is_sat in results.items() if is_sat]
    
    for t1 in sat_times:
        for t2 in sorted(results.keys()):
            if t2 > t1 and not results[t2]:
                violations.append((t1, t2))
                break  # Only need first violation for each SAT time
    
    print(f"\nNon-monotonic violations found: {len(violations)}")
    for t1, t2 in violations[:5]:  # Show first 5
        t1_sec = t1 / 10
        t2_sec = t2 / 10
        print(f"  SAT at {t1_sec}s but UNSAT at {t2_sec}s")
    
    if violations:
        print("\n✅ SUCCESS: Found non-monotonic behavior in minimal recipe!")
        print("This can be used to debug and fix the SAT solver.")
        
        # Test a specific violation in detail
        t1, t2 = violations[0]
        print(f"\nTesting violation in detail:")
        print(f"  Time {t1/10}s: {'SAT' if test_time_satisfiable(session, t1) else 'UNSAT'}")
        print(f"  Time {t2/10}s: {'SAT' if test_time_satisfiable(session, t2) else 'UNSAT'}")
        
        return True
    else:
        print("\n❌ No non-monotonic behavior found with this recipe.")
        print("May need to adjust the recipe structure or parameters.")
        return False


def verify_with_different_chef_counts():
    """Test the recipe with different numbers of chefs."""
    print("\n=== Testing with Different Chef Counts ===\n")
    
    for num_chefs in [1, 2, 3]:
        print(f"Testing with {num_chefs} chef(s):")
        session = create_test_session(num_chefs)
        
        # Test a few specific times
        test_times = [time_in_units(2400), time_in_units(3000), time_in_units(3600), time_in_units(4200)]
        for t in test_times:
            is_sat = test_time_satisfiable(session, t)
            status = "SAT" if is_sat else "UNSAT"
            print(f"  {t/10:5.1f}s: {status}")
        print()


def main():
    """Run the minimal non-monotonic test."""
    print("MINIMAL NON-MONOTONIC SAT TEST")
    print("=" * 50)
    
    # Test 1: Look for non-monotonic behavior
    found_violations = find_nonmonotonic_behavior()
    
    # Test 2: Check with different chef counts
    verify_with_different_chef_counts()
    
    # Summary
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    if found_violations:
        print("✅ Successfully reproduced non-monotonic SAT behavior")
        print("This minimal recipe can be used for debugging the SAT solver")
    else:
        print("❌ Could not reproduce non-monotonic behavior")
        print("Try adjusting recipe parameters or using the full cheesecake recipe")
    
    return found_violations


if __name__ == "__main__":
    main()