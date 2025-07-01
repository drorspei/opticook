#!/usr/bin/env python3
"""Test that timer displays show correct recipe times."""

import time
from dataclasses import asdict
from main import _current_session, app, RECIPE_STORE
from data_models import Chef, AtomicInstruction, CookingInstruction, Session
from computations_seconds import refresh_session

def test_timer_display():
    """Test that timers show the original recipe durations."""
    print("Testing timer display for Example Recipe...")
    
    # Reset any existing session
    global _current_session
    _current_session = None
    
    # Create session with Example Recipe (60s chop onions, 30s simmer)
    raw_recipe = RECIPE_STORE["example_recipe"]
    print(f"Raw recipe: {raw_recipe}")
    
    # Build session the same way as main.py
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
    
    # Initialize session with one chef
    chefs_data = {"Alice": Chef("Alice", heartbeat=None)}
    cooking_map = {"Alice": {}}
    done_tasks = {}
    session = Session(cis, chefs_data, cooking_map, done_tasks)
    
    print(f"Session AI durations: {[ai.duration for ai in cis[0].aiList]}")
    
    # Refresh session to assign task  
    # Use relative time starting from 0
    start_time = 0.0
    refreshed_session = refresh_session(session, start_time)
    
    print(f"After refresh:")
    for chef_name, tasks in refreshed_session.cooking_map.items():
        for inst_idx, active_task in tasks.items():
            ai = refreshed_session.recipe[inst_idx].aiList[active_task.ai_index]
            print(f"  {chef_name}: {ai.description}")
            print(f"    - Recipe duration: {ai.duration} seconds")
            print(f"    - Task start time: {active_task.start_time}")
            
            # Simulate what the frontend timer calculation would do
            current_time = start_time + 10  # 10 seconds later
            elapsed = current_time - active_task.start_time
            remaining = max(0, ai.duration - elapsed)
            
            print(f"    - After 10 seconds:")
            print(f"      Elapsed: {elapsed} seconds")
            print(f"      Remaining: {remaining} seconds")
            
            # Check if remaining time makes sense
            expected_remaining = ai.duration - 10  # Should be 50 seconds for 60s task
            if abs(remaining - expected_remaining) < 1:
                print(f"    ✓ Timer calculation correct!")
                return True
            else:
                print(f"    ✗ Timer calculation wrong! Expected ~{expected_remaining}, got {remaining}")
                return False
    
    print("✗ No active tasks found")
    return False

if __name__ == "__main__":
    success = test_timer_display()
    exit(0 if success else 1)