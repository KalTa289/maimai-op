from playwright.sync_api import sync_playwright
import json

def scrape_data(page):
    print("Scraping data...")

    # scroll loop
    for _ in range(30): 
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

    print(f"Scraped {len(data)} rows of data.")
    return data

def clean_and_save(data, diff):
    print(f"Cleaning and saving {diff} data...")

    clean_data = []
    allowed_badges = {"FC", "FC+", "AP", "AP+"}
    for row in data:
        # skip empty arrays
        if not row:
            print("Skipped empty row")
            continue
            
        head = row[0].split("\t")
        # handle unexpected row format
        if len(head) < 3:
            if head[0] == "12.8" or head[1] == "12.8":
                title = "Kisaragi"
                print(f"Kisaragi handled correctly.")
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
        if "%" not in row[-1] or "\t" not in row[-1]:
            played = False
        elif row[-1]:
            tail = row[-1].split("\t")
            rating = tail[0]
            percent = tail[1]
            raw_badges = row[2:-1]
            lamps = [b for b in raw_badges if b in allowed_badges]
            lamp = lamps[0] if lamps else None
            played = True
        else:
            played = False
        
        clean_data.append(
            {
            "title": title,
            "level": level,
            "type": chart_type,
            "played": played,
            "lamp": lamp,
            "rating": rating,
            "percent": percent
            } if played else {
            "title": title,
            "level": level,
            "type": chart_type,
            "played": played,
            }
        )
        
    with open(f"{diff}.json", "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=2, ensure_ascii=False)

    print(f"Finished saving {diff} data.")
    return None

def determine_diff(master_list, remaster_dict):
    print("Generating chart difficulty keys...")

    keys = []
    for chart in master_list:
        title = chart["title"]
        master_level = float(chart["level"])
        # default to master
        diff = "master"
        # compare if remaster exists
        if title in remaster_dict:
            remaster_level = float(remaster_dict[title]["level"])
            if remaster_level >= master_level:
                diff = "remaster"
        keys.append({
            "title": title,
            "difficulty": diff
        })

    print("Chart difficulty keys generated.")
    return keys

def calc_max_op(title, difficulty, master_dict, remaster_dict):
    max_op = 0.0
    if difficulty == "master":
        level = float(master_dict[title]["level"])
    elif difficulty == "remaster":
        level = float(remaster_dict[title]["level"])
    max_op = (level + 3.0) * 5.0
    return max_op

def calc_op(title, difficulty, master_dict, remaster_dict):
    combo_bonus = 0.0
    op = 0.0
    if difficulty == "master":
        if master_dict[title]["played"] == False:
            return op
        else:
            level = float(master_dict[title]["level"])
            lamp = master_dict[title]["lamp"]
            rating = float(master_dict[title]["rating"])/20
            score = float(master_dict[title]["percent"].strip("%"))
    elif difficulty == "remaster":
        if remaster_dict[title]["played"] == False:
            return op
        else:
            level = float(remaster_dict[title]["level"])
            lamp = remaster_dict[title]["lamp"]
            rating = float(remaster_dict[title]["rating"])/20
            score = float(remaster_dict[title]["percent"].strip("%"))

    match lamp:
            case "FC":
                combo_bonus = 0.5
            case "FC+":
                combo_bonus = 0.75
            case "AP":
                combo_bonus = 1.0
            case "AP+":
                combo_bonus = 1.25
    if 97.0000 <= score <= 100.0000: #S~SSS
        op = rating * 5.0 + combo_bonus
    elif score > 100.0000: #SSS~AP+
        score_bonus = (score - 100.0000) * 3.75
        op = (level + 2.0) * 5.0 + combo_bonus + score_bonus
    else: #D~AAA
        op = 0

    return op

url = "https://maimai.shiftpsh.com/en/profile/genz/records/"
total_op = 0.0
total_max_op = 0.0

#Main scraping and processing logic
with sync_playwright() as p:
    print("Beginning scraping...")

    browser = p.chromium.launch(headless=False) 
    page = browser.new_page()
    page.goto(url)
    page.wait_for_load_state("networkidle")
    
    page.locator("button:has(svg.tabler-icon-list)").click()

    page.locator("button:has-text('MAS')").click()
    page.wait_for_timeout(2000)

    print("Fetching Master Scores...")
    raw_data = scrape_data(page)
    print(f"Fetched {len(raw_data)} scores.")
    clean_and_save(raw_data, "master")
    
    page.locator("button:has-text('MAS')").click()
    page.wait_for_timeout(1000)
    page.locator("button:has-text('Re:M')").click()
    page.wait_for_timeout(2000)

    print("Fetching Re:Master Scores...")
    raw_data = scrape_data(page)
    print(f"Fetched {len(raw_data)} scores.")
    clean_and_save(raw_data, "remaster")

    browser.close()
    print("Scraping complete.")

with open("master.json", "r", encoding="utf-8") as f:
    master_data = json.load(f)
master_dict = {item["title"]: item for item in master_data}

with open("remaster.json", "r", encoding="utf-8") as f:
    remaster_data = json.load(f)
remaster_dict = {item["title"]: item for item in remaster_data}

for chart in determine_diff(master_data, remaster_dict):
    max_op = calc_max_op(chart["title"], chart["difficulty"], master_dict, remaster_dict)
    op = calc_op(chart["title"], chart["difficulty"], master_dict, remaster_dict)
    total_max_op += max_op
    total_op += op
print(f"Total OP: {round(total_op, 2)}, Total Max OP: {round(total_max_op, 2)}, OP % = {round((total_op / total_max_op) * 100, 2)}%")