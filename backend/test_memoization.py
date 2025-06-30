#!/usr/bin/env python3
"""Test memoization functionality in computations_optimized.py."""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_models import CookingInstruction, AtomicInstruction
from computations_optimized import (
    instruction_cooking_time, attention_span, _at_most_one_sequential,
    _instruction_cooking_time_cached, _attention_span_cached
)

def test_instruction_cooking_time_memoization():
    """Test that instruction_cooking_time caching works."""
    # Create test instruction
    ai1 = AtomicInstruction(True, 30, "chop onions")
    ai2 = AtomicInstruction(False, 60, "simmer")
    inst = CookingInstruction(0, [ai1, ai2], [])
    
    # First call - should compute
    start = time.time()
    result1 = instruction_cooking_time(inst)
    time1 = time.time() - start
    
    # Second call - should use cache
    start = time.time()
    result2 = instruction_cooking_time(inst)
    time2 = time.time() - start
    
    assert result1 == result2 == 90, f"Expected 90, got {result1}, {result2}"
    print(f"instruction_cooking_time: first call {time1:.6f}s, second call {time2:.6f}s")
    
    # Check cache info
    cache_info = _instruction_cooking_time_cached.cache_info()
    print(f"Cache info: {cache_info}")
    assert cache_info.hits >= 1, "Should have at least 1 cache hit"

def test_attention_span_memoization():
    """Test that attention_span caching works."""
    # Create test instruction with attention spans
    ai1 = AtomicInstruction(True, 30, "chop onions")
    ai2 = AtomicInstruction(False, 60, "simmer")
    ai3 = AtomicInstruction(True, 20, "stir")
    inst = CookingInstruction(0, [ai1, ai2, ai3], [])
    
    # First call
    start = time.time()
    result1 = attention_span(inst)
    time1 = time.time() - start
    
    # Second call - should use cache
    start = time.time()
    result2 = attention_span(inst)
    time2 = time.time() - start
    
    expected = [(0, 30), (90, 110)]
    assert result1 == result2 == expected, f"Expected {expected}, got {result1}, {result2}"
    print(f"attention_span: first call {time1:.6f}s, second call {time2:.6f}s")
    
    # Check cache info
    cache_info = _attention_span_cached.cache_info()
    print(f"Cache info: {cache_info}")
    assert cache_info.hits >= 1, "Should have at least 1 cache hit"

def test_at_most_one_sequential_memoization():
    """Test that _at_most_one_sequential caching works."""
    variables = (1, 5, 10, 15, 20)
    
    # First call
    start = time.time()
    result1 = _at_most_one_sequential(variables)
    time1 = time.time() - start
    
    # Second call - should use cache
    start = time.time()
    result2 = _at_most_one_sequential(variables)
    time2 = time.time() - start
    
    assert result1 == result2, "Results should be identical"
    assert len(result1) > 0, "Should generate some clauses"
    print(f"_at_most_one_sequential: first call {time1:.6f}s, second call {time2:.6f}s")
    print(f"Generated {len(result1)} clauses for {len(variables)} variables")
    
    # Check cache info
    cache_info = _at_most_one_sequential.cache_info()
    print(f"Cache info: {cache_info}")
    assert cache_info.hits >= 1, "Should have at least 1 cache hit"

def test_cache_size_limit():
    """Test that cache respects the 1000 element limit."""
    # Generate many different instructions to test cache eviction
    for i in range(1200):  # More than cache size
        ai = AtomicInstruction(True, i % 100 + 1, f"task_{i}")
        inst = CookingInstruction(i, [ai], [])
        instruction_cooking_time(inst)
    
    cache_info = _instruction_cooking_time_cached.cache_info()
    print(f"After 1200 calls: {cache_info}")
    
    # Cache should not exceed maxsize
    assert cache_info.currsize <= 1000, f"Cache size {cache_info.currsize} exceeds limit of 1000"
    print(f"Cache size properly limited to {cache_info.currsize} <= 1000")

if __name__ == "__main__":
    print("Testing memoization in computations_optimized.py...")
    
    test_instruction_cooking_time_memoization()
    print()
    
    test_attention_span_memoization()
    print()
    
    test_at_most_one_sequential_memoization()
    print()
    
    test_cache_size_limit()
    print()
    
    print("All memoization tests passed! 🎉")