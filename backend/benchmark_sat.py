#!/usr/bin/env python3
"""Benchmark script for SAT solver performance on the cheesecake recipe."""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict
from data_models import Chef, AtomicInstruction, CookingInstruction, Session, time_in_units, DoneTask
from computations_optimized import sat_search, session2sat_optimized, satSolve, cooking_graph

def load_cheesecake_recipe():
    """Load the cheesecake recipe from main.py."""
    from main import parse_cheesecake_recipe
    return parse_cheesecake_recipe()

def create_test_session(num_chefs: int = 2) -> Session:
    """Create a test session with the cheesecake recipe."""
    raw_recipe = load_cheesecake_recipe()
    
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

def benchmark_sat_solver(session: Session, iterations: int = 3):
    """Benchmark the SAT solver performance."""
    print(f"Benchmarking SAT solver with {len(session.recipe)} tasks and {len(session.chefs_data)} chefs...")
    print(f"Running {iterations} iterations...\n")
    
    times = []
    for i in range(iterations):
        print(f"Iteration {i+1}/{iterations}")
        
        # Time the SAT solving
        start_time = time.time()
        solution = sat_search(session, now=0, timeout=300)  # 5 minute timeout
        end_time = time.time()
        
        elapsed = end_time - start_time
        times.append(elapsed)
        
        if solution:
            print(f"  Found solution in {elapsed:.2f} seconds")
            print(f"  Solution has {len(solution)} assignments")
        else:
            print(f"  No solution found (timeout or unsatisfiable) after {elapsed:.2f} seconds")
        print()
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"\nAverage time: {avg_time:.2f} seconds")
        print(f"Min time: {min(times):.2f} seconds")
        print(f"Max time: {max(times):.2f} seconds")

def analyze_sat_encoding(session: Session):
    """Analyze the SAT encoding to understand clause counts."""
    print("Analyzing SAT encoding...")
    
    vertices, edges, time_ub = cooking_graph(session)
    print(f"  Graph vertices: {len(vertices)}")
    print(f"  Graph edges: {len(edges)}")
    print(f"  Time upper bound: {time_ub}")
    
    # Generate SAT encoding (using optimized version)
    triple2idx, clauses = session2sat_optimized(session, time_ub, now=0)
    
    print(f"\nSAT encoding statistics:")
    print(f"  Total variables: {len(triple2idx)}")
    print(f"  Total clauses: {len(clauses)}")
    
    # Analyze clause types
    clause_lengths = {}
    for clause in clauses:
        length = len(clause)
        clause_lengths[length] = clause_lengths.get(length, 0) + 1
    
    print(f"\nClause length distribution:")
    for length in sorted(clause_lengths.keys()):
        print(f"  Length {length}: {clause_lengths[length]} clauses")

def main():
    """Main benchmark function."""
    print("=== SAT Solver Benchmark for Cheesecake Recipe ===\n")
    
    # Test with different numbers of chefs
    for num_chefs in [2, 3]:
        print(f"\n--- Testing with {num_chefs} chefs ---")
        session = create_test_session(num_chefs)
        
        # Analyze the encoding
        analyze_sat_encoding(session)
        
        # Run benchmark
        benchmark_sat_solver(session, iterations=3)
        print("-" * 50)

if __name__ == "__main__":
    main()