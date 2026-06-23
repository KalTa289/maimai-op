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

def clean_and_save(data, diff):
    clean_data = []
    for row in data:
        # skip empty arrays
        if not row:
            continue
            
        head = row[0].split("\t")
        tail = row[-1].split("\t")

        score_rank = row[1]
        raw_badges = row[2:-1] 
        allowed = {"FC", "FC+", "AP", "AP+"}
        badges = [b for b in raw_badges if b in allowed]
        rating = tail[0]
        percent = tail[1]
    
        # handle unexpected row format
        if len(head) < 3:
            if head[0] == "12.8":
                clean_data.append({
                    "title": "Kisaragi",
                    "level": head[0],
                    "type": head[1],
                    "score_rank": score_rank,
                    "badges": badges,
                    "rating": rating,
                    "percent": percent
                })
                print(f"Kisaragi handled correctly.")
                continue
            else:
                print(f"Skipped bad head: {row}")
                continue
        elif len(head) == 4:
            level = head[1]
            chart_type = head[2]
            title = head[3]
        else:
            level = head[0]
            chart_type = head[1]
            title = head[2]
            
        # require at least 3 items in row (head, rank, tail)
        if len(row) < 3:
            print(f"Skipped short row: {row}")
            continue
        
        # handle unexpected tail format
        if "\t" not in row[-1]:
            print(f"Skipped bad tail: {row}")
            continue
        
        clean_data.append({
            "title": title,
            "level": level,
            "type": chart_type,
            "score_rank": score_rank,
            "badges": badges,
            "rating": rating,
            "percent": percent
        })
        
    with open(f"{diff}.json", "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=2, ensure_ascii=False)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False) 
    page = browser.new_page()
    page.goto(url)
    page.wait_for_load_state("networkidle")
    
    page.locator("button:has(svg.tabler-icon-list)").click()

    page.locator("button:has-text('MAS')").click()
    page.wait_for_timeout(2000)

    print("Loading Master...")
    raw_data = scrape_data(page)
    print(f"Loaded {len(raw_data)} scores.")
    clean_and_save(raw_data, "master")
    
    page.locator("button:has-text('MAS')").click()
    page.wait_for_timeout(1000)
    page.locator("button:has-text('Re:M')").click()
    page.wait_for_timeout(2000)

    print("Loading Re:Master...")
    raw_data = scrape_data(page)
    print(f"Loaded {len(raw_data)} scores.")
    clean_and_save(raw_data, "remaster")

    browser.close()