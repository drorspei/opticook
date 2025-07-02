#!/usr/bin/env python3
"""Fixed parallel search algorithms that work with Python's multiprocessing."""

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional, Tuple
import math

# Global functions that can be pickled

def _evaluate_point(point: int, tester_class: type, tester_args: dict) -> Tuple[int, bool]:
    """Evaluate a single point using the tester class."""
    tester = tester_class(**tester_args)
    result = tester(point)
    return point, result


def _find_transition_sequential(start: int, end: int, tester_class: type, tester_args: dict) -> Optional[int]:
    """Sequential binary search within an interval."""
    tester = tester_class(**tester_args)
    last = None
    lb, ub = start, end
    while lb <= ub:
        mid = (lb + ub) // 2
        res = tester(mid)
        if res:
            last = mid
            ub = mid - 1
        else:
            lb = mid + 1
    return last


class ParallelSearcher:
    """Base class for parallel search algorithms that use a callable class pattern."""

    def __init__(self, tester_class: type, tester_args: dict):
        """
        Initialize with a tester class and its initialization arguments.

        Args:
            tester_class: A class that implements __call__(self, t: int) -> bool
            tester_args: Dictionary of arguments to initialize the tester class
        """
        self.tester_class = tester_class
        self.tester_args = tester_args

    def sequential_search(self, lb: int, ub: int) -> Optional[int]:
        """Fallback sequential binary search."""
        tester = self.tester_class(**self.tester_args)
        last = None
        while lb <= ub:
            mid = (lb + ub) // 2
            res = tester(mid)
            if res:
                last = mid
                ub = mid - 1
            else:
                lb = mid + 1
        return last


class ParallelBinarySearcher(ParallelSearcher):
    """Parallel binary search implementation."""

    def search(self, lb: int, ub: int, num_cores: int = None) -> Optional[int]:
        if num_cores is None:
            num_cores = mp.cpu_count()

        if ub - lb < num_cores:
            return self.sequential_search(lb, ub)

        last_valid = None

        with ProcessPoolExecutor(max_workers=num_cores) as executor:
            while lb <= ub:
                # Calculate multiple test points
                range_size = ub - lb + 1
                if range_size <= num_cores:
                    test_points = list(range(lb, ub + 1))
                else:
                    step = range_size // (num_cores + 1)
                    test_points = [lb + (i + 1) * step for i in range(num_cores)]
                    test_points = [p for p in test_points if p <= ub]

                # Submit all evaluations in parallel
                futures = []
                for point in test_points:
                    future = executor.submit(_evaluate_point, point, self.tester_class, self.tester_args)
                    futures.append(future)

                # Collect results
                results = {}
                for future in as_completed(futures):
                    try:
                        point, result = future.result()
                        results[point] = result
                    except Exception as e:
                        print(f"Error evaluating point: {e}")

                # Find the highest point that returned True
                valid_points = [p for p in test_points if results.get(p, False)]

                if valid_points:
                    # Found at least one valid point
                    lowest_valid = min(valid_points)
                    if last_valid is None or lowest_valid < last_valid:
                        last_valid = lowest_valid
                    # Continue searching below the lowest valid point
                    ub = lowest_valid - 1
                else:
                    # No valid points found, search higher
                    if test_points:
                        highest_tested = max(test_points)
                        lb = highest_tested + 1
                    else:
                        break

        return last_valid


class ParallelIntervalSearcher(ParallelSearcher):
    """Parallel interval search implementation."""

    def search(self, lb: int, ub: int, num_cores: int = None) -> Optional[int]:
        if num_cores is None:
            num_cores = mp.cpu_count()

        if ub - lb < num_cores * 2:
            return self.sequential_search(lb, ub)

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
            futures = []
            for start, end in intervals:
                future = executor.submit(_find_transition_sequential, start, end,
                                       self.tester_class, self.tester_args)
                futures.append(future)

            # Collect results
            valid_results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result is not None:
                        valid_results.append(result)
                except Exception as e:
                    print(f"Error in interval search: {e}")

            # Return the minimum valid result
            return min(valid_results) if valid_results else None


class ParallelGoldenSectionSearcher(ParallelSearcher):
    """Parallel golden section search implementation."""

    def search(self, lb: int, ub: int, num_cores: Optional[int] = None) -> Optional[int]:
        if num_cores is None:
            num_cores = mp.cpu_count()

        if ub - lb < num_cores * 2:
            return self.sequential_search(lb, ub)

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
                    step = (point2 - point1) // (num_cores - 1)
                    for i in range(1, num_cores - 1):
                        test_points.append(point1 + i * step)

                # Remove duplicates and sort
                test_points = sorted(list(set(test_points)))

                # Evaluate all points in parallel
                futures = []
                for point in test_points:
                    future = executor.submit(_evaluate_point, point, self.tester_class, self.tester_args)
                    futures.append(future)

                results = {}
                for future in as_completed(futures):
                    try:
                        point, result = future.result()
                        results[point] = result
                    except Exception as e:
                        print(f"Error evaluating point: {e}")

                # Find valid points
                valid_points = [p for p in test_points if results.get(p, False)]

                if valid_points:
                    last_valid = min(valid_points)
                    ub = last_valid - 1
                else:
                    lb = max(test_points) + 1

            # Final sequential search for remaining range
            if lb <= ub:
                seq_result = self.sequential_search(lb, ub)
                if seq_result is not None:
                    last_valid = seq_result

        return last_valid


class AdaptiveParallelSearcher(ParallelSearcher):
    """Adaptive search that chooses the best strategy based on range size."""

    def search(self, lb: int, ub: int, num_cores: Optional[int] = None) -> Optional[int]:
        if num_cores is None:
            num_cores = mp.cpu_count()

        range_size = ub - lb + 1

        if range_size < num_cores * 2:
            # Small range: use sequential
            return self.sequential_search(lb, ub)
        elif range_size < num_cores * 10:
            # Medium range: use parallel binary search
            searcher = ParallelBinarySearcher(self.tester_class, self.tester_args)
            return searcher.search(lb, ub, num_cores)
        elif range_size < num_cores * 50:
            # Large range: use interval search
            searcher = ParallelIntervalSearcher(self.tester_class, self.tester_args)
            return searcher.search(lb, ub, num_cores)
        else:
            # Very large range: use golden section
            searcher = ParallelGoldenSectionSearcher(self.tester_class, self.tester_args)
            return searcher.search(lb, ub, num_cores)
