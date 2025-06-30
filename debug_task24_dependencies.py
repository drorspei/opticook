#!/usr/bin/env python3
"""
Debug Task 24 specifically to understand why it causes UNSAT when included.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import cooking_graph, instruction_cooking_time, recipe_active_part


def create_test_session():
    """Create test session using the cheesecake recipe."""
    from main import parse_cheesecake_recipe
    raw_recipe = parse_cheesecake_recipe()
    
    # Build CookingInstruction list
    cis = []
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
    done_tasks = {}
    
    return Session(cis, chefs_data, cooking_map, done_tasks)


def analyze_task24_dependencies():
    """Analyze Task 24 and its dependency chain."""
    print("=== ANALYZING TASK 24 DEPENDENCY CHAIN ===\n")
    
    session = create_test_session()
    vertex_set, edges, _ = cooking_graph(session)
    
    active_recipe = recipe_active_part(session, 0)
    def _inst(idx: int):
        return active_recipe.get(idx, session.recipe[idx])
    
    # Find Task 24 and trace its dependencies
    task_24 = session.recipe[24]
    print(f"Task 24: {task_24.aiList[0].description}")
    print(f"Duration: {instruction_cooking_time(_inst(24))} units")
    print(f"Dependencies: {task_24.dependencies}")
    
    # Build dependency chain backwards from Task 24
    def get_all_dependencies(task_id, visited=None):
        if visited is None:
            visited = set()
        if task_id in visited:
            return set()  # Avoid cycles
        visited.add(task_id)
        
        deps = set()
        task = session.recipe[task_id]
        for dep in task.dependencies:
            deps.add(dep)
            deps.update(get_all_dependencies(dep, visited.copy()))
        return deps
    
    all_deps = get_all_dependencies(24)
    print(f"\nAll dependencies of Task 24: {sorted(all_deps)}")
    
    # Calculate minimum time needed for all dependencies
    print(f"\nDependency analysis:")
    total_dep_time = 0
    for dep_id in sorted(all_deps):
        dep_task = session.recipe[dep_id]
        dep_duration = instruction_cooking_time(_inst(dep_id))
        print(f"  Task {dep_id}: {dep_duration} units - {dep_task.aiList[0].description}")
        total_dep_time += dep_duration
    
    print(f"\nTotal dependency time (if sequential): {total_dep_time} units")
    
    # Calculate critical path
    def calculate_earliest_start(task_id, memo=None):
        if memo is None:
            memo = {}
        if task_id in memo:
            return memo[task_id]
        
        task = session.recipe[task_id]
        max_dep_end = 0
        
        for dep_id in task.dependencies:
            dep_start = calculate_earliest_start(dep_id, memo)
            dep_duration = instruction_cooking_time(_inst(dep_id))
            dep_end = dep_start + dep_duration
            max_dep_end = max(max_dep_end, dep_end)
        
        memo[task_id] = max_dep_end
        return max_dep_end
    
    task_24_earliest = calculate_earliest_start(24)
    task_24_duration = instruction_cooking_time(_inst(24))
    task_24_earliest_end = task_24_earliest + task_24_duration
    
    print(f"\nCritical path analysis:")
    print(f"  Task 24 earliest start: {task_24_earliest} units")
    print(f"  Task 24 duration: {task_24_duration} units") 
    print(f"  Task 24 earliest end: {task_24_earliest_end} units")
    
    print(f"\nTime bound analysis:")
    print(f"  time_ub=86: Task 24 can fit? {task_24_earliest_end <= 86}")
    print(f"  time_ub=130: Task 24 can fit? {task_24_earliest_end <= 130}")
    
    # The key insight: Task 24 needs ALL its dependencies to complete first
    # If the critical path makes it impossible to complete in the given time,
    # then including Task 24 makes the problem UNSAT
    
    return task_24_earliest_end


def analyze_without_task24():
    """Analyze if the recipe can be completed without Task 24."""
    print("\n=== ANALYZING RECIPE WITHOUT TASK 24 ===\n")
    
    session = create_test_session()
    vertex_set, edges, _ = cooking_graph(session)
    
    active_recipe = recipe_active_part(session, 0)
    def _inst(idx: int):
        return active_recipe.get(idx, session.recipe[idx])
    
    # Find tasks that depend on Task 24
    tasks_depending_on_24 = []
    for task in session.recipe:
        if 24 in task.dependencies:
            tasks_depending_on_24.append(task.index)
    
    print(f"Tasks that depend on Task 24: {tasks_depending_on_24}")
    
    # Find tasks that are dependencies of Task 24  
    task_24_deps = session.recipe[24].dependencies
    print(f"Task 24 depends on: {task_24_deps}")
    
    # If we remove Task 24 and its dependents, can the rest be completed?
    excluded_tasks = {24} | set(tasks_depending_on_24)
    remaining_tasks = vertex_set - excluded_tasks
    
    print(f"Excluded tasks: {sorted(excluded_tasks)}")
    print(f"Remaining tasks: {sorted(remaining_tasks)}")
    
    # Calculate time needed for remaining tasks
    total_time = sum(instruction_cooking_time(_inst(t)) for t in remaining_tasks)
    print(f"Total time for remaining tasks (sequential): {total_time} units")
    
    # This explains why time_ub=86 is SAT: it excludes Task 24 and dependents,
    # making the problem much simpler and solvable
    
    return excluded_tasks, remaining_tasks


def main():
    """Analyze the Task 24 dependency issue."""
    print("TASK 24 DEPENDENCY ANALYSIS")
    print("=" * 50)
    
    critical_path_end = analyze_task24_dependencies()
    excluded, remaining = analyze_without_task24()
    
    print("\n" + "="*50)
    print("CONCLUSION")
    print("="*50)
    print(f"Task 24 has a critical path ending at {critical_path_end} units.")
    print(f"When time_ub=86: Task 24 is excluded (cannot fit), making problem simpler → SAT")
    print(f"When time_ub=130: Task 24 is included (can fit), but creates impossible constraints → UNSAT")
    print(f"")
    print(f"The non-monotonic behavior occurs because:")
    print(f"1. Task 24 has complex dependencies that take time to complete")
    print(f"2. Including Task 24 in the SAT problem adds mandatory constraints")
    print(f"3. These constraints may be unsatisfiable even with more time")
    print(f"4. Excluding Task 24 (when it doesn't fit) makes a simpler, solvable problem")


if __name__ == "__main__":
    main()