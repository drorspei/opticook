#!/usr/bin/env python3
"""Comprehensive tests to verify monotonicity is preserved in the fixed SAT encoding."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_parallel import create_test_session
from computations_optimized import graph2solve_with_timeout
from computations_fixed import graph2solve_with_timeout_fixed
import contextlib
import io
from typing import List, Tuple


class MonotonicityTester:
    """Test monotonicity for a given SAT solving function."""
    
    def __init__(self, session, solver_func, timeout=30):
        self.session = session
        self.solver_func = solver_func
        self.timeout = timeout
    
    def test_time(self, t: int) -> bool:
        """Test if time t is satisfiable."""
        with contextlib.redirect_stderr(io.StringIO()):
            result = self.solver_func(self.session, t, 0, self.timeout)
        return result is not False
    
    def find_violations(self, start: int, end: int, step: int = 1) -> List[Tuple[int, int]]:
        """Find monotonicity violations in the given range."""
        violations = []
        
        print(f"  Testing range {start} to {end} (step {step})...")
        
        # Find all SAT points
        sat_points = []
        for t in range(start, end + 1, step):
            if self.test_time(t):
                sat_points.append(t)
        
        print(f"  Found {len(sat_points)} SAT points: {sat_points[:10]}{'...' if len(sat_points) > 10 else ''}")
        
        # Check for violations: if t1 < t2 and t1 is SAT, then t2 must be SAT
        for i, t1 in enumerate(sat_points):
            # Check a few points after t1 to see if any are UNSAT
            for t2 in range(t1 + step, min(t1 + 20, end + 1), step):
                if not self.test_time(t2):
                    # Found violation: t1 is SAT but t2 > t1 is UNSAT
                    violations.append((t1, t2))
                    print(f"    VIOLATION: SAT at {t1}, UNSAT at {t2}")
                    break  # Don't check further for this t1
        
        return violations


def test_original_vs_fixed():
    """Compare original and fixed SAT encodings for monotonicity."""
    print("=== MONOTONICITY COMPARISON TEST ===\n")
    
    session = create_test_session(2)
    
    print("Testing ORIGINAL SAT encoding:")
    original_tester = MonotonicityTester(session, graph2solve_with_timeout)
    original_violations = original_tester.find_violations(80, 300, step=5)
    
    print(f"\nOriginal encoding violations: {len(original_violations)}")
    for t1, t2 in original_violations[:5]:  # Show first 5
        print(f"  SAT at {t1}, UNSAT at {t2}")
    
    print("\n" + "="*60)
    print("Testing FIXED SAT encoding:")
    fixed_tester = MonotonicityTester(session, graph2solve_with_timeout_fixed)
    fixed_violations = fixed_tester.find_violations(80, 300, step=5)
    
    print(f"\nFixed encoding violations: {len(fixed_violations)}")
    for t1, t2 in fixed_violations[:5]:  # Show first 5
        print(f"  SAT at {t1}, UNSAT at {t2}")
    
    print("\n" + "="*60)
    print("RESULTS:")
    print(f"Original encoding: {len(original_violations)} violations ❌")
    print(f"Fixed encoding: {len(fixed_violations)} violations {'✅' if len(fixed_violations) == 0 else '❌'}")
    
    return len(fixed_violations) == 0


def find_optimal_times():
    """Find the true optimal times using both encodings."""
    print("\n=== OPTIMAL TIME COMPARISON ===\n")
    
    session = create_test_session(2)
    
    # Test both encodings to find optimal times
    print("Finding optimal time with ORIGINAL encoding:")
    original_tester = MonotonicityTester(session, graph2solve_with_timeout)
    original_optimal = None
    for t in range(1, 400):
        if original_tester.test_time(t):
            original_optimal = t
            break
        if t % 20 == 0:
            print(f"  Checked up to {t}...")
    
    print(f"Original encoding optimal: {original_optimal}")
    
    print("\nFinding optimal time with FIXED encoding:")
    fixed_tester = MonotonicityTester(session, graph2solve_with_timeout_fixed)
    fixed_optimal = None
    for t in range(1, 400):
        if fixed_tester.test_time(t):
            fixed_optimal = t
            break
        if t % 20 == 0:
            print(f"  Checked up to {t}...")
    
    print(f"Fixed encoding optimal: {fixed_optimal}")
    
    # Verify both solutions are actually valid
    if original_optimal:
        print(f"\nVerifying original optimal {original_optimal} with fixed encoding:")
        is_valid = fixed_tester.test_time(original_optimal)
        print(f"  {original_optimal} is {'valid' if is_valid else 'INVALID'} in fixed encoding")
    
    if fixed_optimal:
        print(f"\nVerifying fixed optimal {fixed_optimal} with original encoding:")
        is_valid = original_tester.test_time(fixed_optimal)
        print(f"  {fixed_optimal} is {'valid' if is_valid else 'INVALID'} in original encoding")
    
    return original_optimal, fixed_optimal


def main():
    """Run comprehensive monotonicity tests."""
    print("COMPREHENSIVE MONOTONICITY VERIFICATION")
    print("="*60)
    
    # Test 1: Check if fixed encoding preserves monotonicity
    monotonic = test_original_vs_fixed()
    
    # Test 2: Compare optimal solutions
    original_opt, fixed_opt = find_optimal_times()
    
    # Final assessment
    print("\n" + "="*60)
    print("FINAL ASSESSMENT")
    print("="*60)
    
    if monotonic:
        print("✅ MONOTONICITY: Fixed encoding preserves monotonicity")
    else:
        print("❌ MONOTONICITY: Fixed encoding still has violations")
    
    if original_opt and fixed_opt:
        if fixed_opt <= original_opt:
            print(f"✅ OPTIMALITY: Fixed encoding finds better or equal solution ({fixed_opt} vs {original_opt})")
        else:
            print(f"❌ OPTIMALITY: Fixed encoding finds worse solution ({fixed_opt} vs {original_opt})")
    
    print(f"\nRecommendation: {'Use fixed encoding' if monotonic else 'Need further fixes'}")
    
    return monotonic


if __name__ == "__main__":
    main()