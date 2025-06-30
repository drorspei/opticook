#!/usr/bin/env python3
"""
Test script for multi-task recipe functionality.
This tests that both Alice and Bob get tasks at the beginning,
and proper task progression through the cooking session.
"""

import time
from typing import Dict, List
from dataclasses import asdict

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import active_ai_done, refresh_session
from computations import active_ai_done as active_ai_done_old, refresh_session as refresh_session_old

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
    
    # Convert to CookingInstruction format (same as start_session in main.py)
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

def print_session_state(session: Session, title: str = "Session State"):
    """Print current session state for debugging"""
    print(f"\n=== {title} ===")
    print(f"Chefs: {list(session.chefs_data.keys())}")
    print(f"Cooking map: {session.cooking_map}")
    print(f"Done tasks: {list(session.done_tasks.keys())}")
    
    # Show what each chef is working on
    for chef_name in session.chefs_data:
        if chef_name in session.cooking_map and session.cooking_map[chef_name]:
            tasks = session.cooking_map[chef_name]
            for inst_idx, task in tasks.items():
                ai = session.recipe[inst_idx].aiList[task.ai_index]
                print(f"  {chef_name} -> instruction {inst_idx}, AI {task.ai_index}: {ai.description}")
        else:
            print(f"  {chef_name} -> idle")

def test_multi_task_recipe_optimized():
    """Test multi-task recipe with optimized computations"""
    print("Testing multi-task recipe with OPTIMIZED computations...")
    
    # Create recipe and session
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    # Initial state - no one working
    print_session_state(session, "Initial State")
    
    # Simulate time progression
    current_time = 0
    
    # First refresh - should assign tasks to both chefs
    print(f"\n--- Refresh at time {current_time} ---")
    session = refresh_session(session, current_time)
    print_session_state(session, "After First Refresh")
    
    # Check that both chefs got tasks
    alice_tasks = session.cooking_map.get("Alice", {})
    bob_tasks = session.cooking_map.get("Bob", {})
    
    print(f"\nInitial assignment check:")
    print(f"Alice has {len(alice_tasks)} tasks: {list(alice_tasks.keys())}")
    print(f"Bob has {len(bob_tasks)} tasks: {list(bob_tasks.keys())}")
    
    if len(alice_tasks) == 0 or len(bob_tasks) == 0:
        print("❌ PROBLEM: Not both chefs got tasks immediately!")
        return False
    else:
        print("✅ GOOD: Both chefs got tasks immediately")
    
    # Simulate Alice finishing her first AI (chop onions - 60 seconds = 2 quanta)
    current_time += 2
    alice_inst = list(alice_tasks.keys())[0]
    print(f"\n--- Alice finishes AI at time {current_time} (instruction {alice_inst}) ---")
    session = active_ai_done(session, "Alice", alice_inst, current_time)
    print_session_state(session, "After Alice finishes first AI")
    
    # Simulate Bob finishing his first AI (chop carrots - 90 seconds = 3 quanta)
    current_time += 1  # total 3 quanta
    bob_inst = list(bob_tasks.keys())[0]
    print(f"\n--- Bob finishes AI at time {current_time} (instruction {bob_inst}) ---")
    session = active_ai_done(session, "Bob", bob_inst, current_time)
    print_session_state(session, "After Bob finishes first AI")
    
    # Both should now be on their second AIs (non-attention tasks)
    # Let them finish those too
    current_time += 1  # Alice's simmer (1 quantum)
    alice_inst = list(session.cooking_map.get("Alice", {}).keys())[0] if session.cooking_map.get("Alice") else None
    if alice_inst is not None:
        print(f"\n--- Alice finishes second AI at time {current_time} (instruction {alice_inst}) ---")
        session = active_ai_done(session, "Alice", alice_inst, current_time)
        print_session_state(session, "After Alice finishes second AI")
    
    current_time += 1  # Bob's boil (1 quantum) 
    bob_inst = list(session.cooking_map.get("Bob", {}).keys())[0] if session.cooking_map.get("Bob") else None
    if bob_inst is not None:
        print(f"\n--- Bob finishes second AI at time {current_time} (instruction {bob_inst}) ---")
        session = active_ai_done(session, "Bob", bob_inst, current_time)
        print_session_state(session, "After Bob finishes second AI")
    
    # Final refresh - should show no more tasks
    print(f"\n--- Final refresh at time {current_time} ---")
    session = refresh_session(session, current_time)
    print_session_state(session, "Final State")
    
    # Check that recipe is complete
    active_chefs = sum(1 for chef_tasks in session.cooking_map.values() if chef_tasks)
    completed_instructions = len(session.done_tasks)
    
    print(f"\nFinal check:")
    print(f"Active chefs: {active_chefs}")
    print(f"Completed instructions: {completed_instructions}/2")
    
    if active_chefs == 0 and completed_instructions == 2:
        print("✅ SUCCESS: Recipe completed successfully!")
        return True
    else:
        print("❌ PROBLEM: Recipe not completed properly")
        return False

def test_multi_task_recipe_old():
    """Test multi-task recipe with old computations"""
    print("\n" + "="*60)
    print("Testing multi-task recipe with OLD computations...")
    
    # Create recipe and session
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    # Initial state - no one working
    print_session_state(session, "Initial State")
    
    # Simulate time progression
    current_time = 0
    
    # First refresh - should assign tasks to both chefs
    print(f"\n--- Refresh at time {current_time} ---")
    session = refresh_session_old(session, current_time)
    print_session_state(session, "After First Refresh")
    
    # Check that both chefs got tasks
    alice_tasks = session.cooking_map.get("Alice", {})
    bob_tasks = session.cooking_map.get("Bob", {})
    
    print(f"\nInitial assignment check:")
    print(f"Alice has {len(alice_tasks)} tasks: {list(alice_tasks.keys())}")
    print(f"Bob has {len(bob_tasks)} tasks: {list(bob_tasks.keys())}")
    
    if len(alice_tasks) == 0 or len(bob_tasks) == 0:
        print("❌ PROBLEM: Not both chefs got tasks immediately!")
        return False
    else:
        print("✅ GOOD: Both chefs got tasks immediately")
    
    # Simulate Alice finishing her first AI (chop onions - 60 seconds = 2 quanta)
    current_time += 2
    alice_inst = list(alice_tasks.keys())[0]
    print(f"\n--- Alice finishes AI at time {current_time} (instruction {alice_inst}) ---")
    session = active_ai_done_old(session, "Alice", alice_inst, current_time)
    print_session_state(session, "After Alice finishes first AI")
    
    # Simulate Bob finishing his first AI (chop carrots - 90 seconds = 3 quanta)
    current_time += 1  # total 3 quanta
    bob_inst = list(bob_tasks.keys())[0]
    print(f"\n--- Bob finishes AI at time {current_time} (instruction {bob_inst}) ---")
    session = active_ai_done_old(session, "Bob", bob_inst, current_time)
    print_session_state(session, "After Bob finishes first AI")
    
    # Both should now be on their second AIs (non-attention tasks)
    # Let them finish those too
    current_time += 1  # Alice's simmer (1 quantum)
    alice_inst = list(session.cooking_map.get("Alice", {}).keys())[0] if session.cooking_map.get("Alice") else None
    if alice_inst is not None:
        print(f"\n--- Alice finishes second AI at time {current_time} (instruction {alice_inst}) ---")
        session = active_ai_done_old(session, "Alice", alice_inst, current_time)
        print_session_state(session, "After Alice finishes second AI")
    
    current_time += 1  # Bob's boil (1 quantum) 
    bob_inst = list(session.cooking_map.get("Bob", {}).keys())[0] if session.cooking_map.get("Bob") else None
    if bob_inst is not None:
        print(f"\n--- Bob finishes second AI at time {current_time} (instruction {bob_inst}) ---")
        session = active_ai_done_old(session, "Bob", bob_inst, current_time)
        print_session_state(session, "After Bob finishes second AI")
    
    # Final refresh - should show no more tasks
    print(f"\n--- Final refresh at time {current_time} ---")
    session = refresh_session_old(session, current_time)
    print_session_state(session, "Final State")
    
    # Check that recipe is complete
    active_chefs = sum(1 for chef_tasks in session.cooking_map.values() if chef_tasks)
    completed_instructions = len(session.done_tasks)
    
    print(f"\nFinal check:")
    print(f"Active chefs: {active_chefs}")
    print(f"Completed instructions: {completed_instructions}/2")
    
    if active_chefs == 0 and completed_instructions == 2:
        print("✅ SUCCESS: Recipe completed successfully!")
        return True
    else:
        print("❌ PROBLEM: Recipe not completed properly")
        return False

if __name__ == "__main__":
    print("Testing Multi-Task Recipe Functionality")
    print("="*60)
    
    # Test both versions
    optimized_success = test_multi_task_recipe_optimized()
    old_success = test_multi_task_recipe_old()
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"Optimized version: {'✅ PASS' if optimized_success else '❌ FAIL'}")
    print(f"Old version: {'✅ PASS' if old_success else '❌ FAIL'}")
    
    if optimized_success and old_success:
        print("\n✅ Both versions work correctly!")
    elif optimized_success and not old_success:
        print("\n⚠️  Only optimized version works - old version has issues")
    elif not optimized_success and old_success:
        print("\n⚠️  Only old version works - optimized version has issues")
    else:
        print("\n❌ Both versions have problems!")