#!/usr/bin/env python3
"""Analyze the cheesecake recipe structure."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import parse_cheesecake_recipe

def analyze_recipe():
    recipe = parse_cheesecake_recipe()
    print(f"Total tasks: {len(recipe)}")
    
    # Count attention vs non-attention tasks
    attention_tasks = sum(1 for task in recipe if task["aiList"][0]["attention"])
    non_attention_tasks = len(recipe) - attention_tasks
    
    print(f"Attention tasks: {attention_tasks}")
    print(f"Non-attention tasks: {non_attention_tasks}")
    
    # Calculate total time
    total_time = sum(task["aiList"][0]["duration_seconds"] for task in recipe)
    print(f"Total time in seconds: {total_time}")
    print(f"Total time in minutes: {total_time / 60:.1f}")
    print(f"Total time in hours: {total_time / 3600:.1f}")
    
    # Count dependencies
    total_deps = sum(len(task["dependencies"]) for task in recipe)
    print(f"\nTotal dependencies: {total_deps}")
    
    # Find long tasks
    print("\nLongest tasks:")
    sorted_tasks = sorted(recipe, key=lambda t: t["aiList"][0]["duration_seconds"], reverse=True)
    for task in sorted_tasks[:5]:
        duration = task["aiList"][0]["duration_seconds"]
        print(f"  Task {task['index']}: {task['aiList'][0]['description']} - {duration}s ({duration/60:.1f}m)")

if __name__ == "__main__":
    analyze_recipe()