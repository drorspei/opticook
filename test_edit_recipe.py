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
    
    # Test renaming a recipe
    rename_payload = {
        "recipe_name": "Test Recipe Edit Renamed",
        "instructions": update_payload["instructions"]
    }
    
    print("\n6. Testing recipe rename...")
    response = requests.put(f"{BASE_URL}/recipes/Test Recipe Edit", json=rename_payload)
    print(f"Response: {response.status_code} - {response.json()}")
    
    # Verify the old name no longer exists
    print("\n7. Checking old recipe name (should be 404)...")
    response = requests.get(f"{BASE_URL}/session/current/recipes/Test Recipe Edit")
    print(f"Response: {response.status_code}")
    
    # Verify the new name exists
    print("\n8. Getting renamed recipe...")
    response = requests.get(f"{BASE_URL}/session/current/recipes/Test Recipe Edit Renamed")
    print(f"Response: {response.status_code}")
    print(f"Renamed recipe: {json.dumps(response.json(), indent=2)}")
    
    # Test deleting a built-in recipe (should fail)
    print("\n9. Testing delete of built-in recipe (should fail)...")
    response = requests.delete(f"{BASE_URL}/recipes/example_recipe")
    print(f"Response: {response.status_code} - {response.json()}")
    
    # Test deleting the renamed recipe
    print("\n10. Testing delete of custom recipe...")
    response = requests.delete(f"{BASE_URL}/recipes/Test Recipe Edit Renamed")
    print(f"Response: {response.status_code} - {response.json()}")
    
    # Verify the recipe is deleted
    print("\n11. Checking deleted recipe (should be 404)...")
    response = requests.get(f"{BASE_URL}/session/current/recipes/Test Recipe Edit Renamed")
    print(f"Response: {response.status_code}")
    
    # List all recipes to confirm deletion
    print("\n12. Listing all recipes...")
    response = requests.get(f"{BASE_URL}/session/current/recipes")
    print(f"Response: {response.status_code}")
    print(f"Available recipes: {response.json()}")

if __name__ == "__main__":
    test_edit_recipe()