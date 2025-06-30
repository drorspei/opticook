#!/usr/bin/env python3
"""
Simple test for multi-task recipe without SAT solver dependencies.
This manually tests the session logic to see what's happening.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List
from dataclasses import asdict

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask, ActiveTask

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

def manual_assign_tasks(session: Session, current_time: int) -> Session:
    """Manually assign tasks to test the scenario"""
    from dataclasses import replace
    import copy
    
    # Manually assign instruction 0 to Alice and instruction 1 to Bob
    new_map = copy.deepcopy(session.cooking_map)
    
    # Alice gets instruction 0 (chop onions)
    if "Alice" not in new_map:
        new_map["Alice"] = {}
    new_map["Alice"][0] = ActiveTask(0, 0, current_time)
    
    # Bob gets instruction 1 (chop carrots)
    if "Bob" not in new_map:
        new_map["Bob"] = {}
    new_map["Bob"][1] = ActiveTask(1, 0, current_time)
    
    return replace(session, cooking_map=new_map)

def active_ai_done_simple(session: Session, chef: str, inst_index: int, now: int) -> Session:
    """Simplified version of active_ai_done without dependencies"""
    from dataclasses import replace
    import copy
    
    print(f"[DEBUG] active_ai_done: chef={chef}, inst_index={inst_index}, now={now}")
    if chef not in session.cooking_map or inst_index not in session.cooking_map[chef]:
        raise KeyError("No such active task for chef")

    task = session.cooking_map[chef][inst_index]
    ai_idx = task.ai_index
    print(f"[DEBUG] active_ai_done: current ai_idx={ai_idx}, total AIs={len(session.recipe[inst_index].aiList)}")

    # Ensure task.start_time is not None before using it
    if task.start_time is None:
        raise ValueError("Task has not started (start_time is None)")

    # update DoneTask list
    new_done_tasks = copy.deepcopy(session.done_tasks)
    if ai_idx == 0:
        new_done_tasks[inst_index] = DoneTask(inst_index, chef, [(task.start_time, now)])
    else:
        prev = session.done_tasks[inst_index].time_data
        new_done_tasks[inst_index] = DoneTask(inst_index, chef, prev + [(task.start_time, now)])

    # rebuild cooking_map
    new_map = copy.deepcopy(session.cooking_map)
    if ai_idx + 1 < len(session.recipe[inst_index].aiList):
        print(f"[DEBUG] active_ai_done: advancing to next AI (ai_idx + 1 = {ai_idx + 1})")
        new_map[chef][inst_index] = ActiveTask(inst_index, ai_idx + 1, now)
    else:
        print(f"[DEBUG] active_ai_done: instruction completed, removing from cooking_map")
        del new_map[chef][inst_index]
        if not new_map[chef]:
            del new_map[chef]

    return replace(session, cooking_map=new_map, done_tasks=new_done_tasks)

def test_manual_multi_task():
    """Test multi-task recipe with manual task assignment"""
    print("Testing multi-task recipe with MANUAL assignment...")
    
    # Create recipe and session
    recipe = create_multi_task_recipe()
    session = create_session(recipe, ["Alice", "Bob"])
    
    print(f"Recipe has {len(recipe)} instructions:")
    for i, inst in enumerate(recipe):
        print(f"  Instruction {i}: {len(inst.aiList)} AIs, dependencies: {inst.dependencies}")
        for j, ai in enumerate(inst.aiList):
            print(f"    AI {j}: attention={ai.attention}, duration={ai.duration}, desc='{ai.description}'")
    
    # Initial state - no one working
    print_session_state(session, "Initial State")
    
    # Simulate time progression
    current_time = 0
    
    # Manually assign tasks to both chefs at the start
    print(f"\n--- Manual assignment at time {current_time} ---")
    session = manual_assign_tasks(session, current_time)
    print_session_state(session, "After Manual Assignment")
    
    # Check that both chefs got tasks
    alice_tasks = session.cooking_map.get("Alice", {})
    bob_tasks = session.cooking_map.get("Bob", {})
    
    print(f"\nInitial assignment check:")
    print(f"Alice has {len(alice_tasks)} tasks: {list(alice_tasks.keys())}")
    print(f"Bob has {len(bob_tasks)} tasks: {list(bob_tasks.keys())}")
    
    if len(alice_tasks) == 0 or len(bob_tasks) == 0:
        print("❌ PROBLEM: Not both chefs got tasks!")
        return False
    else:
        print("✅ GOOD: Both chefs got tasks")
    
    # Simulate Alice finishing her first AI (chop onions - 60 seconds = 2 quanta)
    current_time += 2
    alice_inst = list(alice_tasks.keys())[0]
    print(f"\n--- Alice finishes AI at time {current_time} (instruction {alice_inst}) ---")
    session = active_ai_done_simple(session, "Alice", alice_inst, current_time)
    print_session_state(session, "After Alice finishes first AI")
    
    # Simulate Bob finishing his first AI (chop carrots - 90 seconds = 3 quanta)
    current_time += 1  # total 3 quanta
    bob_inst = list(bob_tasks.keys())[0]
    print(f"\n--- Bob finishes AI at time {current_time} (instruction {bob_inst}) ---")
    session = active_ai_done_simple(session, "Bob", bob_inst, current_time)
    print_session_state(session, "After Bob finishes first AI")
    
    # Both should now be on their second AIs (non-attention tasks)
    # Let them finish those too
    current_time += 1  # Alice's simmer (1 quantum)
    alice_inst = list(session.cooking_map.get("Alice", {}).keys())[0] if session.cooking_map.get("Alice") else None
    if alice_inst is not None:
        print(f"\n--- Alice finishes second AI at time {current_time} (instruction {alice_inst}) ---")
        session = active_ai_done_simple(session, "Alice", alice_inst, current_time)
        print_session_state(session, "After Alice finishes second AI")
    
    current_time += 1  # Bob's boil (1 quantum) 
    bob_inst = list(session.cooking_map.get("Bob", {}).keys())[0] if session.cooking_map.get("Bob") else None
    if bob_inst is not None:
        print(f"\n--- Bob finishes second AI at time {current_time} (instruction {bob_inst}) ---")
        session = active_ai_done_simple(session, "Bob", bob_inst, current_time)
        print_session_state(session, "After Bob finishes second AI")
    
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
    print("Testing Multi-Task Recipe Functionality (Manual)")
    print("="*60)
    
    success = test_manual_multi_task()
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"Manual test: {'✅ PASS' if success else '❌ FAIL'}")
    
    if success:
        print("\n✅ Basic recipe logic works correctly!")
        print("Now we need to test why the SAT solver isn't assigning both tasks initially...")
    else:
        print("\n❌ Basic recipe logic has problems!")