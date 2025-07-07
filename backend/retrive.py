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

def retrieve_recipe_from_url(url, llm_model="gpt-4.1-nano"):
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
        for ci in ci_list:
            if all(ai.get('attention') == False for ai in ci.get('ai', [])):
                ci_no_attention.append(ci)
        print(f"[DEBUG] Passing {len(ci_no_attention)} ci with no attention to Phase 2 LLM")
        # --- Phase 2: LLM breakdown of ai steps, all at once ---
        if ci_no_attention:
            phase2_prompt = (
                "Given the following list of ci (CookingInstruction) objects, where all ai (AtomicInstruction) steps have attention == false, "
                "break each ai into three parts: (1) a short initialization ai, (2) the main non-attention ai, and (3) a short finalizing ai. "
                "Return ONLY a valid JSON list of ci objects, each with the same structure, with no explanation, comments, or extra text. "
                "The output must be valid JSON, suitable for parsing with Python's json.loads(). "
                "Do not include any trailing commas. Make sure all brackets and braces are closed. "
                "Double-check that every { has a matching } and every [ has a matching ]. If you are unsure, reformat the output to be valid JSON.\n\n"
                "Format:\n"
                "[\n  {\n    \"ai\": [ ... ],\n    \"dependencies\": [ ... ]\n  }, ... ]\n\n"
                f"ci list:\n{json.dumps(ci_no_attention, indent=2)}\n"
            )
            print(f"[DEBUG] Phase 2: Calling LLM for all {len(ci_no_attention)} ci at once")
            try:
                phase2_response = litellm.completion(
                    model=llm_model,
                    messages=[{"role": "user", "content": phase2_prompt}],
                    max_tokens=2048,
                    temperature=0.2,
                )
                ai_json = phase2_response["choices"][0]["message"]["content"]
                print(f"[DEBUG] LLM raw output (Phase 2, all ci): {ai_json!r}")
                # Try to extract JSON from code block if present
                match = re.search(r"```json\\s*(.*?)```", ai_json, re.DOTALL)
                if match:
                    ai_json = match.group(1)
                else:
                    # Try to extract the first JSON array in the string
                    start = ai_json.find('[')
                    end = ai_json.rfind(']')
                    if start != -1 and end != -1 and end > start:
                        ai_json = ai_json[start:end+1]
                def clean_json_string(s):
                    s = re.sub(r',\s*([}\]])', r'\1', s)
                    return s.strip()
                ai_json_clean = clean_json_string(ai_json)
                def auto_close_json(s):
                    open_braces = s.count('{')
                    close_braces = s.count('}')
                    if open_braces > close_braces:
                        print(f"[WARN] Auto-closing JSON for all ci: adding {open_braces - close_braces} '}}'")
                    s += '}' * (open_braces - close_braces)
                    return s
                ai_json_closed = auto_close_json(ai_json_clean)
                try:
                    phase2_results = json.loads(ai_json_closed)
                    print(f"[DEBUG] Successfully parsed JSON for all ci in Phase 2")
                except Exception as e:
                    print(f"[ERROR] JSON parsing failed for all ci: {e}\n[DEBUG] Cleaned+Closed JSON string: {ai_json_closed!r}")
                    phase2_results = []
            except Exception as e:
                print(f"[ERROR] LLM Phase 2 failed for all ci: {e}")
                phase2_results = []
        else:
            phase2_results = []
        # phase2_results is the list of processed ci objects
        ai_list = phase2_results if phase2_results else ci_list
        print("[DEBUG] Successfully retrieved and processed recipe.")
        return ai_list
    except Exception as e:
        print(f"[ERROR] Unexpected error in retrieve_recipe_from_url: {e}")
        return False
