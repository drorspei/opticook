#!/usr/bin/env python3
"""
Test a very simple SAT problem to verify the fundamental logic.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from computations_optimized import satSolve

def test_simple_sat():
    """Test simple SAT problems to verify basic logic"""
    print("Testing simple SAT problems...")
    
    # Test 1: Basic satisfiable problem
    # Variables: 1, 2
    # Constraints: at least one must be true
    triple2idx = {("A", 0): 1, ("B", 1): 2}
    clauses = [[1, 2]]  # 1 OR 2
    
    print("\nTest 1: Basic OR constraint")
    print(f"Variables: {triple2idx}")
    print(f"Clauses: {clauses}")
    
    solution = satSolve(clauses, triple2idx)
    print(f"Solution: {solution}")
    
    # Test 2: Our specific problem - at least one of each instruction
    # Variables: 
    #   1: Alice does inst 0
    #   2: Bob does inst 0  
    #   3: Alice does inst 1
    #   4: Bob does inst 1
    # Constraints:
    #   - At least one does inst 0: 1 OR 2
    #   - At least one does inst 1: 3 OR 4
    #   - Each inst at most once: NOT (1 AND 2), NOT (3 AND 4)
    triple2idx2 = {
        ("Alice", 0): 1,   # Alice does inst 0
        ("Bob", 0): 2,     # Bob does inst 0
        ("Alice", 1): 3,   # Alice does inst 1
        ("Bob", 1): 4      # Bob does inst 1
    }
    
    clauses2 = [
        [1, 2],      # At least one does inst 0
        [3, 4],      # At least one does inst 1
        [-1, -2],    # At most one does inst 0
        [-3, -4]     # At most one does inst 1
    ]
    
    print("\nTest 2: Our problem structure")
    print(f"Variables: {triple2idx2}")
    print(f"Clauses: {clauses2}")
    
    solution2 = satSolve(clauses2, triple2idx2)
    print(f"Solution: {solution2}")
    
    # Test 3: Our specific problem with attention constraints
    # Same variables as Test 2, but add attention constraints:
    #   - Alice can do at most one attention task: NOT (1 AND 3)
    #   - Bob can do at most one attention task: NOT (2 AND 4)
    
    clauses3 = [
        [1, 2],      # At least one does inst 0
        [3, 4],      # At least one does inst 1
        [-1, -2],    # At most one does inst 0
        [-3, -4],    # At most one does inst 1
        [-1, -3],    # Alice: at most one attention task
        [-2, -4]     # Bob: at most one attention task
    ]
    
    print("\nTest 3: With attention constraints")
    print(f"Variables: {triple2idx2}")
    print(f"Clauses: {clauses3}")
    
    solution3 = satSolve(clauses3, triple2idx2)
    print(f"Solution: {solution3}")
    
    # Test what our expected solution does
    expected = [("Alice", 0), ("Bob", 1)]  # Alice does inst 0, Bob does inst 1
    expected_vars = [1, 4]  # Variables 1 and 4
    
    print(f"\nOur expected solution would set variables: {expected_vars}")
    
    # Check each clause
    for i, clause in enumerate(clauses3):
        satisfied = any(
            (var > 0 and var in expected_vars) or (var < 0 and abs(var) not in expected_vars)
            for var in clause
        )
        print(f"Clause {i}: {clause} -> {'✅' if satisfied else '❌'}")

if __name__ == "__main__":
    test_simple_sat()