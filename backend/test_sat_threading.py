#!/usr/bin/env python3
"""
Test script for SAT solver threading implementation.
"""

import time
import threading
from data_models import Chef, AtomicInstruction, CookingInstruction, Session, DoneTask
from sat_solver_thread import SATSolverThread

def create_test_session():
    """Create a simple test session with a basic recipe."""
    recipe = [
        CookingInstruction(
            index=0,
            aiList=[
                AtomicInstruction(attention=True, duration=60, description='chop onions'),
                AtomicInstruction(attention=False, duration=30, description='simmer')
            ],
            dependencies=[]
        ),
        CookingInstruction(
            index=1,
            aiList=[
                AtomicInstruction(attention=True, duration=90, description='chop carrots'),
                AtomicInstruction(attention=False, duration=45, description='boil carrots')
            ],
            dependencies=[]
        )
    ]
    
    chefs_data = {
        'Alice': Chef(name='Alice', addr=None, heartbeat=None, disconnected=False),
        'Bob': Chef(name='Bob', addr=None, heartbeat=None, disconnected=False)
    }
    
    cooking_map = {'Alice': {}, 'Bob': {}}
    done_tasks = {}
    
    return Session(recipe, chefs_data, cooking_map, done_tasks)

def test_sat_solver_thread():
    """Test the SAT solver thread functionality."""
    print("Creating test session...")
    session = create_test_session()
    
    print("Starting SAT solver thread...")
    sat_thread = SATSolverThread()
    sat_thread.start(session)
    
    # Let it run for a few seconds
    print("Letting SAT solver run for 5 seconds...")
    time.sleep(5)
    
    # Check stats
    stats = sat_thread.get_stats()
    print(f"SAT solver stats: {stats}")
    
    # Refresh session to assign tasks
    print("Refreshing session to assign tasks...")
    from computations import refresh_session, active_ai_done
    session = refresh_session(session, now=0)
    
    # Find a chef with an active task
    chef_with_task = None
    task_index = None
    for chef, tasks in session.cooking_map.items():
        if tasks:
            chef_with_task = chef
            task_index = next(iter(tasks.keys()))
            break
    if chef_with_task is None:
        raise RuntimeError("No chef was assigned a task after refresh. Test cannot proceed.")
    print(f"Simulating chef '{chef_with_task}' finishing task {task_index}...")
    new_session = active_ai_done(session, chef_with_task, task_index, 120)  # Simulate completion
    
    # Interrupt and restart SAT solver
    print("Interrupting and restarting SAT solver...")
    sat_thread.interrupt_and_restart(new_session)
    
    # Let it run for a few more seconds
    print("Letting SAT solver run for 3 more seconds...")
    time.sleep(3)
    
    # Check updated stats
    stats = sat_thread.get_stats()
    print(f"Updated SAT solver stats: {stats}")
    
    # Stop the thread
    print("Stopping SAT solver thread...")
    sat_thread.stop()
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_sat_solver_thread() 