import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import litellm  # pip install litellm
from bs4 import BeautifulSoup

# === 1. Extract soup from URL using Selenium ===
def get_soup_from_url(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(4)  # let page load fully; increase if site is slow
    html = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html, "html.parser")
    return soup

# === 2. Get the JSON data using BeautifulSoup ===
def get_yoast_jsonld(soup):
    script = soup.find("script", class_="yoast-schema-graph", type="application/ld+json")
    if script is not None:
        return json.loads(script.string)
    return None

# === 3. Find the recipe in the JSON-LD data ===
def find_recipe_object(data):
    # Yoast typically puts things in @graph
    if isinstance(data, dict) and "@graph" in data:
        for entry in data["@graph"]:
            if isinstance(entry, dict) and entry.get("@type") == "Recipe":
                return entry
    # Fallback: top-level recipe
    if isinstance(data, dict) and data.get("@type") == "Recipe":
        return data
    return None

# === 4. Contact ChatGPT API with recipe details and prompt ===
def ask_chatgpt_for_structured_steps(recipe, model="gpt-4o"):
    prompt = (
        "Given the following recipe (in JSON), break down the instructions into a clear JSON array. "
        "Each line (object) should correspond to a single cooking task/step and contain:\n"
        "- a unique step number\n"
        "- the instruction for the task\n"
        "- an estimated time for the task (in minutes or hours)\n"
        "- a list of step numbers it depends on (i.e., which previous steps must be finished first)\n"
        "Return ONLY the resulting JSON array, with one object per step.\n\n"
        "Recipe JSON:\n"
        f"{json.dumps(recipe, indent=2)}"
    )
    messages = [
        {"role": "system", "content": "You are an expert chef and helpful kitchen assistant."},
        {"role": "user", "content": prompt}
    ]

    # we need to move to using "tools", so the return value should be a JSON array with the same structure every time
    # this means passing a "schema"
    response = litellm.completion(
        model=model,
        messages=messages,
        max_tokens=1024,
        temperature=0.3
    )
    return response["choices"][0]["message"]["content"]


def save_recipe_to_file(recipe, filename="extracted_recipe.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(recipe, f, indent=2, ensure_ascii=False)
    print(f"Recipe data saved to {filename}")

# === Main Function ===
def main(url, model=os.getenv("LLM_MODEL", "openai/gpt-4o")):
    print("using model:", model)
    print("Loading page...")
    soup = get_soup_from_url(url)
    print("Extracting Yoast JSON-LD...")
    jsonld = get_yoast_jsonld(soup)
    if jsonld is None:
        print("Could not find Yoast JSON-LD data.")
        return
    print("Looking for recipe object...")
    recipe = find_recipe_object(jsonld)
    if recipe is None:
        print("Could not find recipe in JSON-LD data.")
        return
    save_recipe_to_file(recipe)
    print("Recipe saved")

    print("Calling LLM...")
    steps_json = ask_chatgpt_for_structured_steps(recipe, model)
    print("Structured steps from ChatGPT:\n")
    print(steps_json)

# === Usage Example ===
if __name__ == "__main__":
    # Example usage: Replace with your OpenAI API key!
    # OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # or paste directly (not recommended for security)
    #URL = "https://meaningfuleats.com/gluten-free-cheesecake/"
    #URL = "https://meaningfuleats.com/chewy-gluten-free-brownies/"
    URL = "https://www.spendwithpennies.com/homemade-bolognese-sauce/"
    rec = main(URL)
