#!/usr/bin/env python3
"""Parallel search algorithms for finding optimal SAT solutions on multi-core machines."""

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, Optional, Tuple, List
import math
from functools import partial

def _binarysearch_sequential(f: Callable[[int], bool], lb: int, ub: int) -> Optional[int]:
    """Original sequential binary search for comparison."""
    last = None
    while lb <= ub:
        mid = (lb + ub) // 2
        res = f(mid)
        if res:
            last = mid
            ub = mid - 1
        else:
            lb = mid + 1
    return last


def parallel_binary_search(f: Callable[[int], bool], lb: int, ub: int, num_cores: int = None) -> Optional[int]:
    """
    Parallel binary search that evaluates multiple midpoints simultaneously.
    
    Strategy: At each level, evaluate multiple points in parallel to reduce
    the search space more quickly. Uses a divide-and-conquer approach.
    """
    if num_cores is None:
        num_cores = mp.cpu_count()
    
    if ub - lb < num_cores:
        # Fall back to sequential for small ranges
        return _binarysearch_sequential(f, lb, ub)
    
    last_valid = None
    
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        while lb <= ub:
            # Calculate multiple test points
            range_size = ub - lb + 1
            if range_size <= num_cores:
                # Test all remaining points
                test_points = list(range(lb, ub + 1))
            else:
                # Divide range into num_cores segments
                step = range_size // (num_cores + 1)
                test_points = [lb + (i + 1) * step for i in range(num_cores)]
                # Ensure we don't exceed bounds
                test_points = [p for p in test_points if p <= ub]
            
            # Submit all evaluations in parallel
            future_to_point = {executor.submit(f, point): point for point in test_points}
            
            # Collect results
            results = {}
            for future in as_completed(future_to_point):
                point = future_to_point[future]
                try:
                    results[point] = future.result()
                except Exception as e:
                    print(f"Error evaluating point {point}: {e}")
                    results[point] = False
            
            # Find the highest point that returned True
            valid_points = [p for p in test_points if results.get(p, False)]
            
            if valid_points:
                # Found at least one valid point
                highest_valid = max(valid_points)
                last_valid = highest_valid
                
                # Continue searching below the lowest valid point
                lowest_valid = min(valid_points)
                ub = lowest_valid - 1
            else:
                # No valid points found, search higher
                lowest_tested = min(test_points)
                lb = lowest_tested + 1
    
    return last_valid


def parallel_interval_search(f: Callable[[int], bool], lb: int, ub: int, num_cores: int = None) -> Optional[int]:
    """
    Parallel interval search that divides the range into chunks.
    
    Strategy: Divide the search space into num_cores intervals and search
    each in parallel. Then combine results and refine.
    """
    if num_cores is None:
        num_cores = mp.cpu_count()
    
    if ub - lb < num_cores * 2:
        # Fall back to sequential for small ranges
        return _binarysearch_sequential(f, lb, ub)
    
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        # Initial coarse search
        range_size = ub - lb + 1
        chunk_size = max(1, range_size // num_cores)
        
        # Create intervals
        intervals = []
        for i in range(num_cores):
            start = lb + i * chunk_size
            end = min(lb + (i + 1) * chunk_size - 1, ub)
            if start <= ub:
                intervals.append((start, end))
        
        # Search each interval for the transition point
        def find_transition_in_interval(interval: Tuple[int, int]) -> Optional[int]:
            start, end = interval
            # Binary search within the interval
            return _binarysearch_sequential(f, start, end)
        
        # Submit all interval searches
        future_to_interval = {
            executor.submit(find_transition_in_interval, interval): interval 
            for interval in intervals
        }
        
        # Collect results
        valid_results = []
        for future in as_completed(future_to_interval):
            try:
                result = future.result()
                if result is not None:
                    valid_results.append(result)
            except Exception as e:
                print(f"Error in interval search: {e}")
        
        # Return the minimum valid result
        return min(valid_results) if valid_results else None


def parallel_golden_section_search(f: Callable[[int], bool], lb: int, ub: int, num_cores: int = None) -> Optional[int]:
    """
    Parallel golden section search for finding the minimum valid time.
    
    Strategy: Use golden ratio to select test points that can be reused
    across iterations, evaluating multiple points in parallel.
    """
    if num_cores is None:
        num_cores = mp.cpu_count()
    
    if ub - lb < num_cores * 2:
        # Fall back to sequential for small ranges
        return _binarysearch_sequential(f, lb, ub)
    
    # Golden ratio
    phi = (1 + math.sqrt(5)) / 2
    inv_phi = 1 / phi
    
    last_valid = None
    
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        while ub - lb > num_cores:
            # Generate test points using golden ratio divisions
            test_points = []
            
            # Primary golden section points
            d = int((ub - lb) * inv_phi)
            point1 = lb + d
            point2 = ub - d
            test_points.extend([point1, point2])
            
            # Additional points for parallel evaluation
            if num_cores > 2:
                # Add intermediate points
                step = (point2 - point1) // (num_cores - 1)
                for i in range(1, num_cores - 1):
                    test_points.append(point1 + i * step)
            
            # Remove duplicates and sort
            test_points = sorted(list(set(test_points)))
            
            # Evaluate all points in parallel
            future_to_point = {executor.submit(f, point): point for point in test_points}
            
            results = {}
            for future in as_completed(future_to_point):
                point = future_to_point[future]
                try:
                    results[point] = future.result()
                except Exception as e:
                    print(f"Error evaluating point {point}: {e}")
                    results[point] = False
            
            # Find valid points
            valid_points = [p for p in test_points if results.get(p, False)]
            
            if valid_points:
                # Update last valid and narrow search to lower values
                last_valid = min(valid_points)
                ub = last_valid - 1
            else:
                # No valid points, search higher
                lb = max(test_points) + 1
        
        # Final sequential search for remaining range
        if lb <= ub:
            seq_result = _binarysearch_sequential(f, lb, ub)
            if seq_result is not None:
                last_valid = seq_result
    
    return last_valid


def speculative_execution_search(f: Callable[[int], bool], lb: int, ub: int, num_cores: int = None) -> Optional[int]:
    """
    Speculative execution search that predicts likely bounds and pre-computes.
    
    Strategy: Based on initial samples, predict where the transition point
    might be and speculatively evaluate nearby points in parallel.
    """
    if num_cores is None:
        num_cores = mp.cpu_count()
    
    if ub - lb < num_cores * 3:
        # Fall back to sequential for small ranges
        return _binarysearch_sequential(f, lb, ub)
    
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        # Phase 1: Initial sampling to estimate transition point
        sample_size = min(num_cores, (ub - lb) // 10 + 1)
        sample_step = (ub - lb) // sample_size
        sample_points = [lb + i * sample_step for i in range(sample_size)]
        sample_points.append(ub)  # Always include upper bound
        
        # Evaluate samples
        future_to_point = {executor.submit(f, point): point for point in sample_points}
        
        sample_results = {}
        for future in as_completed(future_to_point):
            point = future_to_point[future]
            try:
                sample_results[point] = future.result()
            except Exception as e:
                print(f"Error evaluating sample {point}: {e}")
                sample_results[point] = False
        
        # Find transition region based on samples
        valid_samples = sorted([p for p in sample_points if sample_results.get(p, False)])
        invalid_samples = sorted([p for p in sample_points if not sample_results.get(p, False)])
        
        if not valid_samples:
            # No valid points found
            return None
        
        if not invalid_samples:
            # All points valid, minimum is at lower bound
            return lb
        
        # Estimate transition region
        max_invalid = max(invalid_samples) if invalid_samples else lb - 1
        min_valid = min(valid_samples)
        
        # Phase 2: Focus search on transition region with speculative execution
        focus_lb = max(lb, max_invalid)
        focus_ub = min(ub, min_valid)
        
        # Use parallel binary search on focused region
        return parallel_binary_search(f, focus_lb, focus_ub, num_cores)


def adaptive_parallel_search(f: Callable[[int], bool], lb: int, ub: int, num_cores: int = None) -> Optional[int]:
    """
    Adaptive search that chooses the best parallel strategy based on range size.
    
    Strategy: Dynamically select between different parallel algorithms based
    on the characteristics of the search space.
    """
    if num_cores is None:
        num_cores = mp.cpu_count()
    
    range_size = ub - lb + 1
    
    if range_size < num_cores * 2:
        # Small range: use sequential
        return _binarysearch_sequential(f, lb, ub)
    elif range_size < num_cores * 10:
        # Medium range: use parallel binary search
        return parallel_binary_search(f, lb, ub, num_cores)
    elif range_size < num_cores * 50:
        # Large range: use interval search
        return parallel_interval_search(f, lb, ub, num_cores)
    else:
        # Very large range: use speculative execution
        return speculative_execution_search(f, lb, ub, num_cores)