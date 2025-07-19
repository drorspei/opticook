import traceback
import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import litellm  # pip install litellm
from bs4 import BeautifulSoup
import re

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

def retrieve_recipe_from_url(url, llm_model="gpt-4.1-nano", api_key=None):
    """
    Retrieve and process a recipe from a given URL.
    Step 1: Extract recipe JSON-LD from the page.
    Step 2: Use LLM (litellm) to convert to session.recipe format in two phases.
    Returns the recipe structure or False on failure.
    """
    try:
        print(f"[DEBUG] Step 1: Getting soup from URL: {url}")
        soup = get_soup_from_url(url)
        if not soup:
            print("[ERROR] Failed to get soup from URL.")
            return False
        print("[DEBUG] Step 2: Extracting JSON-LD data")
        jsonld = get_yoast_jsonld(soup)
        if not jsonld:
            print("[ERROR] Failed to extract JSON-LD data.")
            return False
        print("[DEBUG] Step 3: Finding recipe object in JSON-LD")
        recipe_obj = find_recipe_object(jsonld)
        if not recipe_obj:
            print("[ERROR] Failed to find recipe object in JSON-LD.")
            return False
        # Phase 1: LLM to extract ci steps
        phase1_prompt = f"""
You are given a recipe in JSON-LD format extracted from a web page.\nYour task is to extract the main cooking steps as a list of \"ci\" (CookingInstruction) objects.\nEach \"ci\" should have:\n- A list of \"ai\" (AtomicInstruction) steps, each with:\n  - description (short, clear, imperative)\n  - duration_seconds (estimate in seconds)\n  - attention (true if the cook must actively attend, false if it can be left alone)\n- Any dependencies (list of indices of other ci that must be completed first)\n\nOutput a JSON list of ci objects, each with the above structure.\nOnly include steps relevant to the actual cooking process (skip serving, cleaning, etc).\n\nHere is the JSON-LD recipe data:\n{json.dumps(recipe_obj, indent=2)}\n"""
        print("[DEBUG] Step 4: Calling LLM for Phase 1 (ci extraction)")
        try:
            phase1_response = litellm.completion(
                model=llm_model,
                messages=[{"role": "user", "content": phase1_prompt}],
                max_tokens=2048,
                temperature=0.2,
                **({"api_key": api_key} if api_key else {})
            )
            ci_json = phase1_response["choices"][0]["message"]["content"]
            print(f"[DEBUG] LLM raw output (Phase 1): {ci_json!r}")
            # Try to extract JSON from code block if present
            match = re.search(r"```json\\s*(.*?)```", ci_json, re.DOTALL)
            if match:
                ci_json = match.group(1)
            else:
                # Try to extract the first JSON array in the string
                start = ci_json.find('[')
                end = ci_json.rfind(']')
                if start != -1 and end != -1 and end > start:
                    ci_json = ci_json[start:end+1]
            ci_list = json.loads(ci_json)
        except Exception as e:
            print(f"[ERROR] LLM Phase 1 failed: {e}")
            return False
        # Filter ci_list to only those where all ai have attention == false
        ci_no_attention = []
        for i, ci in enumerate(ci_list):
            if all(ai.get('attention') == False for ai in ci.get('ai', [])):
                ci_no_attention.append((i, ci))
        print(f"[DEBUG] Passing {len(ci_no_attention)} ci with no attention to Phase 2 LLM")

        for i, ci in enumerate(ci_list):
            pos = 0
            ais = ci.get("ai", [])
            while pos < len(ais):
                ai = ais[pos]
                pos += 1
                if ai.get('attention', True):
                    continue


                # --- Phase 2: LLM breakdown of ai steps, all at once ---
                # We want to break each non-attention ai step into 3 parts: init with attention, main w/o attention, short final with attenion

                prompt = f'''Given the following cooking instruction, which mostly doesn't require the chef's attention (e.g. "bake for 40 minutes"), break it down into two steps:
    a short initialization step with a single verb (e.g. place in the the oven), and a main part that requires no attention that uses a passive verb (e.g. let it bake for 40 minutes).
    Use the object of the original sentence in both steps.
    Reply with a JSON object with the two fields "initialization", "main".
    Here is the sentence:

    {ai}'''
                try:
                    resp = litellm.completion(
                        model=llm_model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=2048,
                        temperature=0.2,
                        **({"api_key": api_key} if api_key else {})
                    )
                    j = json.loads(resp.choices[0].message.content.replace("```json", "```").split("```", 1)[-1].split("```", 1)[0])
                    init, main = j['initialization'], j['main']
                except Exception:
                    # print stack
                    print(f"[DEBUG] Error occurred while processing AI step {ai}")
                    print(traceback.format_exc())
                    continue

                ais[pos-1:pos] = [
                    {
                        "duration_seconds": 30,
                        "attention": True,
                        "description": init
                    },
                    {
                        "duration_seconds": ai.get("duration_seconds"),
                        "attention": False,
                        "description": main
                    },
                ]
                pos += 1


        # # phase2_results is the list of processed ci objects
        # ai_list = phase2_results if phase2_results else ci_list
        print("[DEBUG] Successfully retrieved and processed recipe.")
        return ci_list
    except Exception as e:
        print(f"[ERROR] Unexpected error in retrieve_recipe_from_url: {e}")
        return False
