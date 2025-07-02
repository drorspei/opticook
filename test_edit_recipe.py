import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"

def test_edit_recipe():
    # First, add a new recipe
    add_payload = {
        "recipe_name": "Test Recipe Edit",
        "instructions": [
            {
                "aiList": [
                    {
                        "description": "Original step 1",
                        "attention": True,
                        "duration_seconds": 60
                    }
                ],
                "dependencies": []
            }
        ]
    }
    
    print("1. Adding new recipe...")
    response = requests.post(f"{BASE_URL}/recipes/add", json=add_payload)
    print(f"Response: {response.status_code} - {response.json()}")
    
    if response.status_code != 200:
        print("Failed to add recipe")
        return
    
    # Get the recipe to verify it was added
    print("\n2. Getting recipe...")
    response = requests.get(f"{BASE_URL}/session/current/recipes/Test Recipe Edit")
    print(f"Response: {response.status_code}")
    print(f"Original recipe: {json.dumps(response.json(), indent=2)}")
    
    # Update the recipe
    update_payload = {
        "recipe_name": "Test Recipe Edit",
        "instructions": [
            {
                "aiList": [
                    {
                        "description": "Updated step 1",
                        "attention": False,
                        "duration_seconds": 90
                    },
                    {
                        "description": "New step 2",
                        "attention": True,
                        "duration_seconds": 30
                    }
                ],
                "dependencies": []
            },
            {
                "aiList": [
                    {
                        "description": "New instruction 2",
                        "attention": True,
                        "duration_seconds": 120
                    }
                ],
                "dependencies": [0]
            }
        ]
    }
    
    print("\n3. Updating recipe...")
    response = requests.put(f"{BASE_URL}/recipes/Test Recipe Edit", json=update_payload)
    print(f"Response: {response.status_code} - {response.json()}")
    
    # Get the recipe again to verify update
    print("\n4. Getting updated recipe...")
    response = requests.get(f"{BASE_URL}/session/current/recipes/Test Recipe Edit")
    print(f"Response: {response.status_code}")
    print(f"Updated recipe: {json.dumps(response.json(), indent=2)}")
    
    # Test updating a built-in recipe (should fail)
    print("\n5. Testing update of built-in recipe (should fail)...")
    response = requests.put(f"{BASE_URL}/recipes/example_recipe", json=update_payload)
    print(f"Response: {response.status_code} - {response.json()}")

if __name__ == "__main__":
    test_edit_recipe()