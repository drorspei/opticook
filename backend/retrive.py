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
    #print("soup=",soup)
    return soup

# === 2. Get the JSON data using BeautifulSoup ===
def get_yoast_jsonld(soup):
    script = soup.find("script", class_="yoast-schema-graph", type="application/ld+json")
    if script is not None:
        print("script=",script)
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
        #print("[DEBUG] Step 2: Extracting JSON-LD data")
        #jsonld = get_yoast_jsonld(soup)
        #if not jsonld:
        #    print("[ERROR] Failed to extract JSON-LD data.")
        #    return False
        #print("[DEBUG] Step 3: Finding recipe object in JSON-LD")
        #recipe_obj = find_recipe_object(jsonld)
        #if not recipe_obj:
        #    print("[ERROR] Failed to find recipe object in JSON-LD.")
            #print("jsonld=",jsonld)

        #   return False
        
        # Phase 1: LLM to extract ci steps
        print("[DEBUG] Step 1.5: formulating phase 1 promot")
        phase1_prompt = f"""
You are given a BeautifulSoup object extracted from an html that contains a cooking recipe. 
Locate and extract the cooking instructions in the soup. \n
Then decompose the main cooking steps as a list of \"ci\" (CookingInstruction) 
objects.\nEach \"ci\" is a dictionary with three fields:\n

(1) An "index" field (with counting indices 0,1,2,...)\n
(2) A list called "aiList" consisting smaller tasks called \"ai\" (AtomicInstruction) steps, each is a 
dicrionary with fields: 
  (2.1) "description" (short, clear, imperative),
  (2.2) "duration_seconds" (estimate in seconds), 
  (2.3) "attention" (true if the cook must actively attend, false if it can be left alone. For example 
  "bake for 40 minutes" needs no attention.)\n

(3) A list called "dependencies", consisting of indices of other ci that must be completed first)\n\n
Reply with a JSON object consisting of the list of ci dictionaries called "ciList".
  \n\nHere is the JSON-LD recipe data:\n{soup}\n"""

        print("[DEBUG] Step 2: Calling LLM for Phase 1 (ci extraction)")
        try:
            phase1_response = litellm.completion(
                model=llm_model,
                messages=[{"role": "user", "content": phase1_prompt}],
                max_tokens=2048,
                temperature=0.2,
                **({"api_key": api_key} if api_key else {})
            )
            ci_list = json.loads(phase1_response.choices[0].message.content)['ciList']
            print(f"phase 1 is of type {type(ci_list)} and consists of json = {ci_list}")
        except Exception as e:
                    # print stack
                    print(f"[DEBUG] Error occurred while processing AI step 1: {e}")
                    print(traceback.format_exc())

                  
            #ci_json = phase1_response["choices"][0]["message"]["content"]
            #print(f"[DEBUG] LLM raw output (Phase 1): {ci_json!r}")
            # Try to extract JSON from code block if present
            
        
        #except Exception as e:
        #    print(f"[ERROR] LLM Phase 1 failed: {e}")
        #    return False

        # Filter ci_list to only those where all ai have attention == false
        ci_no_attention = []
        for i, ci in enumerate(ci_list):
            if all(ai.get('attention') == False for ai in ci.get('aiList', [])):
                ci_no_attention.append((i, ci))
        #print(f"[DEBUG] Passing {len(ci_no_attention)} ci with no attention to Phase 2 LLM")

        for i, ci in enumerate(ci_list):
            pos = 0
            ais = ci.get("aiList", [])
            while pos < len(ais):
                ai = ais[pos]
                pos += 1
                if ai.get('attention', True):
                    continue
                print(f"[DEBUG] Passing ai {ai} to Phase 2 LLM")
                # --- Phase 2: LLM breakdown of ai steps, all at once ---
                # We want to break each non-attention ai step into 3 parts: init with attention, main w/o attention, short final with attenion

                prompt = f'''Given the following cooking instruction, which mostly doesn't require the chef's attention (e.g. "bake for 40 minutes"), break it down into two steps:
    a short initialization step with a single verb (e.g. place in the the oven), and a main part that requires no attention that uses a passive verb (e.g. let it bake for 40 minutes).
    Use the object of the original sentence in both steps.
    Reply with a JSON object with the two fields "initialization", "main".
    Here is the sentence:
    {ai.get('description','')}'''
                try:
                    resp = litellm.completion(
                        model=llm_model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=2048,
                        temperature=0.2,
                        **({"api_key": api_key} if api_key else {})
                    )
                    j = json.loads(resp.choices[0].message.content.replace("```json", "```").split("```", 1)[-1].split("```", 1)[0])
                    print(f"Second phase result has type {type(j)} and is {j}")
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
