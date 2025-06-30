#!/usr/bin/env python3
"""Quick test to verify the exact SAT encoding preserves monotonicity."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_parallel import create_test_session
from computations_exact import graph2solve_with_timeout_exact
import contextlib
import io


def test_exact_monotonicity():
    """Test that the exact encoding preserves monotonicity."""
    print("=== Testing Exact SAT Encoding Monotonicity ===\n")
    
    session = create_test_session(2)
    
    def test_time(t: int) -> bool:
        """Test if time t is satisfiable with exact encoding."""
        with contextlib.redirect_stderr(io.StringIO()):
            result = graph2solve_with_timeout_exact(session, t, 0, 30)
        return result is not False
    
    print("Finding minimum satisfiable time...")
    min_sat = None
    for t in range(50, 100):
        if test_time(t):
            min_sat = t
            print(f"First SAT at time: {min_sat}")
            break
        if t % 10 == 0:
            print(f"  Checked up to {t}...")
    
    if min_sat is None:
        print("No SAT found in range 50-100")
        return False
    
    print(f"\nTesting monotonicity from {min_sat} onwards...")
    violations = []
    
    # Test the next 20 time points after min_sat
    for t in range(min_sat + 1, min_sat + 21):
        if not test_time(t):
            violations.append(t)
            print(f"VIOLATION: SAT at {min_sat}, UNSAT at {t}")
    
    print(f"\nMonotonicity test results:")
    print(f"  Minimum SAT time: {min_sat}")
    print(f"  Violations found: {len(violations)}")
    
    if len(violations) == 0:
        print("✅ EXACT ENCODING PRESERVES MONOTONICITY")
        return True
    else:
        print("❌ EXACT ENCODING STILL HAS VIOLATIONS")
        print(f"   Violation times: {violations}")
        return False


def compare_performance():
    """Quick performance comparison between exact and optimized."""
    print("\n=== Performance Comparison ===\n")
    
    session = create_test_session(2)
    
    import time
    from computations_optimized import graph2solve_with_timeout
    
    test_time_point = 90
    
    # Test optimized version
    print(f"Testing optimized encoding at time {test_time_point}...")
    start = time.time()
    with contextlib.redirect_stderr(io.StringIO()):
        result_opt = graph2solve_with_timeout(session, test_time_point, 0, 30, True)
    time_opt = time.time() - start
    
    # Test exact version  
    print(f"Testing exact encoding at time {test_time_point}...")
    start = time.time()
    with contextlib.redirect_stderr(io.StringIO()):
        result_exact = graph2solve_with_timeout_exact(session, test_time_point, 0, 30)
    time_exact = time.time() - start
    
    print(f"\nResults:")
    print(f"  Optimized: {'SAT' if result_opt else 'UNSAT'} in {time_opt:.2f}s")
    print(f"  Exact:     {'SAT' if result_exact else 'UNSAT'} in {time_exact:.2f}s")
    print(f"  Slowdown:  {time_exact/time_opt:.2f}x")
    
    return time_exact / time_opt


def main():
    """Run monotonicity and performance tests."""
    monotonic = test_exact_monotonicity()
    slowdown = compare_performance()
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Monotonicity: {'✅ PRESERVED' if monotonic else '❌ VIOLATED'}")
    print(f"Performance:  {slowdown:.1f}x slower than optimized encoding")
    
    if monotonic:
        print("\n✅ EXACT ENCODING IS READY FOR BENCHMARKING")
    else:
        print("\n❌ NEED FURTHER FIXES")
    
    return monotonic


if __name__ == "__main__":
    main()