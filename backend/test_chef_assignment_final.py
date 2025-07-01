#!/usr/bin/env python3
"""Test that only one chef gets assigned per instruction when starting a recipe."""

import sys
from dataclasses import asdict
from main import _current_session, app
from data_models import Chef, AtomicInstruction, CookingInstruction, Session
from computations_seconds import refresh_session

def test_single_chef_assignment():
    """Test that only one chef gets assigned per instruction."""
    print("Testing single chef assignment for Example Recipe...")
    
    # Reset any existing session
    global _current_session
    _current_session = None
    
    # Create session with Example Recipe
    from main import RECIPE_STORE
    raw_recipe = RECIPE_STORE["example_recipe"]
    
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
    
    print(f"Initial session: 2 chefs, recipe={[ai.description for ai in cis[0].aiList]}")
    
    # Refresh session to trigger task assignment
    current_time = 0.0
    refreshed_session = refresh_session(session, current_time)
    
    print(f"After refresh:")
    
    # Count how many chefs got assigned tasks
    total_assignments = 0
    chop_onions_assignments = 0
    
    for chef_name, tasks in refreshed_session.cooking_map.items():
        if tasks:
            total_assignments += len(tasks)
            print(f"  {chef_name}: {len(tasks)} task(s)")
            for inst_idx, active_task in tasks.items():
                if inst_idx == 0 and active_task.ai_index == 0:
                    chop_onions_assignments += 1
                    print(f"    - Instruction {inst_idx}: {cis[inst_idx].aiList[active_task.ai_index].description}")
        else:
            print(f"  {chef_name}: no tasks")
    
    # Verify exactly one chef got the "chop onions" task
    if chop_onions_assignments == 0:
        print("✗ FAIL: No chef was assigned 'chop onions'")
        return False
    elif chop_onions_assignments == 1:
        print("✓ SUCCESS: Exactly one chef was assigned 'chop onions'")
        return True
    else:
        print(f"✗ FAIL: {chop_onions_assignments} chefs were assigned 'chop onions' (should be 1)")
        return False

if __name__ == "__main__":
    success = test_single_chef_assignment()
    sys.exit(0 if success else 1)