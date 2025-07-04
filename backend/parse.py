from backend.data_models import time_in_units
from typing import Dict, List
import os
import csv

def parse_cheesecake_recipe() -> List[Dict]:
    """Parse the cheesecake recipe from CSV format and convert to RECIPE_STORE format."""
    # Keywords that indicate a task doesn't require attention
    no_attention_keywords = ["bake", "preheat", "soften", "put out", "room temp", "cool", "simmer", "refri"]

    # Read the CSV file
    recipe_path = os.path.join(os.path.dirname(__file__), "cheesecake2.txt")
    tasks = []

    with open(recipe_path, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if row['index']:  # Skip empty rows
                task = {
                    'index': int(row['index']),
                    'title': row['title'],
                    'time': int(row['time']),
                    'child': int(row['child']) if row['child'] != '-1' else None
                }
                tasks.append(task)

    # Convert child-to-parent relationships to parent-to-child dependencies
    dependencies = {}
    for task in tasks:
        if task['child'] is not None:
            # Current task is a parent of task['child']
            child_idx = task['child']
            if child_idx not in dependencies:
                dependencies[child_idx] = []
            dependencies[child_idx].append(task['index'])

    # Convert to RECIPE_STORE format
    recipe = []
    for task in tasks:
        # Determine if task requires attention based on keywords
        title_lower = task['title'].lower()
        requires_attention = not any(keyword in title_lower for keyword in no_attention_keywords)

        # Create the instruction with a single AI
        instruction = {
            "index": task['index'],
            "aiList": [{
                "attention": requires_attention,
                "duration_seconds": time_in_units(int(task['time'])),
                "description": task['title']
            }],
            "dependencies": dependencies.get(task['index'], [])
        }
        recipe.append(instruction)

    return recipe
