from playwright.sync_api import sync_playwright
import json

url = "https://maimai.shiftpsh.com/en/profile/kalta/records/"

def scrape_data(page):
    # scroll loop
    for _ in range(50): 
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(500)

    row_selector = "tr.chakra-table__row"
    page.wait_for_selector(row_selector, timeout=10000)
    
    elements = page.locator(row_selector).all()
    data = []

    for el in elements:
        text = el.inner_text()
        if text.strip():
            items = [line.strip() for line in text.split("\n") if line.strip()]
            data.append(items)
    return data

def sort_data(data):
    clean_data = []
    for row in data:
        head = row[0].split("\t")
    
        # length 4 has rank number. length 3 lacks it.
        if len(head) == 4:
            level = head[1]
            chart_type = head[2]
            title = head[3]
        else:
            level = head[0]
            chart_type = head[1]
            title = head[2]
            
        score_rank = row[1]
        
        # middle elements. handles missing combo/sync badges.
        raw_badges = row[2:-1] 
        allowed = {"FC", "FC+", "AP", "AP+"}
        badges = [b for b in raw_badges if b in allowed]
        
        # split last string by tab
        tail = row[-1].split("\t")
        rating = tail[0]
        percent = tail[1]
        
        clean_data.append({
            "title": title,
            "level": level,
            "type": chart_type,
            "score_rank": score_rank,
            "badges": badges,
            "rating": rating,
            "percent": percent
        })
    return clean_data

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False) 
    page = browser.new_page()
    page.goto(url)
    page.wait_for_load_state("networkidle")
    
    page.locator("button:has(svg.tabler-icon-list)").click()

    page.locator("button:has-text('MAS')").click()
    
    # wait for UI update
    page.wait_for_timeout(2000)

    print(f"Loading Master...")
    data = scrape_data(page)
    print(f"Loaded {len(data)} scores for Master Difficulty.")

    # save separate file per difficulty
    with open(f"master.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    page.locator("button:has-text('MAS')").click()
    page.wait_for_timeout(1000)
    page.locator("button:has-text('Re:M')").click()
    page.wait_for_timeout(2000)

    print(f"Loading Re:Master...")
    data = scrape_data(page)
    print(f"Loaded {len(data)} scores for Re:Master Difficulty.")

    # save separate file per difficulty
    with open(f"remaster.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    browser.close()