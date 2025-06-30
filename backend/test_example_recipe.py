#!/usr/bin/env python3
"""Quick test to verify the Example Recipe works after memoization fixes."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict
from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations import sat_search

def create_example_recipe_session() -> Session:
    """Create a session with the example recipe from RECIPE_STORE."""
    from main import RECIPE_STORE
    
    raw_recipe = RECIPE_STORE["example_recipe"]
    
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

def test_example_recipe():
    """Test that the example recipe works without crashing."""
    print("Testing Example Recipe...")
    
    session = create_example_recipe_session()
    
    try:
        solution = sat_search(session, now=0, timeout=30)
        if solution:
            print(f"✅ Success! Found solution with {len(solution)} assignments")
            for chef, start_time, task in solution[:5]:  # Show first 5
                print(f"  {chef} starts task {task} at time {start_time}")
        else:
            print("✅ Success! No solution found (but no crash)")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_example_recipe()
    if success:
        print("\n🎉 Example Recipe test passed!")
    else:
        print("\n💥 Example Recipe test failed!")
        sys.exit(1)