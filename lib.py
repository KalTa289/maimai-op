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

def clean_data(data):
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

    return clean_data

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