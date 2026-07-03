from playwright.sync_api import sync_playwright
import json
from lib import *

username = "kalta"  # input("Enter the username: ")

with sync_playwright() as p:
    print("Beginning scraping...")

    browser = p.chromium.launch(headless=False) 
    page = browser.new_page()

    for diff in ["MASTER", "RE_MASTER"]:
        print(f"Fetching {diff} Scores...")
        page.goto(f"https://maimai.shiftpsh.com/en/profile/{username}/records?difficulty={diff}&sort=rating&order=desc&n=false")
        page.wait_for_load_state("networkidle")
        page.locator("button:has(svg.tabler-icon-list)").click()
        page.wait_for_timeout(2000)
        data = scrape_data(page)
        clean_data_list = clean_data(data)
        with open(f"{diff}.json", "w", encoding="utf-8") as f:
            json.dump(clean_data_list, f, indent=2, ensure_ascii=False)

    browser.close()
    print("Scraping complete.")