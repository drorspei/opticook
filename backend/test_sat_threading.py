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
    
    # Simulate a chef finishing a task
    print("Simulating chef finishing a task...")
    from computations import active_ai_done
    new_session = active_ai_done(session, 'Alice', 0, 120)  # Alice finishes task 0 at time 120
    
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